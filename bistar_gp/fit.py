"""
Fitting routines: MAP via marginal likelihood, simple MCMC for full Bayesian.
"""

import torch
import gpytorch
import numpy as np
from typing import Dict
from functools import partial
import logging

logger = logging.getLogger(__name__)
torch.set_default_dtype(torch.float64)
DEFAULT_JITTER = 1e-4


def fit_map(model, likelihood, train_x, train_y, n_iter=500, lr=0.05, verbose=True, print_every=50):
    """MAP estimation via Adam + marginal likelihood. Returns loss history."""
    train_x, train_y = train_x.double(), train_y.double()
    model.train()
    likelihood.train()

    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    mll = gpytorch.mlls.ExactMarginalLogLikelihood(likelihood, model)
    losses = []

    for i in range(n_iter):
        optimizer.zero_grad()
        with gpytorch.settings.cholesky_jitter(DEFAULT_JITTER):
            try:
                output = model(train_x)
                loss = -mll(output, train_y)
                loss.backward()
                optimizer.step()
                losses.append(loss.item())
            except RuntimeError as e:
                if "cholesky" in str(e).lower():
                    logger.warning(f"Cholesky error at iter {i}, skipping")
                    continue
                raise

        if verbose and (i + 1) % print_every == 0:
            print(f"  Iter {i+1}/{n_iter} — Loss: {losses[-1]:.4f}")

    model.eval()
    likelihood.eval()
    return losses


def print_hyperparameters(model, likelihood):
    """Pretty-print fitted hyperparameters."""
    print("\n── Hyperparameters ──")
    print(f"  Noise variance: {likelihood.noise.item():.6f}")
    for name, kernel in zip(model.component_names, model.kernel_components):
        print(f"  [{name}]")
        for pname, param, constraint in kernel.named_parameters_and_constraints():
            if constraint is not None:
                print(f"    {pname}: {constraint.transform(param).item():.6f}")
            else:
                print(f"    {pname}: {param.item():.6f}")
    print()


def fit_mcmc_simple(model, likelihood, train_x, train_y,
                    n_samples=10000, n_burnin=1000, proposal_scale=0.1, verbose=True,
                    seed=None):
    """
    Random-walk Metropolis-Hastings over log hyperparameters.
    For production use NumPyro — this is a starting point.
    Returns dict of parameter name -> posterior samples array.
    Pass seed for a reproducible chain (seeds both torch and numpy RNGs).
    """
    if seed is not None:
        torch.manual_seed(seed)
        np.random.seed(seed)
    train_x, train_y = train_x.double(), train_y.double()
    mll = gpytorch.mlls.ExactMarginalLogLikelihood(likelihood, model)

    # Collect raw parameters. The likelihood is a submodule of ExactGP, so its
    # parameters already appear in model.named_parameters(); dedupe by object
    # identity so the noise is one proposal dimension, not two aliases.
    seen = set()
    param_list = []
    for n, p in list(model.named_parameters()) + list(likelihood.named_parameters()):
        if p.requires_grad and p.numel() == 1 and id(p) not in seen:
            seen.add(id(p))
            param_list.append((n, p))
    param_names = [n for n, _ in param_list]

    def get_params():
        return torch.stack([p.data.clone().squeeze() for _, p in param_list])
        
    def set_params(vals):
        for idx, (_, p) in enumerate(param_list):
            p.data.copy_(vals[idx])

    def log_posterior():
        try:
            return _mh_log_joint(mll, model, likelihood, train_x, train_y)
        except RuntimeError:
            return -float("inf")

    current = get_params()
    current_lp = log_posterior()
    samples = {n: [] for n in param_names}
    n_accepted = 0
    total = n_samples + n_burnin

    for i in range(total):
        proposal = current + proposal_scale * torch.randn_like(current)
        set_params(proposal)
        proposed_lp = log_posterior()

        if np.log(np.random.rand()) < (proposed_lp - current_lp):
            current = proposal
            current_lp = proposed_lp
            n_accepted += 1
        else:
            set_params(current)

        if i >= n_burnin:
            vals = get_params()
            for j, n in enumerate(param_names):
                samples[n].append(vals[j].item())

        if verbose and (i + 1) % 2000 == 0:
            print(f"  MCMC {i+1}/{total} — accept rate: {n_accepted/(i+1):.3f}")

    if verbose:
        print(f"  Final acceptance rate: {n_accepted/total:.3f}")

    model.eval()
    likelihood.eval()

    return {k: np.array(v) for k, v in samples.items()}


def _mh_log_joint(mll, model, likelihood, train_x, train_y):
    """Un-normalized summed log joint log p(y|θ) + log p(θ): the MH target.

    Forces train mode on every call: in eval mode model(train_x) returns the
    posterior predictive conditioned on train_y, so scoring train_y against it
    uses the data twice and biases the target toward small-noise/overfit
    hyperparameters (it can also reuse a stale prediction cache after in-place
    parameter writes). gpytorch's ExactMarginalLogLikelihood averages the log
    joint per datum; multiplying by n recovers the summed log joint, the
    correct un-normalized log posterior to sample.
    """
    model.train()
    likelihood.train()
    with gpytorch.settings.cholesky_jitter(DEFAULT_JITTER):
        return (mll(model(train_x), train_y) * train_y.numel()).item()


def _hmc_pyro_model(model, x, y):
    """Pyro NUTS target for fit_hmc: sample every prior once, score y through
    the SAMPLED module.

    gpytorch's model.pyro_sample_from_prior() deep-copies the model, applies the
    sampled hyperparameters to the COPY, and RETURNS it — the original `model` is
    left unchanged. The obs likelihood must therefore be evaluated through the
    returned `sampled` module; scoring the original `model(x)` instead leaves the
    data independent of the latents, so NUTS samples the prior, not the posterior
    (every returned "posterior" draw would just be a prior draw). The likelihood
    is an ExactGP submodule, so `sampled.likelihood` carries the sampled noise and
    each hyperparameter latent — the kernel sites "covar_module.kernels.{i}.*_prior"
    plus "likelihood.noise_covar.noise_prior" — is emitted exactly once.
    """
    import pyro

    sampled = model.pyro_sample_from_prior()
    output = sampled(x)
    with pyro.plate("data", y.shape[0]):
        pyro.sample("obs", sampled.likelihood(output), obs=y)


def fit_hmc(model, likelihood, train_x, train_y,
            n_samples=500, n_warmup=200, verbose=True, seed=None,
            init_to_map=True, max_tree_depth=10):
    """
    Hamiltonian Monte Carlo via Pyro's NUTS sampler.

    This is the production-grade sampler — uses gradients to explore
    the posterior efficiently, unlike random-walk MH.

    init_to_map: start each latent at the model's CURRENT constrained hyperparameter
        value instead of a random prior draw. Pass a MAP-fitted model (run fit_map
        first) so the chain begins in the typical set. The GP hyperparameter posterior
        has a funnel (as the noise variance → 0 the marginal likelihood becomes a stiff
        ridge); a random prior init can land in it, collapsing the NUTS step size toward
        ~1e-7 and saturating the tree depth (each iteration then costs ~2^max_tree_depth
        Cholesky solves). Sites are matched by named_priors() name, which equals the pyro
        sample-site name (verified). init_to_map=False falls back to init_to_sample.
    max_tree_depth: NUTS leapfrog-tree-depth cap (default 10 = pyro default, up to 1023
        steps). Lower it (6–8) for stiff posteriors to bound per-iteration cost.

    Returns dict of parameter name -> numpy array of posterior samples.
    """
    import pyro
    from pyro.infer.mcmc import NUTS, MCMC
    from pyro.infer.autoguide.initialization import init_to_value, init_to_sample
    from functools import partial

    if seed is not None:
        pyro.set_rng_seed(seed)

    train_x, train_y = train_x.double(), train_y.double()
    model.train()
    likelihood.train()

    # Clear any previous pyro state
    pyro.clear_param_store()

    if init_to_map:
        try:
            init_strategy = init_to_value(values=_map_init_values(model))
        except ValueError as e:
            logger.warning("init_to_map: %s; falling back to init_to_sample", e)
            init_strategy = init_to_sample
    else:
        init_strategy = init_to_sample

    nuts = NUTS(
        partial(_hmc_pyro_model, model),
        jit_compile=False,
        step_size=0.1,
        adapt_step_size=True,
        target_accept_prob=0.8,
        max_tree_depth=max_tree_depth,
        init_strategy=init_strategy,
    )

    mcmc_run = MCMC(
        nuts,
        num_samples=n_samples,
        warmup_steps=n_warmup,
        disable_progbar=(not verbose),
    )

    with gpytorch.settings.cholesky_jitter(DEFAULT_JITTER):
        mcmc_run.run(train_x, train_y)

    # Extract samples as numpy arrays. reshape(-1), NOT squeeze(): with
    # n_samples=1 squeeze collapses (1, ...) to a 0-d array, breaking the
    # documented (n,) schema that downstream consumers rely on.
    raw_samples = mcmc_run.get_samples()
    samples = {k: v.reshape(-1).numpy() for k, v in raw_samples.items()}

    if verbose:
        mcmc_run.summary()

    model.eval()
    likelihood.eval()

    return samples


def _map_init_values(model):
    """{sample-site name: current constrained hyperparameter value} for a model,
    guarded against boundary values — the SINGLE authority for MAP-init dicts
    (fit_hmc, fit_vi, fit_hmc_laplace, fit_map_samples all use it).

    named_priors() yields (name, module, prior, closure, setting_closure); the
    name equals the pyro sample-site name and closure(module) the constrained
    value. Pyro initializes in unconstrained space via biject_to(support).inv,
    and a boundary value — e.g. a hyperparameter that underflowed to exactly 0 —
    can be INSIDE a closed support like GreaterThanEq(0) yet map to -inf,
    aborting initialization ("cannot find valid initial params" for NUTS, an
    invalid guide loc for SVI). So the predicate is finiteness of the
    unconstrained image, not support membership; boundary values are nudged
    into the interior, and a value that is still invalid after clamping raises
    ValueError (callers may fall back to init_to_sample).
    """
    from torch.distributions import biject_to

    init_values = {}
    for entry in model.named_priors():
        name, prior, value = entry[0], entry[2], entry[3](entry[1]).detach()
        if not torch.isfinite(biject_to(prior.support).inv(value)).all():
            value = value.clamp(min=1e-8)
        if not torch.isfinite(biject_to(prior.support).inv(value)).all():
            raise ValueError(
                f"{name} is outside its prior support even after clamping")
        init_values[name] = value
    return init_values


def fit_vi(model, likelihood, train_x, train_y,
           n_samples=500, n_steps=2000, lr=0.01, verbose=True, seed=None):
    """Variational inference over the GP hyperparameter posterior (pyro SVI,
    multivariate-normal guide), returning the fit_hmc dict schema.

    The thesis chapter's PRIMARY implementation was VI (Appendix II: results
    "were based on variational inference", gpflow/ADVI, cross-checked against
    HMC with "similar" results). The guide is a full-covariance Gaussian in
    unconstrained space (ADVI-style), initialized at the model's current
    (MAP-fitted) hyperparameters. VI avoids the stiff-funnel NUTS pathology
    (D8) — optimization has no step-size collapse — at the price of a Gaussian
    approximation whose adequacy in that funnel must itself be checked.
    """
    import pyro
    from pyro.infer import SVI, Trace_ELBO
    from pyro.infer.autoguide import AutoMultivariateNormal
    from pyro.infer.autoguide.initialization import init_to_value
    from pyro.optim import Adam

    if seed is not None:
        pyro.set_rng_seed(seed)

    train_x, train_y = train_x.double(), train_y.double()
    model.train()
    likelihood.train()
    pyro.clear_param_store()

    model_fn = partial(_hmc_pyro_model, model)
    guide = AutoMultivariateNormal(
        model_fn, init_loc_fn=init_to_value(values=_map_init_values(model)))
    svi = SVI(model_fn, guide, Adam({"lr": lr}), Trace_ELBO())

    with gpytorch.settings.cholesky_jitter(DEFAULT_JITTER):
        for step in range(n_steps):
            loss = svi.step(train_x, train_y)
            if verbose and (step + 1) % max(1, n_steps // 5) == 0:
                print(f"  SVI {step + 1}/{n_steps} — ELBO loss: {loss:.2f}")

    collected = {}
    with torch.no_grad():
        for _ in range(n_samples):
            draw = guide(train_x, train_y)   # {site: constrained value}
            for name, value in draw.items():
                collected.setdefault(name, []).append(float(value.detach()))

    model.eval()
    likelihood.eval()
    return {k: np.array(v) for k, v in collected.items()}


def fit_map_samples(model, likelihood, train_x, train_y,
                    n_iter=500, lr=0.05, verbose=False):
    """MAP/MMLE point estimate in the fit_hmc dict schema (length-1 arrays).

    The thesis chapter's explicitly-contrasted simpler alternative (Fig. 6
    "best fitting" vs Fig. 7a full Bayes): a single GP instance at the
    maximum-marginal-likelihood hyperparameters. Returning the shared schema
    lets the degenerate "posterior" flow through extract_gp_predictives /
    BMS* / decomposition unchanged — the predictive is then the familiar
    single-GP posterior predictive, with no hyperparameter uncertainty.
    """
    fit_map(model, likelihood, train_x, train_y, n_iter=n_iter, lr=lr,
            verbose=verbose)
    return {name: np.array([float(value)])
            for name, value in _map_init_values(model).items()}


def fit_hmc_laplace(model, likelihood, train_x, train_y,
                    n_samples=500, n_warmup=200, verbose=True, seed=None,
                    max_tree_depth=10):
    """NUTS on the Laplace-whitened posterior (preconditioned HMC).

    Computes the Hessian H of the negative log joint at the MAP in
    UNCONSTRAINED space and runs NUTS on z, where u = u_map + A z with
    A = chol(H^{-1}) — i.e. the posterior is approximately N(0, I) in z.
    A linear reparameterization is mathematically identical to running HMC
    with mass matrix H, so this delivers "Laplace-preconditioned NUTS" and
    "linear reparameterization" as one option. Pass a MAP-fitted model.
    Falls back to identity whitening (plain unconstrained NUTS) if the
    Hessian is not usable. Returns the fit_hmc dict schema.
    """
    import pyro
    from pyro.infer.mcmc import NUTS, MCMC
    from pyro.infer.mcmc.util import initialize_model
    from pyro.infer.autoguide.initialization import init_to_value

    if seed is not None:
        pyro.set_rng_seed(seed)

    train_x, train_y = train_x.double(), train_y.double()
    model.train()
    likelihood.train()
    pyro.clear_param_store()

    init_params, potential_fn, transforms, _ = initialize_model(
        partial(_hmc_pyro_model, model), model_args=(train_x, train_y),
        init_strategy=init_to_value(values=_map_init_values(model)))

    # Flatten the unconstrained site dict into one vector u.
    sites = sorted(init_params)
    shapes = {s: init_params[s].reshape(-1).shape[0] for s in sites}
    u_map = torch.cat([init_params[s].reshape(-1).double() for s in sites])

    def unflatten(u):
        out, i = {}, 0
        for s in sites:
            n = shapes[s]
            out[s] = u[i:i + n].reshape(init_params[s].shape)
            i += n
        return out

    def potential_u(u):
        with gpytorch.settings.cholesky_jitter(DEFAULT_JITTER):
            return potential_fn(unflatten(u))

    # Laplace whitening matrix A = chol(H^{-1}) from the MAP Hessian
    # (eigenvalue floor keeps a flat/negative direction from breaking chol).
    try:
        H = torch.autograd.functional.hessian(potential_u, u_map)
        H = 0.5 * (H + H.T)
        eigval, eigvec = torch.linalg.eigh(H)
        eigval = eigval.clamp(min=1e-6)
        A = eigvec @ torch.diag(eigval.rsqrt())   # H^{-1} = A A^T
    except Exception as e:
        logger.warning("fit_hmc_laplace: Hessian failed (%s); identity whitening", e)
        A = torch.eye(len(u_map), dtype=torch.float64)

    def potential_z(z_dict):
        return potential_u(u_map + A @ z_dict["z"])

    z0 = {"z": torch.zeros(len(u_map), dtype=torch.float64)}
    nuts = NUTS(potential_fn=potential_z, jit_compile=False, step_size=0.1,
                adapt_step_size=True, target_accept_prob=0.8,
                max_tree_depth=max_tree_depth)
    mcmc_run = MCMC(nuts, num_samples=n_samples, warmup_steps=n_warmup,
                    initial_params=z0, disable_progbar=(not verbose))
    with gpytorch.settings.cholesky_jitter(DEFAULT_JITTER):
        mcmc_run.run()

    z_draws = mcmc_run.get_samples()["z"]              # (n_samples, d)
    u_draws = u_map.unsqueeze(0) + z_draws @ A.T        # back to unconstrained u
    out = {}
    for j, s in enumerate(sites):                       # constrained via transforms
        col = u_draws[:, sum(shapes[t] for t in sites[:j]):
                      sum(shapes[t] for t in sites[:j]) + shapes[s]]
        out[s] = transforms[s].inv(col.squeeze(-1)).detach().numpy().reshape(-1)

    model.eval()
    likelihood.eval()
    return out


GP_INFERENCE_METHODS = ("hmc", "vi", "map", "hmc_laplace")


def fit_gp(model, likelihood, train_x, train_y, method="hmc", **kwargs):
    """One entry point for the GP hyperparameter-inference options (D9).

    All methods return the SAME dict schema (site name -> (n,) array), so any
    choice flows through extract_gp_predictives / BMS* / decomposition
    unchanged and results are directly comparable across methods.

      "hmc"          full-Bayes NUTS (default; thesis-equivalent — the chapter
                     validated HMC against its primary VI implementation).
                     Accepts fit_hmc kwargs (init_to_map, max_tree_depth, ...).
      "vi"           ADVI-style SVI, the thesis chapter's PRIMARY
                     implementation (Appendix II); no NUTS-style step-size
                     pathology, but a Gaussian posterior approximation.
      "map"          MAP/MMLE point estimate (thesis Fig. 6 contrast);
                     length-1 arrays, no hyperparameter uncertainty.
      "hmc_laplace"  NUTS on the Laplace-whitened posterior (== MAP-Hessian
                     mass-matrix preconditioning == linear reparameterization).

    Defaults follow the thesis chapter (full-Bayes sampling; see
    docs/inference-and-metric-options.md for the justification writeup).
    Except for "map", pass a MAP-fitted model so initialization starts in the
    typical set (run fit_map first).
    """
    dispatch = {
        "hmc": fit_hmc,
        "vi": fit_vi,
        "map": fit_map_samples,
        "hmc_laplace": fit_hmc_laplace,
    }
    if method not in dispatch:
        raise ValueError(f"unknown method {method!r}; one of {GP_INFERENCE_METHODS}")
    return dispatch[method](model, likelihood, train_x, train_y, **kwargs)


def sample_prior(model, n_samples=500, seed=None):
    """Draw i.i.d. hyperparameter samples from the GP priors — no data, no MCMC.

    Prior sampling needs no NUTS: the registered priors are known distributions,
    so we draw directly and exactly by tracing model.pyro_sample_from_prior().
    Returns the SAME dict schema as fit_hmc (site name -> (n_samples,) array), so
    prior draws flow through extract_gp_predictives(condition_on_data=False) and
    decompose_model_hmc for PRIOR predictive checks exactly as fit_hmc posterior
    draws feed the posterior predictive checks. Depends only on the priors, so it
    is independent of the model's train targets.
    """
    import pyro

    if seed is not None:
        pyro.set_rng_seed(seed)

    collected = {}
    for _ in range(n_samples):
        trace = pyro.poutine.trace(model.pyro_sample_from_prior).get_trace()
        for name, site in trace.nodes.items():
            if site["type"] == "sample" and not site.get("is_observed", False):
                collected.setdefault(name, []).append(float(site["value"].detach()))
    return {k: np.array(v) for k, v in collected.items()}
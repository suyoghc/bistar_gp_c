"""E1 direct-parameter potential (D19 M2b; plan §2 Stage B, prereg addendum v1.2).

The S1 pyro path (fit_hmc) pays a full model deep copy per potential
evaluation (`pyro_sample_from_prior()`), the measured ~200x per-leapfrog
overhead the D19 cost table records. E1 removes the copy while keeping the
target AND the coordinates bit-compatible with S1, so S1f ("adapted baseline
on E1") is S1 with cheap leapfrogs — not a reparameterization, which is the
S3 strategy under test and must stay there (addendum v1.2, point 1).

Coordinate convention (v1.2): the PUBLIC NUTS coordinates are the exact pyro
unconstrained sample-site coordinates returned by
`pyro.infer.mcmc.util.initialize_model` on the S1 target (`_hmc_pyro_model`)
— same site set, same site order, same support transforms. GPyTorch raw
parameters (softplus et al.) are an internal evaluation representation only;
they never define sampling coordinates, and no raw-space potential is ever
compared against the pyro potential except through the explicit coordinate
map and its change-of-variables Jacobian (v1.2, point 2).

Composition rule (v1.2, point 3): for a pyro-coordinate state u,

    potential(u) = -( log p(y | theta)                       [exactly once]
                    + sum_s log p_s(theta_s)                 [each prior once]
                    + sum_s log |d theta_s / d u_s| )        [each Jacobian once]

with theta_s = transforms[s].inv(u_s) via the oracle's own site transform.
The observation term is the summed `log_prob(y)` of the noise-added marginal
MVN, computed directly — never `ExactMarginalLogLikelihood`, which already
adds registered prior log-probs and divides by N, so composing it with an
explicit prior sum double-counts every prior and mis-scales the likelihood
(the D6 error class).

Evaluation path: theta maps into the corresponding gpytorch raw parameters
through each constraint's `inverse_transform` and the model is evaluated on
the SAME module via `torch.func.functional_call` — autograd flows u -> theta
-> raw -> K -> log_prob with no `.data` writes and no deep copy (v1.2,
point 1). The A10-frozen period is not a sample site, receives no override,
and is asserted frozen at build (v1.2, point 4).
"""

import logging

import torch
import gpytorch
import numpy as np

from .fit import DEFAULT_JITTER, _hmc_pyro_model, _map_init_values

logger = logging.getLogger(__name__)
torch.set_default_dtype(torch.float64)


class _JointModule(torch.nn.Module):
    """Marginal-likelihood evaluator: log p(y | theta) exactly once.

    The likelihood is an ExactGP submodule, so a single functional_call on
    this wrapper substitutes kernel hyperparameters and noise together (the
    override keys are "gp.<raw parameter fqname>").
    """

    def __init__(self, gp_model):
        super().__init__()
        self.gp = gp_model

    def forward(self, x, y):
        out = self.gp(x)                       # prior latent MVN (train mode)
        marginal = self.gp.likelihood(out)     # + noise: the observation marginal
        return marginal.log_prob(y)


def _site_parameter_map(model, sites):
    """{site name: (prior, raw fqname, constraint, raw shape)} with the v1.2
    duplicate-site/duplicate-prior inventory enforced structurally.

    named_priors() names equal the pyro sample-site names (the _map_init_values
    contract, test-verified); the raw parameter behind a prior on
    hyperparameter <hp> is the module's `raw_<hp>` with constraint
    `raw_<hp>_constraint`. Raises on: duplicate prior registrations (the D4
    double-registration class), site/prior set mismatch (a latent pyro sees
    but E1 would drop, or vice versa — the D6 class), two sites resolving to
    one raw parameter, and any period site (A10: the frozen period must not
    be sampled).
    """
    param_name_by_id = {id(p): n for n, p in model.named_parameters()}

    prior_entries = list(model.named_priors())
    prior_names = [e[0] for e in prior_entries]
    if len(prior_names) != len(set(prior_names)):
        dupes = sorted({n for n in prior_names if prior_names.count(n) > 1})
        raise RuntimeError(f"duplicate prior registrations: {dupes}")
    if set(prior_names) != set(sites):
        raise RuntimeError(
            "pyro site set and named_priors set disagree — a latent would be "
            f"dropped or invented: sites={sorted(sites)} "
            f"priors={sorted(prior_names)}")
    period_sites = [s for s in sites if "period" in s]
    if period_sites:
        raise RuntimeError(
            f"A10 violation: frozen period appears as a sample site: {period_sites}")

    site_map, seen_raw = {}, {}
    for name, module, prior, closure, _setting in prior_entries:
        attr = name.split(".")[-1]
        if not attr.endswith("_prior"):
            raise RuntimeError(f"unrecognized prior attribute name: {name}")
        hp = attr[: -len("_prior")]
        raw = getattr(module, "raw_" + hp, None)
        if raw is None:
            raise RuntimeError(
                f"site {name}: no raw parameter raw_{hp} on {type(module).__name__}")
        constraint = getattr(module, "raw_" + hp + "_constraint", None)
        fq = param_name_by_id.get(id(raw))
        if fq is None:
            raise RuntimeError(f"site {name}: raw_{hp} is not a model parameter")
        if fq in seen_raw:
            raise RuntimeError(
                f"two sites resolve to one raw parameter {fq}: "
                f"{seen_raw[fq]} and {name}")
        seen_raw[fq] = name
        site_map[name] = (prior, fq, constraint, raw.shape)
    return site_map


class E1Potential:
    """The E1 direct-parameter potential over S1's pyro coordinates.

    Attributes:
        sites: site names, in the exact order initialize_model produced them
            (the S1 order authority; v1.2 point 1).
        init_params: {site: unconstrained tensor} at the model's current
            (MAP-fitted) hyperparameters — MCMC initial_params material.
        transforms: the initialize_model site-transform dict (constrained to
            unconstrained; `.inv` recovers theta).
        oracle_potential_fn: pyro's own potential from initialize_model (the
            deep-copy path) — the equivalence-battery reference, never the
            sampling vehicle.
    """

    def __init__(self, model, likelihood, train_x, train_y, jitter=DEFAULT_JITTER):
        import pyro
        from functools import partial
        from pyro.infer.mcmc.util import initialize_model
        from pyro.infer.autoguide.initialization import init_to_value

        train_x, train_y = train_x.double(), train_y.double()
        self._model, self._likelihood = model, likelihood
        self._x, self._y = train_x, train_y
        self._jitter = jitter

        model.train()
        likelihood.train()
        pyro.clear_param_store()
        with gpytorch.settings.cholesky_jitter(jitter):
            init_params, potential_fn, transforms, _ = initialize_model(
                partial(_hmc_pyro_model, model), model_args=(train_x, train_y),
                init_strategy=init_to_value(values=_map_init_values(model)))

        self.sites = tuple(init_params)
        self.init_params = {s: v.detach().clone() for s, v in init_params.items()}
        self.transforms = transforms
        self._oracle_potential = potential_fn
        self._site_map = _site_parameter_map(model, self.sites)
        self._joint = _JointModule(model)

        # A10: any stamped frozen period must hold its target at build time,
        # and — receiving no override below — cannot move during evaluation.
        for mod_name, module in model.named_modules():
            target = getattr(module, "_a10_frozen_period", None)
            if target is not None:
                value = module.period_length.item()
                assert value == target, (
                    f"A10 violation at E1 build: {mod_name}.period_length = "
                    f"{value!r}, stamped freeze target {target!r}")

    # ── coordinate maps ──────────────────────────────────────────

    def constrain(self, u):
        """{site: theta} from a pyro-coordinate state, via the oracle's own
        transforms (v1.2 point 1)."""
        return {s: self.transforms[s].inv(u[s]) for s in self.sites}

    def unconstrain(self, theta):
        """{site: u} from constrained values — inverse of constrain()."""
        return {s: self.transforms[s](theta[s]) for s in self.sites}

    # ── the potential ────────────────────────────────────────────

    def components(self, u):
        """(log_marginal, log_prior, log_jacobian) at u, each term assembled
        exactly once (v1.2 point 3). Battery consumers test the pieces
        separately; potential_fn is their negative sum."""
        self._model.train()
        self._likelihood.train()
        overrides = {}
        log_prior = self._y.new_zeros(())
        log_jac = self._y.new_zeros(())
        for s in self.sites:
            t = self.transforms[s]
            theta = t.inv(u[s])
            prior, fq, constraint, shape = self._site_map[s]
            log_prior = log_prior + prior.log_prob(theta).sum()
            log_jac = log_jac + t.inv.log_abs_det_jacobian(u[s], theta).sum()
            raw = constraint.inverse_transform(theta) if constraint is not None else theta
            overrides["gp." + fq] = raw.reshape(shape)
        with gpytorch.settings.cholesky_jitter(self._jitter):
            log_marginal = torch.func.functional_call(
                self._joint, overrides, (self._x, self._y))
        return log_marginal, log_prior, log_jac

    def potential_fn(self, u):
        """-(log p(y|theta) + log p(theta) + log|dtheta/du|): equals the S1
        pyro potential on the same coordinates (battery-gated)."""
        log_marginal, log_prior, log_jac = self.components(u)
        return -(log_marginal + log_prior + log_jac)

    def oracle_potential_fn(self, u):
        """The initialize_model potential (deep-copy path) under the same
        jitter setting — the battery's reference target."""
        with gpytorch.settings.cholesky_jitter(self._jitter):
            return self._oracle_potential(u)


def build_e1_potential(model, likelihood, train_x, train_y, jitter=DEFAULT_JITTER):
    """Build the E1 potential for a MAP-fitted model. Returns E1Potential."""
    return E1Potential(model, likelihood, train_x, train_y, jitter=jitter)


def fit_hmc_e1(model, likelihood, train_x, train_y,
               n_samples=500, n_warmup=200, verbose=True, seed=None,
               max_tree_depth=10, return_diagnostics=False,
               jitter=DEFAULT_JITTER):
    """S1f: NUTS on the E1 potential — fit_hmc's sampler settings, statistically
    identical target and coordinates, no per-leapfrog deep copy.

    Mirrors fit_hmc exactly where the two share surface: MAP-init (pass a
    MAP-fitted model), step_size 0.1 with adaptation, target_accept_prob 0.8,
    max_tree_depth, the returned dict schema (site name -> (n,) constrained
    numpy array), and return_diagnostics -> (samples, SamplerDiagnostics)
    with sampler="nuts_e1" (leapfrog counts derived from potential
    evaluations, one per leapfrog step, as the D20 tracker does for the
    traced path).
    """
    import pyro
    from pyro.infer.mcmc import NUTS, MCMC

    from .sampler_diagnostics import PotentialEvalTracker, diagnostics_from_pyro_mcmc

    if seed is not None:
        pyro.set_rng_seed(seed)

    e1 = build_e1_potential(model, likelihood, train_x, train_y, jitter=jitter)

    potential = e1.potential_fn
    tracker = None
    if return_diagnostics:
        tracker = PotentialEvalTracker(potential)
        potential = tracker

    nuts = NUTS(
        potential_fn=potential,
        jit_compile=False,
        step_size=0.1,
        adapt_step_size=True,
        target_accept_prob=0.8,
        max_tree_depth=max_tree_depth,
    )
    mcmc_run = MCMC(
        nuts,
        num_samples=n_samples,
        warmup_steps=n_warmup,
        initial_params={s: v.clone() for s, v in e1.init_params.items()},
        disable_progbar=(not verbose),
        hook_fn=(tracker.hook if tracker is not None else None),
    )
    with gpytorch.settings.cholesky_jitter(jitter):
        mcmc_run.run()

    # Constrained via the oracle's transforms; reshape(-1), NOT squeeze()
    # (fit_hmc's documented (n,) schema, including at n_samples=1).
    u_draws = mcmc_run.get_samples()
    samples = {}
    for s in e1.sites:
        theta = e1.transforms[s].inv(u_draws[s])
        samples[s] = theta.detach().numpy().reshape(-1)

    if verbose:
        mcmc_run.summary()

    diagnostics = None
    if return_diagnostics:
        diagnostics = diagnostics_from_pyro_mcmc(
            mcmc_run,
            sampler="nuts_e1",
            n_draws=n_samples,
            n_warmup=n_warmup,
            site_names=tuple(e1.sites),
            max_tree_depth=max_tree_depth,
            step_size=getattr(nuts, "step_size", None),
            eval_records=tracker.records,
        )

    model.eval()
    likelihood.eval()

    if return_diagnostics:
        return samples, diagnostics
    return samples

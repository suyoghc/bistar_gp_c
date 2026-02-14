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
                    n_samples=10000, n_burnin=1000, proposal_scale=0.1, verbose=True):
    """
    Random-walk Metropolis-Hastings over log hyperparameters.
    For production use NumPyro — this is a starting point.
    Returns dict of parameter name -> posterior samples array.
    """
    train_x, train_y = train_x.double(), train_y.double()
    model.eval()
    likelihood.eval()
    mll = gpytorch.mlls.ExactMarginalLogLikelihood(likelihood, model)

    # Collect raw parameters
    param_list = [(n, p) for n, p in 
                  list(model.named_parameters()) + list(likelihood.named_parameters())
                  if p.requires_grad and p.numel() == 1]
    param_names = [n for n, _ in param_list]

    def get_params():
        return torch.stack([p.data.clone().squeeze() for _, p in param_list])
        
    def set_params(vals):
        for idx, (_, p) in enumerate(param_list):
            p.data.copy_(vals[idx])

    def log_posterior():
        with gpytorch.settings.cholesky_jitter(DEFAULT_JITTER):
            try:
                return mll(model(train_x), train_y).item()
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

    return {k: np.array(v) for k, v in samples.items()}

def fit_hmc(model, likelihood, train_x, train_y,
            n_samples=500, n_warmup=200, verbose=True):
    """
    Hamiltonian Monte Carlo via Pyro's NUTS sampler.
    
    This is the production-grade sampler — uses gradients to explore
    the posterior efficiently, unlike random-walk MH.
    
    Returns dict of parameter name -> numpy array of posterior samples.
    """
    import pyro
    from pyro.infer.mcmc import NUTS, MCMC
    from functools import partial

    train_x, train_y = train_x.double(), train_y.double()
    model.train()
    likelihood.train()

    # Clear any previous pyro state
    pyro.clear_param_store()

    # Pyro model: sample hyperparameters from priors, compute likelihood
    def pyro_model(model, likelihood, x, y):
        model.pyro_sample_from_prior()
        likelihood.pyro_sample_from_prior()
        output = model(x)
        with pyro.plate("data", y.shape[0]):
            pyro.sample("obs", likelihood(output), obs=y)

    nuts = NUTS(
        partial(pyro_model, model, likelihood),
        jit_compile=False,
        step_size=0.1,
        adapt_step_size=True,
        target_accept_prob=0.8,
    )

    mcmc_run = MCMC(
        nuts,
        num_samples=n_samples,
        warmup_steps=n_warmup,
        disable_progbar=(not verbose),
    )

    with gpytorch.settings.cholesky_jitter(DEFAULT_JITTER):
        mcmc_run.run(train_x, train_y)

    # Extract samples as numpy arrays
    raw_samples = mcmc_run.get_samples()
    samples = {k: v.squeeze().numpy() for k, v in raw_samples.items()}

    if verbose:
        mcmc_run.summary()

    model.eval()
    likelihood.eval()

    return samples
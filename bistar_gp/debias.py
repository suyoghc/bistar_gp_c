"""
Debiasing pipeline: fit additive GP, decompose, extract labeled components.
Works for any number of additive components.

2026-09 review fix pass (FIX-1 and FIX-2). The hyperparameter-draw routines
`decompose_model_hmc` and `decompose_model_mcmc` used to discard each draw's
conditional covariance and report `std` as the across-draw spread of the
conditional means alone, which understated every band they produced (the
D58 Mauna cards by an order of magnitude). They now retain each draw's
conditional variance and report law-of-total-variance moments,

    Var[f(x) | y] = E_d[ Var(f(x) | y, eta_d) ] + Var_d[ E(f(x) | y, eta_d) ],

for every component, for the full posterior of the summed kernel, and for
any requested GROUP of components. Group moments come from conditioning the
summed group blocks with the Cholesky factor of the entire training
covariance plus noise, never from summing component variances, so a group
containing every component reproduces the full posterior exactly.
"""

import logging

import torch
import numpy as np
from typing import Dict, List, Optional, Sequence, Tuple
from dataclasses import dataclass, field

from .decompose import (
    decompose_additive_gp, decompose_component, compute_cholesky,
    sample_from_component, mixture_central_interval,
)

logger = logging.getLogger(__name__)


@dataclass
class ComponentResult:
    """Posterior summary of one additive component (or of a component group).

    ``mean``, ``std`` and ``cov`` are TOTAL posterior moments over the
    retained hyperparameter draws (law of total variance). ``samples`` keeps
    its historical position and meaning for the MAP path (function draws);
    on the draw-based paths it holds the per-draw conditional means, and
    ``samples_kind`` says which. ``conditional_means`` and
    ``conditional_vars`` (n_draws, n_test) are what interval construction
    needs; ``within_var_mean`` and ``between_var`` are the two terms whose
    sum is ``std ** 2``.
    """
    name: str
    mean: np.ndarray       # (n_test,)
    std: np.ndarray        # (n_test,)  total posterior sd
    cov: np.ndarray        # (n_test, n_test)  total posterior covariance
    samples: np.ndarray    # (n_samples, n_test); see samples_kind
    samples_kind: str = "function_draws"        # or "conditional_means"
    conditional_means: Optional[np.ndarray] = None   # (n_draws, n_test)
    conditional_vars: Optional[np.ndarray] = None    # (n_draws, n_test)
    within_var_mean: Optional[np.ndarray] = None     # E_d[var_d]
    between_var: Optional[np.ndarray] = None         # Var_d[mean_d]
    n_draws: int = 0

    def central_interval(self, mass: float = 0.95):
        """Pointwise central interval of the retained draw mixture."""
        if self.conditional_means is None or self.conditional_vars is None:
            raise ValueError(
                f"component {self.name!r} carries no per-draw conditional "
                "moments; intervals need a decomposition produced by this "
                "package version")
        return mixture_central_interval(self.conditional_means,
                                        self.conditional_vars, mass=mass)


@dataclass
class DecompositionResult:
    """Decomposition of one additive GP posterior.

    The seven fields below are a positional rebuild contract pinned by
    tests/test_poster_d58_driver.py; additional per-draw information is
    attached as non-field attributes in __post_init__ (``full``, ``groups``,
    ``n_draws_attempted``, ``n_draws_retained``) so that contract holds.
    """
    x_test: np.ndarray
    x_train: np.ndarray
    y_train: np.ndarray
    components: Dict[str, ComponentResult]
    full_mean: np.ndarray
    full_std: np.ndarray
    noise_var: float

    def __post_init__(self):
        # Non-field attributes (not part of dataclasses.fields()).
        self.full: Optional[ComponentResult] = None
        self.groups: Dict[Tuple[str, ...], ComponentResult] = {}
        self.n_draws_attempted: int = 0
        self.n_draws_retained: int = 0

    @staticmethod
    def group_key(names: Sequence[str]) -> Tuple[str, ...]:
        return tuple(sorted(names))

    def group(self, names: Sequence[str]) -> ComponentResult:
        """Joint posterior summary of the sum of the named components.

        Groups must be requested at decomposition time (``groups=`` on
        `decompose_model_hmc` / `decompose_model_mcmc`) because their
        conditional moments are computed per hyperparameter draw from the
        summed kernel blocks. A group of every component is the full
        posterior; a singleton is the component; an empty group is zero.
        """
        key = self.group_key(names)
        if len(key) == 0:
            n = len(self.x_test)
            zeros = np.zeros(n)
            n_draws = max(self.n_draws_retained, 1)
            return ComponentResult(
                name="", mean=zeros, std=zeros, cov=np.zeros((n, n)),
                samples=np.zeros((n_draws, n)), samples_kind="conditional_means",
                conditional_means=np.zeros((n_draws, n)),
                conditional_vars=np.zeros((n_draws, n)),
                within_var_mean=zeros, between_var=zeros, n_draws=n_draws)
        if len(key) == 1 and key[0] in self.components:
            return self.components[key[0]]
        if key == self.group_key(self.components.keys()) and self.full is not None:
            return self.full
        if key in self.groups:
            return self.groups[key]
        raise KeyError(
            f"group {list(key)} was not requested at decomposition time; pass "
            f"groups=[{list(key)}] to decompose_model_hmc/decompose_model_mcmc "
            "(joint group moments cannot be derived from component summaries)")


# ── shared draw accumulation ────────────────────────────────────────

def _blocks_sum(km, names, key):
    return sum(km[n][key] for n in names)


class _DrawAccumulator:
    """Accumulate per-draw conditional moments for components, the full
    posterior and requested groups, then form total posterior moments."""

    def __init__(self, names: List[str], n_test: int,
                 groups: Optional[Sequence[Sequence[str]]]):
        self.names = list(names)
        self.n_test = n_test
        self.group_keys: Dict[Tuple[str, ...], List[str]] = {}
        for g in (groups or []):
            key = DecompositionResult.group_key(g)
            unknown = [n for n in key if n not in self.names]
            if unknown:
                raise KeyError(f"group {list(g)} names unknown components {unknown}")
            if 0 < len(key) < len(self.names) and len(key) > 1:
                self.group_keys[key] = list(key)
        targets = ["__full__"] + self.names + [",".join(k) for k in self.group_keys]
        self.means = {t: [] for t in targets}
        self.vars = {t: [] for t in targets}
        self.cov_sum = {t: np.zeros((n_test, n_test)) for t in targets}
        self.n = 0

    def _record(self, target, mean_t, cov_t):
        m = mean_t.numpy() if hasattr(mean_t, "numpy") else np.asarray(mean_t)
        c = cov_t.numpy() if hasattr(cov_t, "numpy") else np.asarray(cov_t)
        c = 0.5 * (c + c.T)
        self.means[target].append(np.array(m, dtype=float))
        self.vars[target].append(np.clip(np.diag(c), 0.0, None))
        self.cov_sum[target] += c

    def add_draw(self, km, noise_var, y_train, jitter):
        """One hyperparameter draw: a single Cholesky of the summed training
        covariance serves every component, the full posterior and the groups."""
        L = compute_cholesky(_blocks_sum(km, self.names, "XX"), noise_var, jitter)
        for n in self.names:
            mean_i, cov_i = decompose_component(
                km[n]["XstarX"], km[n]["XstarXstar"], km[n]["XXstar"], L, y_train)
            self._record(n, mean_i, cov_i)
        mean_f, cov_f = decompose_component(
            _blocks_sum(km, self.names, "XstarX"),
            _blocks_sum(km, self.names, "XstarXstar"),
            _blocks_sum(km, self.names, "XXstar"), L, y_train)
        self._record("__full__", mean_f, cov_f)
        for key, members in self.group_keys.items():
            mean_g, cov_g = decompose_component(
                _blocks_sum(km, members, "XstarX"),
                _blocks_sum(km, members, "XstarXstar"),
                _blocks_sum(km, members, "XXstar"), L, y_train)
            self._record(",".join(key), mean_g, cov_g)
        self.n += 1

    def _finalize_target(self, target, name) -> ComponentResult:
        M = np.stack(self.means[target])                 # (n_draws, n_test)
        V = np.stack(self.vars[target])
        within_cov = self.cov_sum[target] / self.n
        if M.shape[0] > 1:
            between_cov = np.cov(M, rowvar=False, bias=True)
            between_cov = np.atleast_2d(between_cov)
        else:
            between_cov = np.zeros((self.n_test, self.n_test))
        cov = within_cov + between_cov
        within = V.mean(axis=0)
        between = M.var(axis=0)
        std = np.sqrt(np.clip(within + between, 0.0, None))
        return ComponentResult(
            name=name, mean=M.mean(axis=0), std=std, cov=cov,
            samples=M, samples_kind="conditional_means",
            conditional_means=M, conditional_vars=V,
            within_var_mean=within, between_var=between, n_draws=self.n)

    def finalize(self):
        if self.n == 0:
            raise RuntimeError("no hyperparameter draw was decomposed")
        components = {n: self._finalize_target(n, n) for n in self.names}
        full = self._finalize_target("__full__", "__full__")
        groups = {key: self._finalize_target(",".join(key), "+".join(key))
                  for key in self.group_keys}
        return components, full, groups


def _assemble(x_test, x_train, y_train, components, full, groups, noise_var,
              n_attempted, n_retained) -> DecompositionResult:
    result = DecompositionResult(
        x_test=x_test.numpy(), x_train=x_train.numpy(), y_train=y_train.numpy(),
        components=components, full_mean=full.mean, full_std=full.std,
        noise_var=noise_var)
    result.full = full
    result.groups = groups
    result.n_draws_attempted = n_attempted
    result.n_draws_retained = n_retained
    return result


# ── MAP decomposition ───────────────────────────────────────────────

def decompose_model(model, likelihood, x_train, y_train, x_test, n_samples=25, jitter=1e-4,
                    groups=None):
    """
    Decompose a fitted additive GP into its components.
    Single set of hyperparameters (MAP). For full Bayesian, use decompose_model_hmc.

    groups: optional list of component-name lists. Each requested group's
    posterior is the posterior of the summed group kernel conditioned with
    the Cholesky factor of the ENTIRE training covariance (never a
    group-only factorization); retrieve it with ``result.group(names)``.
    """
    model.eval()
    likelihood.eval()
    x_train, y_train, x_test = x_train.double(), y_train.double(), x_test.double()
    noise_var = likelihood.noise.item()

    km = model.get_component_kernel_matrices(x_train, x_test)
    names = model.component_names

    with torch.no_grad():
        results = decompose_additive_gp(
            [km[n]["XX"] for n in names],
            [km[n]["XstarX"] for n in names],
            [km[n]["XstarXstar"] for n in names],
            [km[n]["XXstar"] for n in names],
            noise_var, y_train, jitter,
        )

    components = {}
    full_mean = torch.zeros(x_test.shape[0], dtype=torch.float64)

    for (mean_i, cov_i), name in zip(results, names):
        samples_i = sample_from_component(mean_i, cov_i, n_samples)
        var_i = torch.clamp(torch.diag(cov_i), min=1e-10)
        std_i = torch.sqrt(var_i)
        components[name] = ComponentResult(
            name=name, mean=mean_i.numpy(), std=std_i.numpy(),
            cov=cov_i.numpy(), samples=samples_i.numpy(),
            samples_kind="function_draws",
            conditional_means=mean_i.numpy()[None, :],
            conditional_vars=var_i.numpy()[None, :],
            within_var_mean=var_i.numpy(), between_var=np.zeros(len(mean_i)),
            n_draws=1,
        )
        full_mean += mean_i

    # Full posterior covariance of f = sum_i f_i is NOT the sum of the
    # component covariances: that drops every inter-component cross-covariance
    # term Cov(f_i, f_j). Compute it directly as the posterior of the sum
    # kernel, reusing one Cholesky of (K_sum(X,X) + sigma^2 I).
    with torch.no_grad():
        K_sum_XX = sum(km[n]["XX"] for n in names)
        K_sum_XstarX = sum(km[n]["XstarX"] for n in names)
        K_sum_XstarXstar = sum(km[n]["XstarXstar"] for n in names)
        K_sum_XXstar = sum(km[n]["XXstar"] for n in names)
        L_sum = compute_cholesky(K_sum_XX, noise_var, jitter)
        _, full_cov_t = decompose_component(
            K_sum_XstarX, K_sum_XstarXstar, K_sum_XXstar, L_sum, y_train,
        )
    full_cov = full_cov_t.numpy()
    full_var = np.clip(np.diag(full_cov), 1e-10, None)
    full_std = np.sqrt(full_var)

    # Requested groups (FIX-2b/2d): the summed group blocks conditioned with
    # the same full-kernel factor L_sum; a single hyperparameter setting, so
    # the between-draw term is zero.
    group_results = {}
    for g in (groups or []):
        key = DecompositionResult.group_key(g)
        unknown = [n for n in key if n not in names]
        if unknown:
            raise KeyError(f"group {list(g)} names unknown components {unknown}")
        if not (1 < len(key) < len(names)):
            continue        # empty, singleton and all-component groups are derived
        with torch.no_grad():
            mean_g_t, cov_g_t = decompose_component(
                _blocks_sum(km, key, "XstarX"), _blocks_sum(km, key, "XstarXstar"),
                _blocks_sum(km, key, "XXstar"), L_sum, y_train)
        mean_g, cov_g = mean_g_t.numpy(), cov_g_t.numpy()
        cov_g = 0.5 * (cov_g + cov_g.T)
        var_g = np.clip(np.diag(cov_g), 1e-10, None)
        group_results[key] = ComponentResult(
            name="+".join(key), mean=mean_g, std=np.sqrt(var_g), cov=cov_g,
            samples=mean_g[None, :], samples_kind="conditional_means",
            conditional_means=mean_g[None, :], conditional_vars=var_g[None, :],
            within_var_mean=var_g, between_var=np.zeros(len(var_g)), n_draws=1)

    result = DecompositionResult(
        x_test=x_test.numpy(), x_train=x_train.numpy(), y_train=y_train.numpy(),
        components=components, full_mean=full_mean.numpy(), full_std=full_std, noise_var=noise_var,
    )
    result.full = ComponentResult(
        name="__full__", mean=full_mean.numpy(), std=full_std, cov=full_cov,
        samples=full_mean.numpy()[None, :], samples_kind="conditional_means",
        conditional_means=full_mean.numpy()[None, :], conditional_vars=full_var[None, :],
        within_var_mean=full_var, between_var=np.zeros(len(full_var)), n_draws=1)
    result.groups = group_results
    result.n_draws_attempted = result.n_draws_retained = 1
    return result


# ── draw-based decompositions ───────────────────────────────────────

def _raw_parameter_map(model, likelihood):
    """{name: parameter} over model + likelihood scalar parameters, deduplicated
    by object identity with the first name kept (the fit_mcmc_simple naming)."""
    seen = set()
    out = {}
    for n, p in list(model.named_parameters()) + list(likelihood.named_parameters()):
        if p.requires_grad and p.numel() == 1 and id(p) not in seen:
            seen.add(id(p))
            out[n] = p
    return out


def decompose_model_mcmc(model, likelihood, x_train, y_train, x_test,
                         mcmc_samples, n_posterior_samples=100, jitter=1e-4,
                         groups=None, rng=None):
    """
    Full Bayesian decomposition over RAW-parameter draws (fit_mcmc_simple
    output: dict keyed by named_parameters names, raw unconstrained values).

    Draws are matched to parameters BY NAME (the previous positional pairing
    silently mis-assigned any differently ordered dict); every parameter must
    have a key and every key must name a parameter, or the call raises.
    Bands are law-of-total-variance moments (see the module docstring).
    """
    model.eval()
    likelihood.eval()
    x_train, y_train, x_test = x_train.double(), y_train.double(), x_test.double()
    n_test = x_test.shape[0]

    param_map = _raw_parameter_map(model, likelihood)
    keys = list(mcmc_samples.keys())
    unknown = [k for k in keys if k not in param_map]
    missing = [n for n in param_map if n not in mcmc_samples]
    if unknown or missing:
        raise KeyError(
            "decompose_model_mcmc: sample keys and model parameters do not "
            f"match by name (unknown keys {unknown}, parameters without a key "
            f"{missing}); positional pairing is no longer performed")

    total_mcmc = len(mcmc_samples[keys[0]])
    n_take = min(n_posterior_samples, total_mcmc)
    if rng is not None:
        indices = rng.choice(total_mcmc, n_take, replace=False)
    else:
        indices = np.random.choice(total_mcmc, n_take, replace=False)

    names = list(model.component_names)
    acc = _DrawAccumulator(names, n_test, groups)
    noise_var = float(likelihood.noise.item())
    for idx in indices:
        for name, p in param_map.items():
            p.data.fill_(float(mcmc_samples[name][idx]))
        noise_var = likelihood.noise.item()
        km = model.get_component_kernel_matrices(x_train, x_test)
        with torch.no_grad():
            acc.add_draw(km, noise_var, y_train, jitter)

    components, full, group_results = acc.finalize()
    return _assemble(x_test, x_train, y_train, components, full, group_results,
                     noise_var, len(indices), acc.n)


def decompose_model_hmc(model, likelihood, x_train, y_train, x_test,
                        mcmc_samples, kernel_builder, n_posterior_samples=200,
                        jitter=1e-4, groups=None, strict=True, rng=None):
    """
    Decomposition over Pyro/E1 hyperparameter draws (fit_hmc dict schema:
    constrained values keyed by pyro sample-site name).

    kernel_builder: callable that returns (kernel_components, names), e.g.
                    build_toy_kernels or build_mauna_loa_kernels.
    groups: optional list of component-name lists; each requested group's
            joint posterior (sum of the components) is computed per draw and
            available through DecompositionResult.group(names).
    strict: True (default) raises on an unrecognized or failing sample site
            and on a draw whose decomposition fails; False keeps the previous
            skip-and-continue behavior and records the dropped draws.
    """
    from .model import build_model, build_likelihood, select_hmc_sites, apply_hp_value

    x_train, y_train, x_test = x_train.double(), y_train.double(), x_test.double()
    n_test = x_test.shape[0]

    first_key = list(mcmc_samples.keys())[0]
    total_mcmc = len(mcmc_samples[first_key])
    n_take = min(n_posterior_samples, total_mcmc)
    if rng is not None:
        indices = rng.choice(total_mcmc, n_take, replace=False)
    else:
        indices = np.random.choice(total_mcmc, n_take, replace=False)

    relevant_keys = select_hmc_sites(mcmc_samples.keys())
    kernel_keys = [k for k in relevant_keys if not k.endswith("noise_covar.noise_prior")]
    if not kernel_keys:
        msg = ("decompose_model_hmc: no kernel hyperparameter site recognized "
               f"among {sorted(mcmc_samples.keys())}")
        if strict:
            raise ValueError(msg)
        logger.warning(msg)

    names = list(model.component_names)
    acc = _DrawAccumulator(names, n_test, groups)
    dropped = []
    last_noise = float(likelihood.noise.item())

    for idx in indices:
        kernels, fresh_names = kernel_builder()
        if list(fresh_names) != names:
            raise ValueError(
                f"kernel_builder names {list(fresh_names)} differ from the "
                f"model's component names {names}")
        fresh_likelihood = build_likelihood()
        fresh_model, fresh_likelihood = build_model(x_train, y_train, kernels, fresh_names, fresh_likelihood)

        for pyro_name in relevant_keys:
            val = float(mcmc_samples[pyro_name][idx])
            try:
                applied = apply_hp_value(fresh_model, fresh_likelihood, pyro_name, val)
            except (IndexError, AttributeError, RuntimeError) as exc:
                msg = (f"decompose_model_hmc: applying site {pyro_name!r} for "
                       f"draw {int(idx)} raised {type(exc).__name__}: {exc}")
                if strict:
                    raise ValueError(msg) from exc
                logger.warning(msg)
                continue
            if not applied:
                msg = (f"decompose_model_hmc: apply_hp_value did not recognize "
                       f"site {pyro_name!r} (draw {int(idx)})")
                if strict:
                    raise ValueError(msg)
                logger.warning(msg)

        fresh_model.eval()
        fresh_likelihood.eval()
        noise_var = fresh_likelihood.noise.item()
        km = fresh_model.get_component_kernel_matrices(x_train, x_test)

        with torch.no_grad():
            try:
                acc.add_draw(km, noise_var, y_train, jitter)
                last_noise = noise_var
            except RuntimeError as exc:
                if strict:
                    raise RuntimeError(
                        f"decompose_model_hmc: decomposition failed for draw "
                        f"{int(idx)} ({exc}); pass strict=False to drop failing "
                        "draws and record them") from exc
                dropped.append((int(idx), str(exc)))
                continue

    if acc.n == 0:
        raise RuntimeError("All MCMC samples failed decomposition")

    print(f"  Decomposed {acc.n}/{len(indices)} MCMC samples successfully")
    if dropped:
        logger.warning("decompose_model_hmc dropped %d of %d draws: %s",
                       len(dropped), len(indices), [d for d, _ in dropped][:10])

    components, full, group_results = acc.finalize()
    result = _assemble(x_test, x_train, y_train, components, full, group_results,
                       last_noise, len(indices), acc.n)
    result.dropped = dropped
    return result

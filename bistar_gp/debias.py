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

import functools
import logging
import operator

import torch
import numpy as np
from typing import Dict, List, Optional, Sequence, Tuple
from dataclasses import dataclass, field

from .decompose import (
    decompose_additive_gp, decompose_component, compute_cholesky,
    sample_from_component, mixture_central_interval,
)
from .bms_star import sample_draw_count, _validate_sample_sites

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
    ``n_draws_attempted``, ``n_draws_retained``, ``noise_var_draws``) so that
    contract holds. ``noise_var`` is the mean observation-noise variance over
    the retained draws and ``noise_var_draws`` the per-draw values, so
    neither depends on draw order (fix pass 2a, SYNTHESIS A-10).
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
        self.noise_var_draws: Optional[np.ndarray] = None

    @staticmethod
    def group_key(names: Sequence[str]) -> Tuple[str, ...]:
        return tuple(sorted(set(names)))     # a repeated name is one member (review F3)

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
        if len(key) == 1:
            if key[0] not in self.components:
                raise KeyError(f"unknown component {key[0]!r}; components are "
                               f"{list(self.components)}")
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
    """Sum of the named components' kernel blocks. A single name returns its
    block itself (no leading ``0 +`` step), so a lone component follows
    exactly the arithmetic of the per-component path."""
    return functools.reduce(operator.add, [km[n][key] for n in names])


def _summarize(name, M, V, cov, samples, samples_kind) -> ComponentResult:
    """The one place a ComponentResult is packaged (fix pass 1b).

    M, V: (n_draws, n_test) conditional means and variances. cov: the total
    posterior covariance the caller assembled (one draw's conditional
    covariance, or mean_d C_d + Cov_d m_d over draws). std is the
    law-of-total-variance sd sqrt(E_d[var_d] + Var_d[mean_d]).
    """
    M = np.asarray(M, dtype=float)
    V = np.asarray(V, dtype=float)
    within = V.mean(axis=0)
    between = M.var(axis=0)
    std = np.sqrt(np.clip(within + between, 0.0, None))
    return ComponentResult(
        name=name, mean=M.mean(axis=0), std=std, cov=cov,
        samples=samples, samples_kind=samples_kind,
        conditional_means=M, conditional_vars=V,
        within_var_mean=within, between_var=between, n_draws=M.shape[0])


def _single_draw_summary(name, mean, cov, samples=None) -> ComponentResult:
    """Summary of one conditional Gaussian (the MAP path), variance floored
    at 1e-10 as before; ``samples`` are function draws when given."""
    mean = np.asarray(mean, dtype=float)
    var = np.clip(np.diag(cov), 1e-10, None)
    if samples is None:
        return _summarize(name, mean[None, :], var[None, :], cov, mean[None, :],
                          "conditional_means")
    return _summarize(name, mean[None, :], var[None, :], cov, samples, "function_draws")


def _validated_groups(names, groups) -> Dict[Tuple[str, ...], List[str]]:
    """{sorted-name tuple: members} for the requested groups that need their
    own conditioning (more than one component, fewer than all). Empty,
    singleton and all-component requests are derived by
    DecompositionResult.group; repeated names collapse to one member; unknown
    members raise."""
    out = {}
    for g in (groups or []):
        g = list(g)
        key = DecompositionResult.group_key(g)
        unknown = [n for n in key if n not in names]
        if unknown:
            raise KeyError(f"group {g} names unknown components {unknown}")
        if 1 < len(key) < len(names):
            out[key] = list(key)
    return out


class _DrawAccumulator:
    """Accumulate per-draw conditional moments for components, the full
    posterior and requested groups, then form total posterior moments.

    Targets are keyed by typed tuples ``("component", name)``, ``("group",
    sorted names)`` and ``("full",)``, so a component name can never collide
    with a group label or the full posterior (fix pass 1b, review R3)."""

    def __init__(self, names: List[str], n_test: int,
                 groups: Optional[Sequence[Sequence[str]]]):
        self.names = list(names)
        self.n_test = n_test
        self.group_keys = _validated_groups(self.names, groups)
        self.targets = ([("full",)] + [("component", n) for n in self.names]
                        + [("group", k) for k in self.group_keys])
        self.means = {t: [] for t in self.targets}
        self.vars = {t: [] for t in self.targets}
        self.cov_sum = {t: np.zeros((n_test, n_test)) for t in self.targets}
        self.n = 0

    def _members(self, target):
        if target[0] == "full":
            return self.names
        if target[0] == "component":
            return [target[1]]
        return self.group_keys[target[1]]

    def add_draw(self, km, noise_var, y_train, jitter):
        """One hyperparameter draw: a single Cholesky of the summed training
        covariance serves every target. Every target is conditioned into a
        local record first and committed together at the end, so a failure
        part-way leaves no partially recorded draw (fix pass 1b, review R2)."""
        L = compute_cholesky(_blocks_sum(km, self.names, "XX"), noise_var, jitter)
        record = {}
        for target in self.targets:
            members = self._members(target)
            mean_t, cov_t = decompose_component(
                _blocks_sum(km, members, "XstarX"), _blocks_sum(km, members, "XstarXstar"),
                _blocks_sum(km, members, "XXstar"), L, y_train)
            m = np.array(mean_t.numpy() if hasattr(mean_t, "numpy") else mean_t, dtype=float)
            c = np.asarray(cov_t.numpy() if hasattr(cov_t, "numpy") else cov_t, dtype=float)
            c = 0.5 * (c + c.T)
            v = np.clip(np.diag(c), 0.0, None)
            np.fill_diagonal(c, v)      # keep diag(cov) == std**2 when a diagonal is numerically negative (K3-4)
            record[target] = (m, v, c)
        for target, (m, v, c) in record.items():
            self.means[target].append(m)
            self.vars[target].append(v)
            self.cov_sum[target] += c
        self.n += 1

    def _finalize_target(self, target, name) -> ComponentResult:
        M = np.stack(self.means[target])                 # (n_draws, n_test)
        V = np.stack(self.vars[target])
        within_cov = self.cov_sum[target] / self.n
        if M.shape[0] > 1:
            between_cov = np.atleast_2d(np.cov(M, rowvar=False, bias=True))
        else:
            between_cov = np.zeros((self.n_test, self.n_test))
        return _summarize(name, M, V, within_cov + between_cov, M, "conditional_means")

    def finalize(self):
        if self.n == 0:
            raise RuntimeError("no hyperparameter draw was decomposed")
        components = {n: self._finalize_target(("component", n), n) for n in self.names}
        full = self._finalize_target(("full",), "__full__")
        groups = {key: self._finalize_target(("group", key), "+".join(key))
                  for key in self.group_keys}
        return components, full, groups


def _assemble(x_test, x_train, y_train, components, full, groups, noise_draws,
              n_attempted, n_retained) -> DecompositionResult:
    """Package a draw-path decomposition. ``noise_draws`` holds the retained
    draws' noise variances; ``noise_var`` is their mean (fix pass 2a,
    SYNTHESIS A-10: it used to be the last retained draw's value)."""
    noise_draws = np.asarray(noise_draws, dtype=float)
    result = DecompositionResult(
        x_test=x_test.numpy(), x_train=x_train.numpy(), y_train=y_train.numpy(),
        components=components, full_mean=full.mean, full_std=full.std,
        noise_var=float(noise_draws.mean()))
    result.full = full
    result.groups = groups
    result.n_draws_attempted = n_attempted
    result.n_draws_retained = n_retained
    result.noise_var_draws = noise_draws
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
        components[name] = _single_draw_summary(name, mean_i.numpy(), cov_i.numpy(),
                                                samples=samples_i.numpy())
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
    full = _single_draw_summary("__full__", full_mean.numpy(), full_cov_t.numpy())

    # Requested groups (FIX-2b/2d): the summed group blocks conditioned with
    # the same full-kernel factor L_sum; a single hyperparameter setting, so
    # the between-draw term is zero.
    group_results = {}
    for key, members in _validated_groups(names, groups).items():
        with torch.no_grad():
            mean_g_t, cov_g_t = decompose_component(
                _blocks_sum(km, members, "XstarX"), _blocks_sum(km, members, "XstarXstar"),
                _blocks_sum(km, members, "XXstar"), L_sum, y_train)
        cov_g = cov_g_t.numpy()
        group_results[key] = _single_draw_summary("+".join(key), mean_g_t.numpy(),
                                                  0.5 * (cov_g + cov_g.T))

    result = DecompositionResult(
        x_test=x_test.numpy(), x_train=x_train.numpy(), y_train=y_train.numpy(),
        components=components, full_mean=full_mean.numpy(), full_std=full.std, noise_var=noise_var,
    )
    result.full = full
    result.groups = group_results
    result.n_draws_attempted = result.n_draws_retained = 1
    result.noise_var_draws = np.array([noise_var])
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

    The draws are written into the caller's ``model`` and ``likelihood`` in
    place, and the parameters keep the last decomposed draw's values on
    return (SYNTHESIS A-18); refit or restore the model before reusing it.
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

    total_mcmc = sample_draw_count(mcmc_samples, keys, "decompose_model_mcmc")
    n_take = min(n_posterior_samples, total_mcmc)
    if rng is not None:
        indices = rng.choice(total_mcmc, n_take, replace=False)
    else:
        indices = np.random.choice(total_mcmc, n_take, replace=False)

    names = list(model.component_names)
    acc = _DrawAccumulator(names, n_test, groups)
    noise_draws = []
    for idx in indices:
        for name, p in param_map.items():
            p.data.fill_(float(mcmc_samples[name][idx]))
        noise_var = likelihood.noise.item()
        km = model.get_component_kernel_matrices(x_train, x_test)
        with torch.no_grad():
            acc.add_draw(km, noise_var, y_train, jitter)
        noise_draws.append(noise_var)

    components, full, group_results = acc.finalize()
    return _assemble(x_test, x_train, y_train, components, full, group_results,
                     noise_draws, len(indices), acc.n)


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
    strict: True (default) raises on an unrecognized or failing sample site,
            on a sampled site of the model with no draws supplied, and on a
            draw whose decomposition fails; False keeps the previous
            skip-and-continue behavior and records the dropped draws. Sample
            arrays of unequal length raise under either setting.
    """
    from .model import build_model, build_likelihood, apply_hp_value

    x_train, y_train, x_test = x_train.double(), y_train.double(), x_test.double()
    n_test = x_test.shape[0]

    relevant_keys, total_mcmc = _validate_sample_sites(
        mcmc_samples, kernel_builder, build_likelihood, x_train, y_train,
        "decompose_model_hmc", strict)

    n_take = min(n_posterior_samples, total_mcmc)
    if rng is not None:
        indices = rng.choice(total_mcmc, n_take, replace=False)
    else:
        indices = np.random.choice(total_mcmc, n_take, replace=False)

    names = list(model.component_names)
    acc = _DrawAccumulator(names, n_test, groups)
    dropped = []
    noise_draws = []

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
                noise_draws.append(noise_var)
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
                       noise_draws, len(indices), acc.n)
    result.dropped = dropped
    return result

"""E1 direct-parameter potential (D19 M2b; plan §2 Stage B, prereg addenda v1.2-v1.5).

The S1 pyro path (fit_hmc) pays a full model deep copy per potential
evaluation (`pyro_sample_from_prior()`) and proposes with partially broken
gradients: gpytorch's prior-value injection severs the autograd graph for
every kernel hyperparameter site (D23), so S1's NUTS moves those coordinates
as if the likelihood did not exist. E1 keeps the target AND the coordinates
bit-compatible with S1 while fixing both defects by construction — measured
(prereg v1.5): a 1.2-3.2x per-evaluation advantage plus correct gradients
that kept S1f at 6.7 leapfrogs per draw where S1 saturated td7 at 127.
(The plan's original "~200x deep-copy penalty" motivation was dominated by
the D22 plate defect and is superseded by v1.5.) S1f ("adapted baseline on
E1") is S1 with a corrected evaluation path — not a reparameterization,
which is the S3 strategy under test and must stay there (v1.2, point 1).

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
E1 computes the observation term directly, as the summed `log_prob(y)` of
the noise-added marginal MVN — never through `ExactMarginalLogLikelihood`,
which already adds registered prior log-probs and divides by N, so composing
it with an explicit prior sum double-counts every prior and mis-scales the
likelihood (the D6 error class).

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
from linear_operator.utils.errors import NotPSDError

from .fit import (
    DEFAULT_JITTER,
    _guard_init_values,
    _hmc_pyro_model,
    _map_init_values,
)

logger = logging.getLogger(__name__)
torch.set_default_dtype(torch.float64)
E1_NOTPSD_FAIL_RATE = 1e-3   # author-ratified D31 (post-warmup fail ceiling)
PREFLIGHT_ROUNDTRIP_TOL = 1e-10


class _NotPSDRejectingPotential:
    """Convert only terminal ``NotPSDError`` failures into NUTS rejections.

    This policy adds no jitter ladder. By default, E1 evaluates the marginal
    under ``gpytorch.settings.cholesky_jitter(DEFAULT_JITTER=1e-4)``; internal
    decompositions also use linear_operator's ``psd_safe_cholesky`` retry
    defaults. Once those retries fail, Pyro 1.9.1's registered
    ``torch_singular`` handler recognizes the RuntimeError text below and
    converts the proposal to zero gradients plus NaN energy. NUTS then rejects
    that proposal. Successful return values pass through without modification.
    """

    def __init__(self, potential_fn):
        self._potential_fn = potential_fn
        self.n_evaluations = 0
        self.notpsd_rejections = 0

    def __call__(self, *args, **kwargs):
        self.n_evaluations += 1
        try:
            return self._potential_fn(*args, **kwargs)
        except NotPSDError:
            self.notpsd_rejections += 1
            raise RuntimeError(
                "input is not positive-definite after terminal NotPSDError "
                "(D28 rejection policy)") from None


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

    def __init__(self, model, likelihood, train_x, train_y, jitter=DEFAULT_JITTER,
                 init_to_map=True, init_values=None):
        import pyro
        from functools import partial
        from pyro.infer.mcmc.util import initialize_model
        from pyro.infer.autoguide.initialization import init_to_sample, init_to_value

        train_x, train_y = train_x.double(), train_y.double()
        self._model, self._likelihood = model, likelihood
        self._x, self._y = train_x, train_y
        self._jitter = jitter

        # Explicit constrained values take precedence over init_to_map. Both
        # paths use the same finite-unconstrained boundary guard.
        if init_values is not None:
            init_strategy = init_to_value(
                values=_guard_init_values(model, init_values))
        elif init_to_map:
            try:
                init_strategy = init_to_value(values=_map_init_values(model))
            except ValueError as e:
                logger.warning(
                    "init_to_map: %s; falling back to init_to_sample", e)
                init_strategy = init_to_sample
        else:
            init_strategy = init_to_sample

        model.train()
        likelihood.train()
        pyro.clear_param_store()
        with gpytorch.settings.cholesky_jitter(jitter):
            init_params, potential_fn, transforms, _ = initialize_model(
                partial(_hmc_pyro_model, model), model_args=(train_x, train_y),
                init_strategy=init_strategy)

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


def build_e1_potential(model, likelihood, train_x, train_y, jitter=DEFAULT_JITTER,
                       init_to_map=True, init_values=None):
    """Build E1, with explicit constrained ``init_values`` taking priority."""
    return E1Potential(model, likelihood, train_x, train_y, jitter=jitter,
                       init_to_map=init_to_map, init_values=init_values)


def preflight_start_state(model, likelihood, train_x, train_y, init_values,
                          jitter=DEFAULT_JITTER):
    """Run the D30 checks before the two-stage freeze pins a start state.

    ``init_values`` contains constrained prior-IS authority values. Checks run
    deterministically in protocol order and stop at the first failure.
    """
    report = {}
    try:
        e1 = build_e1_potential(
            model, likelihood, train_x, train_y, jitter=jitter,
            init_values=init_values)
    except ValueError:
        report["site_set"] = False
        return False, "site_set", report
    except (NotPSDError, RuntimeError):
        report["site_set"] = True
        report["potential_finite"] = False
        return False, "potential_finite", report
    report["site_set"] = True

    u0 = e1.init_params
    constrained_back = e1.constrain(u0)
    round_trip_ok = True
    for site, value in init_values.items():
        expected = value.detach().double()
        actual = constrained_back[site].detach().double()
        denominator = max(1.0, float(expected.abs().max()))
        relative_error = float((actual - expected).abs().max()) / denominator
        if not np.isfinite(relative_error) or relative_error > PREFLIGHT_ROUNDTRIP_TOL:
            round_trip_ok = False
            break
    report["round_trip"] = round_trip_ok
    if not round_trip_ok:
        return False, "round_trip", report

    try:
        potential = e1.potential_fn(u0)
    except NotPSDError:
        report["potential_finite"] = False
        return False, "potential_finite", report
    potential_finite = bool(torch.isfinite(potential).all())
    report["potential_finite"] = potential_finite
    if not potential_finite:
        return False, "potential_finite", report

    u_req = {
        site: value.detach().clone().requires_grad_(True)
        for site, value in u0.items()
    }
    try:
        potential = e1.potential_fn(u_req)
        gradients = torch.autograd.grad(
            potential, tuple(u_req[site] for site in e1.sites))
    except NotPSDError:
        report["gradient_finite"] = False
        return False, "gradient_finite", report
    gradient_finite = all(bool(torch.isfinite(grad).all()) for grad in gradients)
    report["gradient_finite"] = gradient_finite
    if not gradient_finite:
        return False, "gradient_finite", report

    return True, None, report


def select_start_state(model, likelihood, train_x, train_y, candidates,
                       jitter=DEFAULT_JITTER):
    """Return the first D30-eligible candidate in preregistered order."""
    reports = []
    failure_reasons = []
    for index, values in enumerate(candidates):
        ok, reason, report = preflight_start_state(
            model, likelihood, train_x, train_y, values, jitter=jitter)
        reports.append(report)
        if ok:
            return index, values, reports
        failure_reasons.append(reason)

    reason_text = ", ".join(
        f"candidate {index}: {reason}"
        for index, reason in enumerate(failure_reasons)
    )
    raise RuntimeError(
        f"D30 start-state preflight failed after {len(candidates)} candidates; "
        f"failure reasons: {reason_text}")


def fit_hmc_e1(model, likelihood, train_x, train_y,
               n_samples=500, n_warmup=200, verbose=True, seed=None,
               init_to_map=True, max_tree_depth=10, return_diagnostics=False,
               jitter=DEFAULT_JITTER, init_values=None):
    """S1f: NUTS on the E1 potential — fit_hmc's sampler settings, statistically
    identical target and coordinates, no per-leapfrog deep copy.

    Mirrors fit_hmc exactly where the two share surface: init_to_map with the
    same boundary-guarded fallback to init_to_sample (pass a MAP-fitted
    model), step_size 0.1 with adaptation, target_accept_prob 0.8,
    max_tree_depth, the returned dict schema (site name -> (n,) constrained
    numpy array), and return_diagnostics -> (samples, SamplerDiagnostics)
    with sampler="nuts_e1" (leapfrog counts derived from potential
    evaluations, one per leapfrog step, as the D20 tracker does for the
    traced path). A constrained ``init_values`` dict takes precedence over
    ``init_to_map`` when supplied.
    """
    import pyro
    from pyro.infer.mcmc import NUTS, MCMC

    from .sampler_diagnostics import PotentialEvalTracker, diagnostics_from_pyro_mcmc

    if seed is not None:
        pyro.set_rng_seed(seed)

    e1 = build_e1_potential(model, likelihood, train_x, train_y, jitter=jitter,
                            init_to_map=init_to_map, init_values=init_values)

    rejecting_potential = _NotPSDRejectingPotential(e1.potential_fn)
    tracker = PotentialEvalTracker(rejecting_potential)
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
        hook_fn=tracker.hook,
    )
    with gpytorch.settings.cholesky_jitter(jitter):
        mcmc_run.run()

    diagnostics = diagnostics_from_pyro_mcmc(
        mcmc_run,
        sampler="nuts_e1",
        n_draws=n_samples,
        n_warmup=n_warmup,
        site_names=tuple(e1.sites),
        max_tree_depth=max_tree_depth,
        step_size=getattr(nuts, "step_size", None),
        eval_records=tracker.records,
        notpsd_rejections=rejecting_potential.notpsd_rejections,
    )

    if diagnostics.notpsd_rejections_warmup:
        logger.info(
            "D29 observed %d NotPSD rejections during warmup "
            "(including initialization before the first warmup hook)",
            diagnostics.notpsd_rejections_warmup)

    post_warmup = diagnostics.notpsd_post_warmup_total
    if post_warmup:
        draw_indices = [
            i for i, count in enumerate(
                diagnostics.notpsd_rejections_per_draw[0]) if count]
        logger.warning(
            "D29 observed %d post-warmup NotPSD rejections at draw indices %s",
            post_warmup, draw_indices)

    notpsd_rate = diagnostics.notpsd_post_warmup_rate
    if notpsd_rate is not None and notpsd_rate >= E1_NOTPSD_FAIL_RATE:
        error = RuntimeError(
            "D29 post-warmup NotPSD rejection rate "
            f"{notpsd_rate:.12g} reaches the ratified failure threshold "
            f"{E1_NOTPSD_FAIL_RATE:.12g} (D31)")
        error.diagnostics = diagnostics
        model.eval()
        likelihood.eval()
        raise error

    # Constrained via the oracle's transforms; reshape(-1), NOT squeeze()
    # (fit_hmc's documented (n,) schema, including at n_samples=1).
    u_draws = mcmc_run.get_samples()
    samples = {}
    for s in e1.sites:
        theta = e1.transforms[s].inv(u_draws[s])
        samples[s] = theta.detach().numpy().reshape(-1)

    if verbose:
        mcmc_run.summary()

    model.eval()
    likelihood.eval()

    if return_diagnostics:
        return samples, diagnostics
    return samples

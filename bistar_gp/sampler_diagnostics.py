"""
Serializable sampler diagnostics (D20, M2a item 6).

fit_hmc historically discarded the pyro MCMC object, so divergences,
tree-depth saturation, and acceptance were unrecoverable — but the D19 G-B
gate (docs/plan-d19-mauna.md §6.7) needs exactly those, and the M2c
divergence-clustering predicate (§6.15) will be defined against a stable
record of them. This module supplies that record: a plain, frozen,
JSON-round-trippable dataclass — never a live Pyro object.

Honesty contract: a diagnostic this sampler or path could not observe is
reported as None AND named in `unavailable` — never fabricated as zero. The
invariant is enforced at construction, so a consumer reading
`divergence_rate is None` can trust that divergences were unobservable rather
than absent. The same rule distinguishes an observed zero terminal-NotPSD
rejection count from a path that cannot apply or report the D28 policy.

Pyro 1.9.1 specifics this module encodes (verified against the installed
source and a live probe):
- MCMC.diagnostics() exposes "divergences" as {"chain c": [draw indices]}
  where indices are POST-WARMUP draw indices (hmc.py records
  `self._t - self._warmup_steps`), and "acceptance rate" as {"chain c": float}.
- Per-iteration tree depth is NOT exposed. It is recovered observationally:
  each NUTS leapfrog step evaluates the potential (one traced model call)
  exactly once, so wrapping the model callable in a counter and snapshotting
  the count from an MCMC hook at every iteration yields per-draw leapfrog
  counts; depth saturation at cap d means a count of at least 2**d - 1
  leapfrogs (127 at the Mauna td7 convention, matching the D8 record).
"""

import json
import math
from dataclasses import dataclass, fields

SCHEMA_VERSION = 2

# Observation fields under the None-iff-unavailable honesty contract.
_OBSERVATION_FIELDS = (
    "divergence_draws", "acceptance_rate", "leapfrog_counts",
    "notpsd_rejections",
)


class PotentialEvalTracker:
    """Counts traced model evaluations and snapshots them per MCMC iteration.

    Wraps the pyro model callable; `hook` is passed as MCMC's hook_fn. Each
    NUTS leapfrog evaluates the model once, so the count delta between
    consecutive iteration hooks equals that iteration's leapfrog count. The
    first warmup delta additionally contains initialization overhead, which is
    why leapfrog counts are only derived for the sampling stage (the first
    sampling delta is measured against the last warmup snapshot and is clean).
    """

    def __init__(self, model_fn):
        self._model_fn = model_fn
        self.n_evals = 0
        self.records = []  # (stage, iteration, cumulative eval count)

    def __call__(self, *args, **kwargs):
        self.n_evals += 1
        return self._model_fn(*args, **kwargs)

    def hook(self, kernel, params, stage, i):
        self.records.append((str(stage), int(i), int(self.n_evals)))


@dataclass(frozen=True)
class SamplerDiagnostics:
    """Frozen, JSON-serializable record of one sampler run's diagnostics.

    Chain-major layout: every per-chain field has length n_chains; per-draw
    entries index post-warmup draws 0..n_draws-1. All sequence fields are
    tuples so instances are immutable and compare by value (the round-trip
    tests rely on equality).
    """

    sampler: str                    # e.g. "nuts_pyro"
    n_chains: int
    n_draws: int                    # post-warmup draws per chain
    n_warmup: int
    site_names: tuple               # ordered exactly as the samples dict
    max_tree_depth: int = None      # None when the sampler has no depth cap
    step_size: float = None         # final adapted step size, if exposed
    divergence_draws: tuple = None  # per chain: post-warmup draw indices
    acceptance_rate: tuple = None   # per chain
    leapfrog_counts: tuple = None   # per chain: per-draw potential evals
    notpsd_rejections: int = None   # total terminal NotPSD rejections
    unavailable: tuple = ()         # observation fields this path cannot see
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self):
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(
                f"schema_version must be {SCHEMA_VERSION} for new records")
        for name in _OBSERVATION_FIELDS:
            value, listed = getattr(self, name), name in self.unavailable
            if (value is None) != listed:
                raise ValueError(
                    f"{name}: honesty contract violated — a diagnostic must be "
                    "None exactly when it appears in `unavailable` "
                    f"(value={'None' if value is None else 'present'}, "
                    f"listed={listed})")
        for name in ("divergence_draws", "acceptance_rate", "leapfrog_counts"):
            value = getattr(self, name)
            if value is not None and len(value) != self.n_chains:
                raise ValueError(
                    f"{name} has {len(value)} chains; expected {self.n_chains}")
        if self.leapfrog_counts is not None:
            for c, counts in enumerate(self.leapfrog_counts):
                if len(counts) != self.n_draws:
                    raise ValueError(
                        f"leapfrog_counts chain {c} has {len(counts)} draws; "
                        f"expected {self.n_draws}")
        if self.divergence_draws is not None:
            for c, idxs in enumerate(self.divergence_draws):
                bad = [t for t in idxs if not (0 <= t < self.n_draws)]
                if bad:
                    raise ValueError(
                        f"divergence_draws chain {c} indices out of range: {bad}")
        if self.acceptance_rate is not None:
            bad = [a for a in self.acceptance_rate
                   if not (math.isfinite(a) and 0.0 <= a <= 1.0)]
            if bad:
                raise ValueError(
                    f"acceptance_rate entries outside finite [0, 1]: {bad}")
        if (self.notpsd_rejections is not None
                and (type(self.notpsd_rejections) is not int
                     or self.notpsd_rejections < 0)):
            raise ValueError("notpsd_rejections must be a nonnegative int")

    # ── derived quantities (None whenever their observation is None) ──

    @property
    def n_divergences(self):
        if self.divergence_draws is None:
            return None
        return tuple(len(idxs) for idxs in self.divergence_draws)

    @property
    def divergence_rate(self):
        if self.divergence_draws is None:
            return None
        total = sum(len(idxs) for idxs in self.divergence_draws)
        return total / float(self.n_chains * self.n_draws)

    @property
    def tree_depths(self):
        """Per-chain per-draw depth implied by the leapfrog count.

        A count of s leapfrogs needs a tree of depth ceil(log2(s + 1)); this
        inverts the saturated-count relation s = 2**d - 1.
        """
        if self.leapfrog_counts is None:
            return None
        return tuple(
            tuple(int(math.ceil(math.log2(s + 1))) for s in chain)
            for chain in self.leapfrog_counts)

    @property
    def depth_saturation_rate(self):
        """Fraction of draws whose tree hit the cap (>= 2**max_tree_depth - 1
        leapfrogs); the G-B predicate compares this against 10% (§6.7)."""
        if self.leapfrog_counts is None or self.max_tree_depth is None:
            return None
        cap = 2 ** self.max_tree_depth - 1
        flat = [s for chain in self.leapfrog_counts for s in chain]
        return sum(s >= cap for s in flat) / float(len(flat))

    # ── serialization ──

    def to_dict(self):
        """Plain-JSON payload (nested lists, no tuples/arrays)."""

        def listify(value):
            if isinstance(value, tuple):
                return [listify(v) for v in value]
            return value

        return {f.name: listify(getattr(self, f.name)) for f in fields(self)}

    def to_json(self):
        # allow_nan=False: non-finite values would serialize as the
        # non-standard NaN token and break strict JSON consumers; the
        # validation above keeps them out, this keeps them out loudly.
        return json.dumps(self.to_dict(), allow_nan=False)

    @classmethod
    def from_dict(cls, payload):
        """Inverse of to_dict, including migration of schema-version 1.

        Version 1 did not record terminal NotPSD rejections. Loading one
        therefore marks ``notpsd_rejections`` unavailable rather than
        fabricating zero. Other versions and unknown keys remain errors.
        """
        payload = dict(payload)
        known = {f.name for f in fields(cls)}
        unknown = set(payload) - known
        if unknown:
            raise ValueError(f"unknown SamplerDiagnostics keys: {sorted(unknown)}")
        version = payload.get("schema_version", SCHEMA_VERSION)
        if version == 1:
            if "notpsd_rejections" in payload:
                raise ValueError(
                    "schema_version 1 cannot contain notpsd_rejections")
            unavailable = list(payload.get("unavailable", ()))
            if "notpsd_rejections" not in unavailable:
                unavailable.append("notpsd_rejections")
            payload["notpsd_rejections"] = None
            payload["unavailable"] = unavailable
            payload["schema_version"] = SCHEMA_VERSION
        elif version != SCHEMA_VERSION:
            raise ValueError(
                f"schema_version {version} not readable by this code "
                f"(accepts 1 or {SCHEMA_VERSION})")

        def tuplify(value):
            if isinstance(value, list):
                return tuple(tuplify(v) for v in value)
            return value

        return cls(**{k: tuplify(v) for k, v in payload.items()})

    @classmethod
    def from_json(cls, text):
        return cls.from_dict(json.loads(text))


def leapfrog_counts_from_records(records):
    """Per-draw leapfrog counts from PotentialEvalTracker records.

    Only sampling-stage iterations are counted; the baseline for the first
    sampling draw is the last warmup snapshot (clean, per the probe). Without
    a warmup snapshot there is no clean baseline — the first delta would
    absorb initialization overhead and could fake depth saturation — so a
    no-warmup record stream returns None (unavailable) rather than a
    contaminated count (M2a review round, finding 2). Returns a tuple of
    counts, or None when counts cannot be derived honestly.
    """
    warmup_cums = [c for stage, _i, c in records
                   if not stage.lower().startswith("sample")]
    sample_cums = [c for stage, _i, c in records
                   if stage.lower().startswith("sample")]
    if not sample_cums or not warmup_cums:
        return None
    counts, prev = [], warmup_cums[-1]
    for c in sample_cums:
        counts.append(c - prev)
        prev = c
    return tuple(counts)


def diagnostics_from_pyro_mcmc(mcmc_run, *, sampler, n_draws, n_warmup,
                               site_names, max_tree_depth=None, step_size=None,
                               eval_records=None, notpsd_rejections=None):
    """Build SamplerDiagnostics from a finished pyro MCMC run.

    Every diagnostic the run does not expose lands in `unavailable` (honesty
    contract) — e.g. leapfrog counts require the PotentialEvalTracker hook
    (single-chain, in-process only), and a diagnostics() dict from another
    kernel may lack divergence or acceptance entries entirely.
    """
    n_chains = int(getattr(mcmc_run, "num_chains", 1))
    try:
        diag = mcmc_run.diagnostics()
    except Exception:
        diag = {}
    unavailable = []

    # A per-chain observation counts as available only when EVERY chain
    # reported it: a missing chain key silently coerced to "no divergences"
    # or a NaN acceptance would be a fabricated observation, the exact
    # failure the honesty contract exists to prevent (M2a review round,
    # finding 3).
    chain_keys = [f"chain {c}" for c in range(n_chains)]

    div = diag.get("divergences")
    if isinstance(div, dict) and all(k in div for k in chain_keys):
        divergence_draws = tuple(
            tuple(int(t) for t in div[k]) for k in chain_keys)
    else:
        divergence_draws = None
        unavailable.append("divergence_draws")

    acc = diag.get("acceptance rate")
    if (isinstance(acc, dict) and all(k in acc for k in chain_keys)
            and all(math.isfinite(float(acc[k])) for k in chain_keys)):
        acceptance_rate = tuple(float(acc[k]) for k in chain_keys)
    else:
        acceptance_rate = None
        unavailable.append("acceptance_rate")

    counts = leapfrog_counts_from_records(eval_records) if eval_records else None
    if counts is not None and n_chains == 1 and len(counts) == n_draws:
        leapfrog_counts = (counts,)
    else:
        # Multi-chain pyro runs execute hooks in worker processes, so the
        # tracker sees nothing; a record/draw-count mismatch means the hook
        # stream is not trustworthy. Both report as unavailable.
        leapfrog_counts = None
        unavailable.append("leapfrog_counts")

    if notpsd_rejections is None:
        unavailable.append("notpsd_rejections")

    return SamplerDiagnostics(
        sampler=sampler,
        n_chains=n_chains,
        n_draws=n_draws,
        n_warmup=n_warmup,
        site_names=tuple(site_names),
        max_tree_depth=max_tree_depth,
        step_size=(float(step_size) if step_size is not None else None),
        divergence_draws=divergence_draws,
        acceptance_rate=acceptance_rate,
        leapfrog_counts=leapfrog_counts,
        notpsd_rejections=notpsd_rejections,
        unavailable=tuple(unavailable),
    )

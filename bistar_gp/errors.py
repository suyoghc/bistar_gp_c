"""Exceptions shared across the package.

`EvaluationFailure` lives here rather than in `laplace_evidence` because the
modules that raise it (`laplace_evidence`, `induced_prior`, `bms_star`,
`candidates`) import one another in that direction; `laplace_evidence`
re-exports it, so existing imports keep working (fix pass 2a, SYNTHESIS A-2).
"""


class EvaluationFailure(RuntimeError):
    """A candidate predictor, divergence metric or candidate fit failed, and
    no valid number exists for the quantity that needed it.

    Raised under strict evaluation, and wherever a failure would otherwise be
    replaced by a substitute value (a penalty, a preset parameter, a uniform
    weight). A subclass of RuntimeError so that callers catching the earlier
    exception still do; the optimizer fallback handlers in `laplace_evidence`
    re-raise it so it can never turn into a start-point expansion.
    """

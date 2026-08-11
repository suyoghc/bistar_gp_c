#!/usr/bin/env python3
"""Regenerate the Case B Occam-dial figure and its numeric artifact.

The three arms reproduce the D17 attribution ladder at n=50 on the shared
informative-config, MAP-based averaged GP. The local viz_unification table,
when available, provides only a cross-check; all plotted values come from
fresh calls to the repository's scoring machinery.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
VIZ_SCRIPTS = REPO_ROOT / "bistar_viz" / "scripts"
if str(VIZ_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(VIZ_SCRIPTS))

import _viz_spaces as V  # noqa: E402


MODEL_NAMES = ["Linear", "Sinusoidal", "Sin+Linear", "Quadratic"]
DEFAULT_OUT_DIR = REPO_ROOT / "runs" / "occam_dial"
TAU = 0.3
DATA_SEED = 42
IS_SEED = 0
N_IS = 40_000
N_DRAWS = 150
N_PERTURB = 5
ANCHOR_TOLERANCE = 0.003
ANCHORS = {
    "p1_priors_lap_occam": {"Linear": 0.534, "Sin+Linear": 0.382},
    "p2_priors_is_occam": {"Linear": 0.507, "Sin+Linear": 0.465},
    "p3_priors_canonical": {"Sin+Linear": 0.992},
}


def _native(value: Any) -> Any:
    """Convert NumPy containers and scalars into JSON-native values."""
    if isinstance(value, dict):
        return {str(k): _native(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_native(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer, np.bool_)):
        return value.item()
    return value


def build_map_gp():
    """Build the n=50 averaged GP with the D17 visualization recipe."""
    x_eval = np.linspace(-10.0, 10.0, 80)
    x_50, y_50 = V.generate_data(50, seed=DATA_SEED)
    avg_gp, retained = V.averaged_gp(
        x_eval,
        x_50,
        y_50,
        gp_method="map",
        n_draws=N_DRAWS,
        seed=DATA_SEED,
    )
    return x_eval, x_50, y_50, avg_gp, retained


def _arm(
    spaces,
    x_eval,
    avg_gp,
    starts_map,
    *,
    estimator: str,
    occam: bool,
    n_is: int,
) -> dict[str, Any]:
    names, log_z, posterior, diagnostics = V.model_prior_curves(
        spaces,
        x_eval,
        avg_gp,
        [TAU],
        estimator=estimator,
        occam=occam,
        seed=IS_SEED,
        n_is=n_is,
        starts_map=starts_map,
    )
    return {
        "estimator": estimator,
        "occam": occam,
        "log_Z_M": {name: float(log_z[0, j]) for j, name in enumerate(names)},
        "model_posterior": {
            name: float(posterior[0, j]) for j, name in enumerate(names)
        },
        "ess": {
            name: None
            if diagnostics[name] is None
            else float(diagnostics[name][0])
            for name in names
        },
    }


def _assert_anchors(arms: dict[str, dict[str, Any]], tolerance: float) -> dict:
    checks = {}
    for arm_name, expected_by_model in ANCHORS.items():
        checks[arm_name] = {}
        for model_name, expected in expected_by_model.items():
            actual = arms[arm_name]["model_posterior"][model_name]
            error = abs(actual - expected)
            passed = error <= tolerance
            checks[arm_name][model_name] = {
                "expected": expected,
                "actual": actual,
                "absolute_error": error,
                "passed": passed,
            }
            if not passed:
                raise AssertionError(
                    f"{arm_name} {model_name}: {actual:.6f} differs from "
                    f"anchor {expected:.3f} by {error:.6f}, above {tolerance}"
                )
    return checks


def _crosscheck_local_table(
    arms: dict[str, dict[str, Any]], tolerance: float
) -> dict[str, Any]:
    """Compare against the optional local D17 table without sourcing data."""
    path = REPO_ROOT / "runs" / "viz_unification" / "delta_table.md"
    if not path.exists():
        return {"available": False, "path": str(path.relative_to(REPO_ROOT))}

    rows: dict[str, list[float]] = {}
    wanted = {f"{arm_name}/n=50" for arm_name in arms}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"\|\s*([^|]+?)\s*\|\s*(.+)\|$", line)
        if not match or match.group(1).strip() not in wanted:
            continue
        key = match.group(1).strip()
        values = [float(v.strip()) for v in match.group(2).split("|")]
        if len(values) == len(MODEL_NAMES):
            rows[key] = values

    checks = {}
    for arm_name in arms:
        key = f"{arm_name}/n=50"
        if key not in rows:
            checks[arm_name] = {"found": False}
            continue
        errors = {
            model: abs(arms[arm_name]["model_posterior"][model] - rows[key][j])
            for j, model in enumerate(MODEL_NAMES)
        }
        passed = max(errors.values()) <= tolerance
        checks[arm_name] = {
            "found": True,
            "table_values": dict(zip(MODEL_NAMES, rows[key])),
            "absolute_errors": errors,
            "passed": passed,
        }
        if not passed:
            raise AssertionError(
                f"fresh {arm_name} values do not match the optional local "
                f"D17 table within {tolerance}"
            )
    return {
        "available": True,
        "path": str(path.relative_to(REPO_ROOT)),
        "checks": checks,
    }


def _plot(arms: dict[str, dict[str, Any]], out_path: Path) -> None:
    colors = [V.COLORS[name] for name in MODEL_NAMES]
    panels = [
        (
            "p1_priors_lap_occam",
            "p1: pure Laplace\noccam=True",
            0.82,
        ),
        (
            "p2_priors_is_occam",
            "p2: IS\noccam=True",
            0.52,
        ),
        (
            "p3_priors_canonical",
            "p3: IS\noccam=False",
            0.88,
        ),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(15.8, 7.4), sharey=True)
    for panel_index, (ax, (arm_name, title, alpha)) in enumerate(
        zip(axes, panels)
    ):
        values = [arms[arm_name]["model_posterior"][name] for name in MODEL_NAMES]
        bars = ax.bar(
            np.arange(len(MODEL_NAMES)),
            values,
            color=colors,
            alpha=alpha,
            edgecolor="white",
            linewidth=1.3,
        )
        for bar, value in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value + 0.018,
                f"{value:.3f}",
                ha="center",
                va="bottom",
                fontsize=10,
                fontweight="bold",
            )
        ax.axhline(0.25, color="#6b7280", ls="--", lw=1, alpha=0.55)
        ax.set_xticks(np.arange(len(MODEL_NAMES)))
        ax.set_xticklabels(MODEL_NAMES, rotation=22, ha="right")
        ax.set_ylim(0.0, 1.08)
        ax.set_title(title, fontsize=13, fontweight="bold")
        ax.grid(axis="y", alpha=0.16)
        if panel_index == 0:
            ax.set_ylabel("Induced model prior", fontsize=12)

    fig.suptitle(
        "Occam convention changes the informative-config, MAP-based model prior at n = 50",
        fontsize=15,
        fontweight="bold",
        y=0.965,
    )
    fig.text(
        0.5,
        0.875,
        "p1 to p2 changes the Z_M estimator; p2 to p3 changes the occam convention",
        ha="center",
        fontsize=11.5,
        color="#374151",
    )
    fig.text(
        0.5,
        0.105,
        "Nesting: Linear ⊂ Sin+Linear at A=0; Sinusoidal ⊂ Sin+Linear at b=c=0; "
        "Quadratic not nested.",
        ha="center",
        fontsize=10.5,
    )
    fig.text(
        0.5,
        0.062,
        "The comparison evaluates the occam convention, not which model generated the data.",
        ha="center",
        fontsize=10.5,
        fontweight="bold",
    )
    fig.text(
        0.5,
        0.022,
        "D17 legacy context, not recomputed here: trajectory Sin+Linear 0.934; "
        "priors Linear 0.693.",
        ha="center",
        fontsize=9,
        color="#4b5563",
    )
    fig.subplots_adjust(left=0.075, right=0.985, bottom=0.22, top=0.79, wspace=0.1)
    fig.savefig(out_path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _fmt_posteriors(arm: dict[str, Any]) -> str:
    return ", ".join(
        f"{name} {arm['model_posterior'][name]:.6f}" for name in MODEL_NAMES
    )


def write_combined_readme(out_dir: Path) -> None:
    """Write one run-directory README from whichever Case B artifacts exist."""
    figure_path = out_dir / "figure_results.json"
    e6_path = out_dir / "e6_results.json"
    figure = json.loads(figure_path.read_text(encoding="utf-8")) if figure_path.exists() else None
    e6 = json.loads(e6_path.read_text(encoding="utf-8")) if e6_path.exists() else None

    lines = [
        "# Case B: Occam dial and nesting monotonicity",
        "",
        "Regenerate from the repository root:",
        "",
        "```bash",
        "python experiments/occam_dial_figure.py",
        "python experiments/e6_nesting_monotonicity.py",
        "```",
        "",
        "Both scripts use local CPU computation only. They construct the n=50 averaged GP with "
        "`PRIOR_CONFIGS[\"informative\"]`, `gp_method=\"map\"`, data seed 42, 80 "
        "evaluation points over [-10, 10], and the primary `pw_kl_vcal` metric. MAP retains "
        "one GP predictive. The scripts import the shared construction from "
        "`bistar_viz/scripts/_viz_spaces.py` and the existing evidence machinery from "
        "`bistar_gp/laplace_evidence.py`.",
        "",
        "## Figure computation",
        "",
        "`occam_dial.png` and `figure_results.json` use τ=0.3, IS seed 0, "
        "n_is=40,000, five seeded perturbations per legacy start, and the canonical "
        "visualization parameter boxes. The optional `runs/viz_unification/delta_table.md` "
        "only supplies a cross-check when present.",
        "",
        "The anchor tolerance equals 0.003 in absolute model probability. The published "
        "anchors were rounded to three decimals, and the remaining allowance covers small "
        "cross-platform optimizer differences. The tolerance remains well below the 0.042 "
        "p2 Linear versus Sin+Linear gap.",
    ]
    if figure is not None:
        lines.extend(["", "Fresh n=50 posteriors:", ""])
        for arm_name in (
            "p1_priors_lap_occam",
            "p2_priors_is_occam",
            "p3_priors_canonical",
        ):
            lines.append(f"- `{arm_name}`: {_fmt_posteriors(figure['arms'][arm_name])}")
        cross = figure["optional_local_crosscheck"]
        lines.extend(
            [
                "",
                f"The optional D17 table cross-check was {'available' if cross['available'] else 'not available'}.",
            ]
        )

    lines.extend(
        [
            "",
            "The D17-recorded legacy 0.934 and 0.693 values provide historical context only. "
            "`bistar_viz/scripts/viz_unification_compare.py`, with pinned legacy commit "
            "`a87356a`, regenerates those legacy arms. Neither new script invokes that "
            "git-based extraction path.",
            "",
            "## E6 computation",
            "",
            "E6 uses 161 log-spaced τ values from 10^-1.5 through 10^2.5, IS seed 0, "
            "n_is=100,000, and the same five perturbations per start. One "
            "`is_log_Z_Mx` call per model computes the full raw sweep; the package's "
            "`_log_reference_volume` helper supplies the occam-normalized sweep. The visualization "
            "box uses A >= 0.01 for numerical plotting. E6 alone extends the encompassing "
            "Sin+Linear box to A >= 0 so Linear at A=0 forms an exact restriction. All "
            "other bounds match the canonical visualization boxes. The embedded restricted "
            "optima seed the encompassing multi-start optimization. IS uses interior perturbed "
            "starts plus the best encompassing optimum, which avoids flat boundary-Hessian "
            "components without changing the integral.",
            "",
            "The min-Ḡ comparison tolerance equals 1e-8 in Ḡ units. It only classifies "
            "floating-point near-ties and remains many orders of magnitude below the observed "
            "margins. τ crossings use linear interpolation in log10(τ) inside the reported "
            "adjacent grid bracket; the bracket, rather than extra decimal places in the "
            "interpolant, provides the resolution statement.",
        ]
    )
    if e6 is not None:
        lines.extend(["", "Fresh E6 results:", ""])
        for pair_name, pair in e6["nested_pairs"].items():
            lines.append(
                f"- `{pair_name}`: min Ḡ(restricted)={pair['restricted']['min_Gbar']:.9f}, "
                f"min Ḡ(encompassing)={pair['encompassing']['min_Gbar']:.9f}, "
                f"margin={pair['margin_restricted_minus_encompassing']:.9f}, "
                f"holds={pair['inequality_holds']}."
            )
            for convention in ("occam_false", "occam_true"):
                crossing_text = ", ".join(
                    f"{item['tau_log_interpolated']:.6f} within "
                    f"[{item['tau_bracket'][0]:.6f}, {item['tau_bracket'][1]:.6f}]"
                    for item in pair["Z_M_ordering"][convention]["crossings"]
                ) or "no crossing on the grid"
                lines.append(f"  - `{convention}`: {crossing_text}.")
        lines.extend(
            [
                "",
                f"E6 verdict: {e6['verdict']['statement']}",
            ]
        )

    lines.extend(
        [
            "",
            "## Files",
            "",
            "- `occam_dial.png`: E4 attribution-ladder figure, kept below 2 MB.",
            "- `figure_results.json`: all freshly computed E4 arm values and anchor checks.",
            "- `e6_results.json`: min-Ḡ optima, exact-embedding checks, both Z_M conventions, "
            "ESS diagnostics, the full τ grid, and crossing brackets.",
        ]
    )
    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(out_dir: Path, *, n_is: int, anchor_tolerance: float) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    x_eval, _x_50, _y_50, avg_gp, retained = build_map_gp()
    spaces = V.canonical_spaces()
    starts_map = {
        name: V.perturbed_starts(name, spaces, N_PERTURB, seed=DATA_SEED)
        for name in MODEL_NAMES
    }

    arms = {
        "p1_priors_lap_occam": _arm(
            spaces,
            x_eval,
            avg_gp,
            starts_map,
            estimator="laplace",
            occam=True,
            n_is=n_is,
        ),
        "p2_priors_is_occam": _arm(
            spaces,
            x_eval,
            avg_gp,
            starts_map,
            estimator="is",
            occam=True,
            n_is=n_is,
        ),
        "p3_priors_canonical": _arm(
            spaces,
            x_eval,
            avg_gp,
            starts_map,
            estimator="is",
            occam=False,
            n_is=n_is,
        ),
    }
    anchor_checks = _assert_anchors(arms, anchor_tolerance)
    local_crosscheck = _crosscheck_local_table(arms, anchor_tolerance)

    results = {
        "schema_version": 1,
        "case": "B",
        "artifact": "occam_dial_figure",
        "provenance": {
            "gp_config": "informative",
            "gp_method": "map",
            "metric": "pw_kl_vcal",
            "n": 50,
            "data_seed": DATA_SEED,
            "is_seed": IS_SEED,
            "x_eval_count": len(x_eval),
            "x_eval_range": [float(x_eval[0]), float(x_eval[-1])],
            "tau": TAU,
            "n_draws_requested": N_DRAWS,
            "gp_predictives_retained": retained,
            "n_is": n_is,
            "n_perturb": N_PERTURB,
            "spaces": "bistar_viz/scripts/_viz_spaces.py:canonical_spaces",
            "evidence": "bistar_gp/laplace_evidence.py",
        },
        "arms": arms,
        "anchor_tolerance_absolute_probability": anchor_tolerance,
        "anchor_checks": anchor_checks,
        "optional_local_crosscheck": local_crosscheck,
        "legacy_context_not_recomputed": {
            "source": "Notes/DECISIONS.md D17",
            "legacy_trajectory_Sin+Linear_n50": 0.934,
            "legacy_priors_Linear_n50": 0.693,
            "regeneration_script": "bistar_viz/scripts/viz_unification_compare.py",
            "pinned_legacy_commit": "a87356a",
        },
        "interpretation_scope": (
            "informative-config, MAP-based methods-validation and legacy-comparison "
            "material; the comparison evaluates the occam convention, not which "
            "model generated the data"
        ),
    }
    json_path = out_dir / "figure_results.json"
    json_path.write_text(
        json.dumps(_native(results), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    figure_path = out_dir / "occam_dial.png"
    _plot(arms, figure_path)
    if figure_path.stat().st_size >= 2_000_000:
        raise AssertionError(f"{figure_path} exceeds the 2 MB figure limit")
    write_combined_readme(out_dir)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--n-is", type=int, default=N_IS)
    parser.add_argument(
        "--anchor-tolerance", type=float, default=ANCHOR_TOLERANCE
    )
    args = parser.parse_args()
    results = run(
        args.out_dir.resolve(),
        n_is=args.n_is,
        anchor_tolerance=args.anchor_tolerance,
    )
    print("n=50 model posteriors")
    for arm_name, arm in results["arms"].items():
        print(f"  {arm_name}: {_fmt_posteriors(arm)}")
    print(f"wrote {args.out_dir.resolve() / 'figure_results.json'}")
    print(f"wrote {args.out_dir.resolve() / 'occam_dial.png'}")


if __name__ == "__main__":
    main()

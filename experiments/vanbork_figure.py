#!/usr/bin/env python3
"""Re-plot the committed van Bork external-validation artifact."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter


ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = ROOT / "runs" / "vanbork_external_validation" / "results.json"
OUTPUT_PATH = ROOT / "runs" / "vanbork_external_validation" / "target_figure.png"

# Author-specified, validated colorblind-safe pair.
OURS = "#2E6FB8"
THEIRS = "#C4356B"


def row_at_tau(rows: list[dict[str, float]], tau: float) -> dict[str, float]:
    """Return the unique artifact row at tau without interpolating."""
    matches = [row for row in rows if row["tau"] == tau]
    assert len(matches) == 1, f"Expected exactly one artifact row at tau={tau!r}"
    return matches[0]


def main() -> None:
    artifact = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    target_a = artifact["target_a"]
    target_b = artifact["target_b"]

    min_tau = min(artifact["taus"])
    model_a_names = tuple(target_a["names"])
    routes = (
        ("rows_pooled", "Pooled\n(failing)"),
        ("rows_perdraw", "Eq. 4 per atom\n(exact)"),
        (
            "rows_shipped_npd_true",
            "Shipped\nnormalize_per_draw=True\n(exact)",
        ),
    )

    panel_a_rows = tuple(row_at_tau(target_a[key], min_tau) for key, _ in routes)
    panel_a_values = tuple(
        tuple(row[name] for name in model_a_names) for row in panel_a_rows
    )
    panel_a_targets = tuple(target_a["target"][name] for name in model_a_names)

    panel_b_rows = tuple(target_b["rows"])
    panel_b_taus = tuple(row["tau"] for row in panel_b_rows)
    model_b_name = target_b["names"][0]
    panel_b_values = tuple(row[model_b_name] for row in panel_b_rows)
    panel_b_target = target_b["published_weight_Mx"]
    panel_b_tick_positions = panel_b_taus[::2] + (panel_b_taus[-1],)

    # Exact-equality gate: every scientific value sent to Matplotlib is checked
    # against its corresponding scalar in the committed JSON before savefig.
    comparisons: list[tuple[float, float]] = []
    for route_index, (key, _) in enumerate(routes):
        source_row = row_at_tau(target_a[key], min_tau)
        comparisons.append((panel_a_rows[route_index]["tau"], source_row["tau"]))
        comparisons.extend(
            (panel_a_values[route_index][model_index], source_row[name])
            for model_index, name in enumerate(model_a_names)
        )
    comparisons.extend(
        (panel_a_targets[model_index], target_a["target"][name])
        for model_index, name in enumerate(model_a_names)
    )
    for row_index, source_row in enumerate(target_b["rows"]):
        comparisons.append((panel_b_taus[row_index], source_row["tau"]))
        comparisons.append((panel_b_values[row_index], source_row[model_b_name]))
    comparisons.append((panel_b_target, target_b["published_weight_Mx"]))
    assert all(plotted == source for plotted, source in comparisons), (
        "A plotted value differs from its results.json scalar"
    )

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.0,
            "axes.titlesize": 9.5,
            "axes.labelsize": 8.5,
            "axes.linewidth": 0.7,
            "xtick.labelsize": 7.5,
            "ytick.labelsize": 7.5,
            "legend.fontsize": 7.2,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )
    fig, (ax_a, ax_b) = plt.subplots(
        1,
        2,
        figsize=(7.2, 3.15),
        dpi=180,
        constrained_layout=True,
        gridspec_kw={"width_ratios": (1.08, 1.0)},
    )

    group_x = (0.0, 1.0, 2.0)
    bar_width = 0.31
    m1_bars = ax_a.bar(
        [x - bar_width / 2 for x in group_x],
        [values[0] for values in panel_a_values],
        width=bar_width,
        color=OURS,
        edgecolor=OURS,
        linewidth=0.8,
        label=r"$p(M_1)$",
        zorder=3,
    )
    m2_bars = ax_a.bar(
        [x + bar_width / 2 for x in group_x],
        [values[1] for values in panel_a_values],
        width=bar_width,
        color="white",
        edgecolor=OURS,
        linewidth=1.1,
        hatch="////",
        label=r"$p(M_2)$",
        zorder=3,
    )
    for target in panel_a_targets:
        ax_a.axhline(target, color=THEIRS, linestyle=(0, (4, 2)), linewidth=1.2, zorder=2)
    ax_a.text(
        2.46,
        panel_a_targets[0] - 0.028,
        rf"their $M_1$ target {panel_a_targets[0]:.1f}",
        color=THEIRS,
        ha="right",
        va="top",
        fontsize=6.8,
        bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.8, "alpha": 0.9},
        zorder=4,
    )
    ax_a.text(
        2.46,
        panel_a_targets[1] + 0.025,
        rf"their $M_2$ target {panel_a_targets[1]:.1f}",
        color=THEIRS,
        ha="right",
        va="bottom",
        fontsize=6.8,
        bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.8, "alpha": 0.9},
        zorder=4,
    )
    for bars, model_index in ((m1_bars, 0), (m2_bars, 1)):
        ax_a.bar_label(
            bars,
            labels=[f"{values[model_index]:.3f}" for values in panel_a_values],
            padding=2,
            fontsize=7.0,
            color="#17324D",
        )
    tau_mantissa, tau_exponent = f"{min_tau:.0e}".split("e")
    ax_a.set_title(
        rf"(a) Target A at $\tau={tau_mantissa}\times 10^{{{int(tau_exponent)}}}$",
        loc="left",
        fontweight="bold",
    )
    ax_a.set_ylabel("Model probability")
    ax_a.set_xticks(group_x, [label for _, label in routes])
    ax_a.set_xlim(-0.52, 2.52)
    ax_a.set_ylim(0.0, 1.12)
    ax_a.yaxis.set_major_formatter(FormatStrFormatter("%.1f"))
    ax_a.grid(axis="y", color="#D9DEE5", linewidth=0.6, alpha=0.7, zorder=0)
    ax_a.legend(loc="upper left", frameon=False, ncols=2, handlelength=1.4)

    ax_b.plot(
        panel_b_taus,
        panel_b_values,
        color=OURS,
        linewidth=1.8,
        marker="o",
        markersize=4.2,
        markerfacecolor="white",
        markeredgecolor=OURS,
        markeredgewidth=1.2,
        label=r"Our $p(M_x)$",
        zorder=3,
    )
    ax_b.axhline(
        panel_b_target,
        color=THEIRS,
        linestyle=(0, (4, 2)),
        linewidth=1.2,
        zorder=2,
    )
    ax_b.text(
        0.98,
        panel_b_target + 0.008,
        f"Their closed form evaluated at\ndouble precision: {panel_b_target:.6f}",
        transform=ax_b.get_yaxis_transform(),
        color=THEIRS,
        ha="right",
        va="bottom",
        fontsize=6.8,
        bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.8, "alpha": 0.9},
        zorder=4,
    )
    ax_b.set_title(r"(b) Target B across $\tau$", loc="left", fontweight="bold")
    ax_b.set_xscale("log")
    ax_b.invert_xaxis()
    ax_b.set_xticks(panel_b_tick_positions)
    ax_b.set_xlabel(r"Temperature $\tau$ (log scale)")
    ax_b.set_ylabel(r"$p(M_x)$")
    ax_b.set_ylim(0.50, 0.875)
    ax_b.yaxis.set_major_formatter(FormatStrFormatter("%.2f"))
    ax_b.grid(axis="y", color="#D9DEE5", linewidth=0.6, alpha=0.7, zorder=0)
    ax_b.legend(loc="lower right", frameon=False, handlelength=2.0)

    for ax in (ax_a, ax_b):
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.tick_params(width=0.7, length=3)

    assert OUTPUT_PATH.parent.is_dir(), "Authorized output directory is missing"
    fig.savefig(
        OUTPUT_PATH,
        dpi=240,
        format="png",
        metadata={"Software": "Matplotlib"},
        pil_kwargs={"compress_level": 9},
    )
    plt.close(fig)
    print(f"Assertion gate passed for {len(comparisons)} plotted artifact values.")
    print(f"Wrote {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

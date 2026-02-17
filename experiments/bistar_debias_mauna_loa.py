"""
BI* Debiasing: Three Interpretations of Mauna Loa CO₂

The SAME GP decomposition (trend + seasonal + medium-term) can be
interpreted differently depending on which components an analyst
labels as "truth" vs "bias":

  1. Believer:  truth = trend + seasonal + medium_term, bias = none
  2. Moderate:  truth = trend + seasonal, bias = medium_term
  3. Skeptic:   truth = seasonal, bias = trend + medium_term

BI* makes this labeling choice EXPLICIT and TRACEABLE.
The decomposition is identical — only the interpretation differs.

Usage:
    python bistar_debias_mauna_loa.py                 # runs HMC fresh
    python bistar_debias_mauna_loa.py --use-cache      # loads cached HMC samples
    python bistar_debias_mauna_loa.py --map-only        # MAP only (fast)
"""

import sys, os, argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import torch
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

from bistar_gp import load_mauna_loa, build_model
from bistar_gp.model import build_mauna_loa_kernels, build_likelihood
from bistar_gp.fit import fit_map, print_hyperparameters, fit_hmc
from bistar_gp.debias import decompose_model, decompose_model_hmc

torch.set_default_dtype(torch.float64)


# ═══════════════════════════════════════════════════════════════════
# Interpretation definitions
# ═══════════════════════════════════════════════════════════════════

INTERPRETATIONS = {
    "Believer": {
        "truth": ["trend", "seasonal", "medium_term"],
        "bias": [],
        "description": (
            "All components are real signal.\n"
            "CO₂ rises due to emissions (trend),\n"
            "seasonal photosynthesis (seasonal),\n"
            "and ENSO/volcanos (medium-term)."
        ),
        "color_truth": "#2ecc71",
        "color_bias": "#e74c3c",
    },
    "Moderate": {
        "truth": ["trend", "seasonal"],
        "bias": ["medium_term"],
        "description": (
            "Trend and seasonal are real.\n"
            "Medium-term fluctuations are\n"
            "natural variability (bias) obscuring\n"
            "the true trend + seasonal signal."
        ),
        "color_truth": "#3498db",
        "color_bias": "#e67e22",
    },
    "Skeptic": {
        "truth": ["seasonal"],
        "bias": ["trend", "medium_term"],
        "description": (
            "Only the seasonal cycle is real\n"
            "(tied to biology). The long-term\n"
            "'trend' could be measurement drift,\n"
            "station effects, or urban heat island."
        ),
        "color_truth": "#9b59b6",
        "color_bias": "#e74c3c",
    },
}


def compute_debiased(result, truth_components, bias_components):
    """
    Combine components labeled as truth → debiased signal.
    Combine components labeled as bias → removed bias.
    """
    n_test = len(result.x_test)

    # Truth
    truth_mean = np.zeros(n_test)
    truth_var = np.zeros(n_test)
    for name in truth_components:
        if name in result.components:
            comp = result.components[name]
            truth_mean += comp.mean
            truth_var += comp.std ** 2  # independent components

    # Bias
    bias_mean = np.zeros(n_test)
    bias_var = np.zeros(n_test)
    for name in bias_components:
        if name in result.components:
            comp = result.components[name]
            bias_mean += comp.mean
            bias_var += comp.std ** 2

    return {
        "truth_mean": truth_mean,
        "truth_std": np.sqrt(truth_var),
        "bias_mean": bias_mean,
        "bias_std": np.sqrt(bias_var),
    }


def plot_three_interpretations(result, x_test_held=None, y_test_held=None,
                                info=None, figsize=(18, 14)):
    """
    3-column figure. Each column = one interpretation.
    Row 1: Full data + debiased signal
    Row 2: What's labeled as "truth" (green/blue/purple)
    Row 3: What's labeled as "bias" (red/orange)
    """
    fig = plt.figure(figsize=figsize)
    gs = GridSpec(3, 3, figure=fig, hspace=0.35, wspace=0.3)

    x = result.x_test
    interp_names = list(INTERPRETATIONS.keys())

    for col, interp_name in enumerate(interp_names):
        interp = INTERPRETATIONS[interp_name]
        debiased = compute_debiased(
            result, interp["truth"], interp["bias"]
        )

        # ── Row 0: Full data + debiased overlay ──────────────
        ax0 = fig.add_subplot(gs[0, col])

        # Raw data
        ax0.scatter(result.x_train, result.y_train,
                    c='black', marker='x', s=15, alpha=0.3, zorder=3)
        if x_test_held is not None:
            ax0.scatter(x_test_held, y_test_held,
                        c='red', marker='.', s=10, alpha=0.5, zorder=3)

        # Full GP prediction (gray)
        ax0.plot(x, result.full_mean, color='gray', linewidth=1, alpha=0.5,
                 label='Full GP')

        # Debiased signal
        ct = interp["color_truth"]
        ax0.plot(x, debiased["truth_mean"], color=ct, linewidth=2.5,
                 label='"Truth" signal')
        ax0.fill_between(x,
                         debiased["truth_mean"] - 2 * debiased["truth_std"],
                         debiased["truth_mean"] + 2 * debiased["truth_std"],
                         alpha=0.2, color=ct)

        # Train/test boundary
        x_split = result.x_train.max()
        ax0.axvline(x_split, color='gray', linestyle=':', linewidth=1.5, alpha=0.7)
        ylims = ax0.get_ylim()
        ax0.text(x_split, ylims[1] * 0.95, ' forecast →', fontsize=7,
                 color='gray', ha='left', va='top')
        ax0.text(x_split, ylims[1] * 0.95, '← train ', fontsize=7,
                 color='gray', ha='right', va='top')

        ax0.set_title(f"{interp_name}", fontsize=14, fontweight='bold')
        ax0.legend(fontsize=7, loc='upper left')
        ax0.set_ylabel("CO₂ (normalized)")
        if col == 0:
            ax0.set_ylabel("Debiased signal\n+ data", fontsize=11)

        # ── Row 1: Truth components ──────────────────────────
        ax1 = fig.add_subplot(gs[1, col])

        if interp["truth"]:
            for name in interp["truth"]:
                if name in result.components:
                    comp = result.components[name]
                    ax1.plot(x, comp.mean, linewidth=1.5, label=name)
                    ax1.fill_between(x, comp.mean - 2*comp.std,
                                     comp.mean + 2*comp.std, alpha=0.15)

            # Combined truth
            ax1.plot(x, debiased["truth_mean"], color=ct, linewidth=2.5,
                     linestyle='--', label='combined truth', alpha=0.7)

        ax1.set_title(f"k_truth: {', '.join(interp['truth']) or 'none'}",
                       fontsize=10)
        ax1.legend(fontsize=7, loc='best')
        if col == 0:
            ax1.set_ylabel("\"Truth\" components", fontsize=11)
        ax1.grid(True, alpha=0.2)

        # ── Row 2: Bias components ───────────────────────────
        ax2 = fig.add_subplot(gs[2, col])
        cb = interp["color_bias"]

        if interp["bias"]:
            for name in interp["bias"]:
                if name in result.components:
                    comp = result.components[name]
                    ax2.plot(x, comp.mean, linewidth=1.5, label=name)
                    ax2.fill_between(x, comp.mean - 2*comp.std,
                                     comp.mean + 2*comp.std, alpha=0.15)

            # Combined bias
            ax2.plot(x, debiased["bias_mean"], color=cb, linewidth=2.5,
                     linestyle='--', label='combined bias', alpha=0.7)
        else:
            ax2.text(0.5, 0.5, "No bias components",
                     ha='center', va='center', transform=ax2.transAxes,
                     fontsize=12, color='gray', style='italic')

        ax2.set_title(f"k_bias: {', '.join(interp['bias']) or 'none'}",
                       fontsize=10)
        ax2.legend(fontsize=7, loc='best')
        ax2.set_xlabel("Time (normalized)")
        if col == 0:
            ax2.set_ylabel("\"Bias\" components", fontsize=11)
        ax2.grid(True, alpha=0.2)

    fig.suptitle(
        "BI* Debiasing: Same Decomposition, Three Interpretations\n"
        "The GP posterior is identical — only the truth/bias labeling differs",
        fontsize=15, y=1.02
    )
    return fig


def plot_debiased_comparison(result, info, figsize=(16, 5)):
    """
    Single row: the debiased signal from each interpretation,
    denormalized back to ppm for physical intuition.
    """
    fig, axes = plt.subplots(1, 3, figsize=figsize, sharey=True)

    x = result.x_test
    # Denormalize x back to years
    x_years = x + info["x_offset"] if info else x

    for ax, (interp_name, interp) in zip(axes, INTERPRETATIONS.items()):
        debiased = compute_debiased(result, interp["truth"], interp["bias"])

        # Denormalize y back to ppm
        if info and info["y_std"] != 1.0:
            mean_ppm = debiased["truth_mean"] * info["y_std"] + info["y_mean"]
            std_ppm = debiased["truth_std"] * info["y_std"]
        else:
            mean_ppm = debiased["truth_mean"]
            std_ppm = debiased["truth_std"]

        ct = interp["color_truth"]
        ax.plot(x_years, mean_ppm, color=ct, linewidth=2.5)
        ax.fill_between(x_years, mean_ppm - 2*std_ppm, mean_ppm + 2*std_ppm,
                         alpha=0.2, color=ct)

        # Train/test boundary
        x_boundary = (result.x_train.max() + info["x_offset"]) if info else result.x_train.max()
        ax.axvline(x_boundary, color='gray', linestyle=':', linewidth=1.5, alpha=0.7)
        ylims = ax.get_ylim()
        ax.text(x_boundary, ylims[1] - (ylims[1]-ylims[0])*0.05,
                ' forecast →', fontsize=7, color='gray', ha='left', va='top')

        ax.set_title(f"{interp_name}", fontsize=13, fontweight='bold')
        ax.set_xlabel("Year")
        ax.grid(True, alpha=0.2)

        # Annotate
        ax.text(0.02, 0.98, interp["description"],
                transform=ax.transAxes, fontsize=7,
                verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    axes[0].set_ylabel("CO₂ (ppm)")

    fig.suptitle(
        'BI* Makes the "What is bias?" Question Explicit and Traceable',
        fontsize=14
    )
    fig.tight_layout()
    return fig


def plot_residuals_comparison(result, info, figsize=(16, 5)):
    """
    For each interpretation, show what the 'bias' looks like
    when denormalized — is it plausible as measurement artifact?
    """
    fig, axes = plt.subplots(1, 3, figsize=figsize, sharey=False)

    x = result.x_test
    x_years = x + info["x_offset"] if info else x

    for ax, (interp_name, interp) in zip(axes, INTERPRETATIONS.items()):
        debiased = compute_debiased(result, interp["truth"], interp["bias"])

        if not interp["bias"]:
            ax.text(0.5, 0.5, "No bias\n(everything is signal)",
                    ha='center', va='center', transform=ax.transAxes,
                    fontsize=14, color='gray', style='italic')
            ax.set_title(f"{interp_name}: Removed bias", fontsize=11)
            ax.set_xlabel("Year")
            continue

        # Denormalize bias to ppm
        if info and info["y_std"] != 1.0:
            bias_ppm = debiased["bias_mean"] * info["y_std"]
            bias_std_ppm = debiased["bias_std"] * info["y_std"]
        else:
            bias_ppm = debiased["bias_mean"]
            bias_std_ppm = debiased["bias_std"]

        cb = interp["color_bias"]
        ax.plot(x_years, bias_ppm, color=cb, linewidth=2)
        ax.fill_between(x_years, bias_ppm - 2*bias_std_ppm,
                         bias_ppm + 2*bias_std_ppm, alpha=0.2, color=cb)
        ax.axhline(0, color='gray', linestyle='--', alpha=0.5)

        # Train/test boundary
        x_boundary = (result.x_train.max() + info["x_offset"]) if info else result.x_train.max()
        ax.axvline(x_boundary, color='gray', linestyle=':', linewidth=1.5, alpha=0.7)

        # Scale annotation
        bias_range = bias_ppm.max() - bias_ppm.min()
        ax.set_title(f"{interp_name}: Removed 'bias'\n(range: {bias_range:.1f} ppm)",
                     fontsize=11)
        ax.set_xlabel("Year")
        ax.grid(True, alpha=0.2)

    axes[0].set_ylabel("'Bias' (ppm)")

    fig.suptitle(
        "What Each Interpretation Removes as Bias",
        fontsize=14
    )
    fig.tight_layout()
    return fig


def main():
    parser = argparse.ArgumentParser(description="BI* Debiasing: Mauna Loa")
    parser.add_argument("--map-only", action="store_true")
    parser.add_argument("--use-cache", type=str, default=None,
                        help="Path to cached HMC samples (.pt)")
    parser.add_argument("--n-hmc", type=int, default=100)
    parser.add_argument("--n-warmup", type=int, default=100)
    parser.add_argument("--output-dir", type=str, default="results_debias_mauna_loa")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    print("=" * 60)
    print("  BI* Debiasing: Three Interpretations of Mauna Loa CO₂")
    print("=" * 60)

    # ── 1. Load data ──────────────────────────────────────────────
    x_train, y_train, x_test, y_test, info = load_mauna_loa(
        normalize=True, test_years=5.0
    )
    print(f"\n  Train: {len(x_train)}, Test: {len(x_test)}")

    x_all = torch.cat([x_train, x_test])
    x_pred = torch.linspace(x_all.min().item() - 1,
                            x_all.max().item() + 1, 500).double()

    if args.map_only:
        # ── MAP decomposition ────────────────────────────────
        print("\n── MAP Decomposition ──")
        kernels, names = build_mauna_loa_kernels()
        likelihood = build_likelihood()
        model, likelihood = build_model(x_train, y_train, kernels, names, likelihood)
        fit_map(model, likelihood, x_train, y_train, n_iter=800, lr=0.02, print_every=200)
        print_hyperparameters(model, likelihood)

        result = decompose_model(model, likelihood, x_train, y_train,
                                 x_pred, n_samples=25)
        method_label = "MAP"

    else:
        # ── HMC decomposition ────────────────────────────────
        if args.use_cache and os.path.exists(args.use_cache):
            print(f"\n  Loading cached HMC samples: {args.use_cache}")
            mcmc_samples = torch.load(args.use_cache, weights_only=False)
        else:
            print(f"\n── Running HMC ({args.n_hmc} samples, {args.n_warmup} warmup) ──")
            kernels, names = build_mauna_loa_kernels()
            likelihood = build_likelihood()
            model_map, likelihood_map = build_model(x_train, y_train, kernels, names, likelihood)
            fit_map(model_map, likelihood_map, x_train, y_train,
                    n_iter=800, lr=0.02, print_every=200)

            kernels2, names2 = build_mauna_loa_kernels()
            likelihood2 = build_likelihood()
            model2, likelihood2 = build_model(x_train, y_train, kernels2, names2, likelihood2)

            mcmc_samples = fit_hmc(model2, likelihood2, x_train, y_train,
                                   n_samples=args.n_hmc, n_warmup=args.n_warmup)

            # Cache for reuse
            cache_path = os.path.join(args.output_dir, "hmc_samples.pt")
            torch.save(mcmc_samples, cache_path)
            print(f"  Cached: {cache_path}")

        print("\n── Decomposing HMC samples ──")
        kernels3, names3 = build_mauna_loa_kernels()
        likelihood3 = build_likelihood()
        model3, likelihood3 = build_model(x_train, y_train, kernels3, names3, likelihood3)

        result = decompose_model_hmc(
            model3, likelihood3, x_train, y_train, x_pred,
            mcmc_samples, kernel_builder=build_mauna_loa_kernels,
            n_posterior_samples=100,
        )
        method_label = "HMC"

    # ── 2. Print component summaries ──────────────────────────────
    print(f"\n── Component Summaries ({method_label}) ──")
    for name, comp in result.components.items():
        range_norm = comp.mean.max() - comp.mean.min()
        range_ppm = range_norm * info["y_std"]
        print(f"  {name:15s}: range = {range_norm:.4f} (normalized) = {range_ppm:.2f} ppm")

    # ── 3. Three interpretations ──────────────────────────────────
    print("\n── Interpretations ──")
    for interp_name, interp in INTERPRETATIONS.items():
        debiased = compute_debiased(result, interp["truth"], interp["bias"])
        truth_range = (debiased["truth_mean"].max() - debiased["truth_mean"].min()) * info["y_std"]
        bias_range = (debiased["bias_mean"].max() - debiased["bias_mean"].min()) * info["y_std"]
        print(f"\n  {interp_name}:")
        print(f"    k_truth = {interp['truth']}")
        print(f"    k_bias  = {interp['bias']}")
        print(f"    Debiased signal range: {truth_range:.2f} ppm")
        print(f"    Removed bias range:    {bias_range:.2f} ppm")

    # ── 4. Plots ──────────────────────────────────────────────────
    print("\n── Generating Plots ──")

    # Main 3×3 figure
    fig1 = plot_three_interpretations(
        result, x_test.numpy(), y_test.numpy(), info
    )
    path1 = os.path.join(args.output_dir, f"bistar_three_interpretations_{method_label.lower()}.png")
    fig1.savefig(path1, bbox_inches="tight", dpi=150)
    print(f"  Saved: {path1}")

    # Debiased comparison (denormalized to ppm)
    fig2 = plot_debiased_comparison(result, info)
    path2 = os.path.join(args.output_dir, f"bistar_debiased_ppm_{method_label.lower()}.png")
    fig2.savefig(path2, bbox_inches="tight", dpi=150)
    print(f"  Saved: {path2}")

    # Residuals (what was removed as bias)
    fig3 = plot_residuals_comparison(result, info)
    path3 = os.path.join(args.output_dir, f"bistar_removed_bias_{method_label.lower()}.png")
    fig3.savefig(path3, bbox_inches="tight", dpi=150)
    print(f"  Saved: {path3}")

    plt.close("all")

    # ── 5. Summary ────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("  Key Point for Paper")
    print(f"{'='*60}")
    print("""
  The GP decomposition is IDENTICAL across all three panels.
  Same data, same kernel, same posterior, same HMC samples.

  The ONLY difference is which components the analyst labels
  as "truth" (k_truth) vs "bias" (k_bias).

  BI* contribution: this labeling is now EXPLICIT.
  - Traditional analysis: bias assumptions are buried in
    preprocessing, model specification, or unstated beliefs
  - BI*: the decomposition separates components, and the
    analyst must explicitly choose which to trust

  The skeptic's interpretation removes ~{:.0f} ppm of "bias"
  (the entire upward trend). Whether that's scientifically
  defensible is a separate question — but BI* forces it
  into the open where it can be examined and debated.
    """.format(
        (result.components["trend"].mean.max() - result.components["trend"].mean.min()) * info["y_std"]
    ))

    print(f"  Results in: {args.output_dir}/")
    print("  Done!")


if __name__ == "__main__":
    main()

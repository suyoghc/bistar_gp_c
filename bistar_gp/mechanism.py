"""
Mechanism figures for BI*: How GP hyperparameter beliefs
transfer into parametric model parameter priors.

Design:
    TransferChannel — one GP hyperparameter → one induced model parameter
    MechanismConfig — collection of channels + display settings
    Pre-built configs: TOY_MECHANISM, MAUNA_LOA_MECHANISM

Core computation:
    For each GP posterior sample ψ_i:
        1. Extract GP predictive mean
        2. Fit candidate model to that mean
        3. Collect fitted parameters → induced prior samples

Integration:
    - Works with run_manager.py (save/load from run directories)
    - Works with any dataset/subsample (config specifies what to show)
    - Fully declarative: specify channels, get figures
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Tuple, Any
import json
import warnings


# ═══════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════

@dataclass
class TransferChannel:
    """
    One belief transfer channel: GP hyperparameter → induced model parameter.

    Example:
        TransferChannel(
            hp_pattern="lengthscale",           # substring match in HP keys
            hp_label="SE Lengthscale ℓ",        # display label
            candidate_name="Sin+Linear",        # which candidate
            param_name="omega",                 # which fitted param
            param_label="ω (frequency)",        # display label
            true_value=1.0,                     # ground truth (if known)
            hp_transform=None,                  # optional: raw → display transform
        )
    """
    hp_pattern: str                              # substring to match in hp dict keys
    hp_label: str                                # display name for HP
    candidate_name: str                          # which candidate model
    param_name: str                              # which parameter to extract
    param_label: str                             # display name for induced param
    true_value: Optional[float] = None           # ground truth (None for real data)
    hp_transform: Optional[Callable] = None      # e.g. np.exp for raw→actual
    param_bounds: Optional[Tuple[float, float]] = None  # display range for induced param


@dataclass
class MechanismConfig:
    """
    Full specification for a mechanism figure.

    Declares all transfer channels and display settings.
    """
    name: str                                    # e.g. "toy", "mauna_loa"
    channels: List[TransferChannel]              # the transfer channels to show
    candidates: List[Any] = field(default_factory=list)  # candidate model instances
    gp_draw_label: str = "GP Predictive"
    title: str = "BI* Mechanism"

    # Which candidates to fit (names). If empty, fit all in candidates list.
    fit_candidates: List[str] = field(default_factory=list)

    # Optional: extra params to extract (beyond what channels specify)
    extra_params: Dict[str, List[str]] = field(default_factory=dict)

    @property
    def hp_channels(self) -> List[TransferChannel]:
        """Unique HP channels (deduplicated by hp_pattern)."""
        seen = set()
        result = []
        for ch in self.channels:
            if ch.hp_pattern not in seen:
                seen.add(ch.hp_pattern)
                result.append(ch)
        return result

    @property
    def param_channels(self) -> List[TransferChannel]:
        """All induced parameter channels."""
        return self.channels

    @property
    def candidate_names(self) -> List[str]:
        """Unique candidate names needed."""
        return list(set(ch.candidate_name for ch in self.channels))

    def to_dict(self) -> dict:
        """Serialize for saving to config.json."""
        return {
            "name": self.name,
            "channels": [
                {
                    "hp_pattern": ch.hp_pattern,
                    "hp_label": ch.hp_label,
                    "candidate_name": ch.candidate_name,
                    "param_name": ch.param_name,
                    "param_label": ch.param_label,
                    "true_value": ch.true_value,
                }
                for ch in self.channels
            ],
            "title": self.title,
        }


# ═══════════════════════════════════════════════════════════════════
# Pre-built configs
# ═══════════════════════════════════════════════════════════════════

def toy_mechanism_config():
    """
    Mechanism config for toy sin(x) + 0.25x example.

    Transfer channels:
        SE lengthscale ℓ  →  ω (frequency)    [wiggly ↔ high freq]
        SE outputscale σ  →  A (amplitude)     [large variance ↔ large amplitude]
        Linear variance   →  b (slope)         [trend component]
    """
    from bistar_gp.candidates import SinLinearModel

    return MechanismConfig(
        name="toy",
        channels=[
            TransferChannel(
                hp_pattern="kernel_components.0.base_kernel.lengthscale",
                hp_label="SE Lengthscale ℓ",
                candidate_name="Sin+Linear",
                param_name="omega",
                param_label="ω (frequency)",
                true_value=1.0,
            ),
            TransferChannel(
                hp_pattern="kernel_components.0.outputscale",
                hp_label="SE Outputscale σ_f",
                candidate_name="Sin+Linear",
                param_name="A",
                param_label="A (amplitude)",
                true_value=1.0,
            ),
            TransferChannel(
                hp_pattern="kernel_components.1",  # linear kernel
                hp_label="Linear Variance σ²_lin",
                candidate_name="Sin+Linear",
                param_name="b",
                param_label="b (slope)",
                true_value=0.25,
            ),
        ],
        candidates=[SinLinearModel()],
        title="BI* Mechanism: GP Hyperparameter Priors → Induced Model Parameter Priors",
    )


def mauna_loa_mechanism_config():
    """
    Mechanism config for Mauna Loa CO₂.

    Transfer channels:
        Trend lengthscale     →  curvature a     [smooth trend ↔ gentle curve]
        Trend outputscale     →  slope b          [large trend ↔ steep slope]
        Seasonal outputscale  →  amplitude A₁     [strong season ↔ large amplitude]
        Seasonal lengthscale  →  amplitude A₂     [sharp season ↔ semi-annual present]
    """
    from bistar_gp.mauna_loa_candidates import QuadHarmonic2Model, QuadSinModel

    return MechanismConfig(
        name="mauna_loa",
        channels=[
            TransferChannel(
                hp_pattern="kernel_components.0.base_kernel.lengthscale",
                hp_label="Trend ℓ",
                candidate_name="Quad+2Harm",
                param_name="b",
                param_label="b (slope)",
                true_value=None,  # real data — no ground truth
            ),
            TransferChannel(
                hp_pattern="kernel_components.0.outputscale",
                hp_label="Trend σ",
                candidate_name="Quad+2Harm",
                param_name="a",
                param_label="a (curvature)",
                true_value=None,
            ),
            TransferChannel(
                hp_pattern="kernel_components.1.outputscale",
                hp_label="Seasonal σ",
                candidate_name="Quad+2Harm",
                param_name="A1",
                param_label="A₁ (annual)",
                true_value=None,
            ),
            TransferChannel(
                hp_pattern="kernel_components.1.base_kernel.lengthscale",
                hp_label="Seasonal ℓ",
                candidate_name="Quad+2Harm",
                param_name="A2",
                param_label="A₂ (semi-annual)",
                true_value=None,
            ),
        ],
        candidates=[QuadHarmonic2Model(), QuadSinModel()],
        title="BI* Belief Transfer: Mauna Loa CO₂",
    )


# ═══════════════════════════════════════════════════════════════════
# HP key matching
# ═══════════════════════════════════════════════════════════════════

def find_hp_key(hp_dict: dict, pattern: str) -> Optional[str]:
    """
    Find the key in hp_dict that matches pattern (substring or exact).

    Tries exact match first, then substring, then suffix match.
    """
    # Exact
    if pattern in hp_dict:
        return pattern

    # Substring
    matches = [k for k in hp_dict if pattern in k]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        # Prefer shortest match (most specific)
        return min(matches, key=len)

    # Try just the last component (e.g. "lengthscale" matches "...raw_lengthscale")
    last_part = pattern.split(".")[-1]
    matches = [k for k in hp_dict if last_part in k]
    if len(matches) == 1:
        return matches[0]

    return None


def extract_hp_values(gp_samples, channel: TransferChannel) -> np.ndarray:
    """Extract HP values from GP samples for a given channel."""
    vals = []
    for s in gp_samples:
        key = find_hp_key(s.hyperparameters, channel.hp_pattern)
        if key is not None:
            v = s.hyperparameters[key]
            if channel.hp_transform is not None:
                v = channel.hp_transform(v)
            vals.append(v)
    return np.array(vals)


# ═══════════════════════════════════════════════════════════════════
# Core computation
# ═══════════════════════════════════════════════════════════════════

@dataclass
class InducedPriorResult:
    """Induced parameter samples from fitting candidates to GP draws."""
    candidate_name: str
    param_names: List[str]
    param_samples: Dict[str, np.ndarray]   # param_name → (n_samples,)
    n_valid: int
    n_total: int


@dataclass
class MechanismResult:
    """Full mechanism computation for one condition."""
    # GP info
    hp_values: Dict[str, np.ndarray]       # channel.hp_pattern → values
    gp_means: np.ndarray                   # (n_samples, n_eval)
    x_eval: np.ndarray

    # Induced priors per candidate
    induced: Dict[str, InducedPriorResult]

    # Metadata
    label: str = ""
    n_obs: Optional[int] = None
    config_name: str = ""


def compute_mechanism(
    gp_samples,
    x_eval: np.ndarray,
    config: MechanismConfig,
    label: str = "",
    n_obs: Optional[int] = None,
    extra_candidates: Optional[list] = None,
) -> MechanismResult:
    """
    Run the full mechanism computation.

    Args:
        gp_samples: List[GPPosteriorSample] with .mean and .hyperparameters
        x_eval: evaluation grid the GP means are on
        config: MechanismConfig specifying what to extract
        label: descriptive label (e.g. "informative", "n=150")
        n_obs: number of observations
        extra_candidates: additional candidates beyond config.candidates
    """
    print(f"  Mechanism [{label}]: {len(gp_samples)} GP samples")

    # 1. Extract HP values for each channel
    hp_values = {}
    for ch in config.hp_channels:
        vals = extract_hp_values(gp_samples, ch)
        hp_values[ch.hp_pattern] = vals
        if len(vals) > 0:
            print(f"    HP '{ch.hp_label}': median={np.median(vals):.3f}, "
                  f"range=[{vals.min():.3f}, {vals.max():.3f}]")
        else:
            print(f"    HP '{ch.hp_label}': no values found (pattern: {ch.hp_pattern})")

    # 2. Collect GP predictive means
    gp_means = np.array([s.mean for s in gp_samples])

    # 3. Determine which candidates to fit
    all_candidates = list(config.candidates)
    if extra_candidates:
        all_candidates.extend(extra_candidates)

    needed_names = config.candidate_names
    candidates_to_fit = [c for c in all_candidates if c.name in needed_names]

    if not candidates_to_fit:
        warnings.warn(f"No candidates matched needed names: {needed_names}")

    # 4. Fit candidates to each GP draw
    induced = {}
    for cand_template in candidates_to_fit:
        cand_name = cand_template.name
        all_params = {}
        n_valid = 0

        for i, gp_sample in enumerate(gp_samples):
            cand = cand_template.__class__()
            try:
                cand.fit(x_eval, gp_sample.mean)
                cr = cand.predict(x_eval)
                for pname, pval in cr.parameters.items():
                    if pname == "sigma":
                        continue
                    if pname not in all_params:
                        all_params[pname] = []
                    all_params[pname].append(pval)
                n_valid += 1
            except Exception as e:
                if i == 0:
                    warnings.warn(f"Fit failed {cand_name}[{i}]: {e}")
                continue

        param_samples = {k: np.array(v) for k, v in all_params.items()}
        induced[cand_name] = InducedPriorResult(
            candidate_name=cand_name,
            param_names=list(param_samples.keys()),
            param_samples=param_samples,
            n_valid=n_valid,
            n_total=len(gp_samples),
        )
        print(f"    {cand_name}: {n_valid}/{len(gp_samples)} fits OK")

    return MechanismResult(
        hp_values=hp_values,
        gp_means=gp_means,
        x_eval=x_eval,
        induced=induced,
        label=label,
        n_obs=n_obs,
        config_name=config.name,
    )


# ═══════════════════════════════════════════════════════════════════
# Save / Load (integrates with run_manager)
# ═══════════════════════════════════════════════════════════════════

def save_mechanism_result(run_dir: str, result: MechanismResult,
                           config: MechanismConfig):
    """Save mechanism result and config to a run directory."""
    import os
    mech_dir = os.path.join(run_dir, "mechanism")
    os.makedirs(mech_dir, exist_ok=True)

    # Save the result arrays
    save_dict = {
        "gp_means": result.gp_means,
        "x_eval": result.x_eval,
        "label": np.array([result.label]),
        "n_obs": np.array([result.n_obs if result.n_obs is not None else -1]),
    }

    # HP values
    for key, vals in result.hp_values.items():
        safe_key = key.replace(".", "_")
        save_dict[f"hp_{safe_key}"] = vals

    # Induced param samples
    for cand_name, ip in result.induced.items():
        for pname, pvals in ip.param_samples.items():
            safe_key = f"induced_{cand_name}_{pname}".replace("+", "plus")
            save_dict[safe_key] = pvals

    suffix = result.label.replace(" ", "_").replace("=", "")
    path = os.path.join(mech_dir, f"mechanism_{suffix}.npz")
    np.savez(path, **save_dict)

    # Save config
    config_path = os.path.join(mech_dir, "mechanism_config.json")
    with open(config_path, "w") as f:
        json.dump(config.to_dict(), f, indent=2)

    print(f"  Mechanism saved → {path}")


def load_mechanism_results(run_dir: str) -> List[str]:
    """List available mechanism result files in a run directory."""
    import os
    mech_dir = os.path.join(run_dir, "mechanism")
    if not os.path.exists(mech_dir):
        return []
    return [f for f in os.listdir(mech_dir) if f.endswith(".npz")]


# ═══════════════════════════════════════════════════════════════════
# ESS computation
# ═══════════════════════════════════════════════════════════════════

def compute_ess(samples: np.ndarray) -> float:
    """Effective sample size via autocorrelation."""
    n = len(samples)
    if n < 10:
        return float(n)
    centered = samples - samples.mean()
    var = np.var(centered)
    if var < 1e-15:
        return float(n)
    acf = np.correlate(centered, centered, mode='full')[n-1:]
    acf = acf / (var * n)
    for t in range(1, len(acf)):
        if acf[t] < 0:
            break
    tau = 1 + 2 * np.sum(acf[1:t])
    return max(1.0, n / tau)


# ═══════════════════════════════════════════════════════════════════
# Figure: Prior Sensitivity (multiple configs, one dataset)
# ═══════════════════════════════════════════════════════════════════

def plot_mechanism_sensitivity(
    results: List[MechanismResult],
    config: MechanismConfig,
    x_train: Optional[np.ndarray] = None,
    y_train: Optional[np.ndarray] = None,
    true_func: Optional[np.ndarray] = None,
    n_gp_draws: int = 20,
    figsize: Optional[Tuple] = None,
):
    """
    Prior sensitivity mechanism figure.

    Layout driven entirely by config.channels:
        Row per unique HP
        Columns: (A) HP distribution | (B) GP draws per config | (C) induced param

    Args:
        results: one MechanismResult per prior config
        config: MechanismConfig (defines layout)
        x_train, y_train: data overlay on GP draws
        true_func: true function at x_eval (if known)
        n_gp_draws: how many GP function draws to show
    """
    hp_channels = config.hp_channels
    param_channels = config.param_channels
    n_configs = len(results)

    # Layout: one row per channel, 3 column groups
    n_rows = len(config.channels)
    n_gp_cols = min(n_configs, 2)  # up to 2 GP draw panels
    ncols = 1 + n_gp_cols + 1     # HP | GP draws | induced param

    if figsize is None:
        figsize = (5 * ncols, 4 * n_rows)

    fig, axes = plt.subplots(n_rows, ncols, figsize=figsize)
    if n_rows == 1:
        axes = axes[np.newaxis, :]

    config_colors = ["#2ecc71", "#3498db", "#e74c3c", "#9b59b6", "#f39c12"]

    for row_idx, ch in enumerate(config.channels):
        # ── Column A: HP distribution ──
        ax = axes[row_idx, 0]
        for cfg_idx, res in enumerate(results):
            color = config_colors[cfg_idx % len(config_colors)]
            vals = res.hp_values.get(ch.hp_pattern, np.array([]))
            if len(vals) > 0:
                ax.hist(vals, bins=40, density=True, alpha=0.3,
                        color=color, label=res.label)
                # KDE
                try:
                    from scipy.stats import gaussian_kde
                    kde = gaussian_kde(vals)
                    x_kde = np.linspace(vals.min() * 0.8, vals.max() * 1.2, 200)
                    ax.plot(x_kde, kde(x_kde), color=color, linewidth=1.5)
                except Exception:
                    pass

        ax.set_xlabel(ch.hp_label)
        ax.set_ylabel("Density")
        if row_idx == 0:
            ax.set_title("(A) GP Hyperparameter", fontsize=11)
        ax.legend(fontsize=7)

        # ── Column(s) B: GP draws ──
        for b_idx in range(n_gp_cols):
            ax = axes[row_idx, 1 + b_idx]
            res = results[b_idx]
            color = config_colors[b_idx % len(config_colors)]

            n_show = min(n_gp_draws, len(res.gp_means))
            for i in range(n_show):
                ax.plot(res.x_eval, res.gp_means[i], color=color,
                        alpha=0.15, linewidth=0.8)

            if true_func is not None:
                ax.plot(res.x_eval, true_func, "k--", linewidth=2,
                        label="True")

            if x_train is not None and y_train is not None:
                ax.scatter(x_train, y_train, color="black", s=12,
                           alpha=0.4, zorder=5)

            ax.set_xlabel("x")
            if row_idx == 0:
                ax.set_title(f"(B) GP Draws — {res.label}", fontsize=11)
            ax.legend(fontsize=7)

        # ── Column C: Induced parameter ──
        ax = axes[row_idx, -1]
        for cfg_idx, res in enumerate(results):
            color = config_colors[cfg_idx % len(config_colors)]
            if ch.candidate_name in res.induced:
                ip = res.induced[ch.candidate_name]
                if ch.param_name in ip.param_samples:
                    vals = ip.param_samples[ch.param_name]
                    ess = compute_ess(vals)
                    ax.hist(vals, bins=40, density=True, alpha=0.3,
                            color=color, label=f"{res.label} (ESS={ess:.0f})")
                    ax.axvline(np.median(vals), color=color, ls="--",
                               alpha=0.7)

        if ch.true_value is not None:
            ax.axvline(ch.true_value, color="black", linewidth=2,
                       label=f"True = {ch.true_value}")

        if ch.param_bounds:
            ax.set_xlim(ch.param_bounds)

        ax.set_xlabel(ch.param_label)
        if row_idx == 0:
            ax.set_title("(C) Induced Prior", fontsize=11)
        ax.legend(fontsize=7)

    fig.suptitle(config.title, fontsize=14, y=1.02)
    fig.tight_layout()
    return fig


# ═══════════════════════════════════════════════════════════════════
# Figure: Data Accumulation (one config, multiple n_obs stages)
# ═══════════════════════════════════════════════════════════════════

def plot_mechanism_accumulation(
    results: List[MechanismResult],
    config: MechanismConfig,
    x_data: Optional[np.ndarray] = None,
    y_data: Optional[np.ndarray] = None,
    true_func: Optional[np.ndarray] = None,
    hp_prior_func: Optional[Callable] = None,
    n_gp_draws: int = 25,
    predictive_candidate: Optional[str] = None,
    figsize: Optional[Tuple] = None,
):
    """
    Data accumulation mechanism figure (one row per n_obs stage).

    Layout driven by config.channels:
        Columns: HP prior/post | GP draws | one col per channel param | [predictive]
        Rows: one per data stage

    Args:
        results: list of MechanismResult ordered by increasing n_obs
        config: MechanismConfig (defines which params to show)
        x_data, y_data: full dataset (subsets shown per row)
        true_func: true function at x_eval
        hp_prior_func: callable(x) → prior density for overlay
        n_gp_draws: GP function draws per panel
        predictive_candidate: if set, show candidate predictive in last column
    """
    n_rows = len(results)
    unique_params = []
    seen = set()
    for ch in config.channels:
        key = (ch.candidate_name, ch.param_name)
        if key not in seen:
            seen.add(key)
            unique_params.append(ch)

    n_param_cols = len(unique_params)
    has_pred = predictive_candidate is not None
    ncols = 2 + n_param_cols + (1 if has_pred else 0)

    if figsize is None:
        figsize = (5 * ncols, 4.5 * n_rows)

    fig, axes = plt.subplots(n_rows, ncols, figsize=figsize, squeeze=False)

    # Pick one HP to show in column 0 (first channel's HP)
    hp_ch = config.hp_channels[0] if config.hp_channels else None

    induced_colors = ["#2ecc71", "#e67e22", "#e74c3c", "#9b59b6"]

    for row_idx, res in enumerate(results):
        n_obs = res.n_obs
        col = 0

        # ── Col 0: HP Prior / Posterior ──
        ax = axes[row_idx, col]
        if hp_ch:
            vals = res.hp_values.get(hp_ch.hp_pattern, np.array([]))
            if len(vals) > 0:
                ax.hist(vals, bins=40, density=True, alpha=0.5,
                        color="#3498db", label="Posterior p(ψ|D)")
                if hp_prior_func is not None:
                    x_hp = np.linspace(0, vals.max() * 1.5, 200)
                    ax.plot(x_hp, hp_prior_func(x_hp), "k--", alpha=0.5,
                            label="Prior p(ψ)")

            ax.set_xlabel(hp_ch.hp_label)
            if row_idx == 0:
                ax.set_title("GP Hyperparameter\nPrior / Posterior", fontsize=10)
            ax.legend(fontsize=7)

        # Row label
        if n_obs is None or n_obs == 0:
            row_label = "Prior\n(no data)"
        else:
            row_label = f"After {n_obs}\nobservations"
        ax.set_ylabel(row_label, fontsize=11, fontweight="bold",
                       rotation=0, labelpad=60, ha="right", va="center")

        col += 1

        # ── Col 1: GP Draws ──
        ax = axes[row_idx, col]
        n_show = min(n_gp_draws, len(res.gp_means))
        for i in range(n_show):
            ax.plot(res.x_eval, res.gp_means[i], color="#3498db",
                    alpha=0.12, linewidth=0.8)
        if len(res.gp_means) > 0:
            ax.plot(res.x_eval, res.gp_means.mean(axis=0),
                    color="#3498db", linewidth=1.5, alpha=0.7, label="GP mean")
        if true_func is not None:
            ax.plot(res.x_eval, true_func, "k--", linewidth=1.5, label="True")
        if x_data is not None and y_data is not None and n_obs and n_obs > 0:
            n_show_d = min(int(n_obs), len(x_data))
            ax.scatter(x_data[:n_show_d], y_data[:n_show_d],
                       color="black", s=12, alpha=0.5, zorder=5)
        ax.set_xlabel("x")
        if row_idx == 0:
            ax.set_title("GP Predictive\n(function draws)", fontsize=10)
        ax.legend(fontsize=7)

        col += 1

        # ── Cols 2+: Induced parameters ──
        for p_idx, ch in enumerate(unique_params):
            ax = axes[row_idx, col + p_idx]
            c = induced_colors[p_idx % len(induced_colors)]

            if ch.candidate_name in res.induced:
                ip = res.induced[ch.candidate_name]
                if ch.param_name in ip.param_samples:
                    vals = ip.param_samples[ch.param_name]
                    ess = compute_ess(vals)
                    ax.hist(vals, bins=35, density=True, alpha=0.5, color=c,
                            label=f"Induced p({ch.param_name}|ψ)")
                    ax.axvline(np.median(vals), color=c, ls="--", alpha=0.7)
                    ax.text(0.95, 0.95, f"ESS = {ess:.0f}",
                            transform=ax.transAxes, fontsize=8,
                            ha="right", va="top",
                            bbox=dict(boxstyle="round,pad=0.2",
                                      fc="white", alpha=0.8))

            if ch.true_value is not None:
                ax.axvline(ch.true_value, color="black", linewidth=2,
                           label=f"True = {ch.true_value}")

            if ch.param_bounds:
                ax.set_xlim(ch.param_bounds)

            ax.set_xlabel(ch.param_label)
            if row_idx == 0:
                ax.set_title(f"Induced Prior\non {ch.param_label}", fontsize=10)
            ax.legend(fontsize=7)

        col += n_param_cols

        # ── Last col: Candidate predictive (optional) ──
        if has_pred:
            ax = axes[row_idx, col]
            if predictive_candidate in res.induced:
                ip = res.induced[predictive_candidate]
                # Reconstruct: need candidate class
                _draw_induced_predictives(ax, ip, res.x_eval,
                                          color=induced_colors[0])
            if true_func is not None:
                ax.plot(res.x_eval, true_func, "k--", linewidth=1.5)
            ax.set_xlabel("x")
            if row_idx == 0:
                ax.set_title(f"{predictive_candidate}\n(from induced prior)",
                             fontsize=10)

    fig.suptitle(config.title, fontsize=13, y=1.02)
    fig.tight_layout()
    return fig


def _draw_induced_predictives(ax, induced_result, x_eval, color, n_draws=25):
    """
    Draw candidate predictive curves from induced parameter samples.

    This is a simple reconstruction — it needs the candidate class
    to be importable. Falls back to showing nothing if unavailable.
    """
    try:
        # Try to import the right candidate class
        cand_name = induced_result.candidate_name
        if cand_name == "Sin+Linear":
            from bistar_gp.candidates import SinLinearModel as CandClass
        elif cand_name == "Quad+2Harm":
            from bistar_gp.mauna_loa_candidates import QuadHarmonic2Model as CandClass
        elif cand_name == "Quad+Sin":
            from bistar_gp.mauna_loa_candidates import QuadSinModel as CandClass
        elif cand_name == "Quadratic":
            from bistar_gp.candidates import QuadraticModel as CandClass
        elif cand_name == "Linear":
            from bistar_gp.candidates import LinearModel as CandClass
        else:
            return

        n_use = min(n_draws, induced_result.n_valid)
        for i in range(n_use):
            cand = CandClass()
            for pname in induced_result.param_names:
                if hasattr(cand, pname):
                    setattr(cand, pname, induced_result.param_samples[pname][i])
            cand.sigma = 0.01  # placeholder
            cr = cand.predict(x_eval)
            ax.plot(x_eval, cr.mean, color=color, alpha=0.1, linewidth=0.8)

    except ImportError:
        pass


# ═══════════════════════════════════════════════════════════════════
# Custom config builder (for ad-hoc experiments)
# ═══════════════════════════════════════════════════════════════════

def custom_mechanism_config(
    name: str,
    hp_param_pairs: List[Dict],
    candidates: list,
    title: str = "BI* Belief Transfer",
) -> MechanismConfig:
    """
    Build a MechanismConfig from a simple list of dicts.

    Args:
        name: config name
        hp_param_pairs: list of dicts, each with:
            hp_pattern, hp_label, candidate_name, param_name, param_label,
            true_value (optional)
        candidates: list of candidate model instances
        title: figure title

    Example:
        config = custom_mechanism_config(
            name="my_experiment",
            hp_param_pairs=[
                {"hp_pattern": "lengthscale", "hp_label": "ℓ",
                 "candidate_name": "Sin+Linear", "param_name": "omega",
                 "param_label": "ω", "true_value": 1.0},
            ],
            candidates=[SinLinearModel()],
        )
    """
    channels = []
    for p in hp_param_pairs:
        channels.append(TransferChannel(
            hp_pattern=p["hp_pattern"],
            hp_label=p["hp_label"],
            candidate_name=p["candidate_name"],
            param_name=p["param_name"],
            param_label=p["param_label"],
            true_value=p.get("true_value"),
            param_bounds=p.get("param_bounds"),
        ))

    return MechanismConfig(
        name=name,
        channels=channels,
        candidates=candidates,
        title=title,
    )

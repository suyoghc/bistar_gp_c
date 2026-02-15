"""
BI* Model Prior Probabilities

Shows how the GP-informed normalizing constant Z_Mx reshapes the
model prior from uniform (1/4 each) to something informed.

Z_Mx = (1/N) Σ exp(-G(ψ, θ_Mx(φ_i)) / τ)

This is the average GP-compatibility of model Mx across its parameter space.
Normalized: p(Mx | ψ) = Z_Mx / Σ Z_Mj

Figures:
1. Bar chart of p(Mx | ψ) at n=0, 10, 50
2. How model priors evolve continuously with n
3. τ sensitivity: how temperature controls the sharpness of model preference
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import gamma as gamma_dist
from scipy.stats import lognorm
import os

# ── GP primitives (same as mechanism_unified.py) ─────────────────

def se_kernel(x1, x2, lengthscale, outputscale):
    sqdist = (x1[:, None] - x2[None, :]) ** 2
    return outputscale * np.exp(-0.5 * sqdist / lengthscale**2)

def linear_kernel(x1, x2, variance):
    return variance * (x1[:, None] * x2[None, :])

def gp_prior_predictive(x_eval, lengthscale, outputscale, linear_var, noise_var):
    K = se_kernel(x_eval, x_eval, lengthscale, outputscale) \
        + linear_kernel(x_eval, x_eval, linear_var)
    n = len(x_eval)
    return np.zeros(n), K + noise_var * np.eye(n)

def gp_posterior_predictive(x_train, y_train, x_eval,
                            lengthscale, outputscale, linear_var, noise_var):
    n_tr = len(x_train)
    n_ev = len(x_eval)
    K_tt = (se_kernel(x_train, x_train, lengthscale, outputscale)
            + linear_kernel(x_train, x_train, linear_var)
            + (noise_var + 1e-6) * np.eye(n_tr))
    K_te = (se_kernel(x_train, x_eval, lengthscale, outputscale)
            + linear_kernel(x_train, x_eval, linear_var))
    K_ee = (se_kernel(x_eval, x_eval, lengthscale, outputscale)
            + linear_kernel(x_eval, x_eval, linear_var)
            + noise_var * np.eye(n_ev))
    try:
        L = np.linalg.cholesky(K_tt)
    except np.linalg.LinAlgError:
        K_tt += 1e-4 * np.eye(n_tr)
        L = np.linalg.cholesky(K_tt)
    alpha = np.linalg.solve(L.T, np.linalg.solve(L, y_train))
    V = np.linalg.solve(L, K_te)
    mean = K_te.T @ alpha
    cov = K_ee - V.T @ V
    cov = 0.5 * (cov + cov.T)
    eigvals = np.linalg.eigvalsh(cov)
    if eigvals.min() < 0:
        cov += (abs(eigvals.min()) + 1e-6) * np.eye(n_ev)
    return mean, cov

def gp_log_marginal_likelihood(x_train, y_train,
                               lengthscale, outputscale, linear_var, noise_var):
    n = len(x_train)
    K = (se_kernel(x_train, x_train, lengthscale, outputscale)
         + linear_kernel(x_train, x_train, linear_var)
         + (noise_var + 1e-6) * np.eye(n))
    try:
        L = np.linalg.cholesky(K)
        alpha = np.linalg.solve(L.T, np.linalg.solve(L, y_train))
        logdet = 2 * np.sum(np.log(np.diag(L)))
        return -0.5 * y_train @ alpha - 0.5 * logdet - 0.5 * n * np.log(2 * np.pi)
    except np.linalg.LinAlgError:
        return -np.inf

# ── Hyperparameter sampling ──────────────────────────────────────

INFORMATIVE = {
    "se_lengthscale": ("gamma", 6.0, 0.85),
    "se_outputscale": ("gamma", 6.0, 0.85),
    "linear_variance": ("gamma", 6.0, 0.85),
    "noise": ("gamma", 1.75, 1.0),
}

def sample_from_prior(family, p1, p2, n, rng):
    if family == "gamma":
        return gamma_dist.rvs(a=p1, scale=1.0/p2, size=n, random_state=rng)
    elif family == "lognormal":
        return lognorm.rvs(s=p2, scale=np.exp(p1), size=n, random_state=rng)

def sample_hyperparams(pc, n, rng):
    ls = np.clip(sample_from_prior(*pc["se_lengthscale"], n, rng), 0.1, 50)
    os_ = np.clip(sample_from_prior(*pc["se_outputscale"], n, rng), 0.01, 50)
    lv = np.clip(sample_from_prior(*pc["linear_variance"], n, rng), 0.001, 50)
    nv = np.clip(sample_from_prior(*pc["noise"], n, rng), 1e-4, 20)
    return ls, os_, lv, nv

def compute_averaged_gp(x_eval, x_train, y_train, pc,
                        n_hyper=200, rng=None, use_data=True):
    if rng is None:
        rng = np.random.RandomState(42)
    ls, os_, lv, nv = sample_hyperparams(pc, n_hyper, rng)
    means, covs_diag, log_mlls = [], [], []
    for i in range(n_hyper):
        if use_data and x_train is not None and len(x_train) > 0:
            mu, cov = gp_posterior_predictive(x_train, y_train, x_eval,
                                              ls[i], os_[i], lv[i], nv[i])
            lml = gp_log_marginal_likelihood(x_train, y_train,
                                             ls[i], os_[i], lv[i], nv[i])
        else:
            mu, cov = gp_prior_predictive(x_eval, ls[i], os_[i], lv[i], nv[i])
            lml = 0.0
        means.append(mu)
        covs_diag.append(np.diag(cov))
        log_mlls.append(lml)
    means = np.array(means)
    covs_diag = np.array(covs_diag)
    log_mlls = np.array(log_mlls)
    valid = np.isfinite(log_mlls)
    if use_data and valid.any():
        lw = log_mlls.copy(); lw[~valid] = -np.inf
        lw -= lw[valid].max()
        mll_w = np.exp(lw); mll_w /= mll_w.sum()
    else:
        mll_w = np.ones(n_hyper) / n_hyper
    avg_mean = np.sum(mll_w[:, None] * means, axis=0)
    avg_var = np.sum(mll_w[:, None] * (covs_diag + means**2), axis=0) - avg_mean**2
    return avg_mean, np.maximum(avg_var, 1e-6)


# ── Parametric model functions ───────────────────────────────────

def sinlinear_fn(x, A, omega, phi, b, c):
    return A * np.sin(omega * x + phi) + b * x + c

def sinusoidal_fn(x, A, omega, phi):
    return A * np.sin(omega * x + phi)

def linear_fn(x, a, b):
    return a * x + b

def quadratic_fn(x, a, b, c):
    return a * x**2 + b * x + c


# ── Model definitions with parameter spaces ─────────────────────

MODELS = {
    "Linear": {
        "sample_fn": lambda rng, n: np.column_stack([
            rng.uniform(-1.5, 1.5, n),    # a (slope)
            rng.uniform(-3, 3, n),         # b (intercept)
        ]),
        "predict_fn": lambda x, *p: linear_fn(x, p[0], p[1]),
        "n_params": 2,
        "color": "#e74c3c",
    },
    "Sinusoidal": {
        "sample_fn": lambda rng, n: np.column_stack([
            rng.uniform(0.1, 3, n),        # A
            rng.uniform(0.3, 3, n),         # omega
            rng.uniform(-np.pi, np.pi, n),  # phi
        ]),
        "predict_fn": lambda x, *p: sinusoidal_fn(x, p[0], p[1], p[2]),
        "n_params": 3,
        "color": "#3498db",
    },
    "Sin+Linear": {
        "sample_fn": lambda rng, n: np.column_stack([
            rng.uniform(0.1, 3, n),         # A
            rng.uniform(0.3, 3, n),          # omega
            rng.uniform(-np.pi, np.pi, n),   # phi
            rng.uniform(-1, 1, n),           # b (slope)
            rng.uniform(-3, 3, n),           # c (intercept)
        ]),
        "predict_fn": lambda x, *p: sinlinear_fn(x, p[0], p[1], p[2], p[3], p[4]),
        "n_params": 5,
        "color": "#27ae60",
    },
    "Quadratic": {
        "sample_fn": lambda rng, n: np.column_stack([
            rng.uniform(-0.2, 0.2, n),      # a (curvature)
            rng.uniform(-1, 1, n),           # b (slope)
            rng.uniform(-3, 3, n),           # c (intercept)
        ]),
        "predict_fn": lambda x, *p: quadratic_fn(x, p[0], p[1], p[2]),
        "n_params": 3,
        "color": "#9b59b6",
    },
}


# ── Compute Z_Mx for a model ────────────────────────────────────

def compute_Z(model_spec, gp_mean, gp_var, x_eval, tau, n_samples=20000, seed=123):
    """
    Z_Mx = (1/N) Σ exp(-G(ψ, θ_Mx(φ_i)) / τ)

    Returns Z (scalar), ESS, and the raw weights.
    """
    rng = np.random.RandomState(seed)
    params = model_spec["sample_fn"](rng, n_samples)
    predict_fn = model_spec["predict_fn"]

    G = np.zeros(n_samples)
    for s in range(n_samples):
        try:
            mu_theta = predict_fn(x_eval, *params[s])
            G[s] = np.mean((gp_mean - mu_theta)**2 / (2 * np.maximum(gp_var, 1e-6)))
        except Exception:
            G[s] = 1e10

    log_boltz = -G / tau

    # Z = mean of exp(-G/τ)  [importance sampling estimate]
    # Use logsumexp trick for numerical stability
    max_lb = np.max(log_boltz[np.isfinite(log_boltz)])
    Z = np.exp(max_lb) * np.mean(np.exp(log_boltz - max_lb))

    # Normalized weights (for ESS)
    log_w = log_boltz - max_lb
    w = np.exp(log_w)
    w /= w.sum()
    ess = 1.0 / np.sum(w**2)

    return Z, ess, w, params


def compute_model_priors(gp_mean, gp_var, x_eval, tau, n_samples=20000, seed=123):
    """Compute Z_Mx for all models, return normalized model prior p(Mx|ψ)."""
    results = {}
    for mname, mspec in MODELS.items():
        Z, ess, w, params = compute_Z(mspec, gp_mean, gp_var, x_eval,
                                       tau, n_samples, seed)
        results[mname] = {"Z": Z, "ess": ess, "w": w, "params": params}

    # Normalize to get model priors
    Z_total = sum(r["Z"] for r in results.values())
    for mname in results:
        results[mname]["prior"] = results[mname]["Z"] / Z_total if Z_total > 0 else 0.25

    return results


# ── Data generation ──────────────────────────────────────────────

def generate_data(n, noise_std=0.3, seed=42, x_range=(-10, 10)):
    rng = np.random.RandomState(seed)
    x = np.sort(rng.uniform(*x_range, n))
    y = np.sin(x) + 0.25 * x + rng.normal(0, noise_std, n)
    return x, y


# ══════════════════════════════════════════════════════════════════
# FIGURES
# ══════════════════════════════════════════════════════════════════

def main():
    out_dir = "/home/claude/model_prior_plots"
    os.makedirs(out_dir, exist_ok=True)

    x_eval = np.linspace(-10, 10, 80)
    x_50, y_50 = generate_data(50, noise_std=0.3, seed=42)

    pc = INFORMATIVE
    tau = 0.3
    n_mc = 25000  # Monte Carlo samples per model

    model_names = list(MODELS.keys())
    model_colors = [MODELS[m]["color"] for m in model_names]

    # ══════════════════════════════════════════════════════════════
    # Figure 1: Bar chart at n=0, 10, 50
    # ══════════════════════════════════════════════════════════════
    print("1. Bar chart at n=0, 10, 50...")

    n_stages = [0, 10, 50]
    stage_labels = ["Prior\n(no data)", "After\nn = 10", "After\nn = 50"]

    fig, axes = plt.subplots(1, 3, figsize=(16, 5.5), sharey=True)

    for col, (n, label) in enumerate(zip(n_stages, stage_labels)):
        ax = axes[col]

        if n == 0:
            rng_gp = np.random.RandomState(42)
            gp_mean, gp_var = compute_averaged_gp(
                x_eval, None, None, pc, n_hyper=200, rng=rng_gp, use_data=False)
        else:
            x_sub, y_sub = x_50[:n], y_50[:n]
            rng_gp = np.random.RandomState(42)
            gp_mean, gp_var = compute_averaged_gp(
                x_eval, x_sub, y_sub, pc, n_hyper=200, rng=rng_gp, use_data=True)

        results = compute_model_priors(gp_mean, gp_var, x_eval, tau,
                                        n_samples=n_mc, seed=123)

        priors = [results[m]["prior"] for m in model_names]
        ess_vals = [results[m]["ess"] for m in model_names]
        Z_vals = [results[m]["Z"] for m in model_names]

        bars = ax.bar(model_names, priors, color=model_colors, alpha=0.8,
                       edgecolor='white', linewidth=1.5)

        # Value labels on bars
        for bar, p, ess in zip(bars, priors, ess_vals):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                    f'{p:.1%}',
                    ha='center', va='bottom', fontsize=11, fontweight='bold')
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height()/2,
                    f'ESS={ess:.0f}',
                    ha='center', va='center', fontsize=8, color='white',
                    fontweight='bold')

        # Uniform reference
        ax.axhline(0.25, color='gray', linestyle='--', linewidth=1, alpha=0.5,
                   label='Uniform (1/4)' if col == 0 else None)

        ax.set_ylim(0, max(priors) * 1.25)
        ax.set_title(label, fontsize=13, fontweight='bold')
        ax.tick_params(axis='x', rotation=15)
        ax.grid(True, alpha=0.15, axis='y')

        if col == 0:
            ax.set_ylabel("GP-Informed Model Prior  p(M | ψ)", fontsize=11)
            ax.legend(fontsize=9, loc='upper left')

        # Log-Z annotation
        log_Z_str = "  ".join([f"{m[:3]}:{Z:.2e}" for m, Z in zip(model_names, Z_vals)])
        ax.text(0.5, -0.18, f"Z: {log_Z_str}", transform=ax.transAxes,
                fontsize=7, ha='center', color='gray')

    fig.suptitle(
        r"BI* Model Prior:  $p(M_x | \psi) = Z_{M_x} / \sum_j Z_{M_j}$"
        "  where  "
        r"$Z_{M_x} = \frac{1}{N}\sum_i \exp(-G(\psi, \theta_{M_x}(\phi_i))/\tau)$"
        f"\nτ = {tau}  |  Informative GP prior  |  "
        "Higher Z = more parameter space compatible with GP",
        fontsize=13, fontweight='bold', y=1.05)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "model_prior_bars.png"),
                dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("  ✓ model_prior_bars.png")

    # ══════════════════════════════════════════════════════════════
    # Figure 2: Continuous sweep n=0..50
    # ══════════════════════════════════════════════════════════════
    print("2. Continuous sweep n=0..50...")

    n_values = [0, 3, 5, 8, 10, 15, 20, 30, 40, 50]
    prior_traces = {m: [] for m in model_names}
    Z_traces = {m: [] for m in model_names}

    for n in n_values:
        if n == 0:
            rng_gp = np.random.RandomState(42)
            gp_mean, gp_var = compute_averaged_gp(
                x_eval, None, None, pc, n_hyper=150, rng=rng_gp, use_data=False)
        else:
            x_sub, y_sub = x_50[:n], y_50[:n]
            rng_gp = np.random.RandomState(42)
            gp_mean, gp_var = compute_averaged_gp(
                x_eval, x_sub, y_sub, pc, n_hyper=150, rng=rng_gp, use_data=True)

        results = compute_model_priors(gp_mean, gp_var, x_eval, tau,
                                        n_samples=n_mc, seed=123)
        for m in model_names:
            prior_traces[m].append(results[m]["prior"])
            Z_traces[m].append(results[m]["Z"])

        print(f"    n={n:3d}: " + "  ".join(
            [f"{m}={results[m]['prior']:.1%}" for m in model_names]))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # Left: model prior probabilities
    for m in model_names:
        ax1.plot(n_values, prior_traces[m], 'o-', color=MODELS[m]["color"],
                 linewidth=2.5, markersize=7, label=m)
    ax1.axhline(0.25, color='gray', linestyle='--', linewidth=1, alpha=0.5,
               label='Uniform (1/4)')
    ax1.set_xlabel("Sample Size n", fontsize=12)
    ax1.set_ylabel("GP-Informed Model Prior  p(M | ψ)", fontsize=12)
    ax1.set_title("Model Prior Probability vs Data", fontsize=13, fontweight='bold')
    ax1.legend(fontsize=10)
    ax1.set_ylim(-0.02, 1.02)
    ax1.grid(True, alpha=0.2)

    # Right: log Z (unnormalized, shows absolute GP-compatibility)
    for m in model_names:
        ax2.plot(n_values, np.log10(np.maximum(Z_traces[m], 1e-30)), 'o-',
                 color=MODELS[m]["color"], linewidth=2.5, markersize=7, label=m)
    ax2.set_xlabel("Sample Size n", fontsize=12)
    ax2.set_ylabel("log₁₀(Z_M)  [GP-compatibility]", fontsize=12)
    ax2.set_title("Unnormalized Model Evidence vs Data", fontsize=13, fontweight='bold')
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.2)

    fig.suptitle(f"BI* Model Selection (τ = {tau}, Informative GP prior)\n"
                 "Left: normalized model priors  |  Right: absolute GP-compatibility",
                 fontsize=14, fontweight='bold', y=1.03)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "model_prior_sweep.png"),
                dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("  ✓ model_prior_sweep.png")

    # ══════════════════════════════════════════════════════════════
    # Figure 3: τ sensitivity
    # ══════════════════════════════════════════════════════════════
    print("3. τ sensitivity at n=50...")

    # Use n=50 GP posterior
    rng_gp = np.random.RandomState(42)
    gp_mean_50, gp_var_50 = compute_averaged_gp(
        x_eval, x_50, y_50, pc, n_hyper=200, rng=rng_gp, use_data=True)

    taus = np.logspace(-1.5, 1.5, 25)
    tau_traces = {m: [] for m in model_names}

    for t in taus:
        results = compute_model_priors(gp_mean_50, gp_var_50, x_eval, t,
                                        n_samples=n_mc, seed=123)
        for m in model_names:
            tau_traces[m].append(results[m]["prior"])

    fig, ax = plt.subplots(figsize=(10, 6))
    for m in model_names:
        ax.plot(taus, tau_traces[m], '-', color=MODELS[m]["color"],
                linewidth=2.5, label=m)

    ax.axhline(0.25, color='gray', linestyle='--', linewidth=1, alpha=0.5,
               label='Uniform (1/4)')
    ax.axvline(0.3, color='gray', linestyle=':', linewidth=1.5, alpha=0.7,
               label=f'τ = {tau} (used)')
    ax.set_xscale('log')
    ax.set_xlabel("Temperature τ", fontsize=12)
    ax.set_ylabel("GP-Informed Model Prior  p(M | ψ)", fontsize=12)
    ax.set_title("τ Controls How Strongly GP Reshapes Model Prior\n"
                 "Low τ = GP dominates  |  High τ = uniform prior recovered",
                 fontsize=13, fontweight='bold')
    ax.legend(fontsize=10, loc='center right')
    ax.set_ylim(-0.02, 1.02)
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "model_prior_tau.png"),
                dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("  ✓ model_prior_tau.png")

    # ══════════════════════════════════════════════════════════════
    # Figure 4: Combined — stacked area showing probability flow
    # ══════════════════════════════════════════════════════════════
    print("4. Stacked area chart...")

    fig, ax = plt.subplots(figsize=(12, 6))

    # Stack in order: Sin+Linear on top (winner), then others
    stack_order = ["Sin+Linear", "Sinusoidal", "Linear", "Quadratic"]
    stack_data = np.array([prior_traces[m] for m in stack_order])
    stack_colors = [MODELS[m]["color"] for m in stack_order]

    ax.stackplot(n_values, stack_data, labels=stack_order,
                 colors=stack_colors, alpha=0.7, edgecolor='white', linewidth=0.5)

    # Overlay lines for clarity
    cumulative = np.zeros(len(n_values))
    for m, data in zip(stack_order, stack_data):
        cumulative += data
        ax.plot(n_values, cumulative, color='white', linewidth=1, alpha=0.5)

    ax.set_xlabel("Sample Size n", fontsize=12)
    ax.set_ylabel("GP-Informed Model Prior  p(M | ψ)", fontsize=12)
    ax.set_title("BI* Model Prior Probability Flow\n"
                 "Sin+Linear captures increasing share as GP learns the pattern",
                 fontsize=13, fontweight='bold')
    ax.legend(loc='center right', fontsize=10, framealpha=0.9)
    ax.set_ylim(0, 1)
    ax.set_xlim(0, 50)
    ax.grid(True, alpha=0.15, axis='y')
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "model_prior_flow.png"),
                dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("  ✓ model_prior_flow.png")

    # ── Summary ──
    print(f"\n{'='*60}")
    print(f"  All figures saved to {out_dir}/")
    print(f"{'='*60}")
    for f in sorted(os.listdir(out_dir)):
        print(f"  {f}")


if __name__ == "__main__":
    main()

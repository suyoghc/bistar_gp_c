"""
BI* Mechanism Visualizations

Three sets of figures that tell the complete BI* story:

1. MECHANISM FIGURE (the "how it works" figure)
   [Left] GP hyperparameter priors p(ℓ), p(σ_f)
   [Middle] GP prior predictive draws (functions implied by those hyperparams)
   [Right] Induced prior on model parameters p(ω|ψ), p(A|ψ), etc.

2. PRIOR & POSTERIOR PREDICTIVE IN FUNCTION SPACE
   Sample φ from induced prior → plot f(x; φ) curves
   Shows what each GP prior "expects" each candidate model to look like

3. PRIOR → POSTERIOR TRANSITION
   As data accumulates (n=0, 5, 10, 20, 50), show how the induced
   predictive sharpens from vague prior predictions to concentrated
   posterior predictions

All GP computations are analytical (no HMC needed).
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from scipy.stats import gamma as gamma_dist
from scipy.stats import lognorm
import os

# ══════════════════════════════════════════════════════════════════
# GP Primitives (analytical, no GPyTorch)
# ══════════════════════════════════════════════════════════════════

def se_kernel(x1, x2, lengthscale, outputscale):
    """Squared Exponential kernel matrix."""
    sqdist = (x1[:, None] - x2[None, :]) ** 2
    return outputscale * np.exp(-0.5 * sqdist / lengthscale**2)


def linear_kernel(x1, x2, variance):
    """Linear kernel matrix."""
    return variance * (x1[:, None] * x2[None, :])


def gp_prior_predictive(x_eval, lengthscale, outputscale, linear_var, noise_var):
    """
    GP prior: p(f*) = N(0, K** + σ²I)
    Returns (mean, cov) at x_eval.
    """
    K = se_kernel(x_eval, x_eval, lengthscale, outputscale) \
        + linear_kernel(x_eval, x_eval, linear_var)
    n = len(x_eval)
    cov = K + noise_var * np.eye(n)
    mean = np.zeros(n)
    return mean, cov


def gp_posterior_predictive(x_train, y_train, x_eval,
                            lengthscale, outputscale, linear_var, noise_var):
    """
    GP posterior: p(f*|X,y) via standard conditioning.
    Returns (mean, cov) at x_eval.
    """
    n_train = len(x_train)
    n_eval = len(x_eval)

    K_tt = se_kernel(x_train, x_train, lengthscale, outputscale) \
           + linear_kernel(x_train, x_train, linear_var)
    K_tt += noise_var * np.eye(n_train)

    K_te = se_kernel(x_train, x_eval, lengthscale, outputscale) \
           + linear_kernel(x_train, x_eval, linear_var)

    K_ee = se_kernel(x_eval, x_eval, lengthscale, outputscale) \
           + linear_kernel(x_eval, x_eval, linear_var)

    # Add jitter for stability
    K_tt += 1e-6 * np.eye(n_train)

    try:
        L = np.linalg.cholesky(K_tt)
        alpha = np.linalg.solve(L.T, np.linalg.solve(L, y_train))
        V = np.linalg.solve(L, K_te)
    except np.linalg.LinAlgError:
        K_tt += 1e-4 * np.eye(n_train)
        L = np.linalg.cholesky(K_tt)
        alpha = np.linalg.solve(L.T, np.linalg.solve(L, y_train))
        V = np.linalg.solve(L, K_te)

    mean = K_te.T @ alpha
    cov = K_ee + noise_var * np.eye(n_eval) - V.T @ V

    # Ensure symmetric PSD
    cov = 0.5 * (cov + cov.T)
    eigvals = np.linalg.eigvalsh(cov)
    if eigvals.min() < 0:
        cov += (abs(eigvals.min()) + 1e-6) * np.eye(n_eval)

    return mean, cov


def gp_log_marginal_likelihood(x_train, y_train,
                               lengthscale, outputscale, linear_var, noise_var):
    """Log marginal likelihood for hyperparameter weighting."""
    n = len(x_train)
    K = se_kernel(x_train, x_train, lengthscale, outputscale) \
        + linear_kernel(x_train, x_train, linear_var) \
        + noise_var * np.eye(n)
    K += 1e-6 * np.eye(n)

    try:
        L = np.linalg.cholesky(K)
        alpha = np.linalg.solve(L.T, np.linalg.solve(L, y_train))
        logdet = 2 * np.sum(np.log(np.diag(L)))
        return -0.5 * y_train @ alpha - 0.5 * logdet - 0.5 * n * np.log(2 * np.pi)
    except np.linalg.LinAlgError:
        return -np.inf


# ══════════════════════════════════════════════════════════════════
# Hyperparameter Prior Sampling
# ══════════════════════════════════════════════════════════════════

PRIOR_CONFIGS = {
    "informative": {
        "description": "Moderate Gamma — reasonable defaults",
        "color": "#2ecc71",
        "se_lengthscale": ("gamma", 6.0, 0.85),
        "se_outputscale": ("gamma", 6.0, 0.85),
        "linear_variance": ("gamma", 6.0, 0.85),
        "noise": ("gamma", 1.75, 1.0),
    },
    "vague": {
        "description": "Broad LogNormal — minimal info",
        "color": "#3498db",
        "se_lengthscale": ("lognormal", 0.0, 2.0),
        "se_outputscale": ("lognormal", 0.0, 2.0),
        "linear_variance": ("lognormal", 0.0, 2.0),
        "noise": ("lognormal", -1.0, 2.0),
    },
    "misspecified_tight": {
        "description": "Tight Gamma away from truth",
        "color": "#e74c3c",
        "se_lengthscale": ("gamma", 20.0, 4.0),
        "se_outputscale": ("gamma", 20.0, 4.0),
        "linear_variance": ("gamma", 20.0, 4.0),
        "noise": ("gamma", 5.0, 5.0),
    },
}


def sample_from_prior(family, p1, p2, n_samples, rng):
    """Sample from a prior distribution."""
    if family == "gamma":
        # scipy gamma: shape=p1, scale=1/p2
        return gamma_dist.rvs(a=p1, scale=1.0/p2, size=n_samples, random_state=rng)
    elif family == "lognormal":
        # scipy lognorm: s=sigma, scale=exp(mu)
        return lognorm.rvs(s=p2, scale=np.exp(p1), size=n_samples, random_state=rng)
    else:
        raise ValueError(f"Unknown family: {family}")


def prior_density(x, family, p1, p2):
    """Evaluate prior density."""
    if family == "gamma":
        return gamma_dist.pdf(x, a=p1, scale=1.0/p2)
    elif family == "lognormal":
        return lognorm.pdf(x, s=p2, scale=np.exp(p1))


def sample_hyperparams(prior_config, n_samples, rng):
    """Sample full hyperparameter vectors from a prior config."""
    ls = sample_from_prior(*prior_config["se_lengthscale"], n_samples, rng)
    os_ = sample_from_prior(*prior_config["se_outputscale"], n_samples, rng)
    lv = sample_from_prior(*prior_config["linear_variance"], n_samples, rng)
    nv = sample_from_prior(*prior_config["noise"], n_samples, rng)

    # Clip to reasonable range
    ls = np.clip(ls, 0.1, 50.0)
    os_ = np.clip(os_, 0.01, 50.0)
    lv = np.clip(lv, 0.001, 50.0)
    nv = np.clip(nv, 1e-4, 20.0)

    return ls, os_, lv, nv


# ══════════════════════════════════════════════════════════════════
# Induced Prior Computation
# ══════════════════════════════════════════════════════════════════

# Parametric model functions
def sinlinear_fn(x, A, omega, phi, b, c):
    return A * np.sin(omega * x + phi) + b * x + c

def sinusoidal_fn(x, A, omega, phi):
    return A * np.sin(omega * x + phi)

def linear_fn(x, a, b):
    return a * x + b

def quadratic_fn(x, a, b, c):
    return a * x**2 + b * x + c


def compute_induced_prior_weights(
    param_samples,   # (n_samples, n_params) array
    predict_fn,      # callable(x_eval, *params) -> mean
    gp_mean,         # (n_eval,)
    gp_cov_diag,     # (n_eval,) diagonal of GP covariance
    x_eval,
    tau=1.0,
):
    """
    Compute induced prior weights via pointwise MSE divergence.

    G(ψ, θ(φ)) = Σ_i (μ_ψ(x_i) - μ_θ(x_i))² / (2 σ²_ψ(x_i))

    Returns weights (n_samples,), ESS
    """
    n_samples = param_samples.shape[0]
    G = np.zeros(n_samples)

    for s in range(n_samples):
        try:
            mu_theta = predict_fn(x_eval, *param_samples[s])
            # Variance-weighted MSE
            G[s] = np.mean((gp_mean - mu_theta)**2 / (2 * np.maximum(gp_cov_diag, 1e-6)))
        except Exception:
            G[s] = 1e10

    log_w = -G / tau
    log_w -= np.max(log_w[np.isfinite(log_w)])
    w = np.exp(log_w)
    w /= w.sum()
    ess = 1.0 / np.sum(w**2)
    return w, ess, G


def compute_averaged_gp(x_eval, x_train, y_train, prior_config,
                        n_hyper_samples=200, rng=None, use_data=True):
    """
    Compute MLL-weighted average GP predictive.

    If use_data=False: prior predictive (no conditioning on data).
    If use_data=True: posterior predictive (condition on x_train, y_train).
    """
    if rng is None:
        rng = np.random.RandomState(42)

    ls, os_, lv, nv = sample_hyperparams(prior_config, n_hyper_samples, rng)

    means = []
    covs_diag = []
    log_mlls = []

    for i in range(n_hyper_samples):
        if use_data and x_train is not None and len(x_train) > 0:
            mu, cov = gp_posterior_predictive(
                x_train, y_train, x_eval,
                ls[i], os_[i], lv[i], nv[i]
            )
            lml = gp_log_marginal_likelihood(
                x_train, y_train, ls[i], os_[i], lv[i], nv[i]
            )
        else:
            mu, cov = gp_prior_predictive(x_eval, ls[i], os_[i], lv[i], nv[i])
            lml = 0.0  # equal weight for prior

        means.append(mu)
        covs_diag.append(np.diag(cov))
        log_mlls.append(lml)

    means = np.array(means)
    covs_diag = np.array(covs_diag)
    log_mlls = np.array(log_mlls)

    # MLL weighting
    valid = np.isfinite(log_mlls)
    if use_data and valid.any():
        lw = log_mlls.copy()
        lw[~valid] = -np.inf
        lw -= lw[valid].max()
        mll_w = np.exp(lw)
        mll_w /= mll_w.sum()
    else:
        mll_w = np.ones(n_hyper_samples) / n_hyper_samples

    avg_mean = np.sum(mll_w[:, None] * means, axis=0)
    avg_cov_diag = np.sum(mll_w[:, None] * (covs_diag + means**2), axis=0) - avg_mean**2

    return avg_mean, np.maximum(avg_cov_diag, 1e-6), means, covs_diag, mll_w


# ══════════════════════════════════════════════════════════════════
# Data Generation
# ══════════════════════════════════════════════════════════════════

def generate_data(n_points, noise_std=0.3, bias_slope=0.25, seed=42,
                  x_range=(-10, 10)):
    rng = np.random.RandomState(seed)
    x = np.sort(rng.uniform(*x_range, n_points))
    y_true = np.sin(x) + bias_slope * x
    y = y_true + rng.normal(0, noise_std, n_points)
    return x, y, y_true


# ══════════════════════════════════════════════════════════════════
# FIGURE 1: Mechanism Figure
# ══════════════════════════════════════════════════════════════════

def plot_mechanism_figure(out_dir, x_eval, x_train=None, y_train=None):
    """
    Three-panel mechanism figure:
    [A] GP hyperparameter priors p(ℓ)
    [B] GP prior/posterior predictive draws
    [C] Induced prior on Sin+Linear's ω parameter
    """
    fig = plt.figure(figsize=(18, 10))
    gs = GridSpec(2, 3, figure=fig, hspace=0.35, wspace=0.3)

    prior_names = ["informative", "vague", "misspecified_tight"]

    # ── Panel A: Hyperparameter priors ──
    ax_ls = fig.add_subplot(gs[0, 0])
    ax_os = fig.add_subplot(gs[1, 0])

    x_ls = np.linspace(0.01, 20, 500)
    x_os = np.linspace(0.01, 15, 500)

    for pname in prior_names:
        pc = PRIOR_CONFIGS[pname]
        color = pc["color"]

        # Lengthscale prior
        y_ls = prior_density(x_ls, *pc["se_lengthscale"])
        ax_ls.plot(x_ls, y_ls, color=color, linewidth=2.5, label=pname)
        ax_ls.fill_between(x_ls, y_ls, alpha=0.15, color=color)

        # Outputscale prior
        y_os = prior_density(x_os, *pc["se_outputscale"])
        ax_os.plot(x_os, y_os, color=color, linewidth=2.5, label=pname)
        ax_os.fill_between(x_os, y_os, alpha=0.15, color=color)

    ax_ls.set_xlabel("SE Lengthscale ℓ", fontsize=12)
    ax_ls.set_ylabel("Prior Density", fontsize=11)
    ax_ls.set_title("(A) GP Hyperparameter Priors", fontsize=13, fontweight='bold')
    ax_ls.legend(fontsize=9)
    ax_ls.set_xlim(0, 20)
    ax_ls.grid(True, alpha=0.2)

    ax_os.set_xlabel("SE Outputscale σ_f", fontsize=12)
    ax_os.set_ylabel("Prior Density", fontsize=11)
    ax_os.set_xlim(0, 15)
    ax_os.grid(True, alpha=0.2)

    # ── Panel B: GP predictive draws ──
    for row_idx, pname in enumerate(prior_names[:2]):  # informative, vague
        ax = fig.add_subplot(gs[row_idx, 1])
        pc = PRIOR_CONFIGS[pname]
        color = pc["color"]
        rng = np.random.RandomState(42)

        ls, os_, lv, nv = sample_hyperparams(pc, 30, rng)

        n_draws = 15
        for i in range(n_draws):
            if x_train is not None and len(x_train) > 0:
                mu, cov = gp_posterior_predictive(
                    x_train, y_train, x_eval,
                    ls[i], os_[i], lv[i], nv[i])
            else:
                mu, cov = gp_prior_predictive(x_eval, ls[i], os_[i], lv[i], nv[i])

            # Draw one function from this GP
            try:
                L = np.linalg.cholesky(cov + 1e-5 * np.eye(len(x_eval)))
                f_draw = mu + L @ rng.normal(size=len(x_eval))
            except np.linalg.LinAlgError:
                f_draw = mu + np.sqrt(np.diag(cov)) * rng.normal(size=len(x_eval))

            ax.plot(x_eval, f_draw, color=color, alpha=0.3, linewidth=0.8)

        # True function
        y_true = np.sin(x_eval) + 0.25 * x_eval
        ax.plot(x_eval, y_true, 'k--', linewidth=2, label='True: sin(x)+0.25x')

        if x_train is not None:
            ax.scatter(x_train, y_train, c='black', s=10, zorder=5, alpha=0.5)

        title_suffix = "Posterior" if x_train is not None else "Prior"
        ax.set_title(f"(B) GP {title_suffix} Draws — {pname}", fontsize=11,
                     fontweight='bold')
        ax.set_ylim(-8, 8)
        ax.set_xlabel("x", fontsize=10)
        ax.legend(fontsize=8, loc='upper left')
        ax.grid(True, alpha=0.2)

    # ── Panel C: Induced prior on ω ──
    ax_omega = fig.add_subplot(gs[0, 2])
    ax_A = fig.add_subplot(gs[1, 2])

    n_param = 8000
    rng_param = np.random.RandomState(123)

    # Sample Sin+Linear parameters from reference prior
    A_samp = rng_param.uniform(0.1, 3.0, n_param)
    omega_samp = rng_param.uniform(0.3, 3.0, n_param)
    phi_samp = rng_param.uniform(-np.pi, np.pi, n_param)
    b_samp = rng_param.uniform(-1.0, 1.0, n_param)
    c_samp = rng_param.uniform(-3.0, 3.0, n_param)
    params = np.column_stack([A_samp, omega_samp, phi_samp, b_samp, c_samp])

    for pname in prior_names:
        pc = PRIOR_CONFIGS[pname]
        color = pc["color"]
        rng_gp = np.random.RandomState(42)

        # Compute averaged GP
        avg_mean, avg_var, _, _, _ = compute_averaged_gp(
            x_eval, x_train, y_train, pc,
            n_hyper_samples=100, rng=rng_gp,
            use_data=(x_train is not None))

        # Compute induced prior weights
        w, ess, _ = compute_induced_prior_weights(
            params,
            lambda x, A, om, ph, b_, c_: sinlinear_fn(x, A, om, ph, b_, c_),
            avg_mean, avg_var, x_eval, tau=1.0)

        # Plot omega marginal
        ax_omega.hist(omega_samp, bins=60, weights=w, density=True, alpha=0.4,
                      color=color, label=f'{pname} (ESS={ess:.0f})')
        w_mean = np.sum(w * omega_samp)
        ax_omega.axvline(w_mean, color=color, linestyle='--', linewidth=1.5, alpha=0.8)

        # Plot A marginal
        ax_A.hist(A_samp, bins=60, weights=w, density=True, alpha=0.4,
                  color=color, label=f'{pname}')
        w_mean_A = np.sum(w * A_samp)
        ax_A.axvline(w_mean_A, color=color, linestyle='--', linewidth=1.5, alpha=0.8)

    # True values
    ax_omega.axvline(1.0, color='black', linewidth=2.5, label='True ω=1.0')
    ax_omega.set_xlabel("ω (frequency)", fontsize=12)
    ax_omega.set_ylabel("Induced Prior Density", fontsize=11)
    ax_omega.set_title("(C) Induced Prior on ω", fontsize=13, fontweight='bold')
    ax_omega.legend(fontsize=8)
    ax_omega.grid(True, alpha=0.2)

    ax_A.axvline(1.0, color='black', linewidth=2.5, label='True A=1.0')
    ax_A.set_xlabel("A (amplitude)", fontsize=12)
    ax_A.set_ylabel("Induced Prior Density", fontsize=11)
    ax_A.set_title("Induced Prior on A", fontsize=11, fontweight='bold')
    ax_A.legend(fontsize=8)
    ax_A.grid(True, alpha=0.2)

    fig.suptitle("BI* Mechanism: GP Hyperparameter Priors → GP Predictive → "
                 "Induced Model Parameter Priors",
                 fontsize=15, fontweight='bold', y=1.02)
    fig.savefig(os.path.join(out_dir, "mechanism_figure.png"),
                dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  ✓ mechanism_figure.png")
    return fig


# ══════════════════════════════════════════════════════════════════
# FIGURE 2: Prior & Posterior Predictive in Function Space
# ══════════════════════════════════════════════════════════════════

def plot_predictive_function_space(out_dir, x_eval, x_train=None, y_train=None):
    """
    For each GP prior config, draw curves from the induced prior on
    Sin+Linear parameters. Shows what the GP-informed prior "expects"
    the parametric model to look like.

    Two rows:
      Top: Prior predictive (no data)
      Bottom: Posterior predictive (with data)
    """
    prior_names = ["informative", "vague", "misspecified_tight"]
    n_param = 10000
    n_curves = 40
    rng_param = np.random.RandomState(123)

    # Reference prior samples
    A_samp = rng_param.uniform(0.1, 3.0, n_param)
    omega_samp = rng_param.uniform(0.3, 3.0, n_param)
    phi_samp = rng_param.uniform(-np.pi, np.pi, n_param)
    b_samp = rng_param.uniform(-1.0, 1.0, n_param)
    c_samp = rng_param.uniform(-3.0, 3.0, n_param)
    params = np.column_stack([A_samp, omega_samp, phi_samp, b_samp, c_samp])

    has_data = x_train is not None and len(x_train) > 0
    n_rows = 2 if has_data else 1

    fig, axes = plt.subplots(n_rows, len(prior_names),
                             figsize=(6 * len(prior_names), 5 * n_rows),
                             squeeze=False)

    for col, pname in enumerate(prior_names):
        pc = PRIOR_CONFIGS[pname]
        color = pc["color"]

        for row, (use_data, title_prefix) in enumerate(
            [(False, "Prior Predictive")] +
            ([(True, "Posterior Predictive")] if has_data else [])
        ):
            ax = axes[row, col]
            rng_gp = np.random.RandomState(42)

            x_data = x_train if use_data else None
            y_data = y_train if use_data else None

            avg_mean, avg_var, _, _, _ = compute_averaged_gp(
                x_eval, x_data, y_data, pc,
                n_hyper_samples=100, rng=rng_gp, use_data=use_data)

            w, ess, _ = compute_induced_prior_weights(
                params,
                lambda x, A, om, ph, b_, c_: sinlinear_fn(x, A, om, ph, b_, c_),
                avg_mean, avg_var, x_eval, tau=1.0)

            # Draw curves from induced prior (weighted resampling)
            rng_draw = np.random.RandomState(99)
            indices = rng_draw.choice(n_param, size=n_curves, p=w)

            for idx in indices:
                y_curve = sinlinear_fn(x_eval,
                                       A_samp[idx], omega_samp[idx], phi_samp[idx],
                                       b_samp[idx], c_samp[idx])
                ax.plot(x_eval, y_curve, color=color, alpha=0.15, linewidth=0.8)

            # Weighted mean prediction
            w_A = np.sum(w * A_samp)
            w_om = np.sum(w * omega_samp)
            w_phi = np.sum(w * phi_samp)
            w_b = np.sum(w * b_samp)
            w_c = np.sum(w * c_samp)
            y_wmean = sinlinear_fn(x_eval, w_A, w_om, w_phi, w_b, w_c)
            ax.plot(x_eval, y_wmean, color=color, linewidth=2.5, alpha=0.9,
                    label=f'Weighted mean')

            # True function
            y_true = np.sin(x_eval) + 0.25 * x_eval
            ax.plot(x_eval, y_true, 'k--', linewidth=2, label='True')

            # Data points
            if use_data and x_train is not None:
                ax.scatter(x_train, y_train, c='black', s=15, zorder=5, alpha=0.6)

            ax.set_ylim(-6, 6)
            ax.set_xlabel("x", fontsize=10)
            ax.set_title(f"{title_prefix}\n{pname} (ESS={ess:.0f})", fontsize=11)
            ax.legend(fontsize=8, loc='upper left')
            ax.grid(True, alpha=0.2)

    fig.suptitle("BI* Induced Predictive: What the GP Prior Expects Sin+Linear to Look Like",
                 fontsize=14, fontweight='bold', y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "predictive_function_space.png"),
                dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  ✓ predictive_function_space.png")


# ══════════════════════════════════════════════════════════════════
# FIGURE 3: Prior → Posterior Transition
# ══════════════════════════════════════════════════════════════════

def plot_prior_to_posterior_transition(out_dir, x_eval, x_full, y_full,
                                       prior_name="informative"):
    """
    Show how the induced predictive sharpens as data accumulates.
    Columns: n=0, 5, 10, 20, 50
    Top row: Induced predictive curves (function space)
    Bottom row: Induced prior on ω
    """
    pc = PRIOR_CONFIGS[prior_name]
    color = pc["color"]
    n_values = [0, 5, 10, 20, 50]

    n_param = 10000
    n_curves = 40
    rng_param = np.random.RandomState(123)

    A_samp = rng_param.uniform(0.1, 3.0, n_param)
    omega_samp = rng_param.uniform(0.3, 3.0, n_param)
    phi_samp = rng_param.uniform(-np.pi, np.pi, n_param)
    b_samp = rng_param.uniform(-1.0, 1.0, n_param)
    c_samp = rng_param.uniform(-3.0, 3.0, n_param)
    params = np.column_stack([A_samp, omega_samp, phi_samp, b_samp, c_samp])

    fig, axes = plt.subplots(2, len(n_values), figsize=(4.5 * len(n_values), 9))

    ess_values = []

    for col, n in enumerate(n_values):
        ax_func = axes[0, col]
        ax_omega = axes[1, col]

        rng_gp = np.random.RandomState(42)

        if n == 0:
            x_sub, y_sub = None, None
            use_data = False
        else:
            # Take first n points (sorted by x)
            x_sub = x_full[:n]
            y_sub = y_full[:n]
            use_data = True

        avg_mean, avg_var, _, _, _ = compute_averaged_gp(
            x_eval, x_sub, y_sub, pc,
            n_hyper_samples=100, rng=rng_gp, use_data=use_data)

        w, ess, _ = compute_induced_prior_weights(
            params,
            lambda x, A, om, ph, b_, c_: sinlinear_fn(x, A, om, ph, b_, c_),
            avg_mean, avg_var, x_eval, tau=1.0)

        ess_values.append(ess)

        # ── Top: function-space spaghetti ──
        rng_draw = np.random.RandomState(99)
        indices = rng_draw.choice(n_param, size=n_curves, p=w)

        for idx in indices:
            y_curve = sinlinear_fn(x_eval,
                                   A_samp[idx], omega_samp[idx], phi_samp[idx],
                                   b_samp[idx], c_samp[idx])
            ax_func.plot(x_eval, y_curve, color=color, alpha=0.15, linewidth=0.8)

        # Weighted mean
        w_A = np.sum(w * A_samp)
        w_om = np.sum(w * omega_samp)
        w_phi = np.sum(w * phi_samp)
        w_b = np.sum(w * b_samp)
        w_c = np.sum(w * c_samp)
        y_wmean = sinlinear_fn(x_eval, w_A, w_om, w_phi, w_b, w_c)
        ax_func.plot(x_eval, y_wmean, color=color, linewidth=2.5, alpha=0.9)

        # True
        y_true = np.sin(x_eval) + 0.25 * x_eval
        ax_func.plot(x_eval, y_true, 'k--', linewidth=2)

        # Data
        if x_sub is not None:
            ax_func.scatter(x_sub, y_sub, c='black', s=20, zorder=5)

        ax_func.set_ylim(-6, 6)
        ax_func.set_title(f"n = {n}" + (f"  (ESS={ess:.0f})" if n > 0 else "  (prior)"),
                          fontsize=12, fontweight='bold')
        ax_func.set_xlabel("x", fontsize=10)
        if col == 0:
            ax_func.set_ylabel("Sin+Linear prediction", fontsize=10)
        ax_func.grid(True, alpha=0.2)

        # ── Bottom: ω marginal ──
        ax_omega.hist(omega_samp, bins=60, density=True, alpha=0.2, color='gray',
                      label='Reference' if col == 0 else None)
        ax_omega.hist(omega_samp, bins=60, weights=w, density=True, alpha=0.6,
                      color=color, label='Induced' if col == 0 else None)
        ax_omega.axvline(1.0, color='black', linewidth=2, linestyle='--',
                         label='True ω=1' if col == 0 else None)

        w_omega_mean = np.sum(w * omega_samp)
        w_omega_std = np.sqrt(np.sum(w * (omega_samp - w_omega_mean)**2))
        ax_omega.axvline(w_omega_mean, color=color, linewidth=1.5, alpha=0.8)

        ax_omega.set_xlabel("ω", fontsize=12)
        ax_omega.set_title(f"ω: {w_omega_mean:.2f} ± {w_omega_std:.2f}", fontsize=10)
        if col == 0:
            ax_omega.set_ylabel("Density", fontsize=10)
            ax_omega.legend(fontsize=8)
        ax_omega.grid(True, alpha=0.2)

    fig.suptitle(f"BI* Prior → Posterior Transition ({prior_name} GP prior)\n"
                 f"As data accumulates, induced predictive sharpens toward truth",
                 fontsize=14, fontweight='bold', y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, f"transition_{prior_name}.png"),
                dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  ✓ transition_{prior_name}.png")

    return n_values, ess_values


def plot_transition_all_priors(out_dir, x_eval, x_full, y_full):
    """
    Same transition but comparing across GP priors.
    Each row = different prior, columns = n=0,5,10,20,50
    """
    prior_names = ["informative", "vague", "misspecified_tight"]
    n_values = [0, 5, 10, 20, 50]

    n_param = 10000
    n_curves = 30
    rng_param = np.random.RandomState(123)

    A_samp = rng_param.uniform(0.1, 3.0, n_param)
    omega_samp = rng_param.uniform(0.3, 3.0, n_param)
    phi_samp = rng_param.uniform(-np.pi, np.pi, n_param)
    b_samp = rng_param.uniform(-1.0, 1.0, n_param)
    c_samp = rng_param.uniform(-3.0, 3.0, n_param)
    params = np.column_stack([A_samp, omega_samp, phi_samp, b_samp, c_samp])

    fig, axes = plt.subplots(len(prior_names), len(n_values),
                             figsize=(4 * len(n_values), 4 * len(prior_names)))

    ess_table = {}

    for row, pname in enumerate(prior_names):
        pc = PRIOR_CONFIGS[pname]
        color = pc["color"]
        ess_table[pname] = []

        for col, n in enumerate(n_values):
            ax = axes[row, col]
            rng_gp = np.random.RandomState(42)

            if n == 0:
                x_sub, y_sub = None, None
                use_data = False
            else:
                x_sub = x_full[:n]
                y_sub = y_full[:n]
                use_data = True

            avg_mean, avg_var, _, _, _ = compute_averaged_gp(
                x_eval, x_sub, y_sub, pc,
                n_hyper_samples=80, rng=rng_gp, use_data=use_data)

            w, ess, _ = compute_induced_prior_weights(
                params,
                lambda x, A, om, ph, b_, c_: sinlinear_fn(x, A, om, ph, b_, c_),
                avg_mean, avg_var, x_eval, tau=1.0)

            ess_table[pname].append(ess)

            # Draw curves
            rng_draw = np.random.RandomState(99)
            indices = rng_draw.choice(n_param, size=n_curves, p=w)

            for idx in indices:
                y_curve = sinlinear_fn(x_eval,
                                       A_samp[idx], omega_samp[idx], phi_samp[idx],
                                       b_samp[idx], c_samp[idx])
                ax.plot(x_eval, y_curve, color=color, alpha=0.15, linewidth=0.8)

            # True function
            y_true = np.sin(x_eval) + 0.25 * x_eval
            ax.plot(x_eval, y_true, 'k--', linewidth=2)

            # Data
            if x_sub is not None:
                ax.scatter(x_sub, y_sub, c='black', s=12, zorder=5)

            ax.set_ylim(-6, 6)
            ax.grid(True, alpha=0.2)

            # Labels
            if row == 0:
                ax.set_title(f"n = {n}", fontsize=13, fontweight='bold')
            if col == 0:
                ax.set_ylabel(f"{pname}\n", fontsize=11, fontweight='bold',
                              color=color)
            if row == len(prior_names) - 1:
                ax.set_xlabel("x", fontsize=10)

            # ESS annotation
            ax.text(0.97, 0.97, f"ESS={ess:.0f}",
                    transform=ax.transAxes, fontsize=8,
                    verticalalignment='top', horizontalalignment='right',
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    fig.suptitle("BI* Prior → Posterior Transition Across GP Priors\n"
                 "Columns: increasing data  |  Rows: different GP priors  |  "
                 "Dashed: true function",
                 fontsize=14, fontweight='bold', y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "transition_all_priors.png"),
                dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  ✓ transition_all_priors.png")

    # ── ESS convergence plot ──
    fig2, ax = plt.subplots(figsize=(8, 5))
    for pname in prior_names:
        pc = PRIOR_CONFIGS[pname]
        ax.plot(n_values, ess_table[pname], 'o-', color=pc["color"],
                linewidth=2.5, markersize=8, label=pname)
    ax.set_xlabel("Sample Size n", fontsize=12)
    ax.set_ylabel("Effective Sample Size (ESS)", fontsize=12)
    ax.set_title("Prior Sharpness vs Data: Lower ESS = Sharper Induced Prior",
                 fontsize=13)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    fig2.tight_layout()
    fig2.savefig(os.path.join(out_dir, "ess_vs_n.png"),
                 dpi=150, bbox_inches='tight')
    plt.close(fig2)
    print(f"  ✓ ess_vs_n.png")

    return ess_table


# ══════════════════════════════════════════════════════════════════
# FIGURE 4: Side-by-side GP hyperprior → Induced parameter prior
# ══════════════════════════════════════════════════════════════════

def plot_side_by_side_priors(out_dir, x_eval, x_train, y_train):
    """
    Direct comparison: left column = GP hyperparameter priors,
    right column = resulting induced priors on model parameters.

    One row per GP prior config. The arrow shows the transfer.
    """
    prior_names = ["informative", "vague", "misspecified_tight"]

    n_param = 10000
    rng_param = np.random.RandomState(123)
    A_samp = rng_param.uniform(0.1, 3.0, n_param)
    omega_samp = rng_param.uniform(0.3, 3.0, n_param)
    phi_samp = rng_param.uniform(-np.pi, np.pi, n_param)
    b_samp = rng_param.uniform(-1.0, 1.0, n_param)
    c_samp = rng_param.uniform(-3.0, 3.0, n_param)
    params = np.column_stack([A_samp, omega_samp, phi_samp, b_samp, c_samp])

    fig, axes = plt.subplots(len(prior_names), 4,
                             figsize=(20, 4 * len(prior_names)))

    for row, pname in enumerate(prior_names):
        pc = PRIOR_CONFIGS[pname]
        color = pc["color"]

        # ── Col 0: Lengthscale prior ──
        ax = axes[row, 0]
        x_ls = np.linspace(0.01, 20, 500)
        y_ls = prior_density(x_ls, *pc["se_lengthscale"])
        ax.fill_between(x_ls, y_ls, alpha=0.3, color=color)
        ax.plot(x_ls, y_ls, color=color, linewidth=2.5)
        ax.set_xlabel("Lengthscale ℓ", fontsize=11)
        ax.set_ylabel("Density", fontsize=10)
        ax.set_title(f"{pname}\np(ℓ)", fontsize=11, fontweight='bold', color=color)
        ax.set_xlim(0, 20)
        ax.grid(True, alpha=0.2)

        # ── Col 1: GP predictive spaghetti ──
        ax = axes[row, 1]
        rng_gp = np.random.RandomState(42)
        ls, os_, lv, nv = sample_hyperparams(pc, 20, rng_gp)

        for i in range(12):
            mu, cov = gp_posterior_predictive(
                x_train, y_train, x_eval, ls[i], os_[i], lv[i], nv[i])
            try:
                L = np.linalg.cholesky(cov + 1e-5 * np.eye(len(x_eval)))
                f_draw = mu + L @ rng_gp.normal(size=len(x_eval))
            except np.linalg.LinAlgError:
                f_draw = mu
            ax.plot(x_eval, f_draw, color=color, alpha=0.25, linewidth=0.8)

        y_true = np.sin(x_eval) + 0.25 * x_eval
        ax.plot(x_eval, y_true, 'k--', linewidth=2)
        ax.scatter(x_train, y_train, c='black', s=8, alpha=0.4)
        ax.set_ylim(-6, 6)
        ax.set_xlabel("x", fontsize=10)
        ax.set_title("GP posterior draws", fontsize=11)
        ax.grid(True, alpha=0.2)

        # Arrow annotation between cols 1 and 2
        ax.annotate("", xy=(1.12, 0.5), xytext=(1.02, 0.5),
                     xycoords='axes fraction',
                     arrowprops=dict(arrowstyle='->', lw=2.5, color=color))

        # ── Col 2: Induced ω prior ──
        ax = axes[row, 2]
        rng_gp2 = np.random.RandomState(42)
        avg_mean, avg_var, _, _, _ = compute_averaged_gp(
            x_eval, x_train, y_train, pc,
            n_hyper_samples=100, rng=rng_gp2, use_data=True)

        w, ess, _ = compute_induced_prior_weights(
            params,
            lambda x, A, om, ph, b_, c_: sinlinear_fn(x, A, om, ph, b_, c_),
            avg_mean, avg_var, x_eval, tau=1.0)

        ax.hist(omega_samp, bins=60, density=True, alpha=0.15, color='gray')
        ax.hist(omega_samp, bins=60, weights=w, density=True, alpha=0.6,
                color=color)
        ax.axvline(1.0, color='black', linewidth=2, linestyle='--')
        w_om = np.sum(w * omega_samp)
        ax.axvline(w_om, color=color, linewidth=1.5)
        ax.set_xlabel("ω", fontsize=12)
        ax.set_title(f"Induced p(ω|ψ)\nESS={ess:.0f}", fontsize=11)
        ax.grid(True, alpha=0.2)

        # ── Col 3: Induced A prior ──
        ax = axes[row, 3]
        ax.hist(A_samp, bins=60, density=True, alpha=0.15, color='gray')
        ax.hist(A_samp, bins=60, weights=w, density=True, alpha=0.6,
                color=color)
        ax.axvline(1.0, color='black', linewidth=2, linestyle='--')
        w_A = np.sum(w * A_samp)
        ax.axvline(w_A, color=color, linewidth=1.5)
        ax.set_xlabel("A", fontsize=12)
        ax.set_title(f"Induced p(A|ψ)", fontsize=11)
        ax.grid(True, alpha=0.2)

    fig.suptitle("BI* Transfer Mechanism: GP Hyperparameter Prior → "
                 "GP Posterior → Induced Model Parameter Prior\n"
                 "Gray = reference prior (uniform)  |  "
                 "Colored = GP-induced prior  |  "
                 "Black dashed = true value",
                 fontsize=13, fontweight='bold', y=1.03)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "side_by_side_priors.png"),
                dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  ✓ side_by_side_priors.png")


# ══════════════════════════════════════════════════════════════════
# FIGURE 5: Multi-model prior predictive comparison
# ══════════════════════════════════════════════════════════════════

def plot_multimodel_predictive(out_dir, x_eval, x_train, y_train,
                               prior_name="informative"):
    """
    Compare prior predictive draws across ALL four candidate models,
    both from reference prior and from GP-induced prior.

    Shows: induced prior concentrates Sin+Linear curves near truth,
    while other models' curves scatter more widely.
    """
    pc = PRIOR_CONFIGS[prior_name]
    color = pc["color"]

    n_param = 10000
    n_curves = 30
    rng = np.random.RandomState(123)

    # Compute averaged GP posterior
    rng_gp = np.random.RandomState(42)
    avg_mean, avg_var, _, _, _ = compute_averaged_gp(
        x_eval, x_train, y_train, pc,
        n_hyper_samples=100, rng=rng_gp, use_data=True)

    # Define models and their parameter spaces
    models = {
        "Linear": {
            "sample_fn": lambda rng, n: np.column_stack([
                rng.uniform(-1, 1, n),      # a
                rng.uniform(-3, 3, n),       # b
            ]),
            "predict_fn": lambda x, *p: linear_fn(x, p[0], p[1]),
            "model_color": "#e74c3c",
        },
        "Sinusoidal": {
            "sample_fn": lambda rng, n: np.column_stack([
                rng.uniform(0.1, 3, n),      # A
                rng.uniform(0.3, 3, n),      # omega
                rng.uniform(-np.pi, np.pi, n),  # phi
            ]),
            "predict_fn": lambda x, *p: sinusoidal_fn(x, p[0], p[1], p[2]),
            "model_color": "#3498db",
        },
        "Sin+Linear": {
            "sample_fn": lambda rng, n: np.column_stack([
                rng.uniform(0.1, 3, n),
                rng.uniform(0.3, 3, n),
                rng.uniform(-np.pi, np.pi, n),
                rng.uniform(-1, 1, n),
                rng.uniform(-3, 3, n),
            ]),
            "predict_fn": lambda x, *p: sinlinear_fn(x, p[0], p[1], p[2], p[3], p[4]),
            "model_color": "#2ecc71",
        },
        "Quadratic": {
            "sample_fn": lambda rng, n: np.column_stack([
                rng.uniform(-0.2, 0.2, n),
                rng.uniform(-1, 1, n),
                rng.uniform(-3, 3, n),
            ]),
            "predict_fn": lambda x, *p: quadratic_fn(x, p[0], p[1], p[2]),
            "model_color": "#9b59b6",
        },
    }

    fig, axes = plt.subplots(2, 4, figsize=(20, 9))

    for col, (mname, mspec) in enumerate(models.items()):
        mc = mspec["model_color"]
        rng_m = np.random.RandomState(123)
        params_m = mspec["sample_fn"](rng_m, n_param)

        # Top row: reference prior predictive
        ax = axes[0, col]
        rng_draw = np.random.RandomState(55)
        for _ in range(n_curves):
            idx = rng_draw.randint(n_param)
            try:
                y_curve = mspec["predict_fn"](x_eval, *params_m[idx])
                ax.plot(x_eval, y_curve, color=mc, alpha=0.15, linewidth=0.8)
            except Exception:
                pass

        y_true = np.sin(x_eval) + 0.25 * x_eval
        ax.plot(x_eval, y_true, 'k--', linewidth=2)
        ax.set_ylim(-8, 8)
        ax.set_title(f"{mname}\n(reference prior)", fontsize=11)
        if col == 0:
            ax.set_ylabel("y", fontsize=11)
        ax.grid(True, alpha=0.2)

        # Bottom row: induced prior predictive
        ax = axes[1, col]

        w, ess, _ = compute_induced_prior_weights(
            params_m, mspec["predict_fn"],
            avg_mean, avg_var, x_eval, tau=1.0)

        rng_draw2 = np.random.RandomState(55)
        indices = rng_draw2.choice(n_param, size=n_curves, p=w)
        for idx in indices:
            try:
                y_curve = mspec["predict_fn"](x_eval, *params_m[idx])
                ax.plot(x_eval, y_curve, color=mc, alpha=0.2, linewidth=0.8)
            except Exception:
                pass

        ax.plot(x_eval, y_true, 'k--', linewidth=2)
        if x_train is not None:
            ax.scatter(x_train, y_train, c='black', s=12, zorder=5, alpha=0.5)
        ax.set_ylim(-8, 8)
        ax.set_title(f"{mname}\n(GP-induced prior, ESS={ess:.0f})", fontsize=11)
        ax.set_xlabel("x", fontsize=10)
        if col == 0:
            ax.set_ylabel("y", fontsize=11)
        ax.grid(True, alpha=0.2)

    fig.suptitle(f"Reference Prior vs GP-Induced Prior Predictive ({prior_name} GP)\n"
                 f"Top: random curves from uniform parameter prior  |  "
                 f"Bottom: curves weighted by GP posterior agreement",
                 fontsize=13, fontweight='bold', y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, f"multimodel_predictive_{prior_name}.png"),
                dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  ✓ multimodel_predictive_{prior_name}.png")


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    out_dir = "/home/claude/mechanism_plots"
    os.makedirs(out_dir, exist_ok=True)

    # Setup
    x_eval = np.linspace(-10, 10, 80)
    x_full, y_full, y_true_full = generate_data(50, noise_std=0.3,
                                                 bias_slope=0.25, seed=42)

    # Use n=50 for posterior plots, full sorted data for transition
    x_train = x_full
    y_train = y_full

    print("=" * 65)
    print("  BI* Mechanism Visualizations")
    print("=" * 65)

    # Figure 1: Mechanism figure (with posterior)
    print("\n1. Mechanism figure...")
    plot_mechanism_figure(out_dir, x_eval, x_train, y_train)

    # Figure 2: Prior & posterior predictive in function space
    print("\n2. Predictive function space...")
    plot_predictive_function_space(out_dir, x_eval, x_train, y_train)

    # Figure 3a: Prior→posterior transition (informative)
    print("\n3. Prior→posterior transition (informative)...")
    plot_prior_to_posterior_transition(out_dir, x_eval, x_full, y_full,
                                       "informative")

    # Figure 3b: Transition across all priors
    print("\n4. Transition across all priors...")
    ess_table = plot_transition_all_priors(out_dir, x_eval, x_full, y_full)

    # Figure 4: Side-by-side priors
    print("\n5. Side-by-side GP hyperprior → induced parameter prior...")
    plot_side_by_side_priors(out_dir, x_eval, x_train, y_train)

    # Figure 5: Multi-model predictive
    print("\n6. Multi-model predictive comparison...")
    plot_multimodel_predictive(out_dir, x_eval, x_train, y_train, "informative")

    # Summary
    print(f"\n{'=' * 65}")
    print(f"  All figures saved to {out_dir}/")
    print(f"{'=' * 65}")
    print(f"\nESS convergence:")
    for pname, ess_vals in ess_table.items():
        print(f"  {pname:<22}: {['%.0f' % e for e in ess_vals]}")

    print(f"\nFiles:")
    for f in sorted(os.listdir(out_dir)):
        print(f"  {f}")


if __name__ == "__main__":
    main()

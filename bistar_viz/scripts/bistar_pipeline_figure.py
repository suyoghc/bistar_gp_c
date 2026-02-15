"""
BI* Pipeline Figure — Clean 3-row layout

Row 1 (Prior):       p(ℓ) | GP prior predictive     | induced p(ω)    | Sin+Linear prior predictive
Row 2 (n=10):        p(ℓ) | GP posterior (partial)   | induced p(ω|D) | Sin+Linear partial posterior predictive
Row 3 (n=50):        p(ℓ) | GP posterior (full)      | induced p(ω|D) | Sin+Linear posterior predictive

Shows the full transfer: qualitative GP belief → GP predictive → induced model parameters → model predictive
And how data progressively sharpens everything downstream.
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from scipy.stats import gamma as gamma_dist
from scipy.stats import lognorm, gaussian_kde
import os


# ══════════════════════════════════════════════════════════════════
# GP Math (analytical, no dependencies)
# ══════════════════════════════════════════════════════════════════

def se_kernel(x1, x2, lengthscale, outputscale):
    sqdist = (x1[:, None] - x2[None, :]) ** 2
    return outputscale * np.exp(-0.5 * sqdist / lengthscale**2)

def linear_kernel(x1, x2, variance):
    return variance * (x1[:, None] * x2[None, :])

def gp_prior_sample(x_eval, lengthscale, outputscale, linear_var, noise_var, rng):
    """Draw one function from the GP prior."""
    n = len(x_eval)
    K = se_kernel(x_eval, x_eval, lengthscale, outputscale) \
        + linear_kernel(x_eval, x_eval, linear_var) \
        + noise_var * np.eye(n) + 1e-5 * np.eye(n)
    try:
        L = np.linalg.cholesky(K)
    except np.linalg.LinAlgError:
        K += 1e-4 * np.eye(n)
        L = np.linalg.cholesky(K)
    return L @ rng.normal(size=n)

def gp_posterior(x_train, y_train, x_eval, lengthscale, outputscale,
                 linear_var, noise_var):
    """GP posterior mean and covariance at x_eval."""
    n_tr = len(x_train)
    n_ev = len(x_eval)
    K_tt = se_kernel(x_train, x_train, lengthscale, outputscale) \
           + linear_kernel(x_train, x_train, linear_var) \
           + noise_var * np.eye(n_tr) + 1e-6 * np.eye(n_tr)
    K_te = se_kernel(x_train, x_eval, lengthscale, outputscale) \
           + linear_kernel(x_train, x_eval, linear_var)
    K_ee = se_kernel(x_eval, x_eval, lengthscale, outputscale) \
           + linear_kernel(x_eval, x_eval, linear_var) \
           + noise_var * np.eye(n_ev)
    try:
        L = np.linalg.cholesky(K_tt)
    except np.linalg.LinAlgError:
        K_tt += 1e-4 * np.eye(n_tr)
        L = np.linalg.cholesky(K_tt)
    alpha = np.linalg.solve(L.T, np.linalg.solve(L, y_train))
    V = np.linalg.solve(L, K_te)
    mu = K_te.T @ alpha
    cov = K_ee - V.T @ V
    cov = 0.5 * (cov + cov.T)
    eig_min = np.linalg.eigvalsh(cov).min()
    if eig_min < 0:
        cov += (abs(eig_min) + 1e-6) * np.eye(n_ev)
    return mu, cov

def gp_posterior_sample(x_train, y_train, x_eval, lengthscale, outputscale,
                        linear_var, noise_var, rng):
    """Draw one function from GP posterior."""
    mu, cov = gp_posterior(x_train, y_train, x_eval, lengthscale,
                           outputscale, linear_var, noise_var)
    try:
        L = np.linalg.cholesky(cov + 1e-5 * np.eye(len(x_eval)))
    except np.linalg.LinAlgError:
        L = np.diag(np.sqrt(np.maximum(np.diag(cov), 1e-6)))
    return mu + L @ rng.normal(size=len(x_eval))

def gp_log_mll(x_train, y_train, lengthscale, outputscale, linear_var, noise_var):
    n = len(x_train)
    K = se_kernel(x_train, x_train, lengthscale, outputscale) \
        + linear_kernel(x_train, x_train, linear_var) \
        + noise_var * np.eye(n) + 1e-6 * np.eye(n)
    try:
        L = np.linalg.cholesky(K)
        alpha = np.linalg.solve(L.T, np.linalg.solve(L, y_train))
        logdet = 2 * np.sum(np.log(np.diag(L)))
        return -0.5 * y_train @ alpha - 0.5 * logdet - 0.5 * n * np.log(2*np.pi)
    except np.linalg.LinAlgError:
        return -np.inf


# ══════════════════════════════════════════════════════════════════
# Prior configs and sampling
# ══════════════════════════════════════════════════════════════════

PRIOR_CONFIGS = {
    "informative": {
        "label": "Informative",
        "color": "#2ecc71",
        "se_lengthscale": ("gamma", 6.0, 0.85),
        "se_outputscale": ("gamma", 6.0, 0.85),
        "linear_variance": ("gamma", 6.0, 0.85),
        "noise": ("gamma", 1.75, 1.0),
    },
    "vague": {
        "label": "Vague",
        "color": "#3498db",
        "se_lengthscale": ("lognormal", 0.0, 2.0),
        "se_outputscale": ("lognormal", 0.0, 2.0),
        "linear_variance": ("lognormal", 0.0, 2.0),
        "noise": ("lognormal", -1.0, 2.0),
    },
    "misspecified_tight": {
        "label": "Misspecified",
        "color": "#e74c3c",
        "se_lengthscale": ("gamma", 20.0, 4.0),
        "se_outputscale": ("gamma", 20.0, 4.0),
        "linear_variance": ("gamma", 20.0, 4.0),
        "noise": ("gamma", 5.0, 5.0),
    },
}

def sample_prior(family, p1, p2, n, rng):
    if family == "gamma":
        return gamma_dist.rvs(a=p1, scale=1.0/p2, size=n, random_state=rng)
    elif family == "lognormal":
        return lognorm.rvs(s=p2, scale=np.exp(p1), size=n, random_state=rng)

def prior_pdf(x, family, p1, p2):
    if family == "gamma":
        return gamma_dist.pdf(x, a=p1, scale=1.0/p2)
    elif family == "lognormal":
        return lognorm.pdf(x, s=p2, scale=np.exp(p1))

def sample_hyperparams(pc, n, rng):
    ls = np.clip(sample_prior(*pc["se_lengthscale"], n, rng), 0.1, 50)
    os_ = np.clip(sample_prior(*pc["se_outputscale"], n, rng), 0.01, 50)
    lv = np.clip(sample_prior(*pc["linear_variance"], n, rng), 0.001, 50)
    nv = np.clip(sample_prior(*pc["noise"], n, rng), 1e-4, 20)
    return ls, os_, lv, nv


# ══════════════════════════════════════════════════════════════════
# Induced prior computation
# ══════════════════════════════════════════════════════════════════

def sinlinear_fn(x, A, omega, phi, b, c):
    return A * np.sin(omega * x + phi) + b * x + c

def compute_averaged_gp(x_eval, x_data, y_data, pc, n_hyper=150, rng=None,
                        use_data=True):
    """MLL-weighted average GP predictive."""
    if rng is None:
        rng = np.random.RandomState(42)
    ls, os_, lv, nv = sample_hyperparams(pc, n_hyper, rng)

    means, vars_diag, log_mlls = [], [], []
    for i in range(n_hyper):
        if use_data and x_data is not None and len(x_data) > 0:
            mu, cov = gp_posterior(x_data, y_data, x_eval,
                                   ls[i], os_[i], lv[i], nv[i])
            lml = gp_log_mll(x_data, y_data, ls[i], os_[i], lv[i], nv[i])
        else:
            n_ev = len(x_eval)
            K = se_kernel(x_eval, x_eval, ls[i], os_[i]) \
                + linear_kernel(x_eval, x_eval, lv[i]) \
                + nv[i] * np.eye(n_ev)
            mu = np.zeros(n_ev)
            cov = K
            lml = 0.0
        means.append(mu)
        vars_diag.append(np.diag(cov))
        log_mlls.append(lml)

    means = np.array(means)
    vars_diag = np.array(vars_diag)
    log_mlls = np.array(log_mlls)

    valid = np.isfinite(log_mlls)
    if use_data and valid.any():
        lw = log_mlls.copy()
        lw[~valid] = -np.inf
        lw -= lw[valid].max()
        w = np.exp(lw)
        w /= w.sum()
    else:
        w = np.ones(n_hyper) / n_hyper

    avg_mean = np.sum(w[:, None] * means, axis=0)
    avg_var = np.sum(w[:, None] * (vars_diag + means**2), axis=0) - avg_mean**2
    return avg_mean, np.maximum(avg_var, 1e-6), w, ls

def compute_induced_weights(params, predict_fn, gp_mean, gp_var, x_eval, tau=1.0):
    """Boltzmann weights from variance-weighted MSE divergence."""
    n_s = params.shape[0]
    G = np.zeros(n_s)
    for s in range(n_s):
        try:
            mu_theta = predict_fn(x_eval, *params[s])
            G[s] = np.mean((gp_mean - mu_theta)**2 / (2 * np.maximum(gp_var, 1e-6)))
        except Exception:
            G[s] = 1e10
    log_w = -G / tau
    log_w -= np.max(log_w[np.isfinite(log_w)])
    w = np.exp(log_w)
    w /= w.sum()
    ess = 1.0 / np.sum(w**2)
    return w, ess


# ══════════════════════════════════════════════════════════════════
# Data
# ══════════════════════════════════════════════════════════════════

def generate_data(n, noise_std=0.3, bias_slope=0.25, seed=42, x_range=(-10, 10)):
    rng = np.random.RandomState(seed)
    x = np.sort(rng.uniform(*x_range, n))
    y = np.sin(x) + bias_slope * x + rng.normal(0, noise_std, n)
    return x, y


# ══════════════════════════════════════════════════════════════════
# THE FIGURE
# ══════════════════════════════════════════════════════════════════

def make_pipeline_figure(prior_name="informative", out_dir="/home/claude/mechanism_plots"):
    os.makedirs(out_dir, exist_ok=True)

    pc = PRIOR_CONFIGS[prior_name]
    color = pc["color"]
    dark_color = "#1a8a4a" if prior_name == "informative" else pc["color"]

    x_eval = np.linspace(-10, 10, 100)
    y_true = np.sin(x_eval) + 0.25 * x_eval

    # Full dataset
    x50, y50 = generate_data(50)

    # Data stages
    stages = [
        {"label": "Prior (n = 0)", "n": 0, "x": None, "y": None, "use_data": False},
        {"label": "After 10 observations", "n": 10, "x": x50[:10], "y": y50[:10], "use_data": True},
        {"label": "After 50 observations", "n": 50, "x": x50, "y": y50, "use_data": True},
    ]

    # Pre-sample Sin+Linear reference prior (shared across rows)
    n_param = 12000
    rng_p = np.random.RandomState(123)
    A_s     = rng_p.uniform(0.1, 3.0, n_param)
    omega_s = rng_p.uniform(0.3, 3.0, n_param)
    phi_s   = rng_p.uniform(-np.pi, np.pi, n_param)
    b_s     = rng_p.uniform(-1.0, 1.0, n_param)
    c_s     = rng_p.uniform(-3.0, 3.0, n_param)
    params_all = np.column_stack([A_s, omega_s, phi_s, b_s, c_s])

    # ── Figure layout ──
    fig = plt.figure(figsize=(22, 15))
    gs = GridSpec(3, 4, figure=fig, hspace=0.38, wspace=0.28,
                  width_ratios=[1, 1.2, 1, 1.2])

    n_gp_draws = 20
    n_sl_draws = 50

    row_labels = []

    for row, stage in enumerate(stages):
        # ────────────────────────────────────────────────────
        # Col 0: Lengthscale prior (+ effective posterior)
        # ────────────────────────────────────────────────────
        ax0 = fig.add_subplot(gs[row, 0])
        x_ls = np.linspace(0.01, 18, 500)
        y_ls = prior_pdf(x_ls, *pc["se_lengthscale"])
        ax0.fill_between(x_ls, y_ls, alpha=0.25, color=color)
        ax0.plot(x_ls, y_ls, color=color, linewidth=2, label="Prior p(ℓ)")

        # If we have data, show MLL-weighted "effective posterior" on ℓ
        rng_gp = np.random.RandomState(42)
        avg_mean, avg_var, mll_weights, ls_samples = compute_averaged_gp(
            x_eval, stage["x"], stage["y"], pc,
            n_hyper=200, rng=rng_gp, use_data=stage["use_data"])

        if stage["use_data"]:
            # Weighted KDE of lengthscale samples
            try:
                # Resample according to MLL weights for KDE
                rng_kde = np.random.RandomState(77)
                resamp_idx = rng_kde.choice(len(ls_samples), size=2000,
                                            p=mll_weights)
                ls_resamp = ls_samples[resamp_idx]
                ls_resamp = ls_resamp[(ls_resamp > 0.1) & (ls_resamp < 18)]
                if len(ls_resamp) > 50:
                    kde = gaussian_kde(ls_resamp, bw_method=0.3)
                    y_post = kde(x_ls)
                    # Scale to similar height as prior for visibility
                    y_post *= y_ls.max() / max(y_post.max(), 1e-10) * 0.8
                    ax0.fill_between(x_ls, y_post, alpha=0.35, color=dark_color)
                    ax0.plot(x_ls, y_post, color=dark_color, linewidth=2.5,
                             linestyle='--', label="Effective p(ℓ|D)")
            except Exception:
                pass

        ax0.set_xlim(0, 18)
        ax0.set_ylim(bottom=0)
        ax0.set_xlabel("Lengthscale ℓ", fontsize=11)
        ax0.set_ylabel("Density", fontsize=10)
        ax0.legend(fontsize=8, loc='upper right')
        ax0.grid(True, alpha=0.15)

        # Row label
        ax0.set_title(stage["label"], fontsize=13, fontweight='bold',
                      pad=12, color='#2c3e50')

        # ────────────────────────────────────────────────────
        # Col 1: GP predictive draws
        # ────────────────────────────────────────────────────
        ax1 = fig.add_subplot(gs[row, 1])

        rng_draw = np.random.RandomState(42)
        ls_d, os_d, lv_d, nv_d = sample_hyperparams(pc, n_gp_draws + 10, rng_draw)

        for i in range(n_gp_draws):
            if stage["use_data"]:
                f_draw = gp_posterior_sample(
                    stage["x"], stage["y"], x_eval,
                    ls_d[i], os_d[i], lv_d[i], nv_d[i], rng_draw)
            else:
                f_draw = gp_prior_sample(
                    x_eval, ls_d[i], os_d[i], lv_d[i], nv_d[i], rng_draw)
            ax1.plot(x_eval, f_draw, color=color, alpha=0.2, linewidth=0.9)

        ax1.plot(x_eval, y_true, 'k-', linewidth=2.5, alpha=0.85,
                 label='True: sin(x)+0.25x')

        if stage["use_data"]:
            ax1.scatter(stage["x"], stage["y"], c='black', s=25, zorder=5,
                        edgecolors='white', linewidth=0.5)

        gp_label = "GP prior predictive" if not stage["use_data"] else \
                   f"GP posterior predictive (n={stage['n']})"
        ax1.set_title(gp_label, fontsize=11)
        ax1.set_ylim(-7, 7)
        ax1.set_xlabel("x", fontsize=10)
        ax1.legend(fontsize=8, loc='upper left')
        ax1.grid(True, alpha=0.15)

        # ────────────────────────────────────────────────────
        # Col 2: Induced prior on ω
        # ────────────────────────────────────────────────────
        ax2 = fig.add_subplot(gs[row, 2])

        w, ess = compute_induced_weights(
            params_all,
            lambda x, A, om, ph, b_, c_: sinlinear_fn(x, A, om, ph, b_, c_),
            avg_mean, avg_var, x_eval, tau=1.0)

        # Reference prior (flat)
        ax2.hist(omega_s, bins=50, density=True, alpha=0.15, color='gray',
                 label='Reference (uniform)')

        # Induced prior
        ax2.hist(omega_s, bins=50, weights=w, density=True, alpha=0.55,
                 color=color, edgecolor='white', linewidth=0.3,
                 label=f'Induced (ESS={ess:.0f})')

        # True value
        ax2.axvline(1.0, color='black', linewidth=2.5, linestyle='--',
                     label='True ω = 1.0', zorder=5)

        # Weighted mean
        w_omega = np.sum(w * omega_s)
        w_omega_std = np.sqrt(np.sum(w * (omega_s - w_omega)**2))
        ax2.axvline(w_omega, color=dark_color, linewidth=2, alpha=0.9)

        ax2.set_xlabel("ω (frequency)", fontsize=11)
        ax2.set_ylabel("Density", fontsize=10)
        ax2.set_title(f"Induced p(ω|ψ)\nω̂ = {w_omega:.2f} ± {w_omega_std:.2f}",
                      fontsize=11)
        ax2.legend(fontsize=7.5, loc='upper right')
        ax2.set_xlim(0.3, 3.0)
        ax2.grid(True, alpha=0.15)

        # ────────────────────────────────────────────────────
        # Col 3: Sin+Linear predictive spaghetti
        # ────────────────────────────────────────────────────
        ax3 = fig.add_subplot(gs[row, 1])  # placeholder
        ax3 = fig.add_subplot(gs[row, 3])

        # Draw curves from induced prior
        rng_sl = np.random.RandomState(99)
        indices = rng_sl.choice(n_param, size=n_sl_draws, p=w)

        for idx in indices:
            y_sl = sinlinear_fn(x_eval, A_s[idx], omega_s[idx], phi_s[idx],
                                b_s[idx], c_s[idx])
            ax3.plot(x_eval, y_sl, color=color, alpha=0.12, linewidth=0.8)

        # Weighted mean curve
        w_A   = np.sum(w * A_s)
        w_om  = np.sum(w * omega_s)
        w_phi = np.sum(w * phi_s)
        w_b   = np.sum(w * b_s)
        w_c   = np.sum(w * c_s)
        y_wmean = sinlinear_fn(x_eval, w_A, w_om, w_phi, w_b, w_c)
        ax3.plot(x_eval, y_wmean, color=dark_color, linewidth=2.5, alpha=0.9,
                 label='Weighted mean')

        ax3.plot(x_eval, y_true, 'k-', linewidth=2.5, alpha=0.85,
                 label='True function')

        if stage["use_data"]:
            ax3.scatter(stage["x"], stage["y"], c='black', s=25, zorder=5,
                        edgecolors='white', linewidth=0.5)

        sl_label = "Sin+Linear prior predictive" if not stage["use_data"] else \
                   f"Sin+Linear induced predictive (n={stage['n']})"
        ax3.set_title(sl_label, fontsize=11)
        ax3.set_ylim(-7, 7)
        ax3.set_xlabel("x", fontsize=10)
        ax3.legend(fontsize=8, loc='upper left')
        ax3.grid(True, alpha=0.15)

    # ── Arrows between columns ──
    # Add column headers
    col_titles = [
        "① GP Hyperparameter\nPrior",
        "② GP Predictive\nDraws",
        "③ Induced Prior\non ω",
        "④ Sin+Linear\nPredictive"
    ]
    for col, title in enumerate(col_titles):
        # Position above the top row
        ax_top = fig.add_subplot(gs[0, col])
        # We'll use fig.text instead
        pass

    # Column header arrows + titles
    arrow_y = 0.96
    col_centers = [0.11, 0.355, 0.60, 0.845]
    # Use first subplot's annotate with figure fraction coords
    ax_ref = fig.axes[0]
    for i in range(3):
        ax_ref.annotate(
            "", xy=(col_centers[i+1] - 0.04, arrow_y),
            xytext=(col_centers[i] + 0.04, arrow_y),
            xycoords='figure fraction', textcoords='figure fraction',
            arrowprops=dict(arrowstyle='->', lw=2.5, color='#7f8c8d'))

    for i, title in enumerate(col_titles):
        fig.text(col_centers[i], arrow_y + 0.015, title,
                 ha='center', va='bottom', fontsize=11, fontweight='bold',
                 color='#2c3e50')

    fig.suptitle(
        f"BI* Pipeline: How GP Hyperparameter Priors Transfer into "
        f"Parametric Model Predictions\n({pc['label']} GP prior)",
        fontsize=15, fontweight='bold', y=1.06, color='#2c3e50')

    fig.savefig(os.path.join(out_dir, f"pipeline_{prior_name}.png"),
                dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  ✓ pipeline_{prior_name}.png")


def make_comparison_figure(out_dir="/home/claude/mechanism_plots"):
    """
    Same layout but one row per GP prior (informative/vague/misspecified),
    all at n=50 (posterior). Shows how different GP beliefs lead to
    different induced priors and different predictives.
    """
    os.makedirs(out_dir, exist_ok=True)

    x_eval = np.linspace(-10, 10, 100)
    y_true = np.sin(x_eval) + 0.25 * x_eval
    x50, y50 = generate_data(50)

    # Shared parameter samples
    n_param = 12000
    rng_p = np.random.RandomState(123)
    A_s     = rng_p.uniform(0.1, 3.0, n_param)
    omega_s = rng_p.uniform(0.3, 3.0, n_param)
    phi_s   = rng_p.uniform(-np.pi, np.pi, n_param)
    b_s     = rng_p.uniform(-1.0, 1.0, n_param)
    c_s     = rng_p.uniform(-3.0, 3.0, n_param)
    params_all = np.column_stack([A_s, omega_s, phi_s, b_s, c_s])

    prior_names = ["informative", "vague", "misspecified_tight"]

    fig = plt.figure(figsize=(22, 15))
    gs = GridSpec(3, 4, figure=fig, hspace=0.38, wspace=0.28,
                  width_ratios=[1, 1.2, 1, 1.2])

    for row, pname in enumerate(prior_names):
        pc = PRIOR_CONFIGS[pname]
        color = pc["color"]

        # Col 0: Lengthscale prior + effective posterior
        ax0 = fig.add_subplot(gs[row, 0])
        x_ls = np.linspace(0.01, 18, 500)
        y_ls = prior_pdf(x_ls, *pc["se_lengthscale"])
        ax0.fill_between(x_ls, y_ls, alpha=0.25, color=color)
        ax0.plot(x_ls, y_ls, color=color, linewidth=2, label="Prior p(ℓ)")

        rng_gp = np.random.RandomState(42)
        avg_mean, avg_var, mll_w, ls_samp = compute_averaged_gp(
            x_eval, x50, y50, pc, n_hyper=200, rng=rng_gp, use_data=True)

        # Effective posterior via resampling + KDE
        try:
            rng_kde = np.random.RandomState(77)
            ls_re = ls_samp[rng_kde.choice(len(ls_samp), 2000, p=mll_w)]
            ls_re = ls_re[(ls_re > 0.1) & (ls_re < 18)]
            if len(ls_re) > 50:
                kde = gaussian_kde(ls_re, bw_method=0.3)
                y_post = kde(x_ls)
                y_post *= y_ls.max() / max(y_post.max(), 1e-10) * 0.8
                ax0.fill_between(x_ls, y_post, alpha=0.35, color=color)
                ax0.plot(x_ls, y_post, color=color, linewidth=2.5,
                         linestyle='--', label="p(ℓ|D)")
        except Exception:
            pass

        ax0.set_xlim(0, 18)
        ax0.set_ylim(bottom=0)
        ax0.set_xlabel("Lengthscale ℓ", fontsize=11)
        ax0.legend(fontsize=8)
        ax0.grid(True, alpha=0.15)
        ax0.set_title(f"{pc['label']} GP prior", fontsize=13,
                      fontweight='bold', color=color)

        # Col 1: GP posterior draws
        ax1 = fig.add_subplot(gs[row, 1])
        rng_d = np.random.RandomState(42)
        ls_d, os_d, lv_d, nv_d = sample_hyperparams(pc, 30, rng_d)
        for i in range(20):
            f_draw = gp_posterior_sample(x50, y50, x_eval,
                                         ls_d[i], os_d[i], lv_d[i], nv_d[i], rng_d)
            ax1.plot(x_eval, f_draw, color=color, alpha=0.2, linewidth=0.9)
        ax1.plot(x_eval, y_true, 'k-', linewidth=2.5, alpha=0.85)
        ax1.scatter(x50, y50, c='black', s=15, zorder=5,
                    edgecolors='white', linewidth=0.3)
        ax1.set_ylim(-7, 7)
        ax1.set_xlabel("x", fontsize=10)
        ax1.set_title("GP posterior draws", fontsize=11)
        ax1.grid(True, alpha=0.15)

        # Col 2: Induced ω
        ax2 = fig.add_subplot(gs[row, 2])
        w, ess = compute_induced_weights(
            params_all,
            lambda x, A, om, ph, b_, c_: sinlinear_fn(x, A, om, ph, b_, c_),
            avg_mean, avg_var, x_eval, tau=1.0)

        ax2.hist(omega_s, bins=50, density=True, alpha=0.15, color='gray')
        ax2.hist(omega_s, bins=50, weights=w, density=True, alpha=0.55,
                 color=color, edgecolor='white', linewidth=0.3)
        ax2.axvline(1.0, color='black', linewidth=2.5, linestyle='--')
        w_om = np.sum(w * omega_s)
        w_std = np.sqrt(np.sum(w * (omega_s - w_om)**2))
        ax2.axvline(w_om, color=color, linewidth=2)
        ax2.set_xlabel("ω", fontsize=11)
        ax2.set_title(f"Induced p(ω|ψ)\nω̂={w_om:.2f}±{w_std:.2f}, ESS={ess:.0f}",
                      fontsize=10)
        ax2.set_xlim(0.3, 3.0)
        ax2.grid(True, alpha=0.15)

        # Col 3: Sin+Linear predictive
        ax3 = fig.add_subplot(gs[row, 3])
        rng_sl = np.random.RandomState(99)
        indices = rng_sl.choice(n_param, size=50, p=w)
        for idx in indices:
            y_sl = sinlinear_fn(x_eval, A_s[idx], omega_s[idx], phi_s[idx],
                                b_s[idx], c_s[idx])
            ax3.plot(x_eval, y_sl, color=color, alpha=0.12, linewidth=0.8)

        # Weighted mean
        y_wm = sinlinear_fn(x_eval,
                             np.sum(w * A_s), np.sum(w * omega_s),
                             np.sum(w * phi_s), np.sum(w * b_s),
                             np.sum(w * c_s))
        ax3.plot(x_eval, y_wm, color=color, linewidth=2.5, label='Weighted mean')
        ax3.plot(x_eval, y_true, 'k-', linewidth=2.5, alpha=0.85, label='True')
        ax3.scatter(x50, y50, c='black', s=15, zorder=5,
                    edgecolors='white', linewidth=0.3)
        ax3.set_ylim(-7, 7)
        ax3.set_xlabel("x", fontsize=10)
        ax3.set_title("Sin+Linear induced predictive", fontsize=11)
        ax3.legend(fontsize=8, loc='upper left')
        ax3.grid(True, alpha=0.15)

    # Column headers + arrows
    col_centers = [0.11, 0.355, 0.60, 0.845]
    arrow_y = 0.96
    col_titles = ["① p(ℓ) and p(ℓ|D)", "② GP Posterior Draws",
                  "③ Induced p(ω|ψ)", "④ Sin+Linear Predictive"]
    ax_ref = fig.axes[0]
    for i in range(3):
        ax_ref.annotate("", xy=(col_centers[i+1]-0.04, arrow_y),
                     xytext=(col_centers[i]+0.04, arrow_y),
                     xycoords='figure fraction', textcoords='figure fraction',
                     arrowprops=dict(arrowstyle='->', lw=2.5, color='#7f8c8d'))
    for i, title in enumerate(col_titles):
        fig.text(col_centers[i], arrow_y+0.015, title,
                 ha='center', va='bottom', fontsize=11, fontweight='bold',
                 color='#2c3e50')

    fig.suptitle("BI* Pipeline Comparison: Different GP Priors → "
                 "Different Induced Predictions (n=50)",
                 fontsize=15, fontweight='bold', y=1.06, color='#2c3e50')
    fig.savefig(os.path.join(out_dir, "pipeline_comparison.png"),
                dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  ✓ pipeline_comparison.png")


# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    out_dir = "/home/claude/mechanism_plots"

    print("=" * 60)
    print("  BI* Pipeline Figures")
    print("=" * 60)

    print("\n1. Pipeline figure (informative GP prior, 3 data stages)...")
    make_pipeline_figure("informative", out_dir)

    print("\n2. Pipeline figure (vague GP prior, 3 data stages)...")
    make_pipeline_figure("vague", out_dir)

    print("\n3. Pipeline figure (misspecified GP prior, 3 data stages)...")
    make_pipeline_figure("misspecified_tight", out_dir)

    print("\n4. Cross-prior comparison at n=50...")
    make_comparison_figure(out_dir)

    print(f"\n{'=' * 60}")
    for f in sorted(os.listdir(out_dir)):
        if f.startswith("pipeline"):
            sz = os.path.getsize(os.path.join(out_dir, f)) / 1024
            print(f"  {f:<40} ({sz:.0f} KB)")

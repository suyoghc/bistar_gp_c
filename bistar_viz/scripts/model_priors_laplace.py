"""
BI* Model Prior Probabilities — Laplace Approximation

Z_Mx = (1/V) ∫ exp(-G(ψ, θ_Mx(φ))/τ) dφ
     ≈ (1/V) × exp(-G(φ*)/τ) × (2πτ)^{d/2} × |H_G|^{-1/2}

where φ* = argmin G, H_G = Hessian of G at φ*, V = reference prior volume.

This fixes the Monte Carlo curse: the integral is estimated analytically
around the peak rather than by random sampling in high-D space.

Shows model priors at n=0, 10, 50 matching the mechanism figure.
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import gamma as gamma_dist, lognorm
from scipy.optimize import minimize
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

def gp_posterior_predictive(x_train, y_train, x_eval, ls, os_, lv, nv):
    n_tr, n_ev = len(x_train), len(x_eval)
    K_tt = (se_kernel(x_train, x_train, ls, os_)
            + linear_kernel(x_train, x_train, lv) + (nv + 1e-6) * np.eye(n_tr))
    K_te = (se_kernel(x_train, x_eval, ls, os_)
            + linear_kernel(x_train, x_eval, lv))
    K_ee = (se_kernel(x_eval, x_eval, ls, os_)
            + linear_kernel(x_eval, x_eval, lv) + nv * np.eye(n_ev))
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
    eig = np.linalg.eigvalsh(cov)
    if eig.min() < 0:
        cov += (abs(eig.min()) + 1e-6) * np.eye(n_ev)
    return mean, cov

def gp_log_marginal_likelihood(x_train, y_train, ls, os_, lv, nv):
    n = len(x_train)
    K = (se_kernel(x_train, x_train, ls, os_)
         + linear_kernel(x_train, x_train, lv) + (nv + 1e-6) * np.eye(n))
    try:
        L = np.linalg.cholesky(K)
        alpha = np.linalg.solve(L.T, np.linalg.solve(L, y_train))
        return -0.5 * y_train @ alpha - np.sum(np.log(np.diag(L))) - 0.5*n*np.log(2*np.pi)
    except np.linalg.LinAlgError:
        return -np.inf

# ── Hyperparameter config ────────────────────────────────────────

INFORMATIVE = {
    "se_lengthscale": ("gamma", 6.0, 0.85),
    "se_outputscale": ("gamma", 6.0, 0.85),
    "linear_variance": ("gamma", 6.0, 0.85),
    "noise": ("gamma", 1.75, 1.0),
}

def _sample(family, p1, p2, n, rng):
    if family == "gamma":
        return gamma_dist.rvs(a=p1, scale=1.0/p2, size=n, random_state=rng)
    return lognorm.rvs(s=p2, scale=np.exp(p1), size=n, random_state=rng)

def sample_hyperparams(pc, n, rng):
    ls = np.clip(_sample(*pc["se_lengthscale"], n, rng), 0.1, 50)
    os_ = np.clip(_sample(*pc["se_outputscale"], n, rng), 0.01, 50)
    lv = np.clip(_sample(*pc["linear_variance"], n, rng), 0.001, 50)
    nv = np.clip(_sample(*pc["noise"], n, rng), 1e-4, 20)
    return ls, os_, lv, nv

def compute_averaged_gp(x_eval, x_train, y_train, pc,
                        n_hyper=200, rng=None, use_data=True):
    if rng is None: rng = np.random.RandomState(42)
    ls, os_, lv, nv = sample_hyperparams(pc, n_hyper, rng)
    means, covs_d, lmls = [], [], []
    for i in range(n_hyper):
        if use_data and x_train is not None and len(x_train) > 0:
            mu, cov = gp_posterior_predictive(x_train, y_train, x_eval,
                                              ls[i], os_[i], lv[i], nv[i])
            lml = gp_log_marginal_likelihood(x_train, y_train,
                                             ls[i], os_[i], lv[i], nv[i])
        else:
            mu, cov = gp_prior_predictive(x_eval, ls[i], os_[i], lv[i], nv[i])
            lml = 0.0
        means.append(mu); covs_d.append(np.diag(cov)); lmls.append(lml)
    means, covs_d, lmls = np.array(means), np.array(covs_d), np.array(lmls)
    ok = np.isfinite(lmls)
    if use_data and ok.any():
        lw = lmls.copy(); lw[~ok] = -np.inf; lw -= lw[ok].max()
        mw = np.exp(lw); mw /= mw.sum()
    else:
        mw = np.ones(n_hyper) / n_hyper
    avg_m = np.sum(mw[:, None] * means, axis=0)
    avg_v = np.sum(mw[:, None] * (covs_d + means**2), axis=0) - avg_m**2
    return avg_m, np.maximum(avg_v, 1e-6)

# ── Model definitions ────────────────────────────────────────────

def sinlinear_fn(x, A, omega, phi, b, c):
    return A * np.sin(omega * x + phi) + b * x + c

def sinusoidal_fn(x, A, omega, phi):
    return A * np.sin(omega * x + phi)

def linear_fn(x, a, b):
    return a * x + b

def quadratic_fn(x, a, b, c):
    return a * x**2 + b * x + c


MODELS = {
    "Linear": {
        "predict_fn": lambda x, p: linear_fn(x, p[0], p[1]),
        "n_params": 2,
        "bounds": [(-2, 2), (-5, 5)],
        "inits": [[0.25, 0.0], [0.0, 0.0], [0.5, 1.0]],
        "color": "#e74c3c",
        "param_names": ["a (slope)", "b (intercept)"],
    },
    "Sinusoidal": {
        "predict_fn": lambda x, p: sinusoidal_fn(x, p[0], p[1], p[2]),
        "n_params": 3,
        "bounds": [(0.01, 5), (0.1, 5), (-np.pi, np.pi)],
        "inits": [[1.0, 1.0, 0.0], [0.5, 0.5, 0.0], [2.0, 1.5, 1.0],
                   [1.0, 2.0, -1.0], [1.5, 0.7, 0.5]],
        "color": "#3498db",
        "param_names": ["A", "ω", "φ"],
    },
    "Sin+Linear": {
        "predict_fn": lambda x, p: sinlinear_fn(x, p[0], p[1], p[2], p[3], p[4]),
        "n_params": 5,
        "bounds": [(0.01, 5), (0.1, 5), (-np.pi, np.pi), (-2, 2), (-5, 5)],
        "inits": [[1.0, 1.0, 0.0, 0.25, 0.0], [0.5, 0.5, 0.0, 0.1, 0.0],
                   [2.0, 1.5, 1.0, 0.5, 1.0], [1.0, 2.0, -1.0, 0.0, 0.0],
                   [1.5, 0.7, 0.5, 0.3, -0.5], [0.8, 1.0, 0.0, 0.25, 0.0]],
        "color": "#27ae60",
        "param_names": ["A", "ω", "φ", "b", "c"],
    },
    "Quadratic": {
        "predict_fn": lambda x, p: quadratic_fn(x, p[0], p[1], p[2]),
        "n_params": 3,
        "bounds": [(-0.5, 0.5), (-2, 2), (-5, 5)],
        "inits": [[0.0, 0.25, 0.0], [0.01, 0.0, 0.0], [-0.05, 0.5, 1.0]],
        "color": "#9b59b6",
        "param_names": ["a", "b", "c"],
    },
}


# ── Laplace approximation for Z_Mx ──────────────────────────────

def compute_G(params, predict_fn, gp_mean, gp_var, x_eval):
    """Pointwise variance-weighted MSE divergence."""
    try:
        mu = predict_fn(x_eval, params)
        return np.mean((gp_mean - mu)**2 / (2 * np.maximum(gp_var, 1e-6)))
    except Exception:
        return 1e10


def compute_log_Z_laplace(model_spec, gp_mean, gp_var, x_eval, tau):
    """
    Laplace approximation to log Z_Mx.

    log Z_Mx ≈ -G(φ*)/τ + (d/2) log(2πτ) - (1/2) log|H_G| - log(V)

    where φ* = argmin G, H_G = Hessian of G at φ*, V = parameter space volume.
    """
    pfn = model_spec["predict_fn"]
    d = model_spec["n_params"]
    bounds = model_spec["bounds"]

    # Parameter space volume (uniform reference prior)
    log_V = sum(np.log(b[1] - b[0]) for b in bounds)

    def objective(p):
        return compute_G(p, pfn, gp_mean, gp_var, x_eval) / tau

    # Multi-start optimization
    best_val = np.inf
    best_p = None
    for p0 in model_spec["inits"]:
        try:
            res = minimize(objective, p0, method='L-BFGS-B', bounds=bounds,
                           options={'maxiter': 2000, 'ftol': 1e-12})
            if res.fun < best_val:
                best_val = res.fun
                best_p = res.x
        except Exception:
            continue

    if best_p is None:
        return -np.inf, None, None

    G_star = best_val * tau  # undo the /tau in objective
    phi_star = best_p

    # Hessian of G (not G/τ) via finite differences
    eps = 1e-4
    H = np.zeros((d, d))
    G0 = compute_G(phi_star, pfn, gp_mean, gp_var, x_eval)

    for i in range(d):
        for j in range(i, d):
            p_pp = phi_star.copy(); p_pp[i] += eps; p_pp[j] += eps
            p_pm = phi_star.copy(); p_pm[i] += eps; p_pm[j] -= eps
            p_mp = phi_star.copy(); p_mp[i] -= eps; p_mp[j] += eps
            p_mm = phi_star.copy(); p_mm[i] -= eps; p_mm[j] -= eps

            H[i, j] = (compute_G(p_pp, pfn, gp_mean, gp_var, x_eval)
                       - compute_G(p_pm, pfn, gp_mean, gp_var, x_eval)
                       - compute_G(p_mp, pfn, gp_mean, gp_var, x_eval)
                       + compute_G(p_mm, pfn, gp_mean, gp_var, x_eval)) / (4 * eps**2)
            H[j, i] = H[i, j]

    # Regularize Hessian
    eigs = np.linalg.eigvalsh(H)
    if eigs.min() < 1e-8:
        H += (abs(eigs.min()) + 1e-6) * np.eye(d)

    # log|H/τ| = log|H| - d*log(τ)  ... but we need |H_G| not |H_{G/τ}|
    # Laplace: log Z ≈ -G*/τ + (d/2)log(2π) - (1/2)log|H/τ|
    #                = -G*/τ + (d/2)log(2πτ) - (1/2)log|H|
    sign, log_det_H = np.linalg.slogdet(H)
    if sign <= 0:
        log_det_H = np.sum(np.log(np.maximum(np.abs(np.linalg.eigvalsh(H)), 1e-10)))

    log_Z = (-G_star / tau
             + 0.5 * d * np.log(2 * np.pi * tau)
             - 0.5 * log_det_H
             - log_V)

    return log_Z, phi_star, G_star


def compute_model_priors_laplace(gp_mean, gp_var, x_eval, tau):
    """Compute normalized model priors via Laplace."""
    results = {}
    for mname, mspec in MODELS.items():
        log_Z, phi_star, G_star = compute_log_Z_laplace(
            mspec, gp_mean, gp_var, x_eval, tau)
        results[mname] = {
            "log_Z": log_Z,
            "phi_star": phi_star,
            "G_star": G_star,
        }

    # Normalize via logsumexp
    log_Zs = np.array([results[m]["log_Z"] for m in MODELS])
    max_lZ = np.max(log_Zs[np.isfinite(log_Zs)])
    priors = np.exp(log_Zs - max_lZ)
    priors /= priors.sum()

    for i, mname in enumerate(MODELS):
        results[mname]["prior"] = priors[i]

    return results


# ── Data generation ──────────────────────────────────────────────

def generate_data(n, noise_std=0.3, seed=42, x_range=(-10, 10)):
    rng = np.random.RandomState(seed)
    x = np.sort(rng.uniform(*x_range, n))
    return x, np.sin(x) + 0.25 * x + rng.normal(0, noise_std, n)


# ══════════════════════════════════════════════════════════════════
# FIGURES
# ══════════════════════════════════════════════════════════════════

def main():
    out_dir = "/home/claude/model_prior_plots"
    os.makedirs(out_dir, exist_ok=True)

    x_eval = np.linspace(-10, 10, 80)
    x_50, y_50 = generate_data(50, seed=42)
    pc = INFORMATIVE
    tau = 0.3

    model_names = list(MODELS.keys())
    model_colors = [MODELS[m]["color"] for m in model_names]

    # ── Compute across stages ────────────────────────────────────
    stages = [
        {"label": "Prior\n(no data)", "n": 0},
        {"label": "After\nn = 10",    "n": 10},
        {"label": "After\nn = 50",    "n": 50},
    ]

    stage_results = []
    for st in stages:
        n = st["n"]
        rng_gp = np.random.RandomState(42)
        if n == 0:
            gp_mean, gp_var = compute_averaged_gp(
                x_eval, None, None, pc, n_hyper=200, rng=rng_gp, use_data=False)
        else:
            xd, yd = x_50[:n], y_50[:n]
            gp_mean, gp_var = compute_averaged_gp(
                x_eval, xd, yd, pc, n_hyper=200, rng=rng_gp, use_data=True)

        results = compute_model_priors_laplace(gp_mean, gp_var, x_eval, tau)
        stage_results.append(results)

        print(f"\nn = {n}:")
        for m in model_names:
            r = results[m]
            phi_str = ""
            if r["phi_star"] is not None:
                phi_str = ", ".join([f"{v:.3f}" for v in r["phi_star"]])
            print(f"  {m:15s}: p(M|ψ) = {r['prior']:6.1%}  "
                  f"log Z = {r['log_Z']:8.2f}  "
                  f"G* = {r['G_star']:.3f}  φ* = [{phi_str}]")

    # ══════════════════════════════════════════════════════════════
    # Figure 1: Bar chart — 3 stages side by side
    # ══════════════════════════════════════════════════════════════
    print("\nGenerating figures...")

    fig, axes = plt.subplots(1, 3, figsize=(17, 6), sharey=True)

    for col, (st, results) in enumerate(zip(stages, stage_results)):
        ax = axes[col]
        priors = [results[m]["prior"] for m in model_names]

        bars = ax.bar(model_names, priors, color=model_colors, alpha=0.85,
                      edgecolor='white', linewidth=1.5)

        for bar, p in zip(bars, priors):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.015,
                    f'{p:.1%}', ha='center', va='bottom', fontsize=12,
                    fontweight='bold')

        ax.axhline(0.25, color='gray', ls='--', lw=1, alpha=0.5,
                   label='Uniform (1/4)' if col == 0 else None)
        ax.set_ylim(0, 1.05)
        ax.set_title(st["label"], fontsize=14, fontweight='bold')
        ax.tick_params(axis='x', rotation=15, labelsize=11)
        ax.grid(True, alpha=0.15, axis='y')

        if col == 0:
            ax.set_ylabel("GP-Informed Model Prior  p(M | ψ)", fontsize=12)
            ax.legend(fontsize=9)

    fig.suptitle(
        r"BI* Model Prior via Laplace:  $p(M_x|\psi) \propto Z_{M_x}$"
        f"  where  "
        r"$Z_{M_x} \approx e^{-G(\phi^*)/\tau} \cdot (2\pi\tau)^{d/2} \cdot |H_G|^{-1/2}$"
        f"\nτ = {tau}  |  Informative GP prior  |  "
        "Correct dimensionality penalty via Hessian determinant",
        fontsize=12, fontweight='bold', y=1.06)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "model_prior_bars_laplace.png"),
                dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("  ✓ model_prior_bars_laplace.png")

    # ══════════════════════════════════════════════════════════════
    # Figure 2: Continuous sweep n=0..50
    # ══════════════════════════════════════════════════════════════
    n_values = [0, 3, 5, 8, 10, 15, 20, 30, 40, 50]
    traces = {m: [] for m in model_names}
    logZ_traces = {m: [] for m in model_names}

    for n in n_values:
        rng_gp = np.random.RandomState(42)
        if n == 0:
            gm, gv = compute_averaged_gp(x_eval, None, None, pc,
                                          n_hyper=150, rng=rng_gp, use_data=False)
        else:
            gm, gv = compute_averaged_gp(x_eval, x_50[:n], y_50[:n], pc,
                                          n_hyper=150, rng=rng_gp, use_data=True)
        res = compute_model_priors_laplace(gm, gv, x_eval, tau)
        for m in model_names:
            traces[m].append(res[m]["prior"])
            logZ_traces[m].append(res[m]["log_Z"])
        print(f"  n={n:3d}: " + "  ".join(
            [f"{m}={res[m]['prior']:.1%}" for m in model_names]))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(17, 6))

    for m in model_names:
        ax1.plot(n_values, traces[m], 'o-', color=MODELS[m]["color"],
                 lw=2.5, ms=7, label=m)
    ax1.axhline(0.25, color='gray', ls='--', lw=1, alpha=0.5, label='Uniform')
    ax1.set_xlabel("Sample Size n", fontsize=12)
    ax1.set_ylabel("GP-Informed Model Prior  p(M | ψ)", fontsize=12)
    ax1.set_title("Model Prior Probability vs Data (Laplace)", fontsize=13,
                  fontweight='bold')
    ax1.legend(fontsize=10)
    ax1.set_ylim(-0.02, 1.02)
    ax1.grid(True, alpha=0.2)

    for m in model_names:
        ax2.plot(n_values, logZ_traces[m], 'o-', color=MODELS[m]["color"],
                 lw=2.5, ms=7, label=m)
    ax2.set_xlabel("Sample Size n", fontsize=12)
    ax2.set_ylabel("log Z_M  (unnormalized)", fontsize=12)
    ax2.set_title("Log Model Evidence vs Data", fontsize=13, fontweight='bold')
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.2)

    fig.suptitle(f"BI* Model Selection via Laplace Approximation (τ = {tau})\n"
                 "Left: normalized model priors  |  Right: unnormalized log Z",
                 fontsize=14, fontweight='bold', y=1.03)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "model_prior_sweep_laplace.png"),
                dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("  ✓ model_prior_sweep_laplace.png")

    # ══════════════════════════════════════════════════════════════
    # Figure 3: Stacked area — probability flow
    # ══════════════════════════════════════════════════════════════
    fig, ax = plt.subplots(figsize=(12, 6))
    stack_order = ["Sin+Linear", "Sinusoidal", "Linear", "Quadratic"]
    stack_data = np.array([traces[m] for m in stack_order])
    stack_colors = [MODELS[m]["color"] for m in stack_order]

    ax.stackplot(n_values, stack_data, labels=stack_order,
                 colors=stack_colors, alpha=0.7, edgecolor='white', lw=0.5)
    ax.set_xlabel("Sample Size n", fontsize=12)
    ax.set_ylabel("GP-Informed Model Prior  p(M | ψ)", fontsize=12)
    ax.set_title("BI* Model Prior Probability Flow (Laplace)\n"
                 "How GP beliefs redistribute probability across models as data arrives",
                 fontsize=13, fontweight='bold')
    ax.legend(loc='center right', fontsize=10, framealpha=0.9)
    ax.set_ylim(0, 1); ax.set_xlim(0, 50)
    ax.grid(True, alpha=0.15, axis='y')
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "model_prior_flow_laplace.png"),
                dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("  ✓ model_prior_flow_laplace.png")

    # ══════════════════════════════════════════════════════════════
    # Figure 4: Decomposition — G* vs Occam factor
    # ══════════════════════════════════════════════════════════════
    fig, axes = plt.subplots(1, 3, figsize=(17, 6))

    for col, (st, results) in enumerate(zip(stages, stage_results)):
        ax = axes[col]

        G_stars = []
        occam_factors = []
        for m in model_names:
            r = results[m]
            d = MODELS[m]["n_params"]
            log_V = sum(np.log(b[1] - b[0]) for b in MODELS[m]["bounds"])

            G_term = -r["G_star"] / tau if r["G_star"] is not None else 0
            occam = r["log_Z"] - G_term + log_V  # extract Occam piece
            G_stars.append(-G_term)  # positive = penalty
            occam_factors.append(-occam)  # positive = penalty

        x_pos = np.arange(len(model_names))
        w = 0.35

        bars1 = ax.bar(x_pos - w/2, G_stars, w, color=[MODELS[m]["color"] for m in model_names],
                       alpha=0.6, label='G*/τ (fit penalty)')
        bars2 = ax.bar(x_pos + w/2, occam_factors, w,
                       color=[MODELS[m]["color"] for m in model_names],
                       alpha=0.3, hatch='///', label='Occam penalty')

        ax.set_xticks(x_pos)
        ax.set_xticklabels(model_names, rotation=15, fontsize=10)
        ax.set_title(st["label"], fontsize=13, fontweight='bold')
        ax.grid(True, alpha=0.15, axis='y')

        if col == 0:
            ax.set_ylabel("Penalty (higher = worse)", fontsize=11)
            ax.legend(fontsize=9)

    fig.suptitle("BI* Evidence Decomposition: GP Fit Penalty vs Occam's Razor\n"
                 "G*/τ = how well best params match GP  |  "
                 "Occam = complexity penalty from parameter space volume",
                 fontsize=12, fontweight='bold', y=1.04)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "model_prior_decomp_laplace.png"),
                dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("  ✓ model_prior_decomp_laplace.png")

    print(f"\n{'='*60}")
    for f in sorted(os.listdir(out_dir)):
        if 'laplace' in f:
            print(f"  {f}")


if __name__ == "__main__":
    main()

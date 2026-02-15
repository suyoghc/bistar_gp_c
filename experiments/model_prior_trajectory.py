"""
BI* Model Prior Trajectory

Shows p(M_x | ψ) as a function of sample size n, using Laplace
approximation for Z_Mx to avoid Monte Carlo dimensionality bias.

Z_Mx ≈ exp(-G(φ*)/τ) · (2πτ)^{d/2} · |H_G|^{-1/2}

where φ* = argmin G(φ), H_G = Hessian of G/τ at φ*.
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import gamma as gamma_dist, lognorm
from scipy.optimize import minimize
from scipy.linalg import det
import os

# ── GP primitives ────────────────────────────────────────────────

def se_kernel(x1, x2, ls, os_):
    return os_ * np.exp(-0.5 * (x1[:, None] - x2[None, :]) ** 2 / ls**2)

def linear_kernel(x1, x2, v):
    return v * (x1[:, None] * x2[None, :])

def gp_prior_predictive(x_eval, ls, os_, lv, nv):
    K = se_kernel(x_eval, x_eval, ls, os_) + linear_kernel(x_eval, x_eval, lv)
    return np.zeros(len(x_eval)), K + nv * np.eye(len(x_eval))

def gp_posterior_predictive(x_tr, y_tr, x_ev, ls, os_, lv, nv):
    nt, ne = len(x_tr), len(x_ev)
    Ktt = se_kernel(x_tr, x_tr, ls, os_) + linear_kernel(x_tr, x_tr, lv) + (nv+1e-6)*np.eye(nt)
    Kte = se_kernel(x_tr, x_ev, ls, os_) + linear_kernel(x_tr, x_ev, lv)
    Kee = se_kernel(x_ev, x_ev, ls, os_) + linear_kernel(x_ev, x_ev, lv) + nv*np.eye(ne)
    try:
        L = np.linalg.cholesky(Ktt)
    except:
        Ktt += 1e-4*np.eye(nt); L = np.linalg.cholesky(Ktt)
    a = np.linalg.solve(L.T, np.linalg.solve(L, y_tr))
    V = np.linalg.solve(L, Kte)
    mu = Kte.T @ a
    cov = Kee - V.T @ V
    cov = 0.5*(cov+cov.T)
    e = np.linalg.eigvalsh(cov)
    if e.min() < 0: cov += (abs(e.min())+1e-6)*np.eye(ne)
    return mu, cov

def gp_lml(x_tr, y_tr, ls, os_, lv, nv):
    n = len(x_tr)
    K = se_kernel(x_tr, x_tr, ls, os_) + linear_kernel(x_tr, x_tr, lv) + (nv+1e-6)*np.eye(n)
    try:
        L = np.linalg.cholesky(K)
        a = np.linalg.solve(L.T, np.linalg.solve(L, y_tr))
        return -0.5*y_tr@a - np.sum(np.log(np.diag(L))) - 0.5*n*np.log(2*np.pi)
    except:
        return -np.inf

# ── Hyperparameter config ────────────────────────────────────────

INFORMATIVE = {
    "se_lengthscale": ("gamma", 6.0, 0.85),
    "se_outputscale": ("gamma", 6.0, 0.85),
    "linear_variance": ("gamma", 6.0, 0.85),
    "noise": ("gamma", 1.75, 1.0),
}

def _sample(fam, p1, p2, n, rng):
    if fam == "gamma": return gamma_dist.rvs(a=p1, scale=1/p2, size=n, random_state=rng)
    return lognorm.rvs(s=p2, scale=np.exp(p1), size=n, random_state=rng)

def sample_hyp(pc, n, rng):
    return (np.clip(_sample(*pc["se_lengthscale"], n, rng), 0.1, 50),
            np.clip(_sample(*pc["se_outputscale"], n, rng), 0.01, 50),
            np.clip(_sample(*pc["linear_variance"], n, rng), 0.001, 50),
            np.clip(_sample(*pc["noise"], n, rng), 1e-4, 20))

def compute_avg_gp(x_ev, x_tr, y_tr, pc, n_hyp=200, rng=None, use_data=True):
    if rng is None: rng = np.random.RandomState(42)
    ls, os_, lv, nv = sample_hyp(pc, n_hyp, rng)
    means, cvd, lmls = [], [], []
    for i in range(n_hyp):
        if use_data and x_tr is not None and len(x_tr) > 0:
            mu, cov = gp_posterior_predictive(x_tr, y_tr, x_ev, ls[i], os_[i], lv[i], nv[i])
            lml = gp_lml(x_tr, y_tr, ls[i], os_[i], lv[i], nv[i])
        else:
            mu, cov = gp_prior_predictive(x_ev, ls[i], os_[i], lv[i], nv[i])
            lml = 0.0
        means.append(mu); cvd.append(np.diag(cov)); lmls.append(lml)
    means, cvd, lmls = np.array(means), np.array(cvd), np.array(lmls)
    ok = np.isfinite(lmls)
    if use_data and ok.any():
        lw = lmls.copy(); lw[~ok] = -np.inf; lw -= lw[ok].max()
        mw = np.exp(lw); mw /= mw.sum()
    else:
        mw = np.ones(n_hyp)/n_hyp
    am = np.sum(mw[:, None]*means, 0)
    av = np.sum(mw[:, None]*(cvd + means**2), 0) - am**2
    return am, np.maximum(av, 1e-6)

# ── Parametric models ────────────────────────────────────────────

def sinlinear_fn(x, A, om, ph, b, c):
    return A * np.sin(om * x + ph) + b * x + c

def sinusoidal_fn(x, A, om, ph):
    return A * np.sin(om * x + ph)

def linear_fn(x, a, b):
    return a * x + b

def quadratic_fn(x, a, b, c):
    return a * x**2 + b * x + c


MODELS = {
    "Linear": {
        "fn": lambda x, p: p[0]*x + p[1],
        "p0_list": [np.array([0.25, 0.0])],
        "bounds": [(-3, 3), (-5, 5)],
        "d": 2,
        "color": "#e74c3c",
    },
    "Sinusoidal": {
        "fn": lambda x, p: p[0]*np.sin(p[1]*x + p[2]),
        "p0_list": [
            np.array([1.0, 1.0, 0.0]),
            np.array([1.0, 0.5, 0.0]),
            np.array([1.0, 2.0, 0.0]),
            np.array([0.5, 1.0, 1.0]),
        ],
        "bounds": [(0.01, 5), (0.1, 5), (-np.pi, np.pi)],
        "d": 3,
        "color": "#3498db",
    },
    "Sin+Linear": {
        "fn": lambda x, p: p[0]*np.sin(p[1]*x + p[2]) + p[3]*x + p[4],
        "p0_list": [
            np.array([1.0, 1.0, 0.0, 0.25, 0.0]),
            np.array([1.0, 0.5, 0.0, 0.0, 0.0]),
            np.array([1.0, 2.0, 0.0, 0.25, 0.0]),
            np.array([0.5, 1.5, 1.0, 0.1, 0.0]),
        ],
        "bounds": [(0.01, 5), (0.1, 5), (-np.pi, np.pi), (-2, 2), (-5, 5)],
        "d": 5,
        "color": "#27ae60",
    },
    "Quadratic": {
        "fn": lambda x, p: p[0]*x**2 + p[1]*x + p[2],
        "p0_list": [
            np.array([0.0, 0.25, 0.0]),
            np.array([0.01, 0.0, 0.0]),
        ],
        "bounds": [(-1, 1), (-3, 3), (-5, 5)],
        "d": 3,
        "color": "#9b59b6",
    },
}


# ── Laplace Z computation ────────────────────────────────────────

def compute_G(params, fn, gp_mean, gp_var, x_eval):
    """Divergence: variance-weighted MSE."""
    try:
        mu = fn(x_eval, params)
        return np.mean((gp_mean - mu)**2 / (2 * np.maximum(gp_var, 1e-6)))
    except:
        return 1e10


def numerical_hessian(f, x, eps=1e-4):
    """Numerical Hessian via finite differences."""
    d = len(x)
    H = np.zeros((d, d))
    f0 = f(x)
    for i in range(d):
        for j in range(i, d):
            ei = np.zeros(d); ei[i] = eps
            ej = np.zeros(d); ej[j] = eps
            fpp = f(x + ei + ej)
            fpm = f(x + ei - ej)
            fmp = f(x - ei + ej)
            fmm = f(x - ei - ej)
            H[i, j] = (fpp - fpm - fmp + fmm) / (4 * eps**2)
            H[j, i] = H[i, j]
    return H


def compute_laplace_Z(model_spec, gp_mean, gp_var, x_eval, tau):
    """
    Laplace approximation for Z_Mx.

    Z_Mx ≈ exp(-G(φ*)/τ) · (2πτ)^{d/2} · |H_G|^{-1/2}

    where H_G is the Hessian of G (not G/τ) at φ*.
    Uses multiple random restarts for robust optimization.
    """
    fn = model_spec["fn"]
    d = model_spec["d"]
    bounds = model_spec["bounds"]

    def obj(p):
        return compute_G(p, fn, gp_mean, gp_var, x_eval)

    # Try explicit starts + random perturbations
    best_G = np.inf
    best_p = None
    rng_opt = np.random.RandomState(42)
    
    all_starts = list(model_spec["p0_list"])
    # Add 20 random perturbations of each starting point
    for p0 in model_spec["p0_list"]:
        for _ in range(20):
            perturbed = p0 + rng_opt.normal(0, 0.3, d)
            # Clip to bounds
            for j in range(d):
                perturbed[j] = np.clip(perturbed[j], bounds[j][0]*0.99, bounds[j][1]*0.99)
            all_starts.append(perturbed)
    # Also add purely random points within bounds
    for _ in range(30):
        rp = np.array([rng_opt.uniform(b[0], b[1]) for b in bounds])
        all_starts.append(rp)

    for p0 in all_starts:
        try:
            res = minimize(obj, p0, bounds=bounds, method='L-BFGS-B',
                           options={'maxiter': 500})
            if res.fun < best_G:
                best_G = res.fun
                best_p = res.x.copy()
        except:
            pass

    if best_p is None:
        return 0.0, np.inf, None

    # Hessian of G at φ*
    H = numerical_hessian(obj, best_p, eps=1e-4)

    # Regularize: ensure H is PD
    eigvals = np.linalg.eigvalsh(H)
    if eigvals.min() <= 0:
        H += (abs(eigvals.min()) + 1e-6) * np.eye(d)

    # log Z = -G*/τ + (d/2)log(2πτ) - (1/2)log|H|
    sign, logdet_H = np.linalg.slogdet(H)
    if sign <= 0:
        logdet_H = np.sum(np.log(np.maximum(np.linalg.eigvalsh(H), 1e-10)))

    log_Z = -best_G / tau + 0.5 * d * np.log(2 * np.pi * tau) - 0.5 * logdet_H

    return log_Z, best_G, best_p


# ── Data ─────────────────────────────────────────────────────────

def generate_data(n, noise_std=0.3, seed=42, x_range=(-10, 10)):
    rng = np.random.RandomState(seed)
    x = np.sort(rng.uniform(*x_range, n))
    return x, np.sin(x) + 0.25*x + rng.normal(0, noise_std, n)


# ══════════════════════════════════════════════════════════════════
# MAIN
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

    # ── Sweep across n ───────────────────────────────────────────
    n_values = list(range(0, 51, 2))  # every 2 from 0 to 50

    log_Z_traces = {m: [] for m in model_names}
    G_star_traces = {m: [] for m in model_names}
    prior_traces = {m: [] for m in model_names}

    print("Computing model priors via Laplace Z...")
    print(f"{'n':>4}  {'Linear':>10}  {'Sinusoidal':>10}  {'Sin+Linear':>10}  {'Quadratic':>10}")
    print("-" * 50)

    for n in n_values:
        if n == 0:
            rng_gp = np.random.RandomState(42)
            gp_mean, gp_var = compute_avg_gp(
                x_eval, None, None, pc, n_hyp=150, rng=rng_gp, use_data=False)
        else:
            x_sub, y_sub = x_50[:n], y_50[:n]
            rng_gp = np.random.RandomState(42)
            gp_mean, gp_var = compute_avg_gp(
                x_eval, x_sub, y_sub, pc, n_hyp=150, rng=rng_gp, use_data=True)

        # Laplace Z for each model
        log_Zs = {}
        for mname, mspec in MODELS.items():
            log_Z, G_star, phi_star = compute_laplace_Z(
                mspec, gp_mean, gp_var, x_eval, tau)
            log_Zs[mname] = log_Z
            log_Z_traces[mname].append(log_Z)
            G_star_traces[mname].append(G_star)

        # Normalize to get model priors
        log_Z_arr = np.array([log_Zs[m] for m in model_names])
        log_Z_arr -= np.max(log_Z_arr)  # numerical stability
        Z_arr = np.exp(log_Z_arr)
        priors = Z_arr / Z_arr.sum()

        for i, m in enumerate(model_names):
            prior_traces[m].append(priors[i])

        if n % 10 == 0 or n <= 4:
            print(f"{n:4d}  " + "  ".join(f"{prior_traces[m][-1]:10.1%}" for m in model_names))

    # ══════════════════════════════════════════════════════════════
    # Figure 1: Model prior trajectory
    # ══════════════════════════════════════════════════════════════
    print("\nPlotting...")

    fig, axes = plt.subplots(1, 3, figsize=(21, 6))

    # Left: Model prior probabilities
    ax = axes[0]
    for m in model_names:
        ax.plot(n_values, prior_traces[m], 'o-', color=MODELS[m]["color"],
                linewidth=2.5, markersize=8, label=m)
    ax.axhline(0.25, color='gray', ls='--', lw=1, alpha=0.5, label='Uniform (1/4)')
    ax.set_xlabel("Sample Size n", fontsize=12)
    ax.set_ylabel("GP-Informed Model Prior  p(M | ψ)", fontsize=12)
    ax.set_title("Model Prior Trajectory", fontsize=13, fontweight='bold')
    ax.legend(fontsize=10)
    ax.set_ylim(-0.02, 1.02)
    ax.grid(True, alpha=0.2)

    # Middle: log Z (shows why — peak fit vs volume)
    ax = axes[1]
    for m in model_names:
        ax.plot(n_values, log_Z_traces[m], 'o-', color=MODELS[m]["color"],
                linewidth=2.5, markersize=8, label=m)
    ax.set_xlabel("Sample Size n", fontsize=12)
    ax.set_ylabel("log Z_M  (Laplace estimate)", fontsize=12)
    ax.set_title("Log Model Evidence (unnormalized)", fontsize=13, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.2)

    # Right: G* (best-case divergence — how well each model CAN fit the GP)
    ax = axes[2]
    for m in model_names:
        ax.plot(n_values, G_star_traces[m], 'o-', color=MODELS[m]["color"],
                linewidth=2.5, markersize=8, label=m)
    ax.set_xlabel("Sample Size n", fontsize=12)
    ax.set_ylabel("G* = min G(φ)  [best-case divergence]", fontsize=12)
    ax.set_title("How Well Each Model Can Match GP", fontsize=13, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.2)

    fig.suptitle(
        f"BI* Model Prior via Laplace: "
        r"$Z_{M} \approx e^{-G^*/\tau} \cdot (2\pi\tau)^{d/2} \cdot |H|^{-1/2}$"
        f"   (τ = {tau})\n"
        "Left: normalized model priors  |  "
        "Middle: log evidence (higher = more GP-compatible)  |  "
        "Right: best-case GP divergence (lower = better fit)",
        fontsize=13, fontweight='bold', y=1.05)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "model_prior_trajectory_laplace.png"),
                dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("  ✓ model_prior_trajectory_laplace.png")

    # ══════════════════════════════════════════════════════════════
    # Figure 2: Stacked area — probability flow
    # ══════════════════════════════════════════════════════════════
    fig, ax = plt.subplots(figsize=(12, 6))

    stack_order = ["Sin+Linear", "Sinusoidal", "Linear", "Quadratic"]
    stack_data = np.array([prior_traces[m] for m in stack_order])
    stack_colors = [MODELS[m]["color"] for m in stack_order]

    ax.stackplot(n_values, stack_data, labels=stack_order,
                 colors=stack_colors, alpha=0.7, edgecolor='white', linewidth=0.5)
    ax.set_xlabel("Sample Size n", fontsize=12)
    ax.set_ylabel("GP-Informed Model Prior  p(M | ψ)", fontsize=12)
    ax.set_title("BI* Model Prior Probability Flow (Laplace Z)\n"
                 "How GP beliefs redistribute probability as data accumulates",
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
    # Figure 3: τ sensitivity at n=50
    # ══════════════════════════════════════════════════════════════
    print("  τ sensitivity...")
    rng_gp = np.random.RandomState(42)
    gp_mean_50, gp_var_50 = compute_avg_gp(
        x_eval, x_50, y_50, pc, n_hyp=150, rng=rng_gp, use_data=True)

    taus = np.logspace(-1.5, 1.5, 30)
    tau_traces = {m: [] for m in model_names}

    for t in taus:
        log_Zs = {}
        for mname, mspec in MODELS.items():
            log_Z, _, _ = compute_laplace_Z(mspec, gp_mean_50, gp_var_50, x_eval, t)
            log_Zs[mname] = log_Z
        log_Z_arr = np.array([log_Zs[m] for m in model_names])
        log_Z_arr -= np.max(log_Z_arr)
        Z_arr = np.exp(log_Z_arr)
        priors = Z_arr / Z_arr.sum()
        for i, m in enumerate(model_names):
            tau_traces[m].append(priors[i])

    fig, ax = plt.subplots(figsize=(10, 6))
    for m in model_names:
        ax.plot(taus, tau_traces[m], '-', color=MODELS[m]["color"],
                linewidth=2.5, label=m)
    ax.axhline(0.25, color='gray', ls='--', lw=1, alpha=0.5, label='Uniform')
    ax.axvline(0.3, color='gray', ls=':', lw=1.5, alpha=0.7, label=f'τ = {tau}')
    ax.set_xscale('log')
    ax.set_xlabel("Temperature τ", fontsize=12)
    ax.set_ylabel("GP-Informed Model Prior  p(M | ψ)", fontsize=12)
    ax.set_title("τ Controls GP Influence on Model Prior (n=50, Laplace Z)\n"
                 "Low τ → GP dominates  |  High τ → uniform",
                 fontsize=13, fontweight='bold')
    ax.legend(fontsize=10)
    ax.set_ylim(-0.02, 1.02)
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "model_prior_tau_laplace.png"),
                dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("  ✓ model_prior_tau_laplace.png")

    # Summary
    print(f"\n{'='*55}")
    for f in sorted(os.listdir(out_dir)):
        if 'laplace' in f:
            print(f"  {f}")


if __name__ == "__main__":
    main()

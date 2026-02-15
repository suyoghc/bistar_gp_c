"""
BI* Unified Mechanism Figure — 3 rows × 5 columns

Row 1 (prior):  p(ℓ,σ²_lin) | GP prior predictive | induced p(ω) | induced p(b) | SL prior predictive
Row 2 (n=10):   posteriors   | GP posterior (10)    | induced p(ω|D)| induced p(b|D)| SL predictive (10)
Row 3 (n=50):   posteriors   | GP posterior (50)    | induced p(ω|D)| induced p(b|D)| SL predictive (50)

ℓ → ω: wiggliness belief transfers to frequency
σ²_lin → b: trend belief transfers to slope
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from scipy.stats import gamma as gamma_dist, lognorm, gaussian_kde
import os

# ── GP primitives ────────────────────────────────────────────────

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
    n_tr, n_ev = len(x_train), len(x_eval)
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

# ── Hyperparameter config and sampling ───────────────────────────

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

def _density(x, family, p1, p2):
    if family == "gamma":
        return gamma_dist.pdf(x, a=p1, scale=1.0/p2)
    return lognorm.pdf(x, s=p2, scale=np.exp(p1))

def sample_hyperparams(pc, n, rng):
    ls = np.clip(_sample(*pc["se_lengthscale"], n, rng), 0.1, 50)
    os_ = np.clip(_sample(*pc["se_outputscale"], n, rng), 0.01, 50)
    lv = np.clip(_sample(*pc["linear_variance"], n, rng), 0.001, 50)
    nv = np.clip(_sample(*pc["noise"], n, rng), 1e-4, 20)
    return ls, os_, lv, nv

# ── Induced prior computation ────────────────────────────────────

def sinlinear_fn(x, A, omega, phi, b, c):
    return A * np.sin(omega * x + phi) + b * x + c

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
        mll_w = np.exp(lw); mll_w /= mll_w.sum()
    else:
        mll_w = np.ones(n_hyper) / n_hyper
    avg_m = np.sum(mll_w[:, None] * means, axis=0)
    avg_v = np.sum(mll_w[:, None] * (covs_d + means**2), axis=0) - avg_m**2
    return avg_m, np.maximum(avg_v, 1e-6), ls, lv, mll_w

def compute_induced_weights(params, predict_fn, gp_mean, gp_var, x_eval, tau=1.0):
    G = np.zeros(params.shape[0])
    for s in range(len(G)):
        try:
            mu = predict_fn(x_eval, *params[s])
            G[s] = np.mean((gp_mean - mu)**2 / (2 * np.maximum(gp_var, 1e-6)))
        except Exception:
            G[s] = 1e10
    lw = -G / tau; lw -= np.max(lw[np.isfinite(lw)])
    w = np.exp(lw); w /= w.sum()
    return w, 1.0 / np.sum(w**2)

def make_kde(samples, weights, grid, bw=0.12):
    rng = np.random.RandomState(42)
    idx = rng.choice(len(samples), size=5000, p=weights)
    return gaussian_kde(samples[idx], bw_method=bw)(grid)

def generate_data(n, noise_std=0.3, seed=42, x_range=(-10, 10)):
    rng = np.random.RandomState(seed)
    x = np.sort(rng.uniform(*x_range, n))
    return x, np.sin(x) + 0.25 * x + rng.normal(0, noise_std, n)


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    out_dir = "/home/claude/mechanism_plots"
    os.makedirs(out_dir, exist_ok=True)

    x_eval = np.linspace(-10, 10, 100)
    y_true = np.sin(x_eval) + 0.25 * x_eval
    x_50, y_50 = generate_data(50, seed=42)
    x_10, y_10 = x_50[:10], y_50[:10]
    pc = INFORMATIVE

    n_param = 15000; tau = 0.3
    rng_p = np.random.RandomState(123)
    A_s  = rng_p.uniform(0.1, 3.0, n_param)
    om_s = rng_p.uniform(0.3, 3.0, n_param)
    ph_s = rng_p.uniform(-np.pi, np.pi, n_param)
    b_s  = rng_p.uniform(-1.0, 1.0, n_param)
    c_s  = rng_p.uniform(-3.0, 3.0, n_param)
    params = np.column_stack([A_s, om_s, ph_s, b_s, c_s])
    pfn = lambda x, A, o, p, b_, c_: sinlinear_fn(x, A, o, p, b_, c_)

    rows = [
        {"label": "Prior\n(no data)",       "xd": None, "yd": None, "use": False},
        {"label": "After 10\nobservations", "xd": x_10, "yd": y_10, "use": True},
        {"label": "After 50\nobservations", "xd": x_50, "yd": y_50, "use": True},
    ]

    rd_list = []
    for r in rows:
        rng_gp = np.random.RandomState(42)
        am, av, ls, lv, mw = compute_averaged_gp(
            x_eval, r["xd"], r["yd"], pc, n_hyper=200,
            rng=rng_gp, use_data=r["use"])
        w, ess = compute_induced_weights(params, pfn, am, av, x_eval, tau=tau)
        rd_list.append(dict(am=am, av=av, ls=ls, lv=lv, mw=mw, w=w, ess=ess))

    # ── Build figure ─────────────────────────────────────────────
    fig = plt.figure(figsize=(28, 15))
    gs = GridSpec(3, 5, figure=fig, hspace=0.40, wspace=0.28,
                  left=0.045, right=0.98, top=0.90, bottom=0.05)

    C_GP    = "#2980b9"
    C_SL    = "#27ae60"
    C_SLOPE = "#e67e22"
    C_REF   = "#bdc3c7"
    C_TRUE  = "black"
    C_DATA  = "#2c3e50"

    for ri, (rinfo, rd) in enumerate(zip(rows, rd_list)):
        xd, yd, use = rinfo["xd"], rinfo["yd"], rinfo["use"]

        # ─── Col 0: GP hyperparameter priors/posteriors ──────────
        ax = fig.add_subplot(gs[ri, 0])
        x_ls = np.linspace(0.01, 25, 500)
        y_pr_ls = _density(x_ls, *pc["se_lengthscale"])
        ax.fill_between(x_ls, y_pr_ls, alpha=0.12, color=C_REF)
        ax.plot(x_ls, y_pr_ls, color=C_REF, lw=1.5, ls='--', label="Prior p(ℓ)")
        if use:
            ax.hist(rd["ls"], bins=50, weights=rd["mw"], density=True,
                    alpha=0.50, color=C_GP, edgecolor='none', label="Posterior p(ℓ|D)")
        else:
            ax.fill_between(x_ls, y_pr_ls, alpha=0.30, color=C_GP)
        ax.set_xlim(0, 20); ax.set_xlabel("SE lengthscale ℓ", fontsize=10)
        ax.set_ylabel("Density", fontsize=9)
        ax.legend(fontsize=7, loc="upper right"); ax.grid(True, alpha=0.15)

        # Inset: σ²_lin
        axi = ax.inset_axes([0.42, 0.40, 0.55, 0.55])
        x_lv = np.linspace(0.01, 20, 500)
        y_pr_lv = _density(x_lv, *pc["linear_variance"])
        axi.fill_between(x_lv, y_pr_lv, alpha=0.12, color=C_REF)
        axi.plot(x_lv, y_pr_lv, color=C_REF, lw=1, ls='--')
        if use:
            axi.hist(rd["lv"], bins=40, weights=rd["mw"], density=True,
                     alpha=0.50, color=C_SLOPE, edgecolor='none')
        else:
            axi.fill_between(x_lv, y_pr_lv, alpha=0.30, color=C_SLOPE)
        axi.set_xlim(0, 15); axi.set_xlabel("σ²_lin", fontsize=8)
        axi.set_title("Linear variance", fontsize=8, color=C_SLOPE, fontweight='bold')
        axi.tick_params(labelsize=6); axi.grid(True, alpha=0.15)

        ax.text(-0.30, 0.5, rinfo["label"], transform=ax.transAxes,
                fontsize=12, fontweight='bold', rotation=90, va='center', ha='center')

        # ─── Col 1: GP predictive draws ─────────────────────────
        ax = fig.add_subplot(gs[ri, 1])
        rng2 = np.random.RandomState(42)
        lsa, osa, lva, nva = sample_hyperparams(pc, 200, rng2)
        rng_d = np.random.RandomState(77)
        for i in range(25):
            if use:
                mu, cov = gp_posterior_predictive(xd, yd, x_eval,
                                                   lsa[i], osa[i], lva[i], nva[i])
            else:
                mu, cov = gp_prior_predictive(x_eval, lsa[i], osa[i], lva[i], nva[i])
            try:
                L = np.linalg.cholesky(cov + 1e-5*np.eye(len(x_eval)))
                f = mu + L @ rng_d.normal(size=len(x_eval))
            except np.linalg.LinAlgError:
                f = mu + np.sqrt(np.maximum(np.diag(cov),0)) * rng_d.normal(size=len(x_eval))
            ax.plot(x_eval, f, color=C_GP, alpha=0.18, lw=0.7)

        ax.plot(x_eval, rd["am"], color=C_GP, lw=2.5, alpha=0.9, label="GP mean")
        s = np.sqrt(rd["av"])
        ax.fill_between(x_eval, rd["am"]-2*s, rd["am"]+2*s, color=C_GP, alpha=0.12)
        ax.plot(x_eval, y_true, color=C_TRUE, lw=2, ls='--', label="True function")
        if xd is not None:
            ax.scatter(xd, yd, c=C_DATA, s=22, zorder=5, edgecolors='white', linewidths=0.5)
        ax.set_ylim(-7, 7); ax.set_xlabel("x", fontsize=10)
        ax.legend(fontsize=7, loc="upper left"); ax.grid(True, alpha=0.15)
        ax.annotate("", xy=(1.06, 0.5), xytext=(1.01, 0.5),
                     xycoords='axes fraction',
                     arrowprops=dict(arrowstyle='->', lw=2, color='#7f8c8d'))

        # ─── Col 2: Induced p(ω|ψ) ─────────────────────────────
        ax = fig.add_subplot(gs[ri, 2])
        og = np.linspace(0.3, 3.0, 300)
        rh = 1.0 / (3.0 - 0.3)
        ax.fill_between(og, rh, alpha=0.12, color=C_REF)
        ax.axhline(rh, color=C_REF, lw=1, alpha=0.4, label="Reference")
        try:
            kv = make_kde(om_s, rd["w"], og, bw=0.12)
            ax.fill_between(og, kv, alpha=0.40, color=C_SL)
            ax.plot(og, kv, color=C_SL, lw=2.5, label="Induced p(ω|ψ)")
        except:
            ax.hist(om_s, bins=60, weights=rd["w"], density=True,
                    alpha=0.5, color=C_SL, edgecolor='none')
        ax.axvline(1.0, color=C_TRUE, lw=2.5, ls='--', label="True ω = 1.0")
        ax.set_xlabel("ω (frequency)", fontsize=10); ax.set_ylabel("Density", fontsize=9)
        ax.set_xlim(0.3, 3.0)
        ax.legend(fontsize=7, loc="upper right"); ax.grid(True, alpha=0.15)
        ax.text(0.03, 0.95, f"ESS = {rd['ess']:.0f}", transform=ax.transAxes,
                fontsize=9, va='top',
                bbox=dict(boxstyle='round,pad=0.3', fc='white', alpha=0.85, ec='#bdc3c7'))

        # ─── Col 3: Induced p(b|ψ) ─────────────────────────────
        ax = fig.add_subplot(gs[ri, 3])
        bg = np.linspace(-1.0, 1.0, 300)
        rh_b = 0.5  # uniform on [-1,1]
        ax.fill_between(bg, rh_b, alpha=0.12, color=C_REF)
        ax.axhline(rh_b, color=C_REF, lw=1, alpha=0.4, label="Reference")
        try:
            kv_b = make_kde(b_s, rd["w"], bg, bw=0.12)
            ax.fill_between(bg, kv_b, alpha=0.40, color=C_SLOPE)
            ax.plot(bg, kv_b, color=C_SLOPE, lw=2.5, label="Induced p(b|ψ)")
        except:
            ax.hist(b_s, bins=60, weights=rd["w"], density=True,
                    alpha=0.5, color=C_SLOPE, edgecolor='none')
        ax.axvline(0.25, color=C_TRUE, lw=2.5, ls='--', label="True b = 0.25")
        ax.set_xlabel("b (slope)", fontsize=10); ax.set_ylabel("Density", fontsize=9)
        ax.set_xlim(-1.0, 1.0)
        ax.legend(fontsize=7, loc="upper left"); ax.grid(True, alpha=0.15)
        ax.annotate("", xy=(1.06, 0.5), xytext=(1.01, 0.5),
                     xycoords='axes fraction',
                     arrowprops=dict(arrowstyle='->', lw=2, color='#7f8c8d'))

        # ─── Col 4: Sin+Linear predictive ───────────────────────
        ax = fig.add_subplot(gs[ri, 4])
        rng_sl = np.random.RandomState(99)
        idx = rng_sl.choice(n_param, size=40, p=rd["w"])
        for j in idx:
            ax.plot(x_eval, sinlinear_fn(x_eval, A_s[j], om_s[j], ph_s[j],
                                          b_s[j], c_s[j]),
                    color=C_SL, alpha=0.15, lw=0.7)
        ax.plot(x_eval, y_true, color=C_TRUE, lw=2, ls='--', label="True function")
        if xd is not None:
            ax.scatter(xd, yd, c=C_DATA, s=22, zorder=5,
                       edgecolors='white', linewidths=0.5)
        ax.set_ylim(-7, 7); ax.set_xlabel("x", fontsize=10)
        ax.legend(fontsize=7, loc="upper left"); ax.grid(True, alpha=0.15)

    # Column headers
    titles = [
        "GP Hyperparameter\nPrior / Posterior",
        "GP Predictive\n(function draws)",
        "Induced Prior\non ω (frequency)",
        "Induced Prior\non b (slope)",
        "Sin+Linear Predictive\n(from induced prior)",
    ]
    for c, t in enumerate(titles):
        fig.axes[c].set_title(t, fontsize=11, fontweight='bold', pad=12)

    fig.suptitle(
        "BI* Mechanism: How GP Hyperparameter Beliefs Transfer into "
        "Parametric Model Predictions\n"
        "Read left→right: belief transfer  |  "
        "Read top→bottom: data accumulation  |  "
        "ℓ → ω (wiggliness → frequency)    σ²_lin → b (trend → slope)",
        fontsize=14, fontweight='bold', y=0.97)

    path = os.path.join(out_dir, "mechanism_unified.png")
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"✓ {path}")

if __name__ == "__main__":
    main()

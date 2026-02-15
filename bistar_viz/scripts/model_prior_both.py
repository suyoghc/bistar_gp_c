"""
BI* Model Prior Trajectory — Two Versions Side by Side

LEFT:  Soft transfer (no Occam): score(Mx|ψ) = ∫ exp(-G(ψ,θ)/τ) dφ
       → Laplace: exp(-G*/τ) · (2πτ)^{d/2} · |H|^{-1/2}
       → Complex models naturally score higher (more compatible volume)

RIGHT: Soft transfer + Occam:   score(Mx|ψ) = ∫ p_ref(φ) exp(-G(ψ,θ)/τ) dφ
       → Laplace: (1/V_ref) · exp(-G*/τ) · (2πτ)^{d/2} · |H|^{-1/2}
       → Penalizes wasteland of bad parameter combinations

Both aggregate over ψ using MLL-weighted GP posterior.
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import gamma as gamma_dist
from scipy.optimize import minimize, differential_evolution
from scipy.ndimage import uniform_filter1d
import os, time, warnings
warnings.filterwarnings('ignore')

# === GP primitives ===
def se_k(x1,x2,ls,os_): return os_*np.exp(-0.5*(x1[:,None]-x2[None,:])**2/ls**2)
def lin_k(x1,x2,v): return v*(x1[:,None]*x2[None,:])

def gp_post(xtr,ytr,xev,ls,os_,lv,nv):
    nt,ne = len(xtr),len(xev)
    Ktt = se_k(xtr,xtr,ls,os_)+lin_k(xtr,xtr,lv)+(nv+1e-6)*np.eye(nt)
    Kte = se_k(xtr,xev,ls,os_)+lin_k(xtr,xev,lv)
    Kee = se_k(xev,xev,ls,os_)+lin_k(xev,xev,lv)+nv*np.eye(ne)
    L = np.linalg.cholesky(Ktt+1e-5*np.eye(nt))
    a = np.linalg.solve(L.T, np.linalg.solve(L, ytr))
    V = np.linalg.solve(L, Kte)
    return Kte.T@a, np.maximum(np.diag(Kee - V.T@V), 1e-6)

def gp_prior(xev,ls,os_,lv,nv):
    K = se_k(xev,xev,ls,os_)+lin_k(xev,xev,lv)+nv*np.eye(len(xev))
    return np.zeros(len(xev)), np.maximum(np.diag(K), 1e-6)

def gp_lml(xtr,ytr,ls,os_,lv,nv):
    n = len(xtr)
    K = se_k(xtr,xtr,ls,os_)+lin_k(xtr,xtr,lv)+(nv+1e-6)*np.eye(n)
    try:
        L = np.linalg.cholesky(K)
        a = np.linalg.solve(L.T, np.linalg.solve(L, ytr))
        return -0.5*ytr@a - np.sum(np.log(np.diag(L))) - 0.5*n*np.log(2*np.pi)
    except: return -np.inf

# === Hyperparameter sampling ===
PC = {"se_lengthscale":("gamma",6.0,0.85), "se_outputscale":("gamma",6.0,0.85),
      "linear_variance":("gamma",6.0,0.85), "noise":("gamma",1.75,1.0)}

def sample_hyp(n, rng):
    s = lambda k: np.clip(gamma_dist.rvs(a=PC[k][1],scale=1/PC[k][2],size=n,random_state=rng),0.01,50)
    return (s("se_lengthscale"), s("se_outputscale"), s("linear_variance"),
            np.clip(gamma_dist.rvs(a=PC["noise"][1],scale=1/PC["noise"][2],size=n,random_state=rng),1e-4,20))

# === Models ===
MODELS = {
    "Linear":      {"fn": lambda x,p: p[0]*x+p[1],
                    "bounds":[(-3,3),(-5,5)], "d":2, "color":"#e74c3c"},
    "Sinusoidal":  {"fn": lambda x,p: p[0]*np.sin(p[1]*x+p[2]),
                    "bounds":[(0.01,5),(0.1,5),(-np.pi,np.pi)], "d":3, "color":"#3498db"},
    "Sin+Linear":  {"fn": lambda x,p: p[0]*np.sin(p[1]*x+p[2])+p[3]*x+p[4],
                    "bounds":[(0.01,5),(0.1,5),(-np.pi,np.pi),(-2,2),(-5,5)], "d":5, "color":"#27ae60"},
    "Quadratic":   {"fn": lambda x,p: p[0]*x**2+p[1]*x+p[2],
                    "bounds":[(-1,1),(-3,3),(-5,5)], "d":3, "color":"#9b59b6"},
}

def compute_G(p, fn, gp_m, gp_v, x):
    try: return np.mean((gp_m - fn(x,p))**2 / (2*gp_v))
    except: return 1e10

def num_hess(f, x, eps=1e-4):
    d = len(x); H = np.zeros((d,d))
    for i in range(d):
        for j in range(i, d):
            ei,ej = np.zeros(d),np.zeros(d); ei[i]=eps; ej[j]=eps
            H[i,j] = (f(x+ei+ej)-f(x+ei-ej)-f(x-ei+ej)+f(x-ei-ej))/(4*eps**2)
            H[j,i] = H[i,j]
    return H

def laplace_Z(mspec, gp_m, gp_v, x_eval, tau):
    """
    Returns (log_Z_raw, log_Z_occam, G_star)
    
    log_Z_raw   = -G*/τ + (d/2)log(2πτ) - ½log|H|          [no Occam]
    log_Z_occam = log_Z_raw - log(V_ref)                     [with Occam]
    """
    fn, d, bounds = mspec["fn"], mspec["d"], mspec["bounds"]
    V_ref = np.prod([b[1]-b[0] for b in bounds])
    obj = lambda p: compute_G(p, fn, gp_m, gp_v, x_eval)

    # Global optimizer + multi-start local
    best_G, best_p = np.inf, None
    try:
        de = differential_evolution(obj, bounds, seed=42, maxiter=200, tol=1e-10, polish=True)
        best_G, best_p = de.fun, de.x
    except: pass

    rng = np.random.RandomState(42)
    for _ in range(40):
        p0 = np.array([rng.uniform(b[0],b[1]) for b in bounds])
        try:
            r = minimize(obj, p0, bounds=bounds, method='L-BFGS-B', options={'maxiter':500})
            if r.fun < best_G: best_G = r.fun; best_p = r.x.copy()
        except: pass

    if best_p is None:
        return -1e10, -1e10, np.inf

    # Hessian
    H = num_hess(obj, best_p, eps=1e-4)
    eig = np.linalg.eigvalsh(H)
    if eig.min() <= 0: H += (abs(eig.min())+1e-4)*np.eye(d)
    sign, logdet = np.linalg.slogdet(H)
    if sign <= 0: logdet = np.sum(np.log(np.maximum(np.linalg.eigvalsh(H), 1e-10)))

    log_Z_raw   = -best_G/tau + 0.5*d*np.log(2*np.pi*tau) - 0.5*logdet
    log_Z_occam = log_Z_raw - np.log(V_ref)

    return log_Z_raw, log_Z_occam, best_G


def compute_avg_gp(x_ev, x_tr, y_tr, n_hyp=150):
    """MLL-weighted averaged GP."""
    rng = np.random.RandomState(42)
    ls, os_, lv, nv = sample_hyp(n_hyp, rng)
    ms, vs, lmls = [], [], []
    for i in range(n_hyp):
        if x_tr is not None and len(x_tr) > 0:
            m, v = gp_post(x_tr, y_tr, x_ev, ls[i], os_[i], lv[i], nv[i])
            lml = gp_lml(x_tr, y_tr, ls[i], os_[i], lv[i], nv[i])
        else:
            m, v = gp_prior(x_ev, ls[i], os_[i], lv[i], nv[i])
            lml = 0.0
        ms.append(m); vs.append(v); lmls.append(lml)
    ms, vs, lmls = np.array(ms), np.array(vs), np.array(lmls)
    ok = np.isfinite(lmls)
    if x_tr is not None and ok.any():
        lw = lmls.copy(); lw[~ok] = -np.inf; lw -= lw[ok].max()
        mw = np.exp(lw); mw /= mw.sum()
    else:
        mw = np.ones(n_hyp)/n_hyp
    am = np.sum(mw[:,None]*ms, 0)
    av = np.sum(mw[:,None]*(vs+ms**2), 0) - am**2
    return am, np.maximum(av, 1e-6)


# === Data ===
def gen_data(n, seed=42):
    rng = np.random.RandomState(seed)
    x = np.sort(rng.uniform(-10,10,n))
    return x, np.sin(x) + 0.25*x + rng.normal(0, 0.3, n)


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    out_dir = "/home/claude/model_prior_plots"
    os.makedirs(out_dir, exist_ok=True)

    x_eval = np.linspace(-10, 10, 80)
    x_50, y_50 = gen_data(50, seed=42)
    tau = 0.3
    mnames = list(MODELS.keys())

    n_values = list(range(0, 51, 2))

    traces_raw   = {m: [] for m in mnames}  # no Occam
    traces_occam = {m: [] for m in mnames}  # with Occam
    Gstar_traces = {m: [] for m in mnames}

    t0 = time.time()
    print("Computing both versions of model prior (Laplace Z)...")
    print(f"  τ={tau}, n_values: {n_values[0]}..{n_values[-1]} (step {n_values[1]-n_values[0]})")
    print()
    print(f"{'n':>4}  {'--- No Occam ---':^44s}  {'--- With Occam ---':^44s}")

    for n in n_values:
        x_sub = x_50[:n] if n > 0 else None
        y_sub = y_50[:n] if n > 0 else None
        gp_m, gp_v = compute_avg_gp(x_eval, x_sub, y_sub, n_hyp=150)

        logZ_raw, logZ_occ = {}, {}
        for m in mnames:
            lr, lo, gs = laplace_Z(MODELS[m], gp_m, gp_v, x_eval, tau)
            logZ_raw[m] = lr
            logZ_occ[m] = lo
            Gstar_traces[m].append(gs)

        # Normalize each version
        for traces, logZs in [(traces_raw, logZ_raw), (traces_occam, logZ_occ)]:
            arr = np.array([logZs[m] for m in mnames])
            arr -= arr.max()
            Z = np.exp(arr); p = Z / Z.sum()
            for i, m in enumerate(mnames):
                traces[m].append(p[i])

        if n % 10 == 0:
            raw_str   = "  ".join(f"{traces_raw[m][-1]:5.1%}" for m in mnames)
            occ_str   = "  ".join(f"{traces_occam[m][-1]:5.1%}" for m in mnames)
            print(f"  {n:2d}   {raw_str}    {occ_str}   [{time.time()-t0:.0f}s]")

    # ══════════════════════════════════════════════════════════════
    # Figure: 2×2 grid
    # ══════════════════════════════════════════════════════════════
    fig, axes = plt.subplots(2, 2, figsize=(18, 13))
    sm = lambda v: uniform_filter1d(np.array(v), 3, mode='nearest')

    # Top-left: No Occam trajectory
    ax = axes[0, 0]
    for m in mnames:
        ax.plot(n_values, sm(traces_raw[m]), 'o-', color=MODELS[m]["color"],
                lw=2.5, ms=5, label=m)
    ax.axhline(0.25, color='gray', ls='--', lw=1, alpha=0.4)
    ax.set_xlabel("Sample Size n", fontsize=12)
    ax.set_ylabel("p(M | ψ)", fontsize=12)
    ax.set_title("Soft Transfer — No Occam Penalty\n"
                 r"$\mathrm{score}(M_x|\psi) = \int e^{-G/\tau}\,d\phi$"
                 "\n(faithful to BI* spirit: complex models capture more ψ-volume)",
                 fontsize=11, fontweight='bold')
    ax.legend(fontsize=9); ax.set_ylim(-0.02, 1.02); ax.grid(True, alpha=0.2)

    # Top-right: With Occam trajectory
    ax = axes[0, 1]
    for m in mnames:
        ax.plot(n_values, sm(traces_occam[m]), 'o-', color=MODELS[m]["color"],
                lw=2.5, ms=5, label=m)
    ax.axhline(0.25, color='gray', ls='--', lw=1, alpha=0.4)
    ax.set_xlabel("Sample Size n", fontsize=12)
    ax.set_ylabel("p(M | ψ)", fontsize=12)
    ax.set_title("Soft Transfer — With Occam Penalty\n"
                 r"$\mathrm{score}(M_x|\psi) = \int p_{ref}(\phi)\,e^{-G/\tau}\,d\phi$"
                 "\n(penalizes fraction of parameter space that is GP-compatible)",
                 fontsize=11, fontweight='bold')
    ax.legend(fontsize=9); ax.set_ylim(-0.02, 1.02); ax.grid(True, alpha=0.2)

    # Bottom-left: G* (shared — same for both versions)
    ax = axes[1, 0]
    for m in mnames:
        ax.plot(n_values, sm(Gstar_traces[m]), 'o-', color=MODELS[m]["color"],
                lw=2.5, ms=5, label=m)
    ax.set_xlabel("Sample Size n", fontsize=12)
    ax.set_ylabel("G* = min_φ G(ψ, θ)", fontsize=12)
    ax.set_title("Best-Case Divergence (shared)\n"
                 "How well each model CAN match the averaged GP",
                 fontsize=11, fontweight='bold')
    ax.legend(fontsize=9); ax.grid(True, alpha=0.2)

    # Bottom-right: Difference — how much Occam changes things
    ax = axes[1, 1]
    for m in mnames:
        diff = np.array(traces_raw[m]) - np.array(traces_occam[m])
        ax.plot(n_values, sm(diff), 'o-', color=MODELS[m]["color"],
                lw=2.5, ms=5, label=m)
    ax.axhline(0, color='gray', ls='-', lw=1, alpha=0.3)
    ax.set_xlabel("Sample Size n", fontsize=12)
    ax.set_ylabel("Δp = p(no Occam) − p(Occam)", fontsize=12)
    ax.set_title("Effect of Occam Penalty\n"
                 "Positive = model gains from removing Occam",
                 fontsize=11, fontweight='bold')
    ax.legend(fontsize=9); ax.grid(True, alpha=0.2)

    fig.suptitle(
        f"BI* Model Prior: Soft Transfer With vs. Without Implicit Occam's Razor   [τ = {tau}]\n"
        "Both use Laplace Z with differential evolution optimizer",
        fontsize=14, fontweight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    path = os.path.join(out_dir, "model_prior_both_versions.png")
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n✓ {path}  [{time.time()-t0:.0f}s]")


if __name__ == "__main__":
    main()

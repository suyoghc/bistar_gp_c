"""
BI* Narrative Figure v4 — polished, prior row fixed

Row 1: GP prior draws (from kernel), flat induced ω, scattered Sin+Linear
Row 2: GP posterior (n=10), partially concentrated ω, Sin+Linear tightening  
Row 3: GP posterior (n=50), sharp ω spike at 1.0, Sin+Linear nails truth
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D
from scipy.stats import gamma as gamma_dist, lognorm, gaussian_kde
from scipy.optimize import minimize as sp_minimize
import os
import warnings
warnings.filterwarnings("ignore")

# ── GP ──

def se_k(x1, x2, ls, os_):
    return os_ * np.exp(-0.5*(x1[:,None]-x2[None,:])**2/ls**2)
def lin_k(x1, x2, v):
    return v*(x1[:,None]*x2[None,:])
def gp_prior(x, ls, os_, lv, nv):
    n=len(x); return np.zeros(n), se_k(x,x,ls,os_)+lin_k(x,x,lv)+nv*np.eye(n)
def gp_post(xt, yt, xe, ls, os_, lv, nv):
    nt,ne=len(xt),len(xe)
    Ktt=se_k(xt,xt,ls,os_)+lin_k(xt,xt,lv)+(nv+1e-6)*np.eye(nt)
    Kte=se_k(xt,xe,ls,os_)+lin_k(xt,xe,lv)
    Kee=se_k(xe,xe,ls,os_)+lin_k(xe,xe,lv)
    L=np.linalg.cholesky(Ktt)
    a=np.linalg.solve(L.T,np.linalg.solve(L,yt))
    V=np.linalg.solve(L,Kte)
    mu=Kte.T@a; cov=Kee+nv*np.eye(ne)-V.T@V; cov=0.5*(cov+cov.T)
    em=np.linalg.eigvalsh(cov).min()
    if em<0: cov+=(abs(em)+1e-6)*np.eye(ne)
    return mu, cov
def gp_lml(xt,yt,ls,os_,lv,nv):
    n=len(xt); K=se_k(xt,xt,ls,os_)+lin_k(xt,xt,lv)+(nv+1e-6)*np.eye(n)
    try:
        L=np.linalg.cholesky(K); a=np.linalg.solve(L.T,np.linalg.solve(L,yt))
        return -0.5*yt@a-np.sum(np.log(np.diag(L)))-0.5*n*np.log(2*np.pi)
    except: return -np.inf

# ── Prior config ──
PR={"ls":("gamma",6.,0.85),"os":("gamma",6.,0.85),"lv":("gamma",6.,0.85),"nv":("gamma",1.75,1.)}

def spr(fam,p1,p2,n,rng):
    if fam=="gamma": return gamma_dist.rvs(a=p1,scale=1/p2,size=n,random_state=rng)
    return lognorm.rvs(s=p2,scale=np.exp(p1),size=n,random_state=rng)
def ppdf(x,fam,p1,p2):
    if fam=="gamma": return gamma_dist.pdf(x,a=p1,scale=1/p2)
    return lognorm.pdf(x,s=p2,scale=np.exp(p1))
def shyp(n,rng):
    return (np.clip(spr(*PR["ls"],n,rng),.1,50),
            np.clip(spr(*PR["os"],n,rng),.01,50),
            np.clip(spr(*PR["lv"],n,rng),.001,50),
            np.clip(spr(*PR["nv"],n,rng),1e-4,20))

def sinlin(x,A,w,p,b,c): return A*np.sin(w*x+p)+b*x+c

def find_map(xd,yd):
    def neg(lp):
        h=np.exp(lp); lml=gp_lml(xd,yd,*h)
        if not np.isfinite(lml): return 1e10
        lpr=sum(np.log(max(ppdf(v,*s),1e-30)) for v,s in
                zip(h,[PR["ls"],PR["os"],PR["lv"],PR["nv"]]))
        return -(lml+lpr)
    bv,bp=np.inf,None
    for l0 in[1,3,7]:
     for o0 in[.5,2,5]:
      for n0 in[.05,.3,1]:
       try:
        r=sp_minimize(neg,np.log([l0,o0,1,n0]),method='Nelder-Mead',options={'maxiter':3000})
        if r.fun<bv: bv,bp=r.fun,np.exp(r.x)
       except: pass
    return bp if bp is not None else np.array([5,5,1,.1])

# ── Profile induced prior ──

def profile_omega(xe, target, omega_range=(0.3,3.0), n_omega=250):
    omegas=np.linspace(*omega_range,n_omega)
    mse=np.zeros(n_omega)
    bps=[None]*n_omega
    for i,om in enumerate(omegas):
        best_m=np.inf
        for phi in np.linspace(-np.pi,np.pi,30):
            X=np.column_stack([np.sin(om*xe+phi),xe,np.ones_like(xe)])
            try:
                c,_,_,_=np.linalg.lstsq(X,target,rcond=None)
                m=np.mean((target-X@c)**2)
                if m<best_m: best_m=m; bps[i]=(c[0],om,phi,c[1],c[2])
            except: pass
        mse[i]=best_m
    return omegas, mse, bps

def mse_to_density(mse, tau_scale=3.0):
    """Convert profile MSE to density, with adaptive tau."""
    tau=max(np.min(mse)*tau_scale, 1e-8)
    lw=-mse/tau; lw-=lw.max()
    w=np.exp(lw)
    # Normalize as density
    dw=w/w.sum()
    wm=np.sum(dw*np.linspace(0,1,len(w)))  # placeholder
    return w, tau, dw

# ── GP prior induced: sample functions, average profile ──

def prior_induced_omega(xe, n_func=30, omega_range=(0.3,3.0), n_omega=250):
    """
    For the prior case: sample functions from GP prior, profile-fit
    each, average MSE profiles, convert to induced density.
    """
    rng=np.random.RandomState(42)
    ls_s,os_s,lv_s,nv_s = shyp(n_func, rng)

    omegas=np.linspace(*omega_range,n_omega)
    mse_total=np.zeros(n_omega)

    for j in range(n_func):
        mu,cov=gp_prior(xe,ls_s[j],os_s[j],lv_s[j],nv_s[j])
        try:
            L=np.linalg.cholesky(cov+1e-5*np.eye(len(xe)))
            f_draw=mu+L@rng.normal(size=len(xe))
        except:
            f_draw=mu+np.sqrt(np.maximum(np.diag(cov),0))*rng.normal(size=len(xe))

        _, mse_j, _ = profile_omega(xe, f_draw, omega_range, n_omega)
        mse_total += mse_j

    mse_avg = mse_total / n_func
    return omegas, mse_avg

# ══════════════════════════════════════════════════════════════════

def main():
    out="/home/claude/mechanism_plots"
    os.makedirs(out,exist_ok=True)

    xe=np.linspace(-10,10,80)
    rng=np.random.RandomState(42)
    xa=np.sort(rng.uniform(-10,10,50))
    ya=np.sin(xa)+0.25*xa+rng.normal(0,0.3,50)
    yt=np.sin(xe)+0.25*xe

    # ── Compute for each stage ──
    print("Stage 0: Prior...")
    mp0=np.array([5.88,5.88,5.88,0.75])
    gp_mu0,gp_cov0=gp_prior(xe,*mp0)
    om0,mse0=prior_induced_omega(xe,n_func=40)
    tau0=max(np.median(mse0)*0.5,1e-4)  # gentle: most ω roughly equal
    lw0=-mse0/tau0; lw0-=lw0.max(); w0=np.exp(lw0)
    d0=w0/(w0.sum()*(om0[1]-om0[0]))
    dw0=w0/w0.sum()
    wm0=np.sum(dw0*om0); ws0=np.sqrt(np.sum(dw0*(om0-wm0)**2))
    print(f"  ω={wm0:.2f}±{ws0:.2f}")

    print("Stage 1: n=10...")
    xd1,yd1=xa[:10],ya[:10]
    mp1=find_map(xd1,yd1)
    gp_mu1,gp_cov1=gp_post(xd1,yd1,xe,*mp1)
    om1,mse1,bps1=profile_omega(xe,gp_mu1)
    tau1=max(np.min(mse1)*3,1e-8)
    lw1=-mse1/tau1; lw1-=lw1.max(); w1=np.exp(lw1)
    d1=w1/(w1.sum()*(om1[1]-om1[0]))
    dw1=w1/w1.sum()
    wm1=np.sum(dw1*om1); ws1=np.sqrt(np.sum(dw1*(om1-wm1)**2))
    print(f"  MAP ℓ={mp1[0]:.2f}  ω={wm1:.2f}±{ws1:.2f}")

    print("Stage 2: n=50...")
    mp2=find_map(xa,ya)
    gp_mu2,gp_cov2=gp_post(xa,ya,xe,*mp2)
    om2,mse2,bps2=profile_omega(xe,gp_mu2)
    tau2=max(np.min(mse2)*3,1e-8)
    lw2=-mse2/tau2; lw2-=lw2.max(); w2=np.exp(lw2)
    d2=w2/(w2.sum()*(om2[1]-om2[0]))
    dw2=w2/w2.sum()
    wm2=np.sum(dw2*om2); ws2=np.sqrt(np.sum(dw2*(om2-wm2)**2))
    print(f"  MAP ℓ={mp2[0]:.2f}  ω={wm2:.2f}±{ws2:.2f}")

    # MLL-weighted hyper samples for col 0
    rng_h=np.random.RandomState(42)
    ls_a,os_a,lv_a,nv_a=shyp(200,rng_h)
    def mll_weights(xd,yd):
        lmls=np.array([gp_lml(xd,yd,ls_a[i],os_a[i],lv_a[i],nv_a[i]) for i in range(200)])
        v=np.isfinite(lmls)
        lw=lmls.copy(); lw[~v]=-np.inf; lw-=lw[v].max()
        mw=np.exp(lw); mw/=mw.sum()
        return mw
    mw1=mll_weights(xd1,yd1)
    mw2=mll_weights(xa,ya)

    # ══════════════════════════════════════════════════════════
    # PLOT
    # ══════════════════════════════════════════════════════════
    GP_C="#2980b9"; SL_C="#27ae60"; PR_C="#8e44ad"; TR_C="#2c3e50"

    fig=plt.figure(figsize=(22,15))
    gs=GridSpec(3,4,figure=fig,hspace=0.38,wspace=0.27,
                left=0.06,right=0.97,top=0.91,bottom=0.06)
    rl=["Prior\n(no data)","Partial data\n(n = 10)","Full data\n(n = 50)"]

    data_stages=[
        (None,None,mp0,gp_mu0,gp_cov0,om0,d0,dw0,wm0,ws0,None,None),
        (xd1,yd1,mp1,gp_mu1,gp_cov1,om1,d1,dw1,wm1,ws1,bps1,mw1),
        (xa,ya,mp2,gp_mu2,gp_cov2,om2,d2,dw2,wm2,ws2,bps2,mw2),
    ]

    for ri,(xd,yd,mp,gmu,gcov,oms,dens,dws,wm,ws,bps,mw) in enumerate(data_stages):
        gvar=np.diag(gcov)
        use_data = xd is not None

        # ──── COL 0: Lengthscale ────
        ax=fig.add_subplot(gs[ri,0])
        xls=np.linspace(0.01,20,500)
        ypr=ppdf(xls,*PR["ls"])

        if ri==0:
            ax.fill_between(xls,ypr,alpha=0.35,color=PR_C)
            ax.plot(xls,ypr,color=PR_C,lw=2.5)
            ax.set_title("Hyperparameter\nprior  p(ℓ)",fontsize=12,fontweight='bold')
        else:
            ax.plot(xls,ypr,color=PR_C,lw=1.2,ls='--',alpha=0.5)
            ax.fill_between(xls,ypr,alpha=0.06,color=PR_C)
            rr=np.random.RandomState(77)
            idx=rr.choice(200,size=8000,p=mw)
            lsp=ls_a[idx]; lsp=lsp[(lsp>.1)&(lsp<20)]
            if len(lsp)>50:
                kde=gaussian_kde(lsp,bw_method=0.25)
                yp=kde(xls)
                ax.plot(xls,yp,color=GP_C,lw=2.5)
                ax.fill_between(xls,yp,alpha=0.25,color=GP_C)
            ax.axvline(mp[0],color=GP_C,lw=1.8,ls=':',alpha=0.7,
                       label=f'MAP ℓ={mp[0]:.1f}')
            ax.legend(fontsize=8)
            ax.set_title(f"p(ℓ | D$_{{{len(xd)}}}$)",fontsize=12,fontweight='bold')

        ax.set_xlabel("Lengthscale ℓ",fontsize=10); ax.set_ylabel("Density",fontsize=10)
        ax.set_xlim(0,18); ax.set_ylim(bottom=0); ax.grid(True,alpha=0.15)
        ax.text(-0.28,0.5,rl[ri],transform=ax.transAxes,fontsize=11,fontweight='bold',
                ha='center',va='center',rotation=90,
                bbox=dict(boxstyle='round,pad=0.3',facecolor='#ecf0f1',edgecolor='#bdc3c7'))

        # ──── COL 1: GP predictive ────
        ax=fig.add_subplot(gs[ri,1])
        rd=np.random.RandomState(42)

        if use_data:
            rh=np.random.RandomState(88)
            hidx=rh.choice(200,size=18,p=mw)
            for hi in hidx:
                try:
                    mu,cv=gp_post(xd,yd,xe,ls_a[hi],os_a[hi],lv_a[hi],nv_a[hi])
                    L=np.linalg.cholesky(cv+1e-5*np.eye(len(xe)))
                    ax.plot(xe,mu+L@rd.normal(size=len(xe)),color=GP_C,alpha=0.18,lw=0.8)
                except: pass
        else:
            # Prior draws — sample hyperparams from prior
            rh=np.random.RandomState(88)
            ls_pr,os_pr,lv_pr,nv_pr=shyp(18,rh)
            for i in range(18):
                try:
                    mu,cv=gp_prior(xe,ls_pr[i],os_pr[i],lv_pr[i],nv_pr[i])
                    L=np.linalg.cholesky(cv+1e-5*np.eye(len(xe)))
                    ax.plot(xe,mu+L@rd.normal(size=len(xe)),color=GP_C,alpha=0.18,lw=0.8)
                except: pass

        # MAP mean + band (skip band for prior — it fills entire range)
        if use_data:
            std=np.sqrt(gvar)
            ax.fill_between(xe,gmu-2*std,gmu+2*std,color=GP_C,alpha=0.08)
        ax.plot(xe,gmu,color=GP_C,lw=2.5 if use_data else 1.5,
                alpha=0.9 if use_data else 0.3)
        ax.plot(xe,yt,color=TR_C,lw=2,ls='--')
        if use_data: ax.scatter(xd,yd,c=TR_C,s=20,zorder=5,edgecolors='white',lw=0.5)
        if ri==0: ax.set_title("GP predictive",fontsize=12,fontweight='bold',color=GP_C)
        ylim = (-8,8) if use_data else (-15,15)
        ax.set_ylim(*ylim); ax.set_xlabel("x",fontsize=10); ax.grid(True,alpha=0.15)

        # ──── COL 2: Induced p(ω) ────
        ax=fig.add_subplot(gs[ri,2])

        ax.fill_between(oms,dens,alpha=0.35,color=SL_C)
        ax.plot(oms,dens,color=SL_C,lw=2.5)
        ax.axvline(1.0,color=TR_C,lw=2.5,ls='--',label='True ω=1' if ri==0 else None)
        ax.axvline(wm,color=SL_C,lw=2,ls=':',alpha=0.8)

        if ri==0:
            ax.set_title("Induced p(ω | ψ)",fontsize=12,fontweight='bold',color=SL_C)
            ax.legend(fontsize=9)

        ax.text(0.97,0.95,f"E[ω] = {wm:.2f}\nσ = {ws:.2f}",
                transform=ax.transAxes,fontsize=10,va='top',ha='right',
                bbox=dict(boxstyle='round',facecolor='white',alpha=0.85,edgecolor=SL_C))
        ax.set_xlabel("ω (frequency)",fontsize=10); ax.set_ylabel("Density",fontsize=10)
        ax.set_xlim(0.3,3.0); ax.grid(True,alpha=0.15)

        # ──── COL 3: Sin+Linear predictive ────
        ax=fig.add_subplot(gs[ri,3])

        if bps is not None:
            # Draw curves weighted by profile
            rng_d=np.random.RandomState(99)
            oidx=rng_d.choice(len(oms),size=45,p=dws)
            for oi in oidx:
                if bps[oi] is not None:
                    ax.plot(xe,sinlin(xe,*bps[oi]),color=SL_C,alpha=0.12,lw=0.9)
            # Best fit
            bi=np.argmax(dws)
            if bps[bi] is not None:
                ax.plot(xe,sinlin(xe,*bps[bi]),color=SL_C,lw=2.5,alpha=0.9)
        else:
            # Prior: random Sin+Linear draws (no concentration)
            rng_d=np.random.RandomState(99)
            for _ in range(45):
                A=rng_d.uniform(.2,2.5)
                om=rng_d.uniform(.3,3.)
                ph=rng_d.uniform(-np.pi,np.pi)
                b=rng_d.uniform(-.8,.8)
                c=rng_d.uniform(-2,2)
                ax.plot(xe,sinlin(xe,A,om,ph,b,c),color=SL_C,alpha=0.1,lw=0.8)

        ax.plot(xe,yt,color=TR_C,lw=2,ls='--')
        if use_data: ax.scatter(xd,yd,c=TR_C,s=20,zorder=5,edgecolors='white',lw=0.5)
        if ri==0: ax.set_title("Sin+Linear\npredictive",fontsize=12,fontweight='bold',color=SL_C)
        ylim = (-8,8) if use_data else (-15,15)
        ax.set_ylim(*ylim); ax.set_xlabel("x",fontsize=10); ax.grid(True,alpha=0.15)

    # ── Arrows ──
    for ci in range(3):
        al=fig.add_subplot(gs[0,ci]).get_position()
        ar=fig.add_subplot(gs[0,ci+1]).get_position()
        fig.text((al.x1+ar.x0)/2,0.935,"→",fontsize=22,ha='center',va='center',
                 fontweight='bold',color='#7f8c8d')

    fig.suptitle("BI* Transfer Pipeline: GP Hyperparameter Beliefs → "
                 "Induced Model Parameter Priors → Predictive",
                 fontsize=15,fontweight='bold',y=0.97)

    legend_els=[
        Line2D([0],[0],color=GP_C,lw=2.5,label='GP (nonparametric scaffold)'),
        Line2D([0],[0],color=SL_C,lw=2.5,label='Sin+Linear (parametric candidate)'),
        Line2D([0],[0],color=TR_C,lw=2,ls='--',label='True: sin(x) + 0.25x'),
        Line2D([0],[0],marker='o',color=TR_C,lw=0,ms=6,label='Observed data'),
    ]
    fig.legend(handles=legend_els,loc='lower center',ncol=4,fontsize=11,
               frameon=True,fancybox=True,bbox_to_anchor=(0.5,0.0))

    fig.savefig(os.path.join(out,"narrative_figure.png"),dpi=180,bbox_inches='tight')
    plt.close(fig)
    print("✓ narrative_figure.png saved")

if __name__=="__main__":
    main()

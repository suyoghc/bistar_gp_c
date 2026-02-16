"""HMC diagnostic: sub0 (correct) vs sub3 (wrong under MAP)."""
import numpy as np
import torch
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from candidates import build_core_candidates
from kernels import (
    PRACTICE_CONFIGS, build_kernel, build_likelihood,
    get_kernel_builder, get_likelihood_builder,
)
from bistar_gp.model import build_model
from bistar_gp.fit import fit_map, fit_hmc
from bistar_gp.bms_star import (
    extract_gp_predictives, compute_G_matrix, GPPosteriorSample,
)
from run import generate_demo_data, normalize

curves = generate_demo_data(50)

for i in [0, 3]:
    print(f"\n{'='*60}")
    print(f"Subject {i} ({curves[i].n_trials}t)")
    print(f"{'='*60}")

    curve = curves[i]
    nc = normalize(curve)

    x_train = torch.tensor(nc.x).double()
    y_train = torch.tensor(nc.y).double()
    x_eval_norm = torch.linspace(0, 1, 50).double()
    x_eval_raw = x_eval_norm.numpy() * (nc.x_max - nc.x_min) + nc.x_min

    # Candidates on raw
    candidates = build_core_candidates()
    crs = []
    for c in candidates:
        c.fit(nc.x_raw, nc.y_raw)
        pred = c.predict(x_eval_raw)
        crs.append(pred)
        print(f"  {c.name}: a={pred.parameters['a']:.1f} "
              f"b={pred.parameters['b']:.4f} c={pred.parameters['c']:.1f}")

    # GP with HMC (agnostic)
    cfg_name = "agnostic"
    cfg = PRACTICE_CONFIGS[cfg_name]
    kernels, names = build_kernel(cfg)
    lik = build_likelihood(cfg)
    model, lik = build_model(x_train, y_train, kernels, names, lik)

    # MAP first (needed for HMC init)
    fit_map(model, lik, x_train, y_train, n_iter=300, lr=0.05, verbose=False)
    print(f"  MAP lengthscale={model.kernel_components[0].base_kernel.lengthscale.item():.4f}")

    # HMC
    mcmc_samples = fit_hmc(
        model, lik, x_train, y_train,
        n_samples=200, n_warmup=100, verbose=True,
    )

    # Print lengthscale distribution from HMC
    ls_key = [k for k in mcmc_samples.keys() if 'lengthscale' in k][0]
    #ls_vals = mcmc_samples[ls_key].numpy()
    ls_vals = mcmc_samples[ls_key] if isinstance(mcmc_samples[ls_key], np.ndarray) else mcmc_samples[ls_key].numpy()
    print(f"  HMC lengthscale: mean={ls_vals.mean():.4f} "
          f"std={ls_vals.std():.4f} "
          f"range=[{ls_vals.min():.4f}, {ls_vals.max():.4f}]")

    gp_samples = extract_gp_predictives(
        model, lik, x_train, y_train, x_eval_norm, mcmc_samples,
        get_kernel_builder(cfg_name), get_likelihood_builder(cfg_name),
        n_posterior_samples=100,
    )

    # Denormalize
    gp_raw = [
        GPPosteriorSample(
            mean=s.mean * nc.y_std + nc.y_mean,
            cov=s.cov * (nc.y_std ** 2),
            hyperparameters=s.hyperparameters,
        )
        for s in gp_samples
    ]

    # G diagnostics
    for metric in ["pw_mse", "pw_hellinger", "pw_nll"]:
        G = compute_G_matrix(gp_raw, crs, metric)
        winners = np.argmin(G, axis=1)
        print(f"\n  {metric}:")
        for j, name in enumerate([cr.name for cr in crs]):
            col = G[:, j]
            delta = (G - G.min(axis=1, keepdims=True))[:, j]
            print(f"    {name}: mean_G={col.mean():.4f} "
                  f"wins={np.sum(winners == j)}/{len(winners)} "
                  f"mean_delta={delta.mean():.4f}")

    # Plot
    fig, ax = plt.subplots(figsize=(10, 6))

    for s in gp_raw[::10]:
        ax.plot(x_eval_raw, s.mean, color='gray', alpha=0.2, lw=0.5)

    gp_mean = np.mean([s.mean for s in gp_raw], axis=0)
    ax.plot(x_eval_raw, gp_mean, 'k-', lw=2, label='GP mean (HMC)')

    colors = ['#e74c3c', '#3498db']
    for cr, col in zip(crs, colors):
        ax.plot(x_eval_raw, cr.mean, lw=2, label=cr.name, color=col)

    ax.scatter(nc.x_raw, nc.y_raw, c='black', marker='x', s=30, zorder=5, label='data')
    ax.set_title(f'sub{i} HMC (agnostic) — {curve.n_trials}t')
    ax.legend()
    ax.set_xlabel('Trial')
    ax.set_ylabel('RT (ms)')
    fig.tight_layout()
    fig.savefig(f'diag_sub{i}_hmc.png', dpi=150, bbox_inches='tight')
    print(f"\n  Saved diag_sub{i}_hmc.png")

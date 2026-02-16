"""Diagnose G matrix for specific power-generated subjects."""
import numpy as np
import torch
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from candidates import build_core_candidates
from kernels import PRACTICE_CONFIGS, build_kernel, build_likelihood
from bistar_gp.model import build_model
from bistar_gp.fit import fit_map
from bistar_gp.bms_star import compute_G_matrix, GPPosteriorSample
from run import generate_demo_data, normalize, extract_map_predictives

curves = generate_demo_data(50)

for i in [3, 4, 8, 14]:
    curve = curves[i]
    nc = normalize(curve)

    x_train = torch.tensor(nc.x).double()
    y_train = torch.tensor(nc.y).double()
    x_eval_norm = torch.linspace(0, 1, 50).double()
    x_eval_raw = x_eval_norm.numpy() * (nc.x_max - nc.x_min) + nc.x_min

    candidates = build_core_candidates()
    crs = []
    for c in candidates:
        c.fit(nc.x_raw, nc.y_raw)
        crs.append(c.predict(x_eval_raw))

    cfg = PRACTICE_CONFIGS["agnostic"]
    kernels, names = build_kernel(cfg)
    lik = build_likelihood(cfg)
    model, lik = build_model(x_train, y_train, kernels, names, lik)
    fit_map(model, lik, x_train, y_train, n_iter=300, lr=0.05, verbose=False)

    gp_samples = extract_map_predictives(
        model, lik, x_train, y_train, x_eval_norm, n_samples=100
    )
    gp_raw = [
        GPPosteriorSample(
            mean=s.mean * nc.y_std + nc.y_mean,
            cov=s.cov * (nc.y_std ** 2),
            hyperparameters=s.hyperparameters,
        )
        for s in gp_samples
    ]

    G = compute_G_matrix(gp_raw, crs, "pw_mse")
    winners = np.argmin(G, axis=1)
    print(f"\nsub{i} (n={curve.n_trials}t):")
    for j, name in enumerate([cr.name for cr in crs]):
        col = G[:, j]
        delta = (G - G.min(axis=1, keepdims=True))[:, j]
        print(f"  {name}: mean_G={col.mean():.2f} wins={np.sum(winners == j)}/100 mean_delta={delta.mean():.4f}")

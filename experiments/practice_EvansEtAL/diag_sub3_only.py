"""Visual diagnostic: sub3 (b=0.16, power-generated, called Exponential)."""
import numpy as np
import torch
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from candidates import build_core_candidates
from kernels import PRACTICE_CONFIGS, build_kernel, build_likelihood
from bistar_gp.model import build_model
from bistar_gp.fit import fit_map
from bistar_gp.bms_star import compute_G_matrix, GPPosteriorSample
from run import generate_demo_data, normalize, extract_map_predictives

curves = generate_demo_data(50)
curve = curves[0]
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
    crs.append(c.predict(x_eval_raw))
    print(f"{c.name}: a={c.predict(x_eval_raw).parameters['a']:.1f} "
          f"b={c.predict(x_eval_raw).parameters['b']:.4f} "
          f"c={c.predict(x_eval_raw).parameters['c']:.1f}")

# GP (agnostic)
cfg = PRACTICE_CONFIGS["agnostic"]
kernels, names = build_kernel(cfg)
lik = build_likelihood(cfg)
model, lik = build_model(x_train, y_train, kernels, names, lik)
fit_map(model, lik, x_train, y_train, n_iter=300, lr=0.05, verbose=False)

print(f"GP lengthscale={model.kernel_components[0].base_kernel.lengthscale.item():.4f}")
print(f"GP outputscale={model.kernel_components[0].outputscale.item():.4f}")
print(f"GP noise={lik.noise.item():.4f}")

gp_samples = extract_map_predictives(
    model, lik, x_train, y_train, x_eval_norm, n_samples=100
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

# Plot
fig, ax = plt.subplots(figsize=(10, 6))

# GP draws (thin)
for s in gp_raw[::10]:
    ax.plot(x_eval_raw, s.mean, color='gray', alpha=0.3, lw=0.5)

# GP mean of means
gp_mean = np.mean([s.mean for s in gp_raw], axis=0)
ax.plot(x_eval_raw, gp_mean, 'k-', lw=2, label='GP mean')

# Candidates
colors = ['#e74c3c', '#3498db']
for cr, col in zip(crs, colors):
    ax.plot(x_eval_raw, cr.mean, lw=2, label=cr.name, color=col)

# Raw data
ax.scatter(nc.x_raw, nc.y_raw, c='black', marker='x', s=30, zorder=5, label='data')

ax.set_title(f'sub3: b=0.16, {curve.n_trials}t — power-generated, BI* says Exponential')
ax.legend()
ax.set_xlabel('Trial')
ax.set_ylabel('RT (ms)')
fig.tight_layout()
fig.savefig('diag_sub3_visual.png', dpi=150, bbox_inches='tight')
print("Saved diag_sub3_visual.png")

# Also print x/y ranges for sanity
print(f"x_eval_raw: [{x_eval_raw.min():.1f}, {x_eval_raw.max():.1f}]")
print(f"y_raw: [{nc.y_raw.min():.1f}, {nc.y_raw.max():.1f}]")
print(f"GP mean range: [{gp_mean.min():.1f}, {gp_mean.max():.1f}]")
print(f"Power pred range: [{crs[0].mean.min():.1f}, {crs[0].mean.max():.1f}]")
print(f"Exp pred range: [{crs[1].mean.min():.1f}, {crs[1].mean.max():.1f}]")

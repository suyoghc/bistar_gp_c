import json, glob

for f in sorted(glob.glob("results/synth_*.json")):
    d = json.load(open(f))
    pw_mse = d.get("bistar_winners", {}).get("practitioner", {}).get("pw_mse", {})
    taus = sorted(pw_mse.keys(), key=float)
    mid = taus[len(taus)//2] if taus else None
    winner = pw_mse.get(mid, "?") if mid else "?"
    print(f"{d['dataset_id']:20s} sub{d['subject_id']:3d}  BIC={d['bic_winner']:12s}  BI*={winner}")

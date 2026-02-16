import json, glob

for f in sorted(glob.glob("results/synth_power_sub0*.json"))[:3]:
    d = json.load(open(f))
    print(f"\n=== {d['dataset_id']} sub{d['subject_id']} ({d['n_trials']}t) ===")
    print("BIC log-ML:")
    for m, v in sorted(d['bic_log_ml'].items(), key=lambda x: -x[1]):
        print(f"  {m:15s} {v:.2f}")
    print("Fitted params:")
    for m, p in d['fitted_params'].items():
        print(f"  {m:15s} {p}")

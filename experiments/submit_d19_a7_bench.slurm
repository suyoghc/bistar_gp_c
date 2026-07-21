#!/bin/bash
#SBATCH --job-name=d19-a7-bench
#SBATCH --account=suyoghc
#SBATCH --partition=cpu
#SBATCH --constraint=cascade
#SBATCH --exclude=della-h12n[1-13],della-h12n[17-18],della-h17n1,della-i13n25
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --chdir=/scratch/gpfs/SUYOGHC/bistar_gp_a7_exec
#SBATCH --output=runs/d19_a7_timing/slurm-%j.out
#SBATCH --error=runs/d19_a7_timing/slurm-%j.err
# D56 (docs/d19-a7-execution-protocol.md): A7 timing matrix under ballot AC1-AC11.
# 16G and 02:00:00 are operational CEILINGS, not predictions. No mail (AC11).
# Submission: sbatch --export=NONE experiments/submit_d19_a7_bench.slurm <execution-sha>
set -euo pipefail

fail() { echo "PREFLIGHT-FAIL($1): $2" >&2; exit "$1"; }

EXEC_ROOT=/scratch/gpfs/SUYOGHC/bistar_gp_a7_exec
[ "$PWD" = "$EXEC_ROOT" ] || fail 64 "PWD $PWD != $EXEC_ROOT"

EXEC_SHA="${1:-}"
[[ "$EXEC_SHA" =~ ^[0-9a-f]{40}$ ]] || fail 65 "missing or malformed execution SHA argument"

command -v module >/dev/null 2>&1 || fail 66 "module command unavailable"
module purge
module load anaconda3/2024.6 || fail 67 "module load anaconda3/2024.6 failed"
eval "$(conda shell.bash hook)" || fail 68 "conda shell hook failed"
conda activate bistar_gp || fail 69 "conda activate bistar_gp failed"

[ "$(git rev-parse HEAD)" = "$EXEC_SHA" ] || fail 70 "HEAD != execution SHA"
git diff --quiet || fail 71 "unstaged tracked modifications"
git diff --cached --quiet || fail 72 "staged (index) modifications"
mapfile -t UT < <(git status --porcelain)
{ [ "${#UT[@]}" -eq 1 ] && [ "${UT[0]}" = "?? runs/d19_a7_timing/" ]; } \
  || fail 73 "unexpected untracked path(s): ${UT[*]:-none}"
mapfile -t EV < <(ls -A runs/d19_a7_timing)
[ "${#EV[@]}" -eq 2 ] || fail 74 "evidence dir not pristine: ${EV[*]:-empty}"
for f in "${EV[@]}"; do
  case "$f" in
    "slurm-${SLURM_JOB_ID}.out"|"slurm-${SLURM_JOB_ID}.err") ;;
    *) fail 75 "unexpected evidence entry: $f" ;;
  esac
done

EXPECT_ENV=/home/sc8918/.conda/envs/bistar_gp
[ "${CONDA_PREFIX:-}" = "$EXPECT_ENV" ] || fail 80 "conda prefix ${CONDA_PREFIX:-unset} != $EXPECT_ENV"
[ "$(command -v python)" = "$EXPECT_ENV/bin/python" ] || fail 81 "python resolves to $(command -v python)"
PYTHONPATH="$EXEC_ROOT" python - "$EXEC_ROOT" <<'PYEOF' || fail 82 "environment drift or bistar_gp containment failure"
import pathlib, platform, sys
EXPECTED_EXE = "/home/sc8918/.conda/envs/bistar_gp/bin/python"
EXPECTED = {"python": "3.11.14", "torch": "2.10.0+cu128",
            "gpytorch": "1.15.1", "pyro": "1.9.1", "numpy": "2.4.2"}
if sys.executable != EXPECTED_EXE:
    raise SystemExit(f"sys.executable {sys.executable} != {EXPECTED_EXE}")
if platform.python_version() != EXPECTED["python"]:
    raise SystemExit(f"python {platform.python_version()} != {EXPECTED['python']}")
import numpy, torch, gpytorch, pyro
for name, mod in (("torch", torch), ("gpytorch", gpytorch),
                  ("pyro", pyro), ("numpy", numpy)):
    if str(mod.__version__) != EXPECTED[name]:
        raise SystemExit(f"{name} {mod.__version__} != {EXPECTED[name]}")
root = pathlib.Path(sys.argv[1]).resolve(strict=True)
import bistar_gp
mod_path = pathlib.Path(bistar_gp.__file__).resolve(strict=True)
if root not in mod_path.parents:
    raise SystemExit(f"bistar_gp at {mod_path}, not inside {root}")
print("ENV-OK", sys.executable, platform.python_version(),
      torch.__version__, gpytorch.__version__, pyro.__version__, numpy.__version__)
PYEOF

NODE_FEATURES=$(scontrol show node "$(hostname -s)" | sed -n 's/^ *ActiveFeatures=//p')
[ "$NODE_FEATURES" = "intel,cascade,rh9" ] || fail 83 "node features '$NODE_FEATURES' != 'intel,cascade,rh9'"

date -u
hostname
echo "job=$SLURM_JOB_ID cpus=$SLURM_CPUS_PER_TASK nodes=$SLURM_JOB_NODELIST sha=$EXEC_SHA"
module list 2>&1
lscpu
scontrol show job "$SLURM_JOB_ID" | grep -E "TRES|NodeList|TimeLimit|Partition|Account|Features" || true

# Matrix (AC2, AC3, AC5): (sub,1) first as the smoke cell; strictly serial;
# STOP on any failure; no retry, no continuation. The script sets none of the
# four thread variables -- the vehicle owns its pre-import contract.
for scale in sub full; do
  for t in 1 2 3 4; do
    target="runs/d19_a7_timing/bench_${scale}_threads_${t}.json"
    [ ! -e "$target" ] || fail 77 "target pre-exists: $target"
    echo "CELL $scale $t start $(date -u +%FT%TZ)"
    rc=0
    PYTHONPATH="$EXEC_ROOT" python experiments/d19_bench.py \
        --scale "$scale" --threads "$t" --budget-s 600 || rc=$?
    echo "CELL $scale $t exit $rc end $(date -u +%FT%TZ)"
    [ "$rc" -eq 0 ] || { echo "MATRIX-STOP: cell ($scale,$t) rc=$rc; no retry, no continuation" >&2; exit "$rc"; }
    [ -s "$target" ] || fail 78 "cell exited 0 but artifact missing or empty: $target"
  done
done
sha256sum runs/d19_a7_timing/bench_*.json
echo "MATRIX-COMPLETE $(date -u +%FT%TZ)"

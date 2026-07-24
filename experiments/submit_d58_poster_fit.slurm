#!/bin/bash
#SBATCH --job-name=d58-poster-fit
#SBATCH --account=suyoghc
#SBATCH --partition=cpu
#SBATCH --constraint=cascade
#SBATCH --exclude=della-h12n[1-13],della-h12n[17-18],della-h17n1,della-i13n25
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=3
#SBATCH --mem=8G
#SBATCH --time=02:00:00
#SBATCH --chdir=/scratch/gpfs/SUYOGHC/bistar_gp_d58
#SBATCH --output=runs/poster_d58/slurm-%j.out
#SBATCH --error=runs/poster_d58/slurm-%j.err
# D58 (docs/d58-poster-execution-protocol.md): ONE poster-grade Mauna fit,
# poster-only and non-paper-grade, under the prereg v1.23 section 6 global
# thread pin (cpus-per-task=3 here; the driver owns the four-variable
# pre-import contract and the torch intra-op pin, mirroring the committed
# D55/A7 division of responsibility). 8G and 02:00:00 are operational
# CEILINGS, not predictions. No mail. One submission, no retry.
# Submission: sbatch --export=NONE experiments/submit_d58_poster_fit.slurm <execution-sha>
set -euo pipefail

# D56b (D56 Update 6, job 11485635): the anaconda3/2024.6 modulefile reads
# ${PS1} unguarded inside the environment-imported _module_raw wrapper, fatal
# under nounset when the batch environment leaves PS1 unset. Define and export
# it (empty when unset) before any module operation; nounset stays enabled.
export PS1="${PS1-}"

fail() { echo "PREFLIGHT-FAIL($1): $2" >&2; exit "$1"; }

EXEC_ROOT=/scratch/gpfs/SUYOGHC/bistar_gp_d58
[ "$PWD" = "$EXEC_ROOT" ] || fail 64 "PWD $PWD != $EXEC_ROOT"

EXEC_SHA="${1:-}"
[[ "$EXEC_SHA" =~ ^[0-9a-f]{40}$ ]] || fail 65 "missing or malformed execution SHA argument"

command -v module >/dev/null 2>&1 || fail 66 "module command unavailable"
module purge
module load anaconda3/2024.6 || fail 67 "module load anaconda3/2024.6 failed"
HOOK_SCRIPT=$(conda shell.bash hook) || fail 68 "conda shell hook failed"
eval "$HOOK_SCRIPT" || fail 68 "conda shell hook eval failed"
conda activate bistar_gp || fail 69 "conda activate bistar_gp failed"

[ "$(git rev-parse HEAD)" = "$EXEC_SHA" ] || fail 70 "HEAD != execution SHA"
git diff --quiet || fail 71 "unstaged tracked modifications"
git diff --cached --quiet || fail 72 "staged (index) modifications"
UT_RAW=$(git status --porcelain --untracked-files=normal) || fail 73 "git status failed"
mapfile -t UT <<< "$UT_RAW"
{ [ "${#UT[@]}" -eq 1 ] && [ "${UT[0]}" = "?? runs/poster_d58/" ]; } \
  || fail 73 "unexpected untracked path(s): ${UT[*]:-none}"
EV_RAW=$(ls -A runs/poster_d58) || fail 74 "output directory unreadable"
mapfile -t EV <<< "$EV_RAW"
# An empty capture yields one empty element; the exact equality checks fail closed.
[ "${#EV[@]}" -eq 2 ] || fail 74 "output dir not pristine: ${EV[*]:-empty}"
for f in "${EV[@]}"; do
  case "$f" in
    "slurm-${SLURM_JOB_ID}.out"|"slurm-${SLURM_JOB_ID}.err") ;;
    *) fail 75 "unexpected output entry: $f" ;;
  esac
done
for name in sitecustomize.py sitecustomize.pyc usercustomize.py usercustomize.pyc; do
  [ ! -e "$EXEC_ROOT/$name" ] || fail 76 "import-hijack file present: $name"
done

EXPECT_ENV=/home/sc8918/.conda/envs/bistar_gp
[ "${CONDA_PREFIX:-}" = "$EXPECT_ENV" ] || fail 80 "conda prefix ${CONDA_PREFIX:-unset} != $EXPECT_ENV"
[ "$(command -v python)" = "$EXPECT_ENV/bin/python" ] || fail 81 "python resolves to $(command -v python)"
PYTHONPATH="$EXEC_ROOT" python -B - "$EXEC_ROOT" <<'PYEOF' || fail 82 "environment drift or bistar_gp containment failure"
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

# ONE fit (P1a: seed 0, 200+200, td7, full N=461, 500-point training-span
# grid). The driver refuses a pre-existing target (no-clobber) and writes the
# six-artifact census in recovery order. STOP on any failure; no retry.
FIT_DIR=runs/poster_d58/fit_full461_seed0
[ ! -e "$FIT_DIR" ] || fail 77 "target pre-exists: $FIT_DIR"
echo "FIT start $(date -u +%FT%TZ)"
rc=0
PYTHONPATH="$EXEC_ROOT" python -B experiments/poster_d58_mauna.py \
    --mode fit --output-dir "$FIT_DIR" \
    --seed 0 --n-warmup 200 --n-samples 200 --max-tree-depth 7 --n-grid 500 || rc=$?
echo "FIT exit $rc $(date -u +%FT%TZ)"
[ "$rc" -eq 0 ] || { echo "FIT-STOP: rc=$rc; no retry, no continuation" >&2; exit "$rc"; }
for f in fit_config.json samples.npz diagnostics.json decomposition.npz provenance.json PROVENANCE.sha256; do
  [ -s "$FIT_DIR/$f" ] || fail 78 "fit exited 0 but artifact missing or empty: $f"
done
sha256sum "$FIT_DIR"/*
echo "FIT-COMPLETE $(date -u +%FT%TZ)"

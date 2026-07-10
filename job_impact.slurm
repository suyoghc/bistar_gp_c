#!/bin/bash
#SBATCH --job-name=bistar-impact
#SBATCH --output=slurm-impact-%j.out
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --mail-type=begin,end,fail
#SBATCH --mail-user=sc8918@princeton.edu
#
# Old-vs-new correctness impact assessment (Della). Runs experiments/impact_assessment.py
# in the current (post-fix) tree and in a worktree at the pre-fix commit, then diffs.
#
# One-time before first run (compute nodes have no internet — pre-cache the CO2 data
# on the login node so load_mauna_loa reads the sklearn cache):
#   python -c "from sklearn.datasets import fetch_openml; fetch_openml(data_id=41187, as_frame=True)"

set -euo pipefail
module purge
module load anaconda3/2024.6
conda activate bistar

REPO="/scratch/gpfs/$USER/bistar_gp_c"    # adjust to your clone path
OLD_SHA="9016a55"                          # pre-fix commit (parent of PR #1)
SUB=150 ; NHMC=200 ; NWARM=200             # scale up for the paper run

cd "$REPO"
export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK" MKL_NUM_THREADS="$SLURM_CPUS_PER_TASK"

echo "== NEW tree ($(git rev-parse --short HEAD)) =="
python experiments/impact_assessment.py --mauna --sub "$SUB" --n-hmc "$NHMC" --n-warmup "$NWARM" --out new.json

echo "== OLD tree ($OLD_SHA) via worktree =="
git worktree add -f ../bistar_old "$OLD_SHA"
cp experiments/impact_assessment.py ../bistar_old/experiments/    # old tree predates the driver
( cd ../bistar_old && python experiments/impact_assessment.py --mauna --sub "$SUB" --n-hmc "$NHMC" --n-warmup "$NWARM" --out "$REPO/old.json" )
git worktree remove -f ../bistar_old

echo "== DIFF =="
python experiments/impact_assessment.py --compare old.json new.json | tee impact_report.txt

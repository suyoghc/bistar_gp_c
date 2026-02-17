#!/bin/bash
#SBATCH --job-name=mauna-debias
#SBATCH --output=logs/mauna_debias_%j.out
#SBATCH --error=logs/mauna_debias_%j.err
#SBATCH --time=6:00:00
#SBATCH --mem=128G
#SBATCH --cpus-per-task=4
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=sc8918@princeton.edu

module purge
module load anaconda3/2024.6
eval "$(conda shell.bash hook)"
conda activate bistar_gp

cd /scratch/gpfs/SUYOGHC/bistar_gp_c/experiments

# If BMS* already ran and cached HMC samples, reuse them:
if [ -f results_bms_mauna_loa/hmc_samples.pt ]; then
    echo "Reusing cached HMC samples from BMS* run"
    python bistar_debias_mauna_loa.py --use-cache results_bms_mauna_loa/hmc_samples.pt
else
    echo "Running fresh HMC"
    python bistar_debias_mauna_loa.py --n-hmc 100 --n-warmup 100
fi

echo "BI* debiasing complete"

#!/bin/bash
#SBATCH --job-name=bistar-hier
#SBATCH --output=logs/hier_%j.out
#SBATCH --error=logs/hier_%j.err
#SBATCH --time=24:00:00
#SBATCH --mem=16G
#SBATCH --cpus-per-task=4
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=sc8918@princeton.edu

module purge
module load anaconda3/2024.6
eval "$(conda shell.bash hook)"
conda activate bistar_gp

cd /scratch/gpfs/SUYOGHC/bistar_gp_c/experiments/practice_EvansEtAL

mkdir -p results_hierarchical

python run_hierarchical.py --demo --kernel rbf --kernel matern32 --kernel matern52 \
    --n_hmc_samples 200 --n_warmup 100 \
    --output_dir results_hierarchical

echo "Hierarchical run complete"

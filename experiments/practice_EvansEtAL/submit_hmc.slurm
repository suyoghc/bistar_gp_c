#!/bin/bash
#SBATCH --job-name=bistar-hmc
#SBATCH --output=logs/hmc_%j.out
#SBATCH --error=logs/hmc_%j.err
#SBATCH --time=12:00:00
#SBATCH --mem=16G
#SBATCH --cpus-per-task=4
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=sc8918@princeton.edu

module purge
module load anaconda3/2024.6
eval "$(conda shell.bash hook)"
conda activate bistar_gp

cd /scratch/gpfs/SUYOGHC/bistar_gp_c/experiments/practice_EvansEtAL

mkdir -p results_hmc

python run.py --demo --mode hmc --output_dir results_hmc --n_hmc_samples 200

echo "HMC run complete"

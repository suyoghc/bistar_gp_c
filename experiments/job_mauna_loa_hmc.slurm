#!/bin/bash
#SBATCH --job-name=bms_mauna_loa
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --output=logs/bms_mauna_loa_%j.out

module purge
module load anaconda3/2024.6
eval "$(conda shell.bash hook)"
conda activate bistar_gp

cd /scratch/gpfs/SUYOGHC/bistar_gp_c/experiments
python bms_star_mauna_loa.py --n-hmc 200 --n-warmup 100 --n-eval 300

#!/bin/bash
#SBATCH --job-name=mauna-bms
#SBATCH --output=logs/mauna_bms_%j.out
#SBATCH --error=logs/mauna_bms_%j.err
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

python bms_star_mauna_loa.py --n-hmc 100 --n-warmup 100 --n-eval 300

echo "Mauna Loa BMS* complete"

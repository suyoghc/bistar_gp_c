#!/bin/bash
#SBATCH --job-name=bms_mauna_loa
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --output=slurm-%j.out

module purge
module load anaconda3/2024.6
conda activate bistar

cd /scratch/network/sc8918/bistar_gp_project
python experiments/bms_star_mauna_loa.py --mode hmc --subsample 150 --n-hmc 200 --n-warmup 100 --n-posterior 80 --n-eval 80

#!/bin/bash
#SBATCH --job-name=bistar_v3
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem-per-cpu=8G
#SBATCH --time=02:00:00
#SBATCH --mail-type=begin,end,fail
#SBATCH --mail-user=sc8918@princeton.edu

module load anaconda3/2024.6
conda activate bistar

cd /scratch/network/sc8918/bistar_gp_project

# Step 1: Generate HMC samples for all priors
python experiments/bms_star_toy.py --priors informative vague misspecified_tight low_noise high_noise

# Step 2: Run v3 comparison across all priors
python experiments/bms_star_v3_comparison.py --priors informative vague misspecified_tight low_noise high_noise

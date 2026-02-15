#!/bin/bash
# Reproduce this run
# Generated: 2026-02-15T07:02:44.790642
cd /scratch/network/sc8918/bistar_gp_project
python experiments/bms_star_mauna_loa.py --mode hmc --subsample 150 --n-hmc 200 --n-warmup 100 --n-posterior 80 --n-eval 80

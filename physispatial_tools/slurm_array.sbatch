#!/bin/bash
#SBATCH --job-name=physispatial
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=02:00:00
# Set your authorized CPU partition/account on the sbatch command line.
set -euo pipefail
pipeline_root="${PHYSISPATIAL_ROOT:-${SLURM_SUBMIT_DIR:?}}"
cd "$pipeline_root"
if [ "$#" -ne 1 ]; then echo 'Pass the prepared sweep directory'; exit 2; fi
exec python3 -B physispatial_tools/sweep.py run --directory "$1" --index "${SLURM_ARRAY_TASK_ID:?}" --jobs 2

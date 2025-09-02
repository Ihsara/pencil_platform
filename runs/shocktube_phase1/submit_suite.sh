#!/bin/bash
#SBATCH --job-name=shock_sweep_ph1
#SBATCH --account=project_2008296
#SBATCH --partition=small
#SBATCH --time=00:15:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --array=1-2
#SBATCH --output=/scratch/project_2008296/chau/runs/shocktube_phase1/slurm_logs/output_%A_%a.txt
#SBATCH --error=/scratch/project_2008296/chau/runs/shocktube_phase1/slurm_logs/errors_%A_%a.txt
#SBATCH --mail-user=chau.c.tran@aalto.fi
#SBATCH --mail-type=END

set -e

# --- START OF FIX ---
# Determine the absolute path of the directory where this script is located.
# This makes the script portable and independent of where SLURM runs it.
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
MANIFEST_FILE="${SCRIPT_DIR}/run_manifest.txt"
# --- END OF FIX ---

# Get the name of the specific run directory for this task from the manifest using its absolute path
RUN_NAME=$(sed -n "${SLURM_ARRAY_TASK_ID}p" "$MANIFEST_FILE")

# Define the absolute path for the run on the HPC
RUN_DIR="/scratch/project_2008296/chau/runs/shocktube_phase1/${RUN_NAME}"

# Create a log file inside the specific run directory for simulation output
LOGFILE="${RUN_DIR}/simulation.log"

# --- Create the run directory first before trying to cd into it ---
# This part of the logic will now be handled by the submission script itself,
# making it more explicit and easier to debug.
echo "INFO: Creating run directory: $RUN_DIR"
mkdir -p "$RUN_DIR"

echo "INFO: Starting SLURM task ${SLURM_ARRAY_TASK_ID} for run: ${RUN_NAME}" > $LOGFILE
echo "INFO: Working directory: ${RUN_DIR}" >> $LOGFILE

# Navigate into the run directory. Exit if it fails.
cd "$RUN_DIR" || exit 1

# --- Run the simulation ---
# (The rest of the script is the same)
if [ -e ERROR -o -e LOCK -o -e RELOAD -o -e STOP -o -e FULLSTOP -o -e ENDTIME -o -e data/proc0/crash.dat -o -e data/allprocs/crash.h5 ]; then
    echo "WARNING: Lock file or previous error detected. Skipping run." >>$LOGFILE 2>&1
else
    if [ ! -e data/param.nml ]; then
       echo "INFO: Running START..." >>$LOGFILE 2>&1
       srun ./start.csh >>$LOGFILE 2>&1
       if [ $? -ne 0 ]; then echo "ERROR: start.csh failed" | tee -a $LOGFILE >&2; exit 1; fi
       echo "INFO: START finished." >>$LOGFILE 2>&1
    else
        echo "INFO: Skipping START (data/param.nml exists)." >>$LOGFILE 2>&1
    fi

    echo "INFO: Running RUN..." >>$LOGFILE 2>&1
    srun ./run.csh >>$LOGFILE 2>&1
    if [ $? -ne 0 ]; then echo "ERROR: run.csh failed" | tee -a $LOGFILE >&2; exit 1; fi
    echo "INFO: RUN finished successfully." >>$LOGFILE 2>&1
fi

echo "INFO: SLURM task finished." >>$LOGFILE 2>&1
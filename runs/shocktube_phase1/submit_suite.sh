#!/bin/bash
#SBATCH --job-name=shock_sweep
#SBATCH --account=project_2008296
#SBATCH --partition=medium
#SBATCH --time=01:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --output=G:\study\bachelor\thesis\platform\runs\shocktube_phase1/slurm_logs/output_%A_%a.txt
#SBATCH --error=G:\study\bachelor\thesis\platform\runs\shocktube_phase1/slurm_logs/errors_%A_%a.txt
#SBATCH --mail-user=chau.c.tran@aalto.fi
#SBATCH --mail-type=END

set -e

# Get the name of the specific run directory for this task from the manifest
RUN_NAME=$(sed -n "${SLURM_ARRAY_TASK_ID}p" run_manifest.txt)
RUN_DIR="/scratch/project_2008296/chau/runs/shocktube/${RUN_NAME}"

# Create a log file inside the specific run directory
LOGFILE="${RUN_DIR}/simulation.log"

echo "INFO: Starting SLURM task ${SLURM_ARRAY_TASK_ID} for run: ${RUN_NAME}" > $LOGFILE
echo "INFO: Working directory: ${RUN_DIR}" >> $LOGFILE

# Navigate into the run directory. Exit if it fails.
cd "$RUN_DIR" || exit 1

# --- Run the simulation ---
# This logic is taken from your provided script.
if [ -e ERROR -o -e LOCK -o -e RELOAD -o -e STOP -o -e FULLSTOP -o -e ENDTIME -o -e data/proc0/crash.dat -o -e data/allprocs/crash.h5 ]; then
    echo "WARNING: Lock file or previous error detected. Skipping run." >>$LOGFILE 2>&1
else
    # Run start.csh if needed
    if [ ! -e data/param.nml ]; then
       echo "INFO: Running START..." >>$LOGFILE 2>&1
       ./start.csh >>$LOGFILE 2>&1
       START_EXIT_CODE=$?
       if [ $START_EXIT_CODE -ne 0 ]; then
           echo "ERROR: start.csh failed with exit code $START_EXIT_CODE" | tee -a $LOGFILE >&2
           exit $START_EXIT_CODE
       fi
       echo "INFO: START finished." >>$LOGFILE 2>&1
    else
        echo "INFO: Skipping START (data/param.nml exists)." >>$LOGFILE 2>&1
    fi

    # Run run.csh
    echo "INFO: Running RUN..." >>$LOGFILE 2>&1
    ./run.csh >>$LOGFILE 2>&1
    RUN_EXIT_CODE=$?
    if [ $RUN_EXIT_CODE -ne 0 ]; then
        echo "ERROR: run.csh failed with exit code $RUN_EXIT_CODE" | tee -a $LOGFILE >&2
        exit $RUN_EXIT_CODE
    fi
    echo "INFO: RUN finished successfully." >>$LOGFILE 2>&1
fi

echo "INFO: SLURM task finished." >>$LOGFILE 2>&1
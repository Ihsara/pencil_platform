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

# --- Debug Information ---
echo "--- SLURM ENVIRONMENT ---"
echo "Job ID: ${SLURM_JOB_ID}"
echo "Array Task ID: ${SLURM_ARRAY_TASK_ID}"
echo "Submission Directory: ${SLURM_SUBMIT_DIR}"
echo "Hostname: $(hostname)"
echo "-------------------------"

# --- PRE-FLIGHT CHECK: Ensure dependency directories exist ---
# The Pencil Code's 'start.csh' script requires a 'data' directory
# to exist in the submission directory to write a jobid.dat file.
# We create it here to prevent the job from failing. The -p flag
# ensures it doesn't fail if the directory already exists.
echo "INFO: Ensuring dependency directory exists: ${SLURM_SUBMIT_DIR}/data"
mkdir -p "${SLURM_SUBMIT_DIR}/data"

# --- Path Definitions ---
MANIFEST_FILE="${SLURM_SUBMIT_DIR}/runs/shocktube_phase1/run_manifest.txt"

if [ ! -f "$MANIFEST_FILE" ]; then
    echo "FATAL ERROR: Manifest file not found at ${MANIFEST_FILE}" >&2
    exit 1
fi

RUN_NAME=$(sed -n "${SLURM_ARRAY_TASK_ID}p" "$MANIFEST_FILE")
if [ -z "$RUN_NAME" ]; then
    echo "FATAL ERROR: Could not read RUN_NAME from manifest for task ID ${SLURM_ARRAY_TASK_ID}" >&2
    exit 1
fi

SOURCE_BASE_DIR="/scratch/project_2008296/chau/chausims/generated_sims_project_group/sod_10_test_proj/quick_test_sod"
RUN_BASE_DIR="/scratch/project_2008296/chau/runs/shocktube_phase1"
RUN_DIR="${RUN_BASE_DIR}/${RUN_NAME}"
LOCAL_GENERATED_CONFIG_DIR="${SLURM_SUBMIT_DIR}/runs/shocktube_phase1/generated_configs/${RUN_NAME}"
LOGFILE="${RUN_DIR}/simulation.log"

echo "INFO: Starting SLURM task ${SLURM_ARRAY_TASK_ID} for run: ${RUN_NAME}"

# --- 1. Setup the Run Directory ---
echo "INFO: Setting up run directory from ${SOURCE_BASE_DIR} to ${RUN_DIR}"
pc_newrun "${SOURCE_BASE_DIR}" "${RUN_DIR}"

# --- 2. Copy Generated Configs ---
echo "INFO: Copying generated config files from ${LOCAL_GENERATED_CONFIG_DIR}"
cp -v "${LOCAL_GENERATED_CONFIG_DIR}"/* "${RUN_DIR}/"

# --- 3. Navigate and Execute ---
echo "INFO: Changing to working directory: ${RUN_DIR}"
cd "$RUN_DIR" || { echo "FATAL ERROR: Could not cd to ${RUN_DIR}"; exit 1; }
echo "INFO: Starting simulation run..." > $LOGFILE

# --- 4. Run the simulation ---
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

echo "INFO: SLURM task finished successfully."
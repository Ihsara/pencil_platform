#!/bin/bash
#
# This script executes a single Pencil Code simulation run.
# It is called by the Snakemake workflow and receives all
# necessary paths and parameters as environment variables.
#

set -e # Exit immediately if a command fails

# --- 1. Announce the Job ---
echo "--- SNAKEMAKE JOB ---"
echo "Job ID: ${SLURM_JOB_ID}"
echo "Run Name: ${SNAKEMAKE_PARAMS_RUN_NAME}"
echo "Log File: ${SNAKEMAKE_LOG_SIMULATION_LOG}"
echo "---------------------"

# --- 2. Setup the Run Directory ---
echo "INFO: Setting up run directory from ${SNAKEMAKE_PARAMS_SOURCE_DIR} to ${SNAKEMAKE_PARAMS_RUN_DIR}"
pc_newrun "${SNAKEMAKE_PARAMS_SOURCE_DIR}" "${SNAKEMAKE_PARAMS_RUN_DIR}"

# --- 3. Copy Generated Configs ---
echo "INFO: Copying generated config files from ${SNAKEMAKE_PARAMS_CONFIG_DIR}"
cp -v "${SNAKEMAKE_PARAMS_CONFIG_DIR}"/* "${SNAKEMAKE_PARAMS_RUN_DIR}/"

# --- 4. Navigate and Build ---
echo "INFO: Changing to working directory: ${SNAKEMAKE_PARAMS_RUN_DIR}"
cd "${SNAKEMAKE_PARAMS_RUN_DIR}" || exit 1

echo "INFO: Building the executable for this specific configuration..." > "${SNAKEMAKE_LOG_SIMULATION_LOG}"

# --- 5. Load Modules and Build ---
# The module load commands are passed in as a single string
source /usr/share/lmod/lmod/init/bash
module purge
eval "${SNAKEMAKE_PARAMS_MODULE_LOADS}"

pc_build --cleanall >> "${SNAKEMAKE_LOG_SIMULATION_LOG}" 2>&1
pc_build >> "${SNAKEMAKE_LOG_SIMULATION_LOG}" 2>&1

# --- 6. Run the Simulation ---
echo "INFO: Running START..." >> "${SNAKEMAKE_LOG_SIMULATION_LOG}" 2>&1
srun ./start.csh >> "${SNAKEMAKE_LOG_SIMULATION_LOG}" 2>&1

echo "INFO: Running RUN..." >> "${SNAKEMAKE_LOG_SIMULATION_LOG}" 2>&1
srun ./run.csh >> "${SNAKEMAKE_LOG_SIMULATION_LOG}" 2>&1

echo "INFO: SLURM task finished successfully."
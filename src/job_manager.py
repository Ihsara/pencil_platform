# src/job_manager.py

import subprocess
import re
import sys
from pathlib import Path
from loguru import logger
import yaml

from .constants import DIRS, FILES

def submit_suite(experiment_name: str, submit_script_path: Path, plan: dict):
    """
    Submits the generated job array script to SLURM and records the job ID.
    """
    # This function is correct and remains unchanged.
    logger.info("Attempting to submit job to SLURM...")
    try:
        cmd = ["sbatch", str(submit_script_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        job_id_match = re.search(r'Submitted batch job (\d+)', result.stdout)
        if job_id_match:
            job_id = job_id_match.group(1)
            local_exp_dir = DIRS.runs / experiment_name
            batch_id_file = local_exp_dir / ".batch_id"
            with open(batch_id_file, 'w') as f:
                f.write(job_id)
            hpc_run_base_dir = plan.get('hpc', {}).get('run_base_dir', 'runs')
            logger.info("="*50)
            logger.info("           JOB SUBMITTED SUCCESSFULLY")
            logger.info("="*50)
            logger.info(f"  Submission Script: {submit_script_path}")
            logger.info(f"  HPC Run Directory: {hpc_run_base_dir}")
            logger.info(f"  SLURM Batch Job ID: {job_id}")
            logger.info(f"  You can check the status with: python main.py {experiment_name} --check")
        else:
            logger.error("Could not parse Job ID from sbatch output.")
            logger.error(f"  STDOUT: {result.stdout}")
    except FileNotFoundError:
        logger.error("`sbatch` command not found. Are you on an HPC login node?")
    except subprocess.CalledProcessError as e:
        logger.error("SLURM job submission failed.")
        logger.error(f"  STDERR: {e.stderr}")

def check_suite_status(experiment_name: str):
    """
    Checks the status of a submitted SLURM job array using the saved batch ID.
    """
    logger.info(f"--- STATUS CHECK MODE for '{experiment_name}' ---")
    
    local_exp_dir = DIRS.runs / experiment_name
    batch_id_file = local_exp_dir / ".batch_id"
    manifest_file = local_exp_dir / FILES.manifest

    if not batch_id_file.exists():
        logger.error(f"Batch ID file not found at '{batch_id_file}'. Cannot check status.")
        sys.exit(1)
    if not manifest_file.exists():
        logger.error(f"Manifest file not found at '{manifest_file}'. Cannot map tasks to run names.")
        sys.exit(1)

    batch_id = batch_id_file.read_text().strip()
    if not batch_id:
        logger.error(f"Batch ID file '{batch_id_file}' is empty.")
        sys.exit(1)

    logger.info(f"Querying SLURM for batch job ID: {batch_id}")

    try:

        cmd = ["sacct", "-j", batch_id, "--format=JobID,State", "-n", "-P"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        status_lines = result.stdout.strip().split('\n')
        
        with open(manifest_file, 'r') as f:
            run_names = [line.strip() for line in f.readlines()]
        
        status_map = {}

        for line in status_lines:
            if not line.strip(): continue
            parts = line.split('|')
            if len(parts) >= 2:
                job_id_str, state = parts[0], parts[1].strip()
                # Check for the array job format, e.g., '1234567_1'
                if '_' in job_id_str:
                    task_id_str = job_id_str.split('_')[-1]
                    if task_id_str.isdigit():
                        status_map[int(task_id_str)] = state

        counts = {"COMPLETED": 0, "FAILED": 0, "PENDING": 0, "RUNNING": 0, "OTHER": 0}
        failed_runs = []
        total_tasks = len(run_names)

        # If sacct returns nothing, it often means the job is old and completed.
        # We will assume completion if no specific status is found for any task.
        if not status_map:
             logger.warning(f"No active or recent job tasks found for Job ID {batch_id}.")
             logger.warning("This usually means the job array has completed successfully and is no longer in the recent accounting database.")
             counts["COMPLETED"] = total_tasks
        else:
            for i in range(total_tasks):
                task_id = i + 1
                # If a task is not in the map, it's likely still pending.
                status = status_map.get(task_id, "PENDING")
                
                # --- FIX: More robust status checking ---
                if "COMPLETED" in status:
                    counts["COMPLETED"] += 1
                elif any(s in status for s in ["FAILED", "CANCELLED", "TIMEOUT"]):
                    counts["FAILED"] += 1
                    failed_runs.append(run_names[i])
                elif "PENDING" in status:
                    counts["PENDING"] += 1
                elif "RUNNING" in status:
                    counts["RUNNING"] += 1
                else:
                    counts["OTHER"] += 1
        
        logger.info("--- Job Status Summary ---")
        logger.info(f"  Total Simulations: {total_tasks}")
        logger.info(f"  Completed: {counts['COMPLETED']}")
        logger.info(f"  Failed/Cancelled: {counts['FAILED']}")
        logger.info(f"  Running: {counts['RUNNING']}")
        logger.info(f"  Pending: {counts['PENDING']}")
        
        if failed_runs:
            logger.warning("The following simulations failed:")
            plan_file = DIRS.config / experiment_name / DIRS.plan_subdir / FILES.plan
            with open(plan_file, 'r') as f:
                plan = yaml.safe_load(f)
            hpc_run_base_dir = Path(plan.get('hpc', {}).get('run_base_dir', 'runs'))
            for run_name in failed_runs:
                print(f"  - {hpc_run_base_dir / run_name}")
        
    except FileNotFoundError:
        logger.error("`sacct` command not found. Are you on an HPC login node?")
    except subprocess.CalledProcessError as e:
        logger.error("Error querying SLURM job status. This can happen if the job ID is invalid or has expired from the accounting database.")
        logger.error(f"  STDERR: {e.stderr.strip()}")
    except Exception as e:
        logger.exception(f"An unexpected error occurred during status check: {e}")
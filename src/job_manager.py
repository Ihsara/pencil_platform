# src/job_manager.py

import subprocess
import re
import sys
from pathlib import Path
from loguru import logger
import yaml

from .constants import DIRS, FILES
from .logging_utils import setup_file_logging

def submit_suite(experiment_name: str, submit_script_path: Path, plan: dict):
    """
    Submits the generated job array script to SLURM and records the job ID.
    """
    # Setup file logging for this submission
    setup_file_logging(experiment_name, 'submission')
    
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

def check_suite_status(experiment_name: str, return_status: bool = False):
    """
    Checks the status of a submitted SLURM job array using the saved batch ID.
    
    Args:
        experiment_name: Name of the experiment
        return_status: If True, returns a dict with status counts instead of just logging
        
    Returns:
        Dict with status counts if return_status=True, otherwise None
    """
    # Setup file logging only for direct status checks (not for internal polling)
    if not return_status:
        setup_file_logging(experiment_name, 'status')
    
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
        
        if return_status:
            return counts
        
    except FileNotFoundError:
        logger.error("`sacct` command not found. Are you on an HPC login node?")
        if return_status:
            return None
    except subprocess.CalledProcessError as e:
        logger.error("Error querying SLURM job status. This can happen if the job ID is invalid or has expired from the accounting database.")
        logger.error(f"  STDERR: {e.stderr.strip()}")
        if return_status:
            return None
    except Exception as e:
        logger.exception(f"An unexpected error occurred during status check: {e}")
        if return_status:
            return None


def wait_for_completion(experiment_name: str, poll_interval: int = 60, max_wait: int = None):
    """
    Waits for a SLURM job array to complete by polling status periodically.
    
    Args:
        experiment_name: Name of the experiment
        poll_interval: Seconds between status checks (default: 60)
        max_wait: Maximum seconds to wait before giving up (default: None = wait forever)
        
    Returns:
        True if job completed successfully, False if failed or timed out
    """
    import time
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
    
    console = Console()
    console.print(f"\n[cyan]Waiting for job completion: {experiment_name}[/cyan]")
    console.print(f"[dim]Poll interval: {poll_interval}s[/dim]\n")
    
    start_time = time.time()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Checking job status...", total=None)
        
        while True:
            # Check status
            status = check_suite_status(experiment_name, return_status=True)
            
            if status is None:
                logger.error("Failed to check job status")
                return False
            
            # Check if all jobs are completed or failed
            total = sum(status.values())
            completed_or_failed = status['COMPLETED'] + status['FAILED']
            
            if completed_or_failed == total and (status['PENDING'] == 0 and status['RUNNING'] == 0):
                # All jobs done
                if status['FAILED'] > 0:
                    logger.warning(f"Job array completed with {status['FAILED']} failures")
                    return False
                else:
                    logger.success(f"Job array completed successfully!")
                    return True
            
            # Update progress description
            progress.update(task, description=f"[cyan]Running: {status['RUNNING']}, Pending: {status['PENDING']}, Completed: {status['COMPLETED']}, Failed: {status['FAILED']}")
            
            # Check timeout
            if max_wait and (time.time() - start_time) > max_wait:
                logger.warning(f"Timed out after {max_wait}s while waiting for job completion")
                return False
            
            # Wait before next poll
            time.sleep(poll_interval)

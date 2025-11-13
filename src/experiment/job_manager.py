# src/job_manager.py

import subprocess
import re
import sys
from pathlib import Path
from loguru import logger
import yaml

from src.core.constants import DIRS, FILES
from src.core.logging import setup_file_logging
from src.experiment.naming import format_short_experiment_name

def _ensure_manifest_exists(experiment_name: str, local_exp_dir: Path) -> bool:
    """
    Ensures the run manifest file exists by regenerating it from generated_configs directory.
    
    Args:
        experiment_name: Name of the experiment
        local_exp_dir: Path to the local experiment directory
        
    Returns:
        True if manifest exists or was successfully created, False otherwise
    """
    manifest_file = local_exp_dir / FILES.manifest
    
    # If manifest already exists, we're good
    if manifest_file.exists():
        return True
    
    # Try to regenerate from generated_configs directory
    generated_configs_dir = local_exp_dir / "generated_configs"
    if not generated_configs_dir.exists():
        logger.error(f"Cannot regenerate manifest: generated_configs directory not found at {generated_configs_dir}")
        return False
    
    # Get all run directories from generated_configs
    run_dirs = [d for d in generated_configs_dir.iterdir() if d.is_dir()]
    
    if not run_dirs:
        logger.error(f"Cannot regenerate manifest: no run directories found in {generated_configs_dir}")
        return False
    
    # Sort run directories by name for consistent ordering
    run_names = sorted([d.name for d in run_dirs])
    
    # Write manifest file
    try:
        with open(manifest_file, 'w') as f:
            for run_name in run_names:
                f.write(f"{run_name}\n")
        logger.info(f"Successfully regenerated manifest with {len(run_names)} runs at {manifest_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to write manifest file: {e}")
        return False

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

def check_suite_status(experiment_name: str, return_status: bool = False, silent: bool = False):
    """
    Checks the status of a submitted SLURM job array using the saved batch ID.
    
    Args:
        experiment_name: Name of the experiment
        return_status: If True, returns a dict with status counts instead of just logging
        silent: If True, suppresses logger output (for use with progress displays)
        
    Returns:
        Dict with status counts if return_status=True, otherwise None
    """
    # Setup file logging only for direct status checks (not for internal polling)
    if not return_status:
        setup_file_logging(experiment_name, 'status')
    
    if not silent:
        logger.info(f"--- STATUS CHECK MODE for '{experiment_name}' ---")
    
    local_exp_dir = DIRS.runs / experiment_name
    batch_id_file = local_exp_dir / ".batch_id"
    manifest_file = local_exp_dir / FILES.manifest

    if not batch_id_file.exists():
        logger.error(f"Batch ID file not found at '{batch_id_file}'. Cannot check status.")
        sys.exit(1)
    
    # Ensure manifest exists - regenerate if missing
    if not manifest_file.exists():
        if not silent:
            logger.warning(f"Manifest file not found. Attempting to regenerate...")
        if not _ensure_manifest_exists(experiment_name, local_exp_dir):
            logger.error(f"Cannot proceed without manifest file.")
            sys.exit(1)

    batch_id = batch_id_file.read_text().strip()
    if not batch_id:
        logger.error(f"Batch ID file '{batch_id_file}' is empty.")
        sys.exit(1)

    if not silent:
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

        # If sacct returns nothing, check if job was just submitted (may not be in sacct yet)
        if not status_map:
            # Try squeue to see if job is still queued
            try:
                squeue_cmd = ["squeue", "-j", batch_id, "-h"]
                squeue_result = subprocess.run(squeue_cmd, capture_output=True, text=True)
                if squeue_result.stdout.strip():
                    # Job is in queue, mark as pending
                    if not silent:
                        logger.info(f"Job {batch_id} is queued or just starting (not yet in sacct)")
                    counts["PENDING"] = total_tasks
                else:
                    # Job not in squeue either - likely old and completed
                    if not silent:
                        logger.warning(f"No active or recent job tasks found for Job ID {batch_id}.")
                        logger.warning("This usually means the job array has completed successfully and is no longer in the recent accounting database.")
                    counts["COMPLETED"] = total_tasks
            except:
                # If squeue fails, assume pending
                counts["PENDING"] = total_tasks
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
        
        if not silent:
            logger.info("--- Job Status Summary ---")
            logger.info(f"  Total Simulations: {total_tasks}")
            logger.info(f"  Completed: {counts['COMPLETED']}")
            logger.info(f"  Failed/Cancelled: {counts['FAILED']}")
            logger.info(f"  Running: {counts['RUNNING']}")
            logger.info(f"  Pending: {counts['PENDING']}")
        
        if failed_runs and not silent:
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


def get_job_stage_info(log_base_dir: Path):
    """
    Analyzes log files to determine the current stage of a job.
    
    Args:
        log_base_dir: Path to the submission log directory for a specific array task
        
    Returns:
        Dict with stage information: {
            'stage': str,  # 'build', 'start', 'run', 'completed', 'failed', 'unknown'
            'iteration': int or None,  # Latest iteration if in 'run' stage
            'details': str,  # Additional info
            'failed_log': Path or None,  # Path to the log file where failure occurred
            'error_tail': list or None  # Last N lines of the failed log
        }
    """
    build_log = log_base_dir / "pc_build.log"
    start_log = log_base_dir / "pc_start.log"
    run_log = log_base_dir / "pc_run.log"
    
    # Check if logs exist and determine stage
    if not log_base_dir.exists():
        return {'stage': 'unknown', 'iteration': None, 'details': 'Log directory not found', 
                'failed_log': None, 'error_tail': None}
    
    # Check for failures in any log
    for log_file, stage_name in [(build_log, 'build'), (start_log, 'start'), (run_log, 'run')]:
        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    content = f.read()
                    if 'ERROR:' in content or 'FATAL ERROR:' in content or 'failed' in content.lower():
                        # Get last 15 lines for error context
                        lines = content.split('\n')
                        error_tail = lines[-15:] if len(lines) > 15 else lines
                        return {
                            'stage': 'failed', 
                            'iteration': None, 
                            'details': f'Failed in {stage_name} stage',
                            'failed_log': log_file,
                            'error_tail': error_tail
                        }
            except:
                pass
    
    # Determine current stage based on which logs exist and their completion
    if run_log.exists():
        # In run stage - extract latest iteration
        try:
            with open(run_log, 'r') as f:
                lines = f.readlines()
                latest_iteration = None
                for line in reversed(lines):
                    # Look for iteration pattern: starts with whitespace and number
                    match = re.match(r'^\s+(\d+)\s+', line)
                    if match:
                        latest_iteration = int(match.group(1))
                        break
                
                # Check if completed - look for multiple completion markers
                last_lines = ''.join(lines[-50:]).lower()
                if 'finished successfully' in last_lines or 'done' in last_lines or 'completed' in last_lines:
                    # Additional check: "Done" often appears standalone on a line
                    for line in lines[-10:]:
                        if line.strip().lower() == 'done':
                            return {'stage': 'completed', 'iteration': latest_iteration, 
                                    'details': 'Run completed successfully',
                                    'failed_log': None, 'error_tail': None}
                    # Fall back to generic completion message
                    return {'stage': 'completed', 'iteration': latest_iteration, 
                            'details': 'Run finished successfully',
                            'failed_log': None, 'error_tail': None}
                
                if latest_iteration is not None:
                    return {'stage': 'run', 'iteration': latest_iteration, 'details': f'Running iteration {latest_iteration}',
                            'failed_log': None, 'error_tail': None}
                else:
                    return {'stage': 'run', 'iteration': None, 'details': 'Run started, no iterations yet',
                            'failed_log': None, 'error_tail': None}
        except:
            return {'stage': 'run', 'iteration': None, 'details': 'Run stage (reading error)',
                    'failed_log': None, 'error_tail': None}
    
    elif start_log.exists():
        try:
            with open(start_log, 'r') as f:
                content = f.read()
                if 'completed successfully' in content.lower():
                    return {'stage': 'start_complete', 'iteration': None, 'details': 'Start completed, waiting for run',
                            'failed_log': None, 'error_tail': None}
                else:
                    return {'stage': 'start', 'iteration': None, 'details': 'Starting simulation',
                            'failed_log': None, 'error_tail': None}
        except:
            return {'stage': 'start', 'iteration': None, 'details': 'Start stage',
                    'failed_log': None, 'error_tail': None}
    
    elif build_log.exists():
        try:
            with open(build_log, 'r') as f:
                content = f.read()
                if 'completed successfully' in content.lower() or 'finished' in content.lower():
                    return {'stage': 'build_complete', 'iteration': None, 'details': 'Build completed',
                            'failed_log': None, 'error_tail': None}
                else:
                    return {'stage': 'build', 'iteration': None, 'details': 'Building code',
                            'failed_log': None, 'error_tail': None}
        except:
            return {'stage': 'build', 'iteration': None, 'details': 'Build stage',
                    'failed_log': None, 'error_tail': None}
    
    return {'stage': 'initializing', 'iteration': None, 'details': 'Job initializing',
            'failed_log': None, 'error_tail': None}


def tail_log_file(log_file: Path, num_lines: int = 10):
    """
    Returns the last N lines of a log file.
    
    Args:
        log_file: Path to log file
        num_lines: Number of lines to return (default: 10)
        
    Returns:
        List of strings (lines)
    """
    if not log_file.exists():
        return []
    
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
            return lines[-num_lines:]
    except:
        return []


def monitor_job_progress(experiment_name: str, show_details: bool = True):
    """
    Monitors the detailed progress of running jobs by checking log files.
    
    Args:
        experiment_name: Name of the experiment
        show_details: Whether to show detailed progress for each task
    """
    from rich.console import Console
    from rich.table import Table
    
    console = Console()
    
    # Get batch ID and manifest
    local_exp_dir = DIRS.runs / experiment_name
    batch_id_file = local_exp_dir / ".batch_id"
    manifest_file = local_exp_dir / FILES.manifest
    
    if not batch_id_file.exists():
        logger.error("Cannot monitor progress: batch ID file not found")
        return
    
    # Ensure manifest exists - regenerate if missing
    if not manifest_file.exists():
        logger.warning(f"Manifest file not found. Attempting to regenerate...")
        if not _ensure_manifest_exists(experiment_name, local_exp_dir):
            logger.error("Cannot monitor progress: manifest file could not be created")
            return
    
    batch_id = batch_id_file.read_text().strip()
    with open(manifest_file, 'r') as f:
        run_names = [line.strip() for line in f.readlines()]
    
    # Find submission log directories
    log_base = Path("logs/submission") / experiment_name
    if not log_base.exists():
        logger.warning("No submission logs found yet")
        return
    
    # Find the most recent submission directory
    submission_dirs = sorted(log_base.glob("sub_*"), key=lambda x: x.name, reverse=True)
    if not submission_dirs:
        logger.warning("No submission directories found")
        return
    
    latest_submission = submission_dirs[0]
    
    # Find ALL job directories - SLURM sometimes creates multiple job IDs
    # Search for all numeric directories (job IDs) and collect all array tasks
    job_dirs = []
    all_job_id_dirs = [d for d in latest_submission.iterdir() if d.is_dir() and d.name.isdigit()]
    
    for job_id_dir in all_job_id_dirs:
        job_dirs.extend(job_id_dir.glob("array_*"))
    
    logger.info(f"Found {len(all_job_id_dirs)} job ID(s) with {len(job_dirs)} total array task(s)")
    
    if not job_dirs:
        logger.warning(f"No array task logs found for job {batch_id} in {latest_submission}")
        logger.info(f"Searched in: {latest_submission / batch_id}")
        return
    
    # Create progress table
    table = Table(title=f"Job Progress: {experiment_name} (Job ID: {batch_id})")
    table.add_column("Task", style="cyan")
    table.add_column("Run Name", style="yellow")
    table.add_column("Stage", style="green")
    table.add_column("Iteration", style="magenta")
    table.add_column("Details", style="white")
    
    stage_counts = {'initializing': 0, 'build': 0, 'start': 0, 'run': 0, 'completed': 0, 'failed': 0, 'pending': 0}
    failed_tasks = []
    
    # Create a mapping of task_id to job_dir for easy lookup
    job_dir_map = {}
    for job_dir in job_dirs:
        task_id = int(job_dir.name.split('_')[-1])
        job_dir_map[task_id] = job_dir
    
    # Loop through ALL tasks (1 to len(run_names)), not just ones with log directories
    for task_id in range(1, len(run_names) + 1):
        run_name = run_names[task_id - 1]
        
        # Check if this task has a log directory
        if task_id in job_dir_map:
            job_dir = job_dir_map[task_id]
            stage_info = get_job_stage_info(job_dir)
            stage = stage_info['stage']
            iteration = stage_info['iteration']
            details = stage_info['details']
            
            # Track failed tasks
            if stage == 'failed':
                failed_tasks.append({
                    'task_id': task_id,
                    'run_name': run_name,
                    'log_file': stage_info.get('failed_log'),
                    'error_tail': stage_info.get('error_tail'),
                    'details': details
                })
            
            # Show log tail if requested and job is running or completed
            if show_details and stage in ['build', 'start', 'run', 'completed']:
                console.print(f"\n[cyan]Task {task_id} - Last 5 lines:[/cyan]")
                if stage == 'build':
                    log_file = job_dir / "pc_build.log"
                elif stage == 'start':
                    log_file = job_dir / "pc_start.log"
                else:
                    log_file = job_dir / "pc_run.log"
                
                # Show location information
                console.print(f"  [yellow]Run location: {DIRS.runs / experiment_name / run_name}[/yellow]")
                console.print(f"  [yellow]Log file: {log_file}[/yellow]")
                
                tail_lines = tail_log_file(log_file, 5)
                for line in tail_lines:
                    console.print(f"  [dim]{line.rstrip()}[/dim]")
        else:
            # Task hasn't started yet - no log directory
            stage = 'pending'
            iteration = None
            details = 'Not started yet'
        
        # Count stages
        if stage in stage_counts:
            stage_counts[stage] += 1
        
        # Add to table
        iter_str = str(iteration) if iteration is not None else "-"
        # Use intelligent name shortening instead of simple truncation
        short_name = format_short_experiment_name(run_name, experiment_name)
        table.add_row(
            str(task_id),
            short_name,
            stage,
            iter_str,
            details
        )
    
    console.print(table)
    
    # Print summary
    console.print("\n[bold]Summary:[/bold]")
    console.print(f"  Pending: {stage_counts['pending']}")
    console.print(f"  Initializing: {stage_counts['initializing']}")
    console.print(f"  Building: {stage_counts['build']}")
    console.print(f"  Starting: {stage_counts['start']}")
    console.print(f"  Running: {stage_counts['run']}")
    console.print(f"  Completed: {stage_counts['completed']}")
    console.print(f"  Failed: {stage_counts['failed']}")
    
    # Show detailed error information for failed tasks
    if failed_tasks:
        console.print("\n[bold red]═══ FAILED TASKS - ERROR DETAILS ═══[/bold red]")
        for failure in failed_tasks:
            console.print(f"\n[red]Task {failure['task_id']}: {failure['run_name']}[/red]")
            console.print(f"[yellow]Error: {failure['details']}[/yellow]")
            
            if failure['log_file']:
                console.print(f"[cyan]Log file: {failure['log_file']}[/cyan]")
                
                if failure['error_tail']:
                    console.print("[dim]Last 15 lines of log:[/dim]")
                    for line in failure['error_tail']:
                        if line.strip():  # Skip empty lines
                            console.print(f"  [dim]{line.rstrip()}[/dim]")
            console.print()  # Blank line between failures


def wait_for_completion(experiment_name: str, poll_interval: int = 60, max_wait: int = None, initial_delay: int = 5):
    """
    Waits for a SLURM job array to complete by polling status and monitoring log files.
    
    Args:
        experiment_name: Name of the experiment
        poll_interval: Seconds between status checks (default: 60)
        max_wait: Maximum seconds to wait before giving up (default: None = wait forever)
        initial_delay: Seconds to wait before first check (default: 5, gives job time to start)
        
    Returns:
        True if job completed successfully, False if failed or timed out
    """
    import time
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
    
    console = Console()
    console.print(f"\n[cyan]Waiting for job completion: {experiment_name}[/cyan]")
    console.print(f"[dim]Poll interval: {poll_interval}s, initial delay: {initial_delay}s[/dim]\n")
    
    # Give the job a moment to start and create initial logs
    if initial_delay > 0:
        console.print(f"[yellow]Waiting {initial_delay}s for job to initialize...[/yellow]")
        time.sleep(initial_delay)
    
    start_time = time.time()
    iteration = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Checking job status...", total=None)
        
        while True:
            iteration += 1
            
            # Check SLURM status (silent mode to not interfere with progress display)
            status = check_suite_status(experiment_name, return_status=True, silent=True)
            
            if status is None:
                logger.error("Failed to check job status")
                return False
            
            # Check if all jobs are completed or failed
            total = sum(status.values())
            completed_or_failed = status['COMPLETED'] + status['FAILED']
            
            # Also check detailed progress from log files
            if iteration % 3 == 0:  # Every 3rd iteration, show detailed progress
                progress.stop()  # Temporarily stop progress display
                console.print(f"\n[cyan]═══ Poll #{iteration} - Detailed Progress ═══[/cyan]")
                monitor_job_progress(experiment_name, show_details=False)
                progress.start()  # Resume progress display
            
            if completed_or_failed == total and (status['PENDING'] == 0 and status['RUNNING'] == 0):
                # All jobs done according to SLURM - but verify this isn't a false positive
                # Check if we have any log files to verify actual completion
                progress.stop()
                console.print("\n[yellow]All SLURM jobs reported as done. Verifying completion...[/yellow]")
                
                # Try to get detailed progress from logs
                local_exp_dir = DIRS.runs / experiment_name
                batch_id_file = local_exp_dir / ".batch_id"
                if batch_id_file.exists():
                    batch_id = batch_id_file.read_text().strip()
                    log_base = Path("logs/submission") / experiment_name
                    
                    # Check if any logs exist
                    has_logs = False
                    if log_base.exists():
                        submission_dirs = sorted(log_base.glob("sub_*"), key=lambda x: x.name, reverse=True)
                        if submission_dirs:
                            latest_submission = submission_dirs[0]
                            job_dirs = list(latest_submission.glob(f"{batch_id}/array_*"))
                            if not job_dirs:
                                # Try alternative locations
                                all_job_id_dirs = [d for d in latest_submission.iterdir() if d.is_dir() and d.name.isdigit()]
                                for job_id_dir in all_job_id_dirs:
                                    job_dirs.extend(job_id_dir.glob("array_*"))
                            has_logs = len(job_dirs) > 0
                    
                    # If no logs exist and we're reporting complete, this is likely a false positive
                    if not has_logs and iteration < 3:
                        console.print("[yellow]No log files found yet - job may still be initializing. Continuing to wait...[/yellow]")
                        progress.start()
                        time.sleep(poll_interval)
                        continue
                
                # We have logs or enough iterations passed - check detailed status
                monitor_job_progress(experiment_name, show_details=False)
                
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

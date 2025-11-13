"""
Examples of using the display system with loguru logging.

This file demonstrates proper separation of:
- Detailed logging (loguru) -> files only
- Terminal display (rich) -> concise, readable, 72-char width
"""

from src.core.display import (
    ConfigScene, SubmissionScene, AnalysisScene, MonitorScene,
    show_header, show_error, show_warning, show_success, show_info,
    create_progress_bar, StatusBar
)
from src.core.logging import setup_file_logging
from loguru import logger
import time


def example_config_validation(exp_name: str):
    """Example: Configuration validation scene."""
    
    # Setup logging (detailed logs go to files)
    setup_file_logging(exp_name, "generation")
    
    # Show header on terminal
    show_header("Configuration Validation", f"Experiment: {exp_name}")
    
    # Create config scene
    scene = ConfigScene(exp_name)
    
    # Run checks (logs detailed info, scene stores results)
    logger.info("Starting config validation")
    
    # Check 1
    logger.debug("Checking sweep.yaml exists...")
    scene.add_check("sweep.yaml", True, "Found")
    
    # Check 2
    logger.debug("Validating parameter ranges...")
    scene.add_check("param ranges", True, "Valid")
    
    # Check 3
    logger.debug("Checking template files...")
    scene.add_check("templates", True, "All present")
    
    # Check 4
    logger.debug("Validating dependencies...")
    scene.add_check("dependencies", False, "Missing: numpy>=1.20")
    
    # Display results on terminal (concise)
    scene.display()
    
    logger.info("Config validation complete")


def example_submission(exp_name: str):
    """Example: Job submission scene."""
    
    setup_file_logging(exp_name, "submission")
    show_header("Job Submission", f"Experiment: {exp_name}")
    
    # Create submission scene
    scene = SubmissionScene(exp_name)
    
    # Gather info (logs details, scene stores for display)
    logger.info("Preparing submission...")
    logger.debug(f"Total runs: 100")
    scene.add_info("Runs", "100")
    
    logger.debug(f"Cores per run: 4")
    scene.add_info("Cores/run", "4")
    
    logger.debug(f"Runtime: 00:30:00")
    scene.add_info("Runtime", "00:30:00")
    
    logger.debug(f"Partition: medium")
    scene.add_info("Partition", "medium")
    
    # Display pre-submission info
    scene.display_pre_submit()
    
    # Submit (with detailed logging)
    logger.info("Submitting job to scheduler...")
    time.sleep(1)  # Simulate submission
    job_id = "12345678"
    logger.success(f"Job {job_id} submitted successfully")
    
    # Display result (concise)
    scene.display_result(job_id, True)


def example_analysis_with_progress(exp_name: str):
    """Example: Analysis scene with progress tracking."""
    
    setup_file_logging(exp_name, "analysis")
    show_header("Analysis Pipeline", f"Experiment: {exp_name}")
    
    # Create analysis scene
    total_runs = 50
    scene = AnalysisScene(exp_name, total_runs)
    
    # Update phase
    scene.update_phase("Loading data")
    logger.info("Loading VAR files...")
    
    # Process runs with progress display
    scene.update_phase("Computing errors")
    logger.info(f"Processing {total_runs} runs...")
    
    for i in range(total_runs):
        run_name = f"run_{i:03d}"
        
        # Detailed logging (to files only)
        logger.debug(f"Processing {run_name}: loading VAR files")
        logger.debug(f"Processing {run_name}: computing L1 norm")
        logger.debug(f"Processing {run_name}: computing L2 norm")
        
        # Concise terminal display
        scene.display_progress(run_name)
        
        time.sleep(0.05)  # Simulate processing
    
    # Add statistics (logged in detail, displayed concisely)
    scene.add_stat("Best L1 error", 0.0234)
    scene.add_stat("Best L2 error", 0.0456)
    scene.add_stat("Avg convergence time", "120s")
    
    # Display summary
    print()  # New line after progress
    scene.display_summary()
    
    logger.info("Analysis complete")


def example_monitoring(exp_name: str):
    """Example: Job monitoring scene."""
    
    setup_file_logging(exp_name, "status")
    show_header("Job Monitor", f"Experiment: {exp_name}")
    
    # Create monitor scene
    scene = MonitorScene(exp_name)
    
    # Update status (detailed logs)
    job_id = "12345678"
    logger.info(f"Checking status for job {job_id}")
    scene.update_status(job_id, "RUNNING")
    
    # Add task info (only show subset on terminal)
    logger.debug("Gathering task information...")
    for i in range(20):
        task_id = f"task_{i:02d}"
        info = {
            "stage": "run" if i < 15 else "build",
            "progress": f"t={i*100}"
        }
        scene.add_task_info(task_id, info)
        logger.debug(f"Task {task_id}: {info}")
    
    # Display concise summary
    scene.display()
    
    logger.info("Monitor update complete")


def example_with_status_bar():
    """Example: Using status bar for long operations."""
    
    show_header("Long Operation", "With status bar")
    
    total_tasks = 12
    status_bar = StatusBar(total_tasks, "Processing")
    
    for i in range(total_tasks):
        task_name = f"task_{i+1}"
        
        # Log details
        logger.debug(f"Starting {task_name}")
        
        # Update status bar
        status_bar.increment()
        status = status_bar.render(task_name)
        print(f"\r{status}", end="", flush=True)
        
        time.sleep(0.3)  # Simulate work
        
        logger.debug(f"Completed {task_name}")
    
    print()  # New line after status bar
    show_success("All tasks completed")


def example_simple_messages():
    """Example: Simple message functions."""
    
    show_header("Message Examples")
    
    show_info("This is an informational message")
    logger.info("This goes to log file with full details")
    
    show_warning("This is a warning")
    logger.warning("Warning details in log file")
    
    show_success("Operation completed successfully")
    logger.success("Success with full context in log")
    
    show_error("An error occurred")
    logger.error("Error details with stack trace in log")


if __name__ == "__main__":
    """Run examples to see the display system in action."""
    
    exp_name = "example_exp"
    
    print("\n" + "="*72)
    print("DISPLAY SYSTEM EXAMPLES")
    print("="*72 + "\n")
    
    # Example 1: Config validation
    example_config_validation(exp_name)
    input("Press Enter for next example...")
    
    # Example 2: Submission
    example_submission(exp_name)
    input("Press Enter for next example...")
    
    # Example 3: Analysis with progress
    example_analysis_with_progress(exp_name)
    input("Press Enter for next example...")
    
    # Example 4: Monitoring
    example_monitoring(exp_name)
    input("Press Enter for next example...")
    
    # Example 5: Status bar
    example_with_status_bar()
    input("Press Enter for next example...")
    
    # Example 6: Simple messages
    example_simple_messages()
    
    print("\n" + "="*72)
    print("Check logs/ directory for detailed log files")
    print("="*72)

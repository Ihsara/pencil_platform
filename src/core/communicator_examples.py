"""
Examples of using the unified Communicator interface.

Demonstrates how tasks automatically output to BOTH terminal and logs.
"""

from src.core.communicator import Communicator, MessageLevel, create_communicator
import time


def example_simple_task():
    """Example: Simple task with start/end."""
    
    # Create communicator for this operation
    comm = Communicator("example_exp", "demo")
    comm.header("Simple Task Example", "One task")
    
    # Start task
    task_id = comm.task_start("process_data", "Processing input data")
    
    # Do work
    time.sleep(1)
    comm.message("Reading files...", MessageLevel.DEBUG, detail="From /path/to/data")
    comm.message("Validating data...", MessageLevel.INFO)
    time.sleep(0.5)
    
    # End task
    comm.task_end(task_id, success=True, result={"records": 100})
    
    # Summary
    comm.summary()


def example_multiple_tasks():
    """Example: Multiple tasks in sequence."""
    
    comm = Communicator("example_exp", "demo")
    comm.header("Multiple Tasks", "Sequential execution")
    
    # Task 1: Load config
    t1 = comm.task_start("load_config", "Loading configuration")
    comm.message("Reading config files", MessageLevel.DEBUG, detail="/path/to/config.yaml")
    time.sleep(0.3)
    comm.task_end(t1, success=True)
    
    # Task 2: Validate
    t2 = comm.task_start("validate", "Validating parameters")
    comm.message("Checking param ranges", MessageLevel.DEBUG)
    time.sleep(0.3)
    comm.task_end(t2, success=True)
    
    # Task 3: Generate
    t3 = comm.task_start("generate", "Generating runs", total_steps=10)
    for i in range(10):
        comm.task_progress(t3, step=i+1, message=f"run_{i:03d}")
        time.sleep(0.1)
    comm.task_end(t3, success=True, result={"runs": 10})
    
    # Summary
    comm.summary(stats={"Total runs": 10, "Config files": 3})


def example_task_with_error():
    """Example: Task that fails."""
    
    comm = Communicator("example_exp", "demo")
    comm.header("Error Handling", "Task failure example")
    
    # Successful task
    t1 = comm.task_start("task_ok", "Task that succeeds")
    time.sleep(0.3)
    comm.task_end(t1, success=True)
    
    # Failed task
    t2 = comm.task_start("task_fail", "Task that fails")
    comm.message("Processing...", MessageLevel.INFO)
    time.sleep(0.3)
    comm.message("Error encountered!", MessageLevel.ERROR, detail="FileNotFoundError: missing.txt")
    comm.task_end(t2, success=False, error="File not found: missing.txt")
    
    # Summary showing failures
    comm.summary()


def example_validation():
    """Example: Using validation table."""
    
    comm = Communicator("example_exp", "demo")
    comm.header("Validation Example", "Configuration checks")
    
    # Define validation checks
    checks = [
        ("Config file exists", True, "config.yaml found"),
        ("Parameter ranges valid", True, "All params in range"),
        ("Templates available", True, "5 templates found"),
        ("Dependencies installed", False, "Missing: numpy>=1.20"),
        ("Disk space sufficient", True, "50GB available"),
    ]
    
    # Display validation table (outputs to both terminal and logs)
    comm.validation_table(checks)
    
    # Check results
    all_passed = all(passed for _, passed, _ in checks)
    if all_passed:
        comm.message("All checks passed", MessageLevel.SUCCESS)
    else:
        comm.message("Some checks failed", MessageLevel.WARNING)


def example_progress_tracking():
    """Example: Detailed progress tracking with steps."""
    
    comm = Communicator("example_exp", "analysis")
    comm.header("Analysis with Progress", "100 runs to process")
    
    # Analysis task with many steps
    total_runs = 100
    task = comm.task_start(
        "analyze_runs",
        "Analyzing simulation runs",
        total_steps=total_runs
    )
    
    for i in range(total_runs):
        run_name = f"run_{i:03d}"
        
        # Detailed work (logged but not shown on terminal)
        comm.message(
            f"Loading VAR files for {run_name}",
            level=MessageLevel.DEBUG,
            detail=f"/path/to/{run_name}/VAR*",
            terminal=False  # Only logs, not terminal
        )
        
        comm.message(
            f"Computing L1 norm for {run_name}",
            level=MessageLevel.DEBUG,
            detail="Using numerical integration",
            terminal=False
        )
        
        # Progress update (shows on terminal)
        comm.task_progress(task, step=i+1, message=run_name)
        
        time.sleep(0.02)  # Simulate work
    
    comm.task_end(task, success=True, result={"best_l1": 0.0234})
    
    # Summary with statistics
    comm.summary(stats={
        "Best L1 error": 0.0234,
        "Best L2 error": 0.0456,
        "Avg time/run": "2.3s"
    })


def example_generation_workflow():
    """Example: Complete generation workflow."""
    
    comm = Communicator("shocktube_phase1", "generation")
    comm.header("Run Generation", "shocktube_phase1")
    
    # Task 1: Validate config
    t1 = comm.task_start("validate_config", "Validating configuration")
    
    checks = [
        ("sweep.yaml", True, "Found"),
        ("templates", True, "All present"),
        ("param ranges", True, "Valid"),
    ]
    comm.validation_table(checks)
    comm.task_end(t1, success=True)
    
    # Task 2: Generate runs
    t2 = comm.task_start("generate_runs", "Generating run directories", total_steps=50)
    for i in range(50):
        comm.message(
            f"Creating run_{i:03d}",
            level=MessageLevel.DEBUG,
            detail=f"With params: nu={0.1*i}, chi={0.2*i}",
            terminal=False
        )
        comm.task_progress(t2, step=i+1, message=f"run_{i:03d}")
        time.sleep(0.05)
    comm.task_end(t2, success=True, result={"runs_created": 50})
    
    # Task 3: Create submission script
    t3 = comm.task_start("create_submit", "Creating sbatch script")
    time.sleep(0.5)
    comm.task_end(t3, success=True)
    
    # Summary
    comm.summary(stats={
        "Total runs": 50,
        "Branches": 5,
        "Submit script": "runs/shocktube_phase1/submit.sh"
    })


def example_analysis_workflow():
    """Example: Complete analysis workflow."""
    
    comm = Communicator("shocktube_phase1", "analysis")
    comm.header("Analysis Pipeline", "Error evolution videos")
    
    # Task 1: Load data
    t1 = comm.task_start("load_data", "Loading simulation data", total_steps=50)
    for i in range(50):
        comm.task_progress(t1, step=i+1, message=f"run_{i:03d}")
        time.sleep(0.02)
    comm.task_end(t1, success=True)
    
    # Task 2: Compute errors
    t2 = comm.task_start("compute_errors", "Computing error metrics", total_steps=50)
    for i in range(50):
        comm.message(
            f"Computing metrics for run_{i:03d}",
            level=MessageLevel.DEBUG,
            detail="L1, L2, Linf norms",
            terminal=False
        )
        comm.task_progress(t2, step=i+1, message=f"run_{i:03d}")
        time.sleep(0.02)
    comm.task_end(t2, success=True)
    
    # Task 3: Create videos
    t3 = comm.task_start("create_videos", "Generating error evolution videos")
    time.sleep(1)
    comm.task_end(t3, success=True)
    
    # Summary with results
    comm.summary(stats={
        "Runs analyzed": 50,
        "Best performer": "run_023",
        "Best L1 error": 0.0123,
        "Videos created": 5
    })


if __name__ == "__main__":
    """Run all examples."""
    
    print("\n" + "="*72)
    print("COMMUNICATOR EXAMPLES")
    print("Unified interface: Task → Communicator → [Terminal, Logs]")
    print("="*72 + "\n")
    
    examples = [
        ("Simple Task", example_simple_task),
        ("Multiple Tasks", example_multiple_tasks),
        ("Error Handling", example_task_with_error),
        ("Validation", example_validation),
        ("Progress Tracking", example_progress_tracking),
        ("Generation Workflow", example_generation_workflow),
        ("Analysis Workflow", example_analysis_workflow),
    ]
    
    for name, func in examples:
        print(f"\n{'='*72}")
        print(f"Example: {name}")
        print(f"{'='*72}")
        func()
        input("\nPress Enter for next example...")
    
    print("\n" + "="*72)
    print("All examples complete!")
    print("Check logs/ directory for detailed log files")
    print("="*72)

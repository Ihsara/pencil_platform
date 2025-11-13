# main.py

import argparse
import sys
from pathlib import Path
from loguru import logger

# Import logic from the src directory
from src.experiment.generator import run_suite
from src.workflows.analysis_pipeline import visualize_suite, analyze_suite_videos_only, analyze_suite_with_error_norms
from src.experiment.job_manager import submit_suite, check_suite_status, wait_for_completion, monitor_job_progress, clean_all_simulation_data
from src.core.constants import DIRS, FILES

def configure_logging():
    """Configures the loguru logger for clean, formatted output."""
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")

def find_available_experiments() -> list:
    """Scans the configuration directory to find all available experiments."""
    plan_glob = DIRS.config.glob(f"*/{DIRS.plan_subdir}/{FILES.plan}")
    return sorted([p.parent.parent.name for p in plan_glob])

def main():
    """Main entry point for the script."""
    configure_logging()
    
    # Detect if running from Windows - warn user
    import platform
    if platform.system() == "Windows":
        logger.warning("=" * 70)
        logger.warning("⚠️  DETECTED: Running from Windows")
        logger.warning("=" * 70)
        logger.warning("This platform is designed to run ON the HPC system (Mahti).")
        logger.warning("Running from Windows will cause monitoring to show incorrect status.")
        logger.warning("")
        logger.warning("RECOMMENDED: SSH to Mahti and run commands there:")
        logger.warning("  1. ssh mahti.csc.fi")
        logger.warning("  2. cd /scratch/project_2008296/chau/pencil_platform")
        logger.warning("  3. python main.py <experiment> [options]")
        logger.warning("")
        logger.warning("See docs/IMPORTANT-RUN-ON-HPC.md for details.")
        logger.warning("=" * 70)
        logger.warning("")

    parser = argparse.ArgumentParser(
        description="Pencil Code Experiment Suite Generator and Manager.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("experiment_name", nargs='?', default=None, type=str, 
                       help="The name of the experiment to generate.")
    parser.add_argument("--test", nargs='?', const=2, type=int, default=None, 
                       help="Enable test mode. Generates a limited number of runs without submitting.")
    parser.add_argument("-a", "--analyze", action="store_true", 
                       help="Run video-only analysis: creates individual error evolution videos and overlay comparisons for branches and top performers.")
    parser.add_argument("--error-norms", action="store_true",
                       help="Run L1/L2 error norm analysis: calculates L1, L2, L∞ metrics with combined scoring to find best parameters. Results saved to 'error_norms' subfolder.")
    parser.add_argument("--viz", nargs='*', default=None,
                       help="Visualize experiment results. Usage: --viz (all runs), --viz run1 run2 (specific runs), --viz ? (interactive)")
    parser.add_argument("--var", type=str, default=None,
                       help="Select specific VAR file for visualization. Options: 'middle' (default), 'random', 'last', 'first', or specific like 'VAR5'")
    parser.add_argument("--rebuild", action="store_true", 
                       help="Forcefully rebuild the executables in each new run directory.")
    parser.add_argument("--check", action="store_true", 
                       help="Check the status of the last submitted job for an experiment.")
    parser.add_argument("-m", "--monitor", action="store_true",
                       help="Monitor detailed progress of running jobs by examining log files. Shows current stage (build/start/run) and iteration counts.")
    parser.add_argument("-w", "--wait", action="store_true",
                       help="Wait for job completion. Can be combined: -mwa = submit + wait + analyze.")
    parser.add_argument("--cleanall", action="store_true",
                       help="Clean all simulation data (VAR files, logs) after completion. Can be used with -w: -w --cleanall = wait then clean.")
    
    args = parser.parse_args()
    experiment_name = args.experiment_name
    available_experiments = find_available_experiments()

    if not available_experiments:
        logger.error(f"No experiment plans found in '{DIRS.config}/*/{DIRS.plan_subdir}/{FILES.plan}'.")
        sys.exit(1)

    if not experiment_name:
        logger.info("Available experiments:")
        for i, name in enumerate(available_experiments):
            print(f"  {i+1}: {name}")
        try:
            choice = int(input("Please choose an experiment number: ")) - 1
            if 0 <= choice < len(available_experiments):
                experiment_name = available_experiments[choice]
            else:
                logger.error("Invalid selection."); sys.exit(1)
        except (ValueError, IndexError):
            logger.error("Invalid input."); sys.exit(1)
        except KeyboardInterrupt:
            logger.info("\nOperation cancelled."); sys.exit(0)

    if experiment_name not in available_experiments:
        logger.error(f"Experiment '{experiment_name}' not found."); sys.exit(1)
        
    logger.info(f"Selected experiment: '{experiment_name}'")
    
    try:
        # Check for standalone monitoring/analysis modes (no submission)
        if args.check:
            check_suite_status(experiment_name)
        elif args.monitor and not args.wait and not args.analyze:
            # Monitor only (standalone)
            monitor_job_progress(experiment_name, show_details=True)
        elif args.wait and not any([args.monitor, args.analyze, args.viz, args.error_norms]):
            # Wait only (for already-submitted job, standalone)
            # Step 0: Cleanup OLD data FIRST before waiting
            logger.info("Cleaning up old simulation data before waiting for new results...")
            clean_all_simulation_data(experiment_name, auto_confirm=True)
            
            if wait_for_completion(experiment_name):
                # Step 1: Run verification checks on the NEW data
                from rich.console import Console
                console = Console()
                console.print("\n[cyan]═══ MANDATORY INTEGRITY VERIFICATION ═══[/cyan]")
                console.print("[dim]This check is required to ensure simulation validity[/dim]\n")
                
                from src.experiment.verification import verify_simulation_integrity
                try:
                    integrity_passed = verify_simulation_integrity(
                        experiment_name, 
                        sample_size=3, 
                        fail_on_critical=False
                    )
                    if not integrity_passed:
                        console.print("\n[bold red]⚠ CRITICAL: Integrity checks FAILED![/bold red]")
                        console.print("[yellow]Please fix simulation issues before proceeding to analysis![/yellow]\n")
                        sys.exit(1)
                    else:
                        console.print("\n[bold green]✓ All integrity checks PASSED![/bold green]\n")
                except Exception as e:
                    logger.error(f"Integrity verification encountered an error: {e}")
                    console.print("\n[bold red]⚠ Integrity verification failed with error[/bold red]")
                    sys.exit(1)
                
                logger.success("Job completed! You can now run analysis or visualization.")
                logger.info(f"Analysis: python main.py {experiment_name} --analyze")
                logger.info(f"Visualization: python main.py {experiment_name} --viz")
            else:
                logger.error("Job did not complete successfully")
                sys.exit(1)
        elif args.wait and args.analyze and not any([args.viz, args.error_norms]):
            # Wait + Analyze (for already-submitted job)
            # Step 0: Cleanup OLD data FIRST before waiting
            logger.info("Cleaning up old simulation data before waiting for new results...")
            clean_all_simulation_data(experiment_name, auto_confirm=True)
            
            if wait_for_completion(experiment_name):
                # Step 1: Run verification checks on the NEW data
                from rich.console import Console
                console = Console()
                console.print("\n[cyan]═══ MANDATORY INTEGRITY VERIFICATION ═══[/cyan]")
                console.print("[dim]This check is required to ensure simulation validity[/dim]\n")
                
                from src.experiment.verification import verify_simulation_integrity
                try:
                    integrity_passed = verify_simulation_integrity(
                        experiment_name, 
                        sample_size=3, 
                        fail_on_critical=False
                    )
                    if not integrity_passed:
                        console.print("\n[bold red]⚠ CRITICAL: Integrity checks FAILED![/bold red]")
                        console.print("[yellow]Please fix simulation issues before proceeding to analysis![/yellow]\n")
                        sys.exit(1)
                    else:
                        console.print("\n[bold green]✓ All integrity checks PASSED![/bold green]\n")
                except Exception as e:
                    logger.error(f"Integrity verification encountered an error: {e}")
                    console.print("\n[bold red]⚠ Integrity verification failed with error[/bold red]")
                    sys.exit(1)
                
                # Step 2: Analysis
                logger.info("Starting video-only analysis...")
                analyze_suite_videos_only(experiment_name)
            else:
                logger.error("Job did not complete successfully")
                sys.exit(1)
        elif args.cleanall:
            # Standalone cleanall (without waiting)
            logger.info("--- CLEANUP MODE ---")
            clean_all_simulation_data(experiment_name)
        elif args.error_norms:
            logger.info("--- L1/L2 ERROR NORM ANALYSIS MODE ---")
            analyze_suite_with_error_norms(experiment_name)
        elif args.analyze and not args.wait:
            # Analyze only (standalone)
            logger.info("--- VIDEO-ONLY ANALYSIS MODE ---")
            analyze_suite_videos_only(experiment_name, combined_video=True)
        elif args.viz is not None:
            logger.info("--- VISUALIZATION MODE ---")
            
            # Handle interactive mode
            if args.viz and args.viz[0] == '?':
                # Load manifest to show available runs
                manifest_file = DIRS.runs / experiment_name / FILES.manifest
                if manifest_file.exists():
                    with open(manifest_file, 'r') as f:
                        available_runs = [line.strip() for line in f if line.strip()]
                    
                    logger.info(f"Available runs ({len(available_runs)}):")
                    for i, run in enumerate(available_runs, 1):
                        print(f"  {i}: {run}")
                    
                    print("\nVisualization options:")
                    print("  - Press Enter to visualize all runs")
                    print("  - Enter run numbers (e.g., '1 3 5') to visualize specific runs")
                    print("  - Enter branch name to visualize all runs in that branch")
                    
                    try:
                        choice = input("Your choice: ").strip()
                        if not choice:
                            # Visualize all
                            specific_runs = None
                        elif choice.isdigit() or ' ' in choice:
                            # Specific run numbers
                            indices = [int(x)-1 for x in choice.split()]
                            specific_runs = [available_runs[i] for i in indices if 0 <= i < len(available_runs)]
                        else:
                            # Branch name
                            specific_runs = [r for r in available_runs if choice in r]
                            if not specific_runs:
                                logger.warning(f"No runs found matching '{choice}'")
                                specific_runs = None
                    except (ValueError, IndexError, KeyboardInterrupt) as e:
                        logger.error(f"Invalid selection: {e}")
                        sys.exit(1)
                else:
                    logger.error(f"Manifest file not found: {manifest_file}")
                    sys.exit(1)
            elif args.viz:
                # Specific runs provided
                specific_runs = args.viz
            else:
                # No arguments, visualize all
                specific_runs = None
            
            visualize_suite(experiment_name, specific_runs=specific_runs, var_selection=args.var)
        else:
            logger.info("--- GENERATION & SUBMISSION MODE ---")
            plan_file = DIRS.config / experiment_name / DIRS.plan_subdir / FILES.plan
            
            # Check for auto-postprocessing flags
            import yaml
            with open(plan_file, 'r') as f:
                plan_config = yaml.safe_load(f)
            
            submit_script_path, plan = run_suite(plan_file=plan_file, limit=args.test, rebuild=args.rebuild)
            
            if not args.test and submit_script_path:
                submit_suite(experiment_name, submit_script_path, plan)
                
                # Check for auto_check and auto_postprocessing flags
                auto_check = plan_config.get('auto_check', False)
                auto_postprocessing = plan_config.get('auto_postprocessing', False)
                
                if auto_check:
                    logger.info("Auto-check enabled, checking job status...")
                    check_suite_status(experiment_name)
                
                # Handle -w (wait) flag in submission mode
                if args.wait:
                    # Step 0: Cleanup OLD data FIRST before waiting
                    logger.info("Cleaning up old simulation data before waiting for new results...")
                    clean_all_simulation_data(experiment_name, auto_confirm=True)
                    
                    logger.info("Waiting for job completion...")
                    if args.monitor:
                        logger.info("(Monitoring enabled - detailed progress will be shown)")
                    
                    if wait_for_completion(experiment_name):
                        # Step 1: Run verification checks on the NEW data
                        from rich.console import Console
                        console = Console()
                        console.print("\n[cyan]═══ MANDATORY INTEGRITY VERIFICATION ═══[/cyan]")
                        console.print("[dim]This check is required to ensure simulation validity[/dim]\n")
                        
                        from src.experiment.verification import verify_simulation_integrity
                        try:
                            integrity_passed = verify_simulation_integrity(
                                experiment_name, 
                                sample_size=3, 
                                fail_on_critical=False
                            )
                            if not integrity_passed:
                                console.print("\n[bold red]⚠ CRITICAL: Integrity checks FAILED![/bold red]")
                                console.print("[yellow]Please fix simulation issues before proceeding to analysis![/yellow]\n")
                                sys.exit(1)
                            else:
                                console.print("\n[bold green]✓ All integrity checks PASSED![/bold green]\n")
                        except Exception as e:
                            logger.error(f"Integrity verification encountered an error: {e}")
                            console.print("\n[bold red]⚠ Integrity verification failed with error[/bold red]")
                            sys.exit(1)
                        
                        # Step 2: Analysis (if requested)
                        if args.analyze:
                            logger.info("Starting video-only analysis...")
                            analyze_suite_videos_only(experiment_name)
                    else:
                        logger.error("Job did not complete successfully")
                        sys.exit(1)
                elif auto_postprocessing:
                    logger.info("Auto-postprocessing enabled.")
                    logger.info("Note: Postprocessing should be run after jobs complete.")
                    logger.info("To run analysis: python main.py {} --analyze".format(experiment_name))
                    logger.info("To run visualization: python main.py {} --viz".format(experiment_name))
            elif args.test:
                logger.warning("TEST MODE: Automatic submission is SKIPPED.")

    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

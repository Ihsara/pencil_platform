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
from src.core.communication.logging import setup_console_logging
from src.core.display import show_header, show_warning, show_error, show_info, show_success

def configure_logging():
    """Configure console-only logging for interactive mode."""
    setup_console_logging()

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
        from rich.console import Console
        from rich.panel import Panel
        console = Console(width=72)
        
        warning_text = (
            "[yellow]⚠️  Running from Windows[/yellow]\n\n"
            "This platform is designed for HPC (Mahti).\n"
            "Monitoring will show incorrect status.\n\n"
            "[cyan]RECOMMENDED:[/cyan]\n"
            "  1. ssh mahti.csc.fi\n"
            "  2. cd /scratch/project_2008296/chau/pencil_platform\n"
            "  3. python main.py <experiment> [options]\n\n"
            "See docs/IMPORTANT-RUN-ON-HPC.md"
        )
        console.print(Panel(warning_text, title="Platform Warning", border_style="yellow"))
        console.print()
        logger.warning("Running from Windows - monitoring may be unreliable")

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
        show_error(f"No plans found in {DIRS.config}/*/{DIRS.plan_subdir}/")
        sys.exit(1)

    if not experiment_name:
        from rich.console import Console
        console = Console(width=72)
        console.print("[cyan]Available experiments:[/cyan]")
        for i, name in enumerate(available_experiments):
            console.print(f"  {i+1}. {name}")
        
        try:
            choice = int(input("\nSelect number: ")) - 1
            if 0 <= choice < len(available_experiments):
                experiment_name = available_experiments[choice]
            else:
                show_error("Invalid selection")
                sys.exit(1)
        except (ValueError, IndexError):
            show_error("Invalid input")
            sys.exit(1)
        except KeyboardInterrupt:
            show_info("Operation cancelled")
            sys.exit(0)

    if experiment_name not in available_experiments:
        show_error(f"Experiment '{experiment_name}' not found")
        sys.exit(1)
    
    show_info(f"Selected: {experiment_name}")
    logger.info(f"Selected experiment: {experiment_name}")
    
    try:
        # Check for standalone monitoring/analysis modes
        if args.check:
            show_header("Status Check", experiment_name)
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
                console = Console(width=72)
                console.print("\n[cyan]═══ INTEGRITY VERIFICATION ═══[/cyan]")
                console.print("[dim]Required to ensure simulation validity[/dim]\n")
                
                from src.experiment.verification import verify_simulation_integrity
                try:
                    integrity_passed = verify_simulation_integrity(
                        experiment_name, 
                        sample_size=3, 
                        fail_on_critical=False
                    )
                    if not integrity_passed:
                        show_error("CRITICAL: Integrity checks FAILED!")
                        show_warning("Fix issues before proceeding")
                        sys.exit(1)
                    else:
                        show_success("All integrity checks PASSED")
                except Exception as e:
                    logger.error(f"Verification error: {e}")
                    show_error("Integrity verification failed")
                    sys.exit(1)
                
                show_success("Job completed")
                show_info(f"Next: python main.py {experiment_name} --analyze")
            else:
                logger.error("Job did not complete successfully")
                sys.exit(1)
        elif args.wait and args.analyze and not any([args.viz, args.error_norms]):
            # Wait + Analyze
            show_info("Cleaning up old data...")
            clean_all_simulation_data(experiment_name, auto_confirm=True)
            
            if wait_for_completion(experiment_name):
                # Step 1: Verification checks
                from rich.console import Console
                console = Console(width=72)
                console.print("\n[cyan]═══ INTEGRITY VERIFICATION ═══[/cyan]")
                console.print("[dim]Required for simulation validity[/dim]\n")
                
                from src.experiment.verification import verify_simulation_integrity
                try:
                    integrity_passed = verify_simulation_integrity(
                        experiment_name, 
                        sample_size=3, 
                        fail_on_critical=False
                    )
                    if not integrity_passed:
                        show_error("CRITICAL: Integrity checks FAILED!")
                        sys.exit(1)
                    else:
                        show_success("All integrity checks PASSED")
                except Exception as e:
                    logger.error(f"Verification error: {e}")
                    show_error("Integrity verification failed")
                    sys.exit(1)
                
                # Step 2: Analysis
                show_header("Analysis Pipeline", experiment_name)
                analyze_suite_videos_only(experiment_name)
            else:
                show_error("Job did not complete")
                sys.exit(1)
        elif args.cleanall:
            show_header("Cleanup Mode", experiment_name)
            clean_all_simulation_data(experiment_name)
        elif args.error_norms:
            show_header("Error Norm Analysis", experiment_name)
            analyze_suite_with_error_norms(experiment_name)
        elif args.analyze and not args.wait:
            show_header("Video Analysis", experiment_name)
            analyze_suite_videos_only(experiment_name, combined_video=True)
        elif args.viz is not None:
            show_header("Visualization", experiment_name)
            
            # Handle interactive mode
            if args.viz and args.viz[0] == '?':
                # Load manifest to show available runs
                manifest_file = DIRS.runs / experiment_name / FILES.manifest
                if manifest_file.exists():
                    with open(manifest_file, 'r') as f:
                        available_runs = [line.strip() for line in f if line.strip()]
                    
                    from rich.console import Console
                    console = Console(width=72)
                    console.print(f"[cyan]Available runs ({len(available_runs)}):[/cyan]")
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
                                show_warning(f"No runs matching '{choice}'")
                                specific_runs = None
                    except (ValueError, IndexError, KeyboardInterrupt) as e:
                        show_error(f"Invalid selection: {e}")
                        sys.exit(1)
                else:
                    show_error(f"Manifest not found: {manifest_file}")
                    sys.exit(1)
            elif args.viz:
                # Specific runs provided
                specific_runs = args.viz
            else:
                # No arguments, visualize all
                specific_runs = None
            
            visualize_suite(experiment_name, specific_runs=specific_runs, var_selection=args.var)
        else:
            show_header("Generation & Submission", experiment_name)
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
                    show_info("Auto-check enabled")
                    check_suite_status(experiment_name)
                
                # Handle wait flag in submission mode
                if args.wait:
                    show_info("Cleaning up old data...")
                    clean_all_simulation_data(experiment_name, auto_confirm=True)
                    
                    show_info("Waiting for job completion...")
                    if args.monitor:
                        show_info("(Monitoring enabled)")
                    
                    if wait_for_completion(experiment_name):
                        # Verification checks
                        from rich.console import Console
                        console = Console(width=72)
                        console.print("\n[cyan]═══ INTEGRITY VERIFICATION ═══[/cyan]")
                        console.print("[dim]Required for simulation validity[/dim]\n")
                        
                        from src.experiment.verification import verify_simulation_integrity
                        try:
                            integrity_passed = verify_simulation_integrity(
                                experiment_name, 
                                sample_size=3, 
                                fail_on_critical=False
                            )
                            if not integrity_passed:
                                show_error("CRITICAL: Checks FAILED!")
                                sys.exit(1)
                            else:
                                show_success("All checks PASSED")
                        except Exception as e:
                            logger.error(f"Verification error: {e}")
                            show_error("Verification failed")
                            sys.exit(1)
                        
                        # Analysis if requested
                        if args.analyze:
                            show_header("Analysis Pipeline", experiment_name)
                            analyze_suite_videos_only(experiment_name)
                    else:
                        show_error("Job did not complete")
                        sys.exit(1)
                elif auto_postprocessing:
                    show_info("Auto-postprocessing enabled")
                    show_info(f"Run after: python main.py {experiment_name} --analyze")
            elif args.test:
                show_warning("TEST MODE: Submission skipped")

    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

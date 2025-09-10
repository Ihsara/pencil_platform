# main.py

import argparse
import sys
from pathlib import Path
from loguru import logger

# Import logic from the src directory
from src.suite_generator import run_suite
from src.post_processing import analyze_suite
from src.job_manager import submit_suite, check_suite_status
from src.constants import DIRS, FILES

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

    parser = argparse.ArgumentParser(
        description="Pencil Code Experiment Suite Generator and Manager.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("experiment_name", nargs='?', default=None, type=str, help="The name of the experiment to generate.")
    parser.add_argument("--test", nargs='?', const=2, type=int, default=None, help="Enable test mode. Generates a limited number of runs without submitting.")
    parser.add_argument("--analyze", action="store_true", help="Run post-processing analysis and generate comparison plots.")
    parser.add_argument("--rebuild", action="store_true", help="Forcefully rebuild the executables in each new run directory.")
    parser.add_argument("--check", action="store_true", help="Check the status of the last submitted job for an experiment.")
    
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
        if args.check:
            check_suite_status(experiment_name)
        elif args.analyze:
            logger.info("--- ANALYSIS & COMPARISON MODE ---")
            analyze_suite(experiment_name)
        else:
            logger.info("--- GENERATION & SUBMISSION MODE ---")
            plan_file = DIRS.config / experiment_name / DIRS.plan_subdir / FILES.plan
            submit_script_path, plan = run_suite(plan_file=plan_file, limit=args.test, rebuild=args.rebuild)
            
            if not args.test and submit_script_path:
                submit_suite(experiment_name, submit_script_path, plan)
            elif args.test:
                 logger.warning("TEST MODE: Automatic submission is SKIPPED.")

    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
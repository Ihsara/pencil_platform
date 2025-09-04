# main.py

import argparse
import sys
from pathlib import Path
from loguru import logger

# Import shared logic and constants from the 'src' directory
from src.suite_generator import run_suite
from src.constants import DIRS, FILES
from src.post_processing import analyze_suite

def configure_logging():
    """Configures the loguru logger for clean, formatted output."""
    logger.remove()  # Remove the default, unformatted handler
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
    )

def find_available_experiments() -> list:
    """
    Scans the configuration directory to find all available experiments
    that have a valid plan file.
    """
    plan_glob = DIRS.config.glob(f"*/{DIRS.plan_subdir}/{FILES.plan}")
    # The experiment name is the parent directory of the 'plan' subdirectory
    return sorted([p.parent.parent.name for p in plan_glob])

def main():
    """
    Main entry point for the script. Handles command-line arguments,
    interactive experiment selection, and orchestrates the suite generation.
    """
    configure_logging()

    parser = argparse.ArgumentParser(
        description="Pencil Code Experiment Suite Generator. "
                    "Run without arguments for an interactive selection menu.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "experiment_name",
        nargs='?',  # The '?' makes the argument optional
        default=None,
        type=str,
        help="The name of the experiment to generate (e.g., 'shocktube_phase1')."
    )
    parser.add_argument(
        "--test",
        nargs='?',
        const=2,  # Default value if --test is provided with no number
        type=int,
        default=None,
        help="Enable test mode. Generates a limited number of runs.\n"
             "  --test    (generates 2 runs)\n"
             "  --test 5  (generates 5 runs)"
    )

    parser.add_argument(
        "--analyze", action="store_true",
        help="Run post-processing analysis on an existing experiment suite."
    )    
    
    args = parser.parse_args()

    experiment_name = args.experiment_name
    available_experiments = find_available_experiments()

    if not available_experiments:
        logger.error(f"No experiment plans found in '{DIRS.config}/*/{DIRS.plan_subdir}/{FILES.plan}'.")
        sys.exit(1)

    # --- Interactive Mode: Triggered if no experiment_name is provided ---
    if not experiment_name:
        logger.info("Available experiments:")
        for i, name in enumerate(available_experiments):
            print(f"  {i+1}: {name}")
        
        try:
            choice_str = input("Please choose an experiment number: ")
            choice = int(choice_str) - 1
            if 0 <= choice < len(available_experiments):
                experiment_name = available_experiments[choice]
            else:
                logger.error(f"Invalid selection. Please choose a number between 1 and {len(available_experiments)}.")
                sys.exit(1)
        except (ValueError, IndexError):
            logger.error("Invalid input. Please enter a valid number.")
            sys.exit(1)
        except KeyboardInterrupt:
            logger.info("\nOperation cancelled by user.")
            sys.exit(0)

    # --- Execution Logic ---
    if experiment_name not in available_experiments:
        logger.error(f"Experiment '{experiment_name}' not found.")
        logger.info(f"Available experiments are: {', '.join(available_experiments)}")
        sys.exit(1)
    
    plan_file = DIRS.config / experiment_name / DIRS.plan_subdir / FILES.plan
    if not plan_file.exists():
        logger.error(f"Plan file not found for experiment '{experiment_name}' at '{plan_file}'")
        sys.exit(1)
        
    if args.analyze:
            logger.info(f"--- ANALYSIS MODE ---")
            analyze_suite(experiment_name=experiment_name)
            logger.success(f"Analysis for '{experiment_name}' finished.")
    else:
        logger.info(f"--- GENERATION MODE ---")
        run_suite(plan_file=plan_file, limit=args.test)
        logger.success(f"Suite generation for '{experiment_name}' finished successfully.")        

    logger.info(f"Selected experiment: '{experiment_name}'")
    
    try:
        # Call the core logic, passing the plan file and the test limit
        run_suite(plan_file=plan_file, limit=args.test)
        
    except Exception as e:
        # Catch any unexpected errors from the generator for a clean exit
        logger.exception(f"An unexpected error occurred during suite generation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
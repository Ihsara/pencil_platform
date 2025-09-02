# Snakefile
#
# This workflow orchestrates the generation of Pencil Code experiment suites.
# It is designed to be equivalent to main.py, sharing the same core logic.
#
# USAGE:
# snakemake --config experiment_name=<your_experiment> -c1
#
# Example for a dry-run:
# snakemake -n --config experiment_name=shocktube
#

import yaml
from pathlib import Path
from src.constants import DIRS, FILES
from src.suite_generator import run_suite

# --- 1. CONFIGURATION ---
# Get the target experiment name from the command line configuration.
# Default to 'shocktube' if not provided (useful for testing).
EXPERIMENT_NAME = config.get("experiment_name", "shocktube")

# Define the primary input for the entire workflow: the plan file.
PLAN_FILE = DIRS.config / EXPERIMENT_NAME / DIRS.plan_subdir / FILES.plan

# --- 2. DEFINE THE FINAL GOAL ---
# The 'all' rule is the main entry point for Snakemake.
# It defines the final files we want the workflow to create.
# In this case, it's the main submission script for the entire suite.
rule all:
    input:
        DIRS.runs / EXPERIMENT_NAME / FILES.submit_script

# --- 3. THE GENERATION RULE ---
# This single rule is responsible for generating the entire experiment suite.
# It calls the shared logic from our Python source code.
rule generate_suite:
    input:
        # This rule depends on the plan file and the Python script that contains the logic.
        # If either of these files change, Snakemake will automatically re-run this rule.
        plan=PLAN_FILE,
        script=DIRS.src / "suite_generator.py",
        constants=DIRS.src / "constants.py"
    output:
        # The rule's output is the final submission script.
        # We also mark the entire directory as output to ensure it's created.
        script=DIRS.runs / EXPERIMENT_NAME / FILES.submit_script,
        manifest=DIRS.runs / EXPERIMENT_NAME / FILES.manifest,
        directory=directory(DIRS.runs / EXPERIMENT_NAME)
    params:
        # Pass necessary parameters to the 'run' block.
        plan_file=PLAN_FILE,
        project_root=DIRS.root
    run:
        # This block executes Python code.
        # It simply calls the centralized function that does all the work.
        # This ensures the Snakefile and main.py are always in sync.
        from loguru import logger

        logger.info(f"SNAKEMAKE: Executing suite generation for experiment '{EXPERIMENT_NAME}'...")
        
        # Call the shared logic
        run_suite(plan_file=Path(params.plan_file))
        
        logger.success(f"SNAKEMAKE: Suite generation for '{EXPERIMENT_NAME}' completed.")
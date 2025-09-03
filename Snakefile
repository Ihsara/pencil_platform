# Snakefile
#
# This workflow orchestrates the generation of Pencil Code experiment suites.
# It is designed to be equivalent to main.py by sharing the same core logic.
#
# USAGE (from the project root directory):
# snakemake --config experiment_name=<your_experiment> --cores 1
#
# Example for a dry-run of the shocktube test suite (2 runs):
# snakemake -n --config experiment_name=shocktube_phase1 limit=2
#

import yaml
import itertools
from pathlib import Path

# Import shared constants and the sweep logic helper
from src.constants import DIRS, FILES
from src.suite_generator import _generate_sweep_combinations

# --- 1. CONFIGURATION ---
# Get the target experiment name from the command line, defaulting to 'shocktube_phase1'.
EXPERIMENT_NAME = config.get("experiment_name", "shocktube_phase1")

# Construct the path to the plan file for the selected experiment.
PLAN_FILE = DIRS.config / EXPERIMENT_NAME / DIRS.plan_subdir / FILES.plan

# --- 2. DYNAMIC TARGET GENERATION ---
# This block is executed by Snakemake before it builds the dependency graph.
# It reads the plan file to determine all the final files that need to be created.
try:
    with open(PLAN_FILE, 'r') as f:
        plan = yaml.safe_load(f)
except FileNotFoundError:
    raise FileNotFoundError(f"FATAL: The plan file for experiment '{EXPERIMENT_NAME}' was not found at {PLAN_FILE}")

# Use the shared helper function to get all unique parameter sets.
ALL_PARAM_COMBINATIONS = _generate_sweep_combinations(plan)

# Generate the full list of unique run names based on the plan.
ALL_RUN_NAMES = []
for branch in plan.get('branches', [{'name': 'default'}]):
    for params in ALL_PARAM_COMBINATIONS:
        params_str = '_'.join([f"{k.split('_')[0]}{v}" for k, v in params.items()])
        run_name = f"{plan['output_prefix']}_{branch['name']}_{params_str}" if params_str else f"{plan['output_prefix']}_{branch['name']}"
        ALL_RUN_NAMES.append(run_name)

# --- 3. THE 'all' RULE ---
# This is the main entry point for Snakemake. It defines the final files
# that the entire workflow is expected to produce.
rule all:
    input:
        # The ultimate goal is the single submission script for the whole suite.
        DIRS.runs / EXPERIMENT_NAME / FILES.submit_script,
        # We also depend on the manifest file as a concrete output.
        DIRS.runs / EXPERIMENT_NAME / FILES.manifest

# --- 4. THE GENERATION RULE ---
# This single rule is responsible for generating the entire experiment suite.
# It calls the shared logic from our Python source code for maximum consistency.
rule generate_suite:
    input:
        # This rule depends on the plan file and the Python scripts that contain the logic.
        # If any of these files change, Snakemake will automatically re-run this rule.
        plan=PLAN_FILE,
        script=DIRS.src / "suite_generator.py",
        constants=DIRS.src / "constants.py"
    output:
        # Define all major outputs of the suite generation process.
        # The 'touch' creates a dummy file to signify that the rule has completed.
        script=touch(DIRS.runs / EXPERIMENT_NAME / FILES.submit_script),
        manifest=touch(DIRS.runs / EXPERIMENT_NAME / FILES.manifest),
        directory=directory(DIRS.runs / EXPERIMENT_NAME)
    params:
        # Pass necessary parameters to the 'run' block.
        plan_file=PLAN_FILE,
        # Allow passing a limit from the command line, e.g., --config limit=2
        limit=config.get("limit", None)
    run:
        # This block executes Python code. It imports and calls the centralized
        # run_suite function, ensuring the Snakefile and main.py are always in sync.
        from src.suite_generator import run_suite
        from loguru import logger
        
        logger.info(f"SNAKEMAKE: Executing suite generation for experiment '{EXPERIMENT_NAME}'...")
        
        # Call the shared logic, passing the plan file and the test limit.
        run_suite(plan_file=Path(params.plan_file), limit=params.limit)
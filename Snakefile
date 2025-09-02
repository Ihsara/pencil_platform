# Snakefile

import yaml
from pathlib import Path
from src.constants import DIRS, FILES
from src.suite_generator import run_suite # We will call this shared logic

# --- Configuration ---
EXPERIMENT_NAME = config.get("experiment_name", "shocktube")
LIMIT = config.get("limit", None) # Get limit from --config limit=N

PLAN_FILE = DIRS.config / EXPERIMENT_NAME / DIRS.plan_subdir / FILES.plan

# --- Rule Definition ---
rule all:
    input:
        # The final goal is always the submission script.
        DIRS.runs / EXPERIMENT_NAME / FILES.submit_script

rule generate_suite:
    input:
        plan=PLAN_FILE,
        script=DIRS.src / "suite_generator.py",
        constants=DIRS.src / "constants.py"
    output:
        # Touch a file to confirm completion
        touch(DIRS.runs / EXPERIMENT_NAME / ".generation_complete")
    params:
        plan_file=PLAN_FILE,
        limit=LIMIT
    run:
        # The Snakefile now calls the exact same function as main.py,
        # passing along the limit.
        logger.info(f"SNAKEMAKE: Executing suite generation for experiment '{EXPERIMENT_NAME}'...")
        run_suite(plan_file=Path(params.plan_file), limit=params.limit)
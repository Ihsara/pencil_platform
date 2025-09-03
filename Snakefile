# Snakefile

import yaml
import itertools
from pathlib import Path

# --- 1. CONFIGURATION AND DYNAMIC TARGET GENERATION ---
EXPERIMENT_NAME = config.get("experiment_name", "shocktube_phase1")
PLAN_FILE = f"config/{EXPERIMENT_NAME}/plan/sweep.yaml"
LIMIT = config.get("limit", None)

with open(PLAN_FILE, 'r') as f:
    plan = yaml.safe_load(f)

# (The Python logic to generate ALL_RUN_NAMES is the same as before)
def _generate_sweep_combinations(p):
    # ... (same logic)
    pass
ALL_PARAM_COMBINATIONS = _generate_sweep_combinations(plan)
# ... (same logic to generate ALL_RUN_NAMES) ...
if LIMIT:
    ALL_RUN_NAMES = ALL_RUN_NAMES[:LIMIT]

# --- 2. WORKFLOW RULES ---

# The 'all' rule defines the final desired output of the entire workflow.
rule all:
    input:
        # We want a log file from each simulation to prove it completed.
        expand("runs/{exp_name}/slurm_logs/{run_name}.log", exp_name=EXPERIMENT_NAME, run_name=ALL_RUN_NAMES)


# Rule to run a single simulation. Snakemake will run this rule for each unique run_name.
rule run_single_simulation:
    output:
        # The main output is the simulation log file, which proves the run happened.
        sim_log="runs/{exp_name}/generated_configs/{run_name}/simulation.log",
    log:
        # Snakemake will redirect stdout/stderr of the job to this file.
        slurm="runs/{exp_name}/slurm_logs/{run_name}.log"
    params:
        # Pass all necessary information to the script.
        run_name="{run_name}",
        hpc=plan['hpc'],
        config_dir="runs/{exp_name}/generated_configs/{run_name}",
        # Condense the multi-line build command into a single line for the shell script
        module_loads="; ".join(line.strip() for line in plan.get('build_command', '').strip().split('\n') if 'module' in line)
    resources:
        # These values are passed to the SLURM profile.
        account=plan['hpc']['sbatch']['account'],
        partition=plan['hpc']['sbatch']['partition'],
        time=plan['hpc']['sbatch']['time'],
        nodes=plan['hpc']['sbatch']['nodes'],
        ntasks=plan['hpc']['sbatch']['ntasks'],
        cpus_per_task=plan['hpc']['sbatch']['cpus_per_task']
    script:
        # This is the key to modularity. It executes the external script.
        "scripts/execute_simulation.sh"


# Rule to generate all the config files for the entire suite.
# This must be run before any of the simulation jobs.
localrule generate_all_configs:
    output:
        # This rule produces a dummy file to signal that config generation is complete.
        touch("runs/{exp_name}/.configs_generated")
    params:
        plan_file=PLAN_FILE,
        limit=LIMIT
    run:
        # It calls the shared Python logic.
        from src.suite_generator import run_suite
        run_suite(plan_file=Path(params.plan_file), limit=params.limit)
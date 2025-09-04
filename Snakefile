# Snakefile

import yaml
from pathlib import Path
from src.constants import DIRS, FILES
# Import both logic modules
from src.suite_generator import _generate_sweep_combinations
from src.post_processing import analyze_suite

# --- 1. CONFIGURATION AND DYNAMIC TARGET GENERATION ---
EXPERIMENT_NAME = config.get("experiment_name", "shocktube_phase1")
PLAN_FILE = DIRS.config / EXPERIMENT_NAME / DIRS.plan_subdir / FILES.plan
LIMIT = config.get("limit", None)

with open(PLAN_FILE, 'r') as f: plan = yaml.safe_load(f)
ALL_PARAM_COMBINATIONS = _generate_sweep_combinations(plan)

if LIMIT: ALL_RUN_NAMES = ALL_RUN_NAMES[:LIMIT]

# --- 2. WORKFLOW RULES ---

# The final goal: a summary plot that depends on all individual plots.
rule all:
    input:
        expand("reports/{exp_name}/{run_name}/density.png", exp_name=EXPERIMENT_NAME, run_name=ALL_RUN_NAMES),
        # expand("reports/{exp_name}/summary_plot.png", exp_name=EXPERIMENT_NAME) # Future goal

# Rule to analyze a single simulation and produce its plots.
rule analyze_single_run:
    input:
        # Depends on the run directory existing and a signal that the run is complete.
        run_dir=directory(f"runs/{EXPERIMENT_NAME}/generated_configs/{{run_name}}"),

    output:
        # Define the three plot files as the output.
        touch(f"reports/{EXPERIMENT_NAME}/{{run_name}}/density.png"),
        touch(f"reports/{EXPERIMENT_NAME}/{{run_name}}/velocity.png"),
        touch(f"reports/{EXPERIMENT_NAME}/{{run_name}}/pressure.png"),
    params:
        run_name="{run_name}",
        report_dir=f"reports/{EXPERIMENT_NAME}/{{run_name}}"
    log:
        f"logs/analysis/{EXPERIMENT_NAME}_{{run_name}}.log"
    run:
        # This block calls the modular analysis logic for a single run.
        from src.post_processing import load_simulation_data, get_analytical_solution, plot_simulation_vs_analytical
        
        sim_data = load_simulation_data(Path(input.run_dir))
        if sim_data:
            analytical_data = get_analytical_solution(sim_data['params'], sim_data['x'], sim_data['t'])
            if analytical_data:
                os.makedirs(params.report_dir, exist_ok=True)
                plot_simulation_vs_analytical(sim_data, analytical_data, Path(params.report_dir), params.run_name)

# Rule to generate all the config files for the entire suite.
localrule generate_all_configs:
    output:
        # This rule produces ALL the config files needed by the analysis rules.
        expand("runs/{exp_name}/generated_configs/{run_name}/start.in", exp_name=EXPERIMENT_NAME, run_name=ALL_RUN_NAMES),
    params:
        plan_file=PLAN_FILE,
        limit=LIMIT
    run:
        from src.suite_generator import run_suite
        run_suite(plan_file=Path(params.plan_file), limit=params.limit)
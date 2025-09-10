# src/suite_generator.py

import os
import yaml
import itertools
from pathlib import Path
from loguru import logger
from copy import deepcopy
import jinja2

from .constants import DIRS, FILES

def _generate_sweep_combinations(plan: dict) -> list:
    """
    Parses the 'parameter_sweeps' section of a plan and returns a list of
    all unique parameter combination dictionaries.
    """
    if 'parameter_sweeps' not in plan:
        return [{}]

    all_param_groups = []
    for sweep in plan.get('parameter_sweeps', []):
        if not sweep:
            continue
            
        sweep_type = sweep.get('type')
        group = []

        if sweep_type == 'linked':
            variables = sweep.get('variables', [])
            for value in sweep.get('values', []):
                group.append({var: value for var in variables})
            
        elif sweep_type == 'product':
            variable = sweep.get('variable')
            if variable:
                group = [{variable: value} for value in sweep.get('values', [])]
        
        else:
            logger.warning(f"Unknown sweep type '{sweep_type}' found in plan. Skipping.")
            continue
        
        if group:
            all_param_groups.append(group)

    final_combinations = []
    for combo_tuple in itertools.product(*all_param_groups):
        merged_dict = {}
        for d in combo_tuple:
            merged_dict.update(d)
        final_combinations.append(merged_dict)
        
    return final_combinations if final_combinations else [{}]

def generate_experiment_from_dict(experiment_name: str, config_data_map: dict, template_dir: Path, output_dir: Path):
    """
    Generates all config files for a single experiment run into its own subdirectory.
    """
    run_config_dir = output_dir / experiment_name
    os.makedirs(run_config_dir, exist_ok=True)
    
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir), trim_blocks=True, lstrip_blocks=True)

    for config_filename, config_content in config_data_map.items():
        output_filename = Path(config_filename).stem.replace('_', '.')
        template_format = config_content.get('format')
        template_data = config_content.get('data', {})

        if not template_format:
            logger.warning(f"No 'format' key in {config_filename} for run {experiment_name}, skipping.")
            continue

        template = env.get_template(f"{template_format}.j2")
        rendered_content = template.render(data=template_data, output_filename=output_filename)
        
        with open(run_config_dir / output_filename, 'w') as f:
            f.write(rendered_content)

def run_suite(plan_file: Path, limit: int = None, rebuild: bool = False):
    """
    Reads an experiment plan, generates all configurations and scripts.
    
    Returns:
        A tuple containing (path_to_submission_script, loaded_plan_dictionary).
    """
    logger.info(f"Loading experiment plan from: {plan_file}")
    with open(plan_file, 'r') as f:
        plan = yaml.safe_load(f)

    base_config_path = DIRS.config / plan['base_experiment'] / DIRS.in_subdir
    if not base_config_path.is_dir():
        logger.error(f"Base configuration directory not found: {base_config_path}")
        return None, None

    base_configs = {p.name: yaml.safe_load(p.read_text()) for p in base_config_path.glob("*.yaml")}
    
    all_runs = []
    all_param_combinations = _generate_sweep_combinations(plan)
    
    for branch in plan.get('branches', [{'name': 'default', 'settings': {}}]):
        for current_params in all_param_combinations:
            params_str = '_'.join([f"{k.replace('_shock', '')}{v}" for k, v in current_params.items()])
            run_name_parts = [plan['output_prefix'], branch['name']]
            if params_str: run_name_parts.append(params_str)
            run_name = '_'.join(run_name_parts)
            
            run_configs = deepcopy(base_configs)
            
            # --- START OF CORRECTED APPLICATION LOGIC ---

            # 1. Apply global modifications from the 'modifications' block
            for file_name, mods in plan.get('modifications', {}).items():
                if file_name in run_configs:
                    config_data = run_configs[file_name]['data']
                    for namelist, params in mods.items():
                        if namelist.endswith('_update'):
                            target_namelist = namelist.replace('_update', '')
                            if target_namelist in config_data:
                                config_data[target_namelist].update(params)
                        else:
                            if namelist in config_data:
                                for key, value in params.items():
                                    if value is None and key in config_data[namelist]:
                                        del config_data[namelist][key]

            # 2. Apply branch-specific settings
            for file_name, settings in branch.get('settings', {}).items():
                if file_name in run_configs:
                    config_data = run_configs[file_name]['data']
                    for namelist, params in settings.items():
                        if namelist in config_data:
                            config_data[namelist].update(params)

            # 3. Apply sweep-specific parameter values
            for param_key, param_value in current_params.items():
                # Find which namelist this parameter belongs to and update it
                for config_file in run_configs.values():
                    for namelist_data in config_file.get('data', {}).values():
                        if isinstance(namelist_data, dict) and param_key in namelist_data:
                            namelist_data[param_key] = param_value
            
            # --- END OF CORRECTED APPLICATION LOGIC ---

            all_runs.append({'name': run_name, 'configs': run_configs})

    if limit is not None and limit > 0:
        logger.warning(f"TEST MODE: Limiting generation to the first {limit} run(s).")
        all_runs = all_runs[:limit]

    plan['total_sims'] = len(all_runs)

    # --- Write all generated files locally ---
    experiment_name = plan_file.parent.parent.name
    local_exp_dir = DIRS.runs / experiment_name
    generated_configs_dir = local_exp_dir / "generated_configs"
    os.makedirs(local_exp_dir / "slurm_logs", exist_ok=True)
    
    for run in all_runs:
        generate_experiment_from_dict(
            experiment_name=run['name'],
            config_data_map=run['configs'],
            template_dir=DIRS.templates,
            output_dir=generated_configs_dir
        )
    logger.success(f"Generated config files for {len(all_runs)} run(s) in '{generated_configs_dir}'")

    manifest_path = local_exp_dir / FILES.manifest
    with open(manifest_path, 'w') as f:
        for run in all_runs:
            f.write(f"{run['name']}\n")
    logger.success(f"Generated run manifest at '{manifest_path}'")

    # --- Generate the main submission script ---
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(DIRS.templates))
    submit_template = env.get_template("sbatch_array.j2")
    
    hpc_config = plan.get('hpc', {})
    submit_script_content = submit_template.render(
        hpc=hpc_config,
        sbatch=hpc_config.get('sbatch', {}),
        run_base_dir=hpc_config.get('run_base_dir', 'runs'),
        manifest_file=FILES.manifest,
        num_jobs=len(all_runs),
        experiment_name=experiment_name,
        rebuild=rebuild,
        module_loads=hpc_config.get('module_loads', '')
    )
    
    submit_script_path = local_exp_dir / FILES.submit_script
    with open(submit_script_path, 'w') as f:
        f.write(submit_script_content)
    logger.success(f"Generated SLURM submission script at '{submit_script_path}'")

    # --- Summary Table ---
    branch_names = [b['name'] for b in plan.get('branches', [])]
    num_combinations = len(all_param_combinations)
    
    logger.info("--- Experiment Summary ---")
    summary_table = (
        f"  Branches: {', '.join(branch_names)} ({len(branch_names)})\n"
        f"  Parameter Combinations per Branch: {num_combinations}\n"
        f"  -----------------------------------\n"
        f"  Total Simulations to Generate: {len(all_runs)}"
    )
    print(summary_table)

    return submit_script_path, plan
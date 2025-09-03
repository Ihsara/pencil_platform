# src/suite_generator.py

import os
import yaml
import itertools
from pathlib import Path
from loguru import logger
from copy import deepcopy
import jinja2

# Import the centralized constants
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
        # ROBUSTNESS FIX: Skip any empty or malformed entries in the list
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

# NAMEERROR FIX: The missing helper function is now defined here.
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

def run_suite(plan_file: Path, limit: int = None):
    """
    Reads an experiment plan YAML and generates all specified run directories,
    configuration files, and a master submission script.
    """
    logger.info(f"Loading experiment plan from: {plan_file}")
    with open(plan_file, 'r') as f:
        plan = yaml.safe_load(f)

    base_config_path = DIRS.config / plan['base_experiment'] / DIRS.in_subdir
    if not base_config_path.is_dir():
        logger.error(f"Base configuration directory not found: {base_config_path}")
        return

    base_configs = {p.name: yaml.safe_load(p.read_text()) for p in base_config_path.glob("*.yaml")}
    
    all_runs = []
    all_param_combinations = _generate_sweep_combinations(plan)
    
    for branch in plan.get('branches', [{'name': 'default', 'settings': {}}]):
        for current_params in all_param_combinations:
            params_str = '_'.join([f"{k.split('_')[0]}{v}" for k, v in current_params.items()])
            run_name = f"{plan['output_prefix']}_{branch['name']}_{params_str}" if params_str else f"{plan['output_prefix']}_{branch['name']}"
            
            run_configs = deepcopy(base_configs)
            # Apply global modifications
            for file, settings in plan.get('modifications', {}).items():
                for namelist, params in settings.items():
                    for key, value in params.items():
                        if namelist.endswith('_update'):
                            clean_namelist = namelist.replace('_update', '')
                            if key in run_configs.get(file,{}).get('data',{}).get(clean_namelist,{}):
                                run_configs[file]['data'][clean_namelist][key] = value
                        elif value is None:
                            if key in run_configs.get(file,{}).get('data',{}).get(namelist,{}):
                                del run_configs[file]['data'][namelist][key]

            # Apply branch-specific settings
            for file, settings in branch.get('settings', {}).items():
                for key, params in settings.items():
                    run_configs[file]['data'][key].update(params)
            
            # Apply sweep-specific settings
            for key, value in current_params.items():
                for namelist in ['viscosity_run_pars', 'entropy_run_pars', 'density_run_pars']:
                    if key in run_configs.get('run_in.yaml', {}).get('data', {}).get(namelist, {}):
                        run_configs['run_in.yaml']['data'][namelist][key] = value

            all_runs.append({'name': run_name, 'configs': run_configs})

    if limit is not None and limit > 0:
        logger.warning(f"TEST MODE: Limiting generation to the first {limit} run(s) of the suite.")
        all_runs = all_runs[:limit]

    # --- Write all generated files locally ---
    experiment_name = plan_file.parent.parent.name
    local_exp_dir = DIRS.runs / experiment_name
    generated_configs_dir = local_exp_dir / "generated_configs"
    os.makedirs(local_exp_dir / "slurm_logs", exist_ok=True)
    
    for run in all_runs:
        # NAMEERROR FIX: The call to this function now works correctly.
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
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(DIRS.templates), trim_blocks=True, lstrip_blocks=True)
    submit_template = env.get_template("sbatch_array.j2")
    
    submit_script_content = submit_template.render(
        hpc=plan.get('hpc', {}),
        sbatch=plan.get('hpc', {}).get('sbatch', {}),
        run_base_dir=plan.get('hpc', {}).get('run_base_dir', 'runs'),
        manifest_file=FILES.manifest,
        num_jobs=len(all_runs),
        experiment_name=experiment_name
    )
    
    submit_script_path = local_exp_dir / FILES.submit_script
    with open(submit_script_path, 'w') as f:
        f.write(submit_script_content)
    logger.success(f"Generated SLURM submission script at '{submit_script_path}'")

    if limit:
        logger.info("The following run directories will be created on the HPC:")
        for run in all_runs:
            print(f"  - {Path(plan.get('hpc', {}).get('run_base_dir', 'runs')) / run['name']}")
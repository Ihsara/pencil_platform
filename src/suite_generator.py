# src/suite_generator.py

import os
import yaml
import itertools
from pathlib import Path
from loguru import logger
from copy import deepcopy
import jinja2

from src.constants import DIRS, FILES

def generate_experiment_from_dict(experiment_name: str, config_data_map: dict, template_dir: Path, output_dir: Path):
    """Generates a single experiment run directory from a dictionary of configurations."""
    exp_output_dir = output_dir / experiment_name
    os.makedirs(exp_output_dir, exist_ok=True)
    
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir), trim_blocks=True, lstrip_blocks=True)

    for config_filename, config_content in config_data_map.items():
        output_filename = Path(config_filename).stem.replace('_', '.')
        template_format = config_content.get('format')
        template_data = config_content.get('data', {})

        if not template_format:
            continue

        template = env.get_template(f"{template_format}.j2")
        rendered_content = template.render(data=template_data, output_filename=output_filename)
        
        with open(exp_output_dir / output_filename, 'w') as f:
            f.write(rendered_content)

# THIS IS THE CORRECTED FUNCTION SIGNATURE
def run_suite(plan_file: Path, project_root: Path):
    """Reads an experiment plan and generates all specified run directories and scripts."""
    logger.info(f"Loading experiment plan from: {plan_file}")
    with open(plan_file, 'r') as f:
        plan = yaml.safe_load(f)

    # --- Setup Paths ---
    # Now correctly uses the provided project_root
    config_dir = project_root / "config"
    template_dir = project_root / "template" / "generic"
    output_dir = project_root / "runs"

    base_config_path = config_dir / plan['base_experiment'] / DIRS.in_subdir
    if not base_config_path.is_dir():
        logger.error(f"Base configuration directory not found: {base_config_path}")
        return

    # ... rest of the function is the same ...
    base_configs = {p.name: yaml.safe_load(p.read_text()) for p in base_config_path.glob("*.yaml")}
    
    all_runs = []
    sweep_params = plan['sweep_parameters']
    sweep_values = list(itertools.product(*sweep_params.values()))
    
    for branch in plan['branches']:
        for values in sweep_values:
            current_params = dict(zip(sweep_params.keys(), values))
            params_str = '_'.join([f"{k.split('_')[0]}{v}" for k, v in current_params.items()])
            run_name = f"{plan['output_prefix']}_{branch['name']}_{params_str}"
            
            run_configs = deepcopy(base_configs)
            for file, settings in branch['settings'].items():
                for key, params in settings.items():
                    run_configs[file]['data'][key].update(params)
            
            for key, value in current_params.items():
                if key in run_configs.get('run_in.yaml', {}).get('data', {}).get('viscosity_run_pars', {}):
                    run_configs['run_in.yaml']['data']['viscosity_run_pars'][key] = value
                if key in run_configs.get('run_in.yaml', {}).get('data', {}).get('entropy_run_pars', {}):
                    run_configs['run_in.yaml']['data']['entropy_run_pars'][key] = value
                if key in run_configs.get('run_in.yaml', {}).get('data', {}).get('density_run_pars', {}):
                    run_configs['run_in.yaml']['data']['density_run_pars'][key] = value

            all_runs.append({'name': run_name, 'configs': run_configs})

    experiment_name = plan_file.parent.parent.name
    local_exp_dir = output_dir / experiment_name
    os.makedirs(local_exp_dir, exist_ok=True)
    
    manifest_path = local_exp_dir / FILES.manifest
    with open(manifest_path, 'w') as f:
        for run in all_runs:
            f.write(f"{run['name']}\n")
    logger.success(f"Generated run manifest at '{manifest_path}'")

    # Generate the single submission script
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir), trim_blocks=True, lstrip_blocks=True)
    submit_template = env.get_template("sbatch_array.j2")
    submit_script_content = submit_template.render(
        sbatch=plan['hpc']['sbatch'],
        run_base_dir=plan['hpc']['run_base_dir'],
        output_dir=local_exp_dir,
        manifest_file=FILES.manifest,
        num_jobs=len(all_runs)
    )
    submit_script_path = local_exp_dir / FILES.submit_script
    with open(submit_script_path, 'w') as f:
        f.write(submit_script_content)
    logger.success(f"Generated SLURM submission script at '{submit_script_path}'")
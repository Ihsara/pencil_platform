# src/suite_generator.py

import os, yaml, itertools, jinja2
from pathlib import Path
from loguru import logger
from copy import deepcopy
from .constants import DIRS, FILES

def run_suite(plan_file: Path, limit: int = None):
    """Reads an experiment plan and generates all specified run directories and scripts locally."""
    logger.info(f"Loading experiment plan from: {plan_file}")
    with open(plan_file, 'r') as f:
        plan = yaml.safe_load(f)

    base_config_path = DIRS.config / plan['base_experiment'] / DIRS.in_subdir
    if not base_config_path.is_dir():
        logger.error(f"Base configuration directory not found: {base_config_path}")
        return

    base_configs = {p.name: yaml.safe_load(p.read_text()) for p in base_config_path.glob("*.yaml")}
    
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(DIRS.templates), trim_blocks=True, lstrip_blocks=True)
    
    all_runs = []
    # (The logic to generate all_runs is the same as before)
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

    if limit is not None and limit > 0:
        logger.warning(f"TEST MODE: Generating only the first {limit} run(s) of the suite.")
        all_runs = all_runs[:limit]

    # --- Write all generated files locally ---
    experiment_name = plan_file.parent.parent.name
    local_exp_dir = DIRS.runs / experiment_name
    os.makedirs(local_exp_dir / "slurm_logs", exist_ok=True)
    
    # **NEW LOGIC**: Generate the config files for each run into a subdirectory
    for run in all_runs:
        run_config_dir = local_exp_dir / "generated_configs" / run['name']
        os.makedirs(run_config_dir, exist_ok=True)
        for config_filename, config_content in run['configs'].items():
            output_filename = Path(config_filename).stem.replace('_', '.')
            template_format = config_content.get('format')
            template_data = config_content.get('data', {})
            if template_format:
                template = env.get_template(f"{template_format}.j2")
                rendered_content = template.render(data=template_data)
                with open(run_config_dir / output_filename, 'w') as f:
                    f.write(rendered_content)

    # Generate the manifest of run names
    manifest_path = local_exp_dir / FILES.manifest
    with open(manifest_path, 'w') as f:
        for run in all_runs:
            f.write(f"{run['name']}\n")
    logger.success(f"Generated run manifest for {len(all_runs)} run(s) at '{manifest_path}'")

    # Generate the single submission script
    submit_template = env.get_template("sbatch_array.j2")
    submit_script_content = submit_template.render(
        sbatch=plan['hpc']['sbatch'],
        run_base_dir=plan['hpc']['run_base_dir'],
        manifest_file=FILES.manifest,
        num_jobs=len(all_runs)
    )
    submit_script_path = local_exp_dir / FILES.submit_script
    with open(submit_script_path, 'w') as f:
        f.write(submit_script_content)
    logger.success(f"Generated SLURM submission script at '{submit_script_path}'")

    if limit:
        logger.info("The following run directories will be created on the HPC:")
        for run in all_runs:
            print(f"  - {Path(plan['hpc']['run_base_dir']) / run['name']}")
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
    # This helper function is unchanged
    if 'parameter_sweeps' not in plan: return [{}]
    all_param_groups = []
    for sweep in plan.get('parameter_sweeps', []):
        if not sweep: continue
        group = []
        if sweep.get('type') == 'linked':
            for value in sweep.get('values', []):
                group.append({var: value for var in sweep.get('variables', [])})
        elif sweep.get('type') == 'product':
            variable = sweep.get('variable')
            group = [{variable: value} for value in sweep.get('values', [])]
        if group: all_param_groups.append(group)
    final_combinations = [dict(p) for p in itertools.product(*[d.items() for d in group]) for group in all_param_groups] # Simplified this section
    # ... Original logic for product/linked is complex, simplifying for this example, but assuming it works.
    # Re-implementing the core logic correctly.
    final_combinations = []
    for combo_tuple in itertools.product(*all_param_groups):
        merged_dict = {}
        for d in combo_tuple:
            merged_dict.update(d)
        final_combinations.append(merged_dict)
    return final_combinations if final_combinations else [{}]


def generate_experiment_from_dict(experiment_name: str, config_data_map: dict, template_dir: Path, output_dir: Path):
    # This helper function is unchanged
    run_config_dir = output_dir / experiment_name
    os.makedirs(run_config_dir, exist_ok=True)
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir), trim_blocks=True, lstrip_blocks=True)
    for config_filename, config_content in config_data_map.items():
        output_filename = Path(config_filename).stem.replace('_', '.')
        template_format, template_data = config_content.get('format'), config_content.get('data', {})
        if not template_format: continue
        template = env.get_template(f"{template_format}.j2")
        rendered_content = template.render(data=template_data, output_filename=output_filename)
        with open(run_config_dir / output_filename, 'w') as f:
            f.write(rendered_content)

def run_suite(plan_file: Path, limit: int = None, rebuild: bool = False):
    logger.info(f"Loading experiment plan from: {plan_file}")
    with open(plan_file, 'r') as f:
        plan = yaml.safe_load(f)

    base_config_path = DIRS.config / plan['base_experiment'] / DIRS.in_subdir
    base_configs = {p.name: yaml.safe_load(p.read_text()) for p in base_config_path.glob("*.yaml")}
    
    all_runs = []
    all_param_combinations = _generate_sweep_combinations(plan)
    
    for branch in plan.get('branches', [{'name': 'default', 'settings': {}}]):
        for current_params in all_param_combinations:
            
            # --- NEW: Agnostic, Configuration-Driven Logic ---
            
            # 1. Create the full context for this run
            context = {
                'plan': plan,
                'branch': branch,
                **current_params
            }

            # 2. Calculate derived parameters if they are defined in the plan
            if 'derived_parameters' in plan:
                for key, formula in plan['derived_parameters'].items():
                    # Evaluate the formula string using the current context
                    context[key] = eval(formula, {}, context)

            # 3. Generate the run name using the template from the plan
            if 'run_name_template' in plan:
                name_template = jinja2.Template(plan['run_name_template'])
                # Add a filter for filesystem-friendly names
                name_template.environment.filters['fs_safe'] = lambda v: str(v).replace('.', 'p')
                run_name = name_template.render(context)
            else:
                # Fallback to the original, simple naming for backward compatibility
                params_str = '_'.join([f"{k}{v}" for k, v in current_params.items()])
                run_name = '_'.join([plan['output_prefix'], branch['name'], params_str])
            
            # --- END OF NEW LOGIC ---

            run_configs = deepcopy(base_configs)
            
            # Apply branch settings
            for file_name, settings in branch.get('settings', {}).items():
                if file_name in run_configs:
                    config_data = run_configs[file_name]['data']
                    for namelist, params in settings.items():
                        if namelist in config_data:
                            config_data[namelist].update(params)

            # Apply all parameters from the context (swept, derived) to the configs
            for param_key, param_value in context.items():
                for config_file in run_configs.values():
                    for namelist_data in config_file.get('data', {}).values():
                        if isinstance(namelist_data, dict) and param_key in namelist_data:
                            namelist_data[param_key] = param_value
            
            all_runs.append({'name': run_name, 'configs': run_configs})

    if limit is not None and limit > 0:
        all_runs = all_runs[:limit]

    # The rest of the script (file writing, summary) is unchanged
    plan['total_sims'] = len(all_runs)
    experiment_name = plan_file.parent.parent.name
    local_exp_dir = DIRS.runs / experiment_name
    generated_configs_dir = local_exp_dir / "generated_configs"
    os.makedirs(local_exp_dir / "slurm_logs", exist_ok=True)
    
    for run in all_runs:
        generate_experiment_from_dict(run['name'], run['configs'], DIRS.templates, generated_configs_dir)
    logger.success(f"Generated config files for {len(all_runs)} run(s) in '{generated_configs_dir}'")

    manifest_path = local_exp_dir / FILES.manifest
    with open(manifest_path, 'w') as f:
        for run in all_runs: f.write(f"{run['name']}\n")
    logger.success(f"Generated run manifest at '{manifest_path}'")

    env = jinja2.Environment(loader=jinja2.FileSystemLoader(DIRS.templates))
    submit_template = env.get_template("sbatch_array.j2")
    
    hpc_config = plan.get('hpc', {})
    submit_script_path = local_exp_dir / FILES.submit_script
    with open(submit_script_path, 'w') as f:
        f.write(submit_template.render(
            hpc=hpc_config, sbatch=hpc_config.get('sbatch', {}),
            run_base_dir=hpc_config.get('run_base_dir', 'runs'),
            manifest_file=FILES.manifest, num_jobs=len(all_runs),
            experiment_name=experiment_name, rebuild=rebuild,
            module_loads=hpc_config.get('module_loads', '')
        ))
    logger.success(f"Generated submission script at '{submit_script_path}'")

    logger.info("--- Experiment Summary ---")
    print(f"Total Simulations to Generate: {len(all_runs)}")
    return submit_script_path, plan
# src/suite_generator.py

import os
import yaml
import itertools
from pathlib import Path
from loguru import logger
from copy import deepcopy
import jinja2

from src.core.constants import DIRS, FILES
from src.core.logging import setup_file_logging

def _deep_merge_configs(base: dict, override: dict) -> dict:
    """
    Deep merge two configuration dictionaries.
    Override values take precedence over base values.
    For nested dictionaries, merge recursively.
    """
    result = deepcopy(base)
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dictionaries
            result[key] = _deep_merge_configs(result[key], value)
        else:
            # Override or add new key
            result[key] = deepcopy(value)
    
    return result

def _generate_sweep_combinations(plan: dict) -> list:
    """
    Parses the 'parameter_sweeps' section of a plan and returns a list of
    all unique parameter combination dictionaries.
    """
    if 'parameter_sweeps' not in plan:
        return [{}]

    all_param_groups = []
    for sweep in plan.get('parameter_sweeps', []):
        if not sweep: continue
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
        if group:
            all_param_groups.append(group)

    if not all_param_groups: return [{}]
    final_combinations = []
    for combo_tuple in itertools.product(*all_param_groups):
        merged_dict = {}
        for d in combo_tuple: merged_dict.update(d)
        final_combinations.append(merged_dict)
    return final_combinations

def generate_experiment_from_dict(experiment_name: str, config_data_map: dict, template_dir: Path, output_dir: Path):
    """
    Generates all config files for a single experiment run, placing build-time
    files like Makefile.local and cparam.local into a 'src' subdirectory.
    """
    run_config_dir = output_dir / experiment_name
    os.makedirs(run_config_dir, exist_ok=True)
    
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir), trim_blocks=True, lstrip_blocks=True)

    for config_filename, config_content in config_data_map.items():
        output_filename = Path(config_filename).stem.replace('_', '.')
        template_format = config_content.get('format')
        template_data = config_content.get('data', {})

        if not template_format: continue

        template = env.get_template(f"{template_format}.j2")
        rendered_content = template.render(data=template_data, output_filename=output_filename)
      
        if output_filename in ["Makefile.local", "cparam.local"]:
            target_dir = run_config_dir / "src"
            os.makedirs(target_dir, exist_ok=True)
            output_path = target_dir / output_filename
        else:
            output_path = run_config_dir / output_filename
        
        with open(output_path, 'w') as f:
            f.write(rendered_content)

def run_suite(plan_file: Path, limit: int = None, rebuild: bool = False):
    """
    Reads an experiment plan, generates all configurations and scripts.
    """
    # Extract experiment name for logging
    experiment_name = plan_file.parent.parent.name
    
    # Setup file logging for this generation run
    setup_file_logging(experiment_name, 'generation')
    
    logger.info(f"Loading experiment plan from: {plan_file}")
    with open(plan_file, 'r') as f: plan = yaml.safe_load(f)

    # Load base experiment configs first
    base_config_path = DIRS.config / plan['base_experiment'] / DIRS.in_subdir
    base_configs = {p.name: yaml.safe_load(p.read_text()) for p in base_config_path.glob("*.yaml")}
    logger.info(f"Loaded {len(base_configs)} config file(s) from base experiment '{plan['base_experiment']}'")
    
    # Load specific experiment configs and merge with base configs (specific experiment has higher precedence)
    experiment_name = plan_file.parent.parent.name
    specific_config_path = DIRS.config / experiment_name / DIRS.in_subdir
    if specific_config_path.exists() and specific_config_path != base_config_path:
        specific_configs = {p.name: yaml.safe_load(p.read_text()) for p in specific_config_path.glob("*.yaml")}
        if specific_configs:
            logger.info(f"Loaded {len(specific_configs)} config file(s) from specific experiment '{experiment_name}'")
            # Deep merge each config file: base parameters are preserved, specific parameters override/add
            for config_name, specific_config in specific_configs.items():
                if config_name in base_configs:
                    logger.info(f"  Merging '{config_name}': base + specific overrides")
                    base_configs[config_name] = _deep_merge_configs(base_configs[config_name], specific_config)
                else:
                    logger.info(f"  Adding new config '{config_name}' from specific experiment")
                    base_configs[config_name] = specific_config
    
    auto_rebuild = False
    rebuild_reason = ""
    critical_cparams = ['nxgrid', 'nygrid', 'nzgrid', 'ncpus', 'nprocx', 'nprocy', 'nprocz']
    
    # Check if cparam_local differs from base experiment's cparam_local
    base_experiment_name = plan['base_experiment']
    base_cparam_path = DIRS.config / base_experiment_name / DIRS.in_subdir / 'cparam_local.yaml'
    if base_cparam_path.exists():
        with open(base_cparam_path, 'r') as f:
            base_cparam = yaml.safe_load(f)
        
        # Get the final merged cparam_local after all merging
        final_cparam = base_configs.get('cparam_local.yaml', {})
        
        # Compare critical parameters
        base_data = base_cparam.get('data', {})
        final_data = final_cparam.get('data', {})
        
        for param in critical_cparams:
            base_value = base_data.get(param)
            final_value = final_data.get(param)
            if base_value != final_value:
                auto_rebuild = True
                rebuild_reason = f"cparam_local.yaml parameter '{param}' differs from base experiment '{base_experiment_name}' ({base_value} vs {final_value})."
                break
    
    # Check if parameter sweeps modify critical cparams
    if not auto_rebuild:
        for sweep in plan.get('parameter_sweeps', []):
            if sweep.get('variable') in critical_cparams:
                auto_rebuild = True; rebuild_reason = f"Sweep modifies '{sweep.get('variable')}'."
                break
    
    critical_files = ['cparam_local.yaml', 'Makefile_local.yaml']
    if not auto_rebuild:
        for file in critical_files:
            if file in plan.get('modifications', {}):
                auto_rebuild = True; rebuild_reason = f"Plan modifies '{file}'."
                break
        if not auto_rebuild:
            for branch in plan.get('branches', []):
                for file in critical_files:
                    if file in branch.get('settings', {}):
                        auto_rebuild = True; rebuild_reason = f"Branch '{branch['name']}' modifies '{file}'."
                        break
    
    final_rebuild_flag = rebuild or auto_rebuild
    if auto_rebuild:
        logger.warning(f"AUTOMATIC REBUILD ENACTED. Reason: {rebuild_reason}")
    
    all_runs = []
    all_param_combinations = _generate_sweep_combinations(plan)
    
    for branch in plan.get('branches', [{'name': 'default', 'settings': {}}]):
        for current_params in all_param_combinations:
            # Process output_prefix as a template to resolve dynamic values like {data.nxgrid}
            raw_output_prefix = plan.get('output_prefix', '')
            env_prefix = jinja2.Environment()
            # Create context with config data for template evaluation
            prefix_context = {'data': base_configs.get('cparam_local.yaml', {}).get('data', {}), **current_params}
            try:
                output_prefix = env_prefix.from_string(raw_output_prefix).render(prefix_context)
            except:
                output_prefix = raw_output_prefix  # Fallback to raw string if template fails
            
            context = {'plan': plan, 'branch': branch, 'output_prefix': output_prefix, **current_params}
            if 'derived_parameters' in plan:
                for key, formula in plan['derived_parameters'].items():
                    if isinstance(formula, str):
                        try: context[key] = eval(formula, {}, context)
                        except NameError: pass 
                    else: context[key] = formula
                for key, formula in plan['derived_parameters'].items():
                     if isinstance(formula, str) and key not in context: context[key] = eval(formula, {}, context)
            if 'run_name_template' in plan:
                env = jinja2.Environment(); env.filters['fs_safe'] = lambda v: str(v).replace('.', 'p')
                name_template = env.from_string(plan['run_name_template'])
                run_name = name_template.render(context)
            else:
                params_str = '_'.join([f"{k.replace('_shock', '')}{v}" for k, v in current_params.items()])
                run_name = '_'.join(filter(None, [plan.get('output_prefix', ''), branch['name'], params_str]))
            
            run_configs = deepcopy(base_configs)
            for file_name, settings in branch.get('settings', {}).items():
                if file_name in run_configs:
                    config_data = run_configs[file_name]['data']
                    for namelist, params in settings.items():
                        if namelist in config_data: config_data[namelist].update(params)
            for param_key, param_value in context.items():
                for config_file in run_configs.values():
                    for namelist, namelist_data in config_file.get('data', {}).items():
                        if isinstance(namelist_data, dict) and param_key in namelist_data:
                            namelist_data[param_key] = param_value
            
            all_runs.append({'name': run_name, 'configs': run_configs})

    if limit is not None: all_runs = all_runs[:limit]
    
    experiment_name = plan_file.parent.parent.name
    local_exp_dir = DIRS.runs / experiment_name
    
    # Clean up old experiment directory to ensure fresh run
    if os.path.exists(local_exp_dir):
        import shutil
        logger.info(f"Removing existing experiment directory: {local_exp_dir}")
        shutil.rmtree(local_exp_dir)
    
    # Create fresh directory structure
    generated_configs_dir = local_exp_dir / "generated_configs"
    os.makedirs(local_exp_dir / "slurm_logs", exist_ok=True)
    
    for run in all_runs:
        generate_experiment_from_dict(run['name'], run['configs'], DIRS.templates, generated_configs_dir)
    logger.success(f"Generated config files for {len(all_runs)} run(s) in '{generated_configs_dir}'")

    with open(local_exp_dir / FILES.manifest, 'w') as f:
        for run in all_runs: f.write(f"{run['name']}\n")
    logger.success(f"Generated run manifest at '{local_exp_dir / FILES.manifest}'")

    env = jinja2.Environment(loader=jinja2.FileSystemLoader(DIRS.templates))
    submit_template = env.get_template("sbatch_array.j2")
    
    hpc_config = plan.get('hpc', {})
    submit_script_path = local_exp_dir / FILES.submit_script
    with open(submit_script_path, 'w') as f:
        f.write(submit_template.render(
            hpc=hpc_config, sbatch=hpc_config.get('sbatch', {}),
            run_base_dir=hpc_config.get('run_base_dir', 'runs'),
            manifest_file=FILES.manifest, num_jobs=len(all_runs),
            experiment_name=experiment_name, rebuild=final_rebuild_flag,
            module_loads=hpc_config.get('module_loads', '')
        ))
    logger.success(f"Generated submission script at '{submit_script_path}'")
    logger.info("--- Experiment Summary ---\nTotal Simulations to Generate: " + str(len(all_runs)))
    return submit_script_path, plan

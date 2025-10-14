# src/read_config.py

import yaml
from jinja2 import Environment, FileSystemLoader
import os
from pathlib import Path
from loguru import logger

def generate_input_files(experiment_name: str, config_dir: Path, template_dir: Path, output_dir: Path):
    """
    Generates all Fortran input files for a given experiment by dynamically selecting templates.

    Args:
        experiment_name: The name of the experiment subdirectory.
        config_dir: Base directory for configurations.
        template_dir: Base directory for generic templates.
        output_dir: Base directory for run outputs.
    """
    exp_config_dir = config_dir / experiment_name / "in"
    exp_output_dir = output_dir / experiment_name

    if not exp_config_dir.is_dir():
        logger.error(f"Experiment config directory not found: {exp_config_dir}")
        return

    os.makedirs(exp_output_dir, exist_ok=True)
    logger.info(f"Output will be written to: {exp_output_dir}")

    # The loader now points to the single generic template directory
    env = Environment(loader=FileSystemLoader(template_dir), trim_blocks=True, lstrip_blocks=True)

    config_files = list(exp_config_dir.glob('*.yaml'))
    if not config_files:
        logger.warning(f"No YAML configuration files found in {exp_config_dir}")
        return
        
    logger.info(f"Found {len(config_files)} configuration file(s) for experiment '{experiment_name}'.")

    for config_file in config_files:
        output_filename = config_file.stem.replace('_', '.')
        logger.info(f"Processing '{config_file.name}'...")

        try:
            with open(config_file, 'r') as f:
                config_data = yaml.safe_load(f)

            # **KEY CHANGE: Read the format and data from the YAML**
            template_format = config_data.get('format')
            template_data = config_data.get('data', {})

            if not template_format:
                logger.warning(f"  -> Skipping: 'format' key not found in {config_file.name}")
                continue

            template_name = f"{template_format}.j2"
            template = env.get_template(template_name)
            
            # Render with the nested 'data' dictionary
            rendered_content = template.render(data=template_data, output_filename=output_filename)
            
            output_path = exp_output_dir / output_filename
            with open(output_path, 'w') as f:
                f.write(rendered_content)
            logger.success(f"  -> Successfully generated '{output_filename}' using '{template_name}' template.")

        except (yaml.YAMLError, IOError, FileNotFoundError) as e:
            logger.error(f"  -> Failed processing {config_file.name}: {e}")
        except Exception:
            logger.exception(f"An unexpected error occurred while processing {config_file.name}")
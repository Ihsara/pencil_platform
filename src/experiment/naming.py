# src/experiment_name_decoder.py

import re
import yaml
from pathlib import Path
from typing import Dict, Optional
from loguru import logger

from src.core.constants import DIRS


def _load_sweep_config(experiment_name: str) -> Optional[Dict]:
    """
    Load the sweep configuration for a given experiment.
    
    Args:
        experiment_name: Name of the experiment (e.g., 'shocktube_phase1')
    
    Returns:
        Dictionary containing sweep configuration, or None if not found
    """
    sweep_file = DIRS.config / experiment_name / "plan" / "sweep.yaml"
    if not sweep_file.exists():
        logger.warning(f"Sweep config not found: {sweep_file}")
        return None
    
    try:
        with open(sweep_file, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load sweep config from {sweep_file}: {e}")
        return None


def _extract_template_variables(template: str) -> list:
    """
    Extract variable names from a Jinja2 template string.
    
    Args:
        template: Jinja2 template string like "{{ output_prefix }}_{{ branch.name }}_nu{{ nu_shock | fs_safe }}"
    
    Returns:
        List of variable names found in the template
    """
    # Match {{ variable }} or {{ variable | filter }}
    pattern = r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_.]*)\s*(?:\|[^}]*)?\}\}'
    matches = re.findall(pattern, template)
    return matches


def _parse_template_structure(template: str) -> list:
    """
    Parse template into a list of (literal, variable) tuples for reconstruction.
    
    Args:
        template: Jinja2 template string
    
    Returns:
        List of tuples containing (literal_text, variable_name_or_none)
    """
    parts = []
    pattern = r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_.]*)\s*(?:\|[^}]*)?\}\}'
    
    last_end = 0
    for match in re.finditer(pattern, template):
        # Add literal text before the variable
        if match.start() > last_end:
            literal = template[last_end:match.start()]
            if literal:
                parts.append(('literal', literal))
        
        # Add the variable
        var_name = match.group(1)
        parts.append(('variable', var_name))
        last_end = match.end()
    
    # Add any remaining literal text
    if last_end < len(template):
        literal = template[last_end:]
        if literal:
            parts.append(('literal', literal))
    
    return parts


def _decode_from_template(experiment_name: str, template: str, sweep_config: Dict) -> Dict[str, str]:
    """
    Decode an experiment name using the template structure.
    
    Args:
        experiment_name: The experiment name to decode
        template: The run_name_template from sweep.yaml
        sweep_config: Full sweep configuration
    
    Returns:
        Dictionary of decoded parameters
    """
    decoded = {}
    
    # Parse template structure
    template_parts = _parse_template_structure(template)
    
    # Get known values from sweep config to help with matching
    known_values = {}
    if 'output_prefix' in sweep_config:
        known_values['output_prefix'] = sweep_config['output_prefix']
    
    # Get branch names from sweep config
    branch_names = []
    if 'branches' in sweep_config:
        branch_names = [branch['name'] for branch in sweep_config['branches']]
    
    # Build regex pattern from template with intelligent matching
    regex_parts = []
    var_order = []
    
    for i, (part_type, content) in enumerate(template_parts):
        if part_type == 'literal':
            # Escape special regex characters in literals
            regex_parts.append(re.escape(content))
        else:  # variable
            var_order.append(content)
            
            # Use known values for more precise matching
            if content in known_values:
                # Match exact known value
                regex_parts.append(f'({re.escape(known_values[content])})')
            elif content == 'branch.name':
                # For branch names, match the longest possible string from known branches
                if branch_names:
                    # Create alternation pattern for branch names
                    escaped_branches = [re.escape(name) for name in sorted(branch_names, key=len, reverse=True)]
                    regex_parts.append(f"({'|'.join(escaped_branches)})")
                else:
                    # Fallback: match multiple words with underscores
                    regex_parts.append(r'([a-zA-Z0-9_]+)')
            else:
                # For parameters with fs_safe filter (numeric values), match digits and 'p'
                # Look ahead in template to see if next part is a separator
                next_idx = i + 1
                if next_idx < len(template_parts) and template_parts[next_idx][0] == 'literal':
                    next_sep = template_parts[next_idx][1]
                    if next_sep:
                        # Match everything up to the next separator
                        regex_parts.append(f'([^{re.escape(next_sep[0])}]+)')
                    else:
                        regex_parts.append(r'([a-zA-Z0-9p]+)')
                else:
                    # Last variable - match to end
                    regex_parts.append(r'([a-zA-Z0-9p]+)')
    
    pattern = '^' + ''.join(regex_parts) + '$'
    
    try:
        match = re.match(pattern, experiment_name)
        if match:
            for i, var_name in enumerate(var_order):
                value = match.group(i + 1)
                
                # Handle fs_safe filter - convert 'p' back to '.'
                # Check if this looks like a numeric value with 'p' separator
                if re.match(r'^\d+p\d+$', value):
                    value = value.replace('p', '.')
                
                # Store with simplified key name (remove _shock, etc.)
                simple_key = var_name.replace('_shock', '').replace('_', '')
                decoded[simple_key] = value
                
                # Also store original key
                decoded[var_name] = value
        else:
            logger.warning(f"Experiment name '{experiment_name}' does not match template pattern. Pattern: {pattern}")
    except Exception as e:
        logger.error(f"Error decoding experiment name with template: {e}")
    
    # Add additional context from sweep config
    if 'output_prefix' in sweep_config:
        decoded['output_prefix'] = sweep_config['output_prefix']
    
    return decoded


def decode_experiment_name(experiment_name: str, experiment_type: Optional[str] = None) -> Dict[str, str]:
    """
    Decode experiment name into human-readable components.
    
    This function dynamically determines how to parse the experiment name by:
    1. Loading the sweep configuration to get the run_name_template
    2. Using the template to extract parameters
    3. Falling back to hardcoded patterns if config is not available
    
    Args:
        experiment_name: Raw experiment name like 
            'res400_nohyper_massfix_gamma_is_1_nu5p0_chi5p0_diffrho5p0'
        experiment_type: Optional experiment type (e.g., 'shocktube_phase1').
            If not provided, tries to infer from common patterns.
    
    Returns:
        Dictionary with decoded parameters
    
    Examples:
        >>> decode_experiment_name('res400_nohyper_massfix_default_gamma_nu0p1_chi0p1_diffrho0p1', 'shocktube_phase1')
        {'output_prefix': 'res400_nohyper', 'branch.name': 'massfix_default_gamma', ...}
    """
    decoded = {}
    
    # Try to infer experiment type if not provided
    if experiment_type is None:
        # Look for common experiment patterns in the name
        if 'shocktube' in experiment_name.lower():
            # Try to find which phase
            for phase in ['phase1', 'phase2', 'phase3']:
                potential_type = f'shocktube_{phase}'
                if _load_sweep_config(potential_type):
                    experiment_type = potential_type
                    break
            if experiment_type is None:
                experiment_type = 'shocktube_phase1'  # default
    
    # Try to decode using sweep configuration
    if experiment_type:
        sweep_config = _load_sweep_config(experiment_type)
        if sweep_config and 'run_name_template' in sweep_config:
            template = sweep_config['run_name_template']
            decoded = _decode_from_template(experiment_name, template, sweep_config)
            if decoded:
                return decoded
    
    # Fallback to legacy hardcoded parsing for backward compatibility
    logger.debug(f"Using legacy hardcoded decoder for '{experiment_name}'")
    
    # Extract resolution
    res_match = re.search(r'res(\d+)', experiment_name)
    if res_match:
        decoded['res'] = res_match.group(1)
    
    # Extract hyper3 (hyperdiffusion)
    if 'nohyper' in experiment_name:
        decoded['hyper3'] = 'None'
    elif 'hyper' in experiment_name:
        hyper_match = re.search(r'hyper(\d+)', experiment_name)
        if hyper_match:
            decoded['hyper3'] = hyper_match.group(1)
        else:
            decoded['hyper3'] = 'Yes'
    
    # Extract massfix
    if 'massfix' in experiment_name:
        decoded['massfix'] = 'True'
    elif 'nomassfix' in experiment_name:
        decoded['massfix'] = 'False'
    
    # Extract gamma
    gamma_match = re.search(r'gamma_is_(\d+(?:p\d+)?)', experiment_name)
    if gamma_match:
        gamma_val = gamma_match.group(1).replace('p', '.')
        decoded['gamma'] = gamma_val
    elif 'default_gamma' in experiment_name:
        decoded['gamma'] = 'default'
    
    # Extract nu (viscosity coefficient)
    nu_match = re.search(r'nu(\d+p\d+)', experiment_name)
    if nu_match:
        decoded['nu'] = nu_match.group(1).replace('p', '.')
    
    # Extract chi (thermal diffusion coefficient)
    chi_match = re.search(r'chi(\d+p\d+)', experiment_name)
    if chi_match:
        decoded['chi'] = chi_match.group(1).replace('p', '.')
    
    # Extract diffrho (density diffusion coefficient)
    diffrho_match = re.search(r'diffrho(\d+p\d+)', experiment_name)
    if diffrho_match:
        decoded['diffrho'] = diffrho_match.group(1).replace('p', '.')
    
    return decoded


def get_parameter_labels(experiment_type: str) -> Dict[str, str]:
    """
    Get human-readable labels for parameters based on experiment type.
    
    Args:
        experiment_type: Name of the experiment (e.g., 'shocktube_phase1')
    
    Returns:
        Dictionary mapping parameter keys to display labels
    """
    # Default labels
    default_labels = {
        'res': 'Resolution',
        'hyper3': 'Hyper3',
        'massfix': 'Mass Fix',
        'gamma': 'γ',
        'nu': 'ν',
        'nu_shock': 'ν',
        'chi': 'χ',
        'chi_shock': 'χ',
        'diffrho': 'Diff ρ',
        'diffrho_shock': 'Diff ρ',
        'output_prefix': 'Config',
        'branch.name': 'Branch',
        'branch_name': 'Branch',
    }
    
    # Could be extended to load custom labels from config if needed
    sweep_config = _load_sweep_config(experiment_type)
    if sweep_config and 'parameter_labels' in sweep_config:
        default_labels.update(sweep_config['parameter_labels'])
    
    return default_labels


def format_experiment_title(experiment_name: str, max_line_length: int = 80, 
                           experiment_type: Optional[str] = None) -> str:
    """
    Format experiment name into a readable title with proper formatting.
    
    Args:
        experiment_name: Raw experiment name
        max_line_length: Maximum length per line before wrapping
        experiment_type: Optional experiment type for proper decoding
    
    Returns:
        Formatted title string with parameters
    
    Example:
        >>> format_experiment_title('res400_nohyper_massfix_gamma_is_1_nu5p0_chi5p0_diffrho5p0')
        'Resolution: 400 - Hyper3: None - Mass Fix: True - γ: 1\\nν: 5.0 - χ: 5.0 - Diff ρ: 5.0'
    """
    decoded = decode_experiment_name(experiment_name, experiment_type)
    
    if not decoded:
        return experiment_name
    
    # Get parameter labels
    if experiment_type:
        labels = get_parameter_labels(experiment_type)
    else:
        labels = get_parameter_labels('shocktube_phase1')  # default
    
    # First line: resolution, hyper3, massfix, gamma (configuration parameters)
    line1_keys = ['res', 'hyper3', 'massfix', 'gamma']
    line1_parts = []
    
    for key in line1_keys:
        if key in decoded:
            label = labels.get(key, key)
            value = decoded[key]
            
            # Format boolean values
            if value in ['True', 'true', 'yes', 'Yes']:
                value = 'True'
            elif value in ['False', 'false', 'no', 'No']:
                value = 'False'
            
            line1_parts.append(f"{label}: {value}")
    
    # Second line: nu, chi, diffrho (numerical parameters)
    line2_keys = ['nu', 'nu_shock', 'chi', 'chi_shock', 'diffrho', 'diffrho_shock']
    line2_parts = []
    
    for key in line2_keys:
        if key in decoded:
            label = labels.get(key, key)
            value = decoded[key]
            line2_parts.append(f"{label}: {value}")
    
    # Join parts with " - " separator
    if line1_parts and line2_parts:
        return " - ".join(line1_parts) + "\n" + " - ".join(line2_parts)
    elif line1_parts:
        return " - ".join(line1_parts)
    else:
        return " - ".join(line2_parts) if line2_parts else experiment_name


def format_short_experiment_name(experiment_name: str, 
                                 experiment_type: Optional[str] = None) -> str:
    """
    Create a short, compact experiment name for legends and labels.
    
    Args:
        experiment_name: Raw experiment name
        experiment_type: Optional experiment type for proper decoding
    
    Returns:
        Compact formatted name with fallback to simple truncation if decoding fails
    
    Example:
        >>> format_short_experiment_name('res400_nohyper_massfix_gamma_is_1_nu5p0')
        'R400_H:None_MF:T_γ:1_ν:5.0'
    """
    try:
        decoded = decode_experiment_name(experiment_name, experiment_type)
        
        # If decoding failed or returned empty, use simple fallback
        if not decoded:
            return _fallback_short_name(experiment_name)
        
        parts = []
        
        # Abbreviated labels
        abbrev_map = {
            'res': 'R',
            'hyper3': 'H',
            'massfix': 'MF',
            'gamma': 'γ',
            'nu': 'ν',
            'nu_shock': 'ν',
            'chi': 'χ',
            'chi_shock': 'χ',
            'diffrho': 'Dρ',
            'diffrho_shock': 'Dρ',
        }
        
        for key, abbrev in abbrev_map.items():
            if key in decoded:
                value = decoded[key]
                
                # Special handling for massfix
                if key == 'massfix':
                    value = 'T' if value == 'True' else 'F'
                
                parts.append(f"{abbrev}:{value}")
        
        # If we got parts, return them; otherwise fall back
        if parts:
            return "_".join(parts)
        else:
            return _fallback_short_name(experiment_name)
            
    except Exception as e:
        # If anything goes wrong, use fallback
        logger.debug(f"Error in format_short_experiment_name: {e}")
        return _fallback_short_name(experiment_name)


def _fallback_short_name(experiment_name: str) -> str:
    """
    Fallback method to create a shortened name when intelligent decoding fails.
    Simply truncates long names with ellipsis.
    
    Args:
        experiment_name: Raw experiment name
    
    Returns:
        Truncated name if too long, otherwise original name
    """
    max_length = 45
    if len(experiment_name) <= max_length:
        return experiment_name
    return experiment_name[:max_length] + "..."

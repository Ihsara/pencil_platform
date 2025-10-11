# src/experiment_name_decoder.py

import re
from typing import Dict


def decode_experiment_name(experiment_name: str) -> Dict[str, str]:
    """
    Decode experiment name into human-readable components.
    
    Args:
        experiment_name: Raw experiment name like 
            'res400_nohyper_massfix_gamma_is_1_nu5p0_chi5p0_diffrho5p0'
    
    Returns:
        Dictionary with decoded parameters
    
    Examples:
        >>> decode_experiment_name('res400_nohyper_massfix_default_gamma_nu0p1_chi0p1_diffrho0p1')
        {'res': '400', 'hyper3': 'None', 'massfix': 'True', 'gamma': 'default', 
         'nu': '0.1', 'chi': '0.1', 'diffrho': '0.1'}
    """
    decoded = {}
    
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


def format_experiment_title(experiment_name: str, max_line_length: int = 80) -> str:
    """
    Format experiment name into a readable title with proper formatting.
    
    Args:
        experiment_name: Raw experiment name
        max_line_length: Maximum length per line before wrapping
    
    Returns:
        Formatted title string with parameters
    
    Example:
        >>> format_experiment_title('res400_nohyper_massfix_gamma_is_1_nu5p0_chi5p0_diffrho5p0')
        'Resolution: 400 | Hyper3: None | Mass Fix: True\\nGamma: 1 | ν: 5.0 | χ: 5.0 | Diff ρ: 5.0'
    """
    decoded = decode_experiment_name(experiment_name)
    
    if not decoded:
        return experiment_name
    
    # Build formatted string
    parts = []
    
    if 'res' in decoded:
        parts.append(f"Resolution: {decoded['res']}")
    
    if 'hyper3' in decoded:
        parts.append(f"Hyper3: {decoded['hyper3']}")
    
    if 'massfix' in decoded:
        parts.append(f"Mass Fix: {decoded['massfix']}")
    
    if 'gamma' in decoded:
        parts.append(f"γ: {decoded['gamma']}")
    
    if 'nu' in decoded:
        parts.append(f"ν: {decoded['nu']}")
    
    if 'chi' in decoded:
        parts.append(f"χ: {decoded['chi']}")
    
    if 'diffrho' in decoded:
        parts.append(f"Diff ρ: {decoded['diffrho']}")
    
    # Join parts with | separator, wrapping if too long
    line1_parts = []
    line2_parts = []
    current_length = 0
    
    for part in parts:
        part_length = len(part) + 3  # +3 for " | "
        if current_length + part_length <= max_line_length:
            line1_parts.append(part)
            current_length += part_length
        else:
            line2_parts.append(part)
    
    if line2_parts:
        return " | ".join(line1_parts) + "\n" + " | ".join(line2_parts)
    else:
        return " | ".join(line1_parts)


def format_short_experiment_name(experiment_name: str) -> str:
    """
    Create a short, compact experiment name for legends and labels.
    
    Args:
        experiment_name: Raw experiment name
    
    Returns:
        Compact formatted name
    
    Example:
        >>> format_short_experiment_name('res400_nohyper_massfix_gamma_is_1_nu5p0')
        'R400_H:None_MF:T_γ:1_ν:5.0'
    """
    decoded = decode_experiment_name(experiment_name)
    
    if not decoded:
        return experiment_name[:30] + "..." if len(experiment_name) > 30 else experiment_name
    
    parts = []
    
    if 'res' in decoded:
        parts.append(f"R{decoded['res']}")
    
    if 'hyper3' in decoded:
        parts.append(f"H:{decoded['hyper3']}")
    
    if 'massfix' in decoded:
        mf = 'T' if decoded['massfix'] == 'True' else 'F'
        parts.append(f"MF:{mf}")
    
    if 'gamma' in decoded:
        parts.append(f"γ:{decoded['gamma']}")
    
    if 'nu' in decoded:
        parts.append(f"ν:{decoded['nu']}")
    
    if 'chi' in decoded:
        parts.append(f"χ:{decoded['chi']}")
    
    if 'diffrho' in decoded:
        parts.append(f"Dρ:{decoded['diffrho']}")
    
    return "_".join(parts)

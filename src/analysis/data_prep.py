# src/analysis/data_prep.py
"""
Data preparation utilities for error analysis visualization.

This module provides shared data preparation functions that can be used by both
the main pipeline and interactive notebooks for visualization purposes.
"""

import numpy as np
from pathlib import Path
from loguru import logger
from typing import Dict, List, Optional, Tuple
import json


def prepare_spacetime_error_data(
    normalized_errors: Dict,
    variable: str,
    unit_length: float = 1.0,
    use_relative: bool = True
) -> Optional[Dict]:
    """
    Prepare spatial-temporal error data for visualization.
    
    This function extracts and formats error data from the normalized_errors
    structure into a format suitable for various visualization tools including
    Plotly and matplotlib.
    
    Args:
        normalized_errors: Output from calculate_normalized_spatial_errors
        variable: Variable name to extract ('rho', 'ux', 'pp', 'ee')
        unit_length: Unit conversion factor for spatial coordinates (default: 1.0 for code units)
        use_relative: If True, use relative errors; if False, use absolute errors
        
    Returns:
        Dictionary with structured data ready for visualization:
        {
            'x_coords': np.ndarray,        # Spatial coordinates in physical units
            'timesteps': list,             # List of timestep values
            'error_matrix': np.ndarray,    # 2D error field [time, space]
            'max_error': {                 # Maximum error information
                'value': float,
                'time_index': int,
                'space_index': int,
                'time': float,
                'x': float
            },
            'variable': str,               # Variable name
            'error_type': str,             # 'relative' or 'absolute'
            'unit_length': float           # Unit conversion factor used
        }
    """
    if variable not in normalized_errors:
        logger.warning(f"Variable '{variable}' not found in normalized errors")
        return None
    
    var_data = normalized_errors[variable]
    
    # Select error field based on type
    if use_relative:
        error_matrix = var_data['relative_error_field']
        error_type = 'relative'
    else:
        error_matrix = var_data['error_field']
        error_type = 'absolute'
    
    # Convert spatial coordinates to physical units
    x_coords = var_data['x_coords'] * unit_length
    timesteps = var_data['timesteps']
    
    # Extract maximum error location
    max_error_loc = var_data.get('max_error_location', {})
    if max_error_loc:
        max_error_loc['x'] = max_error_loc['x'] * unit_length
    
    return {
        'x_coords': x_coords,
        'timesteps': timesteps,
        'error_matrix': error_matrix,
        'max_error': max_error_loc,
        'variable': variable,
        'error_type': error_type,
        'unit_length': unit_length,
        'dx': var_data.get('dx', 1.0) * unit_length,
        'dt': var_data.get('dt', 1.0)
    }


def prepare_multi_run_spacetime_data(
    runs_normalized_errors: Dict[str, Dict],
    variable: str,
    unit_length: float = 1.0,
    use_relative: bool = True
) -> Dict[str, Dict]:
    """
    Prepare spatial-temporal error data for multiple runs.
    
    Args:
        runs_normalized_errors: Dictionary mapping run names to normalized_errors
        variable: Variable name to extract
        unit_length: Unit conversion factor for spatial coordinates
        use_relative: If True, use relative errors; if False, use absolute errors
        
    Returns:
        Dictionary mapping run names to prepared data dictionaries
    """
    multi_run_data = {}
    
    for run_name, normalized_errors in runs_normalized_errors.items():
        data = prepare_spacetime_error_data(
            normalized_errors,
            variable,
            unit_length,
            use_relative
        )
        if data:
            multi_run_data[run_name] = data
    
    return multi_run_data


def export_spacetime_data_to_json(
    prepared_data: Dict,
    output_path: Path,
    run_name: str,
    variable: str
) -> None:
    """
    Export prepared spacetime data to JSON for notebook usage.
    
    Args:
        prepared_data: Output from prepare_spacetime_error_data
        output_path: Directory to save JSON file
        run_name: Name of the run
        variable: Variable name
    """
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Convert numpy arrays to lists for JSON serialization
    json_data = {
        'run_name': run_name,
        'variable': prepared_data['variable'],
        'error_type': prepared_data['error_type'],
        'unit_length': float(prepared_data['unit_length']),
        'x_coords': prepared_data['x_coords'].tolist(),
        'timesteps': [float(t) for t in prepared_data['timesteps']],
        'error_matrix': prepared_data['error_matrix'].tolist(),
        'max_error': {
            k: float(v) if isinstance(v, (int, float, np.integer, np.floating)) else v
            for k, v in prepared_data['max_error'].items()
        } if prepared_data['max_error'] else None,
        'dx': float(prepared_data['dx']),
        'dt': float(prepared_data['dt'])
    }
    
    filename = output_path / f"{run_name}_{variable}_spacetime_data.json"
    with open(filename, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    logger.debug(f"Exported spacetime data to {filename}")


def load_spacetime_data_from_json(json_path: Path) -> Dict:
    """
    Load prepared spacetime data from JSON file.
    
    Args:
        json_path: Path to JSON file
        
    Returns:
        Dictionary with prepared data (arrays converted back from lists)
    """
    with open(json_path, 'r') as f:
        json_data = json.load(f)
    
    # Convert lists back to numpy arrays
    json_data['x_coords'] = np.array(json_data['x_coords'])
    json_data['timesteps'] = json_data['timesteps']
    json_data['error_matrix'] = np.array(json_data['error_matrix'])
    
    return json_data


def get_error_statistics(error_matrix: np.ndarray) -> Dict:
    """
    Calculate statistics for error matrix.
    
    Args:
        error_matrix: 2D error field [time, space]
        
    Returns:
        Dictionary with statistics
    """
    valid_errors = error_matrix[np.isfinite(error_matrix)]
    
    return {
        'min': float(np.min(valid_errors)) if len(valid_errors) > 0 else 0.0,
        'max': float(np.max(valid_errors)) if len(valid_errors) > 0 else 0.0,
        'mean': float(np.mean(valid_errors)) if len(valid_errors) > 0 else 0.0,
        'median': float(np.median(valid_errors)) if len(valid_errors) > 0 else 0.0,
        'std': float(np.std(valid_errors)) if len(valid_errors) > 0 else 0.0,
        'percentiles': {
            'p10': float(np.percentile(valid_errors, 10)) if len(valid_errors) > 0 else 0.0,
            'p25': float(np.percentile(valid_errors, 25)) if len(valid_errors) > 0 else 0.0,
            'p75': float(np.percentile(valid_errors, 75)) if len(valid_errors) > 0 else 0.0,
            'p90': float(np.percentile(valid_errors, 90)) if len(valid_errors) > 0 else 0.0,
            'p95': float(np.percentile(valid_errors, 95)) if len(valid_errors) > 0 else 0.0,
            'p99': float(np.percentile(valid_errors, 99)) if len(valid_errors) > 0 else 0.0
        }
    }

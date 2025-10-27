# src/visualization/plots_plotly.py
"""
Plotly-based visualization functions for interactive evolution plots.

This module provides plotly equivalents to the matplotlib-based evolution plots,
creating interactive HTML visualizations that can be embedded in reports or
viewed in a browser.
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from pathlib import Path
from loguru import logger
from typing import Dict, List

from src.experiment.naming import format_experiment_title


def create_var_evolution_plotly(
    sim_data_list: List[dict],
    analytical_data_list: List[dict],
    output_path: Path,
    run_name: str,
    variables: List[str] = ['rho', 'ux', 'pp', 'ee']
):
    """
    Creates an interactive Plotly animation showing evolution of variables across all VAR files.
    
    Args:
        sim_data_list: List of simulation data from all VAR files
        analytical_data_list: List of analytical solutions for all VAR files
        output_path: Directory to save the HTML animation
        run_name: Name of the run for title
        variables: List of variables to plot
    """
    output_path.mkdir(parents=True, exist_ok=True)
    
    var_labels = {
        'rho': 'Density ρ [g cm⁻³]',
        'ux': 'Velocity uₓ [km s⁻¹]',
        'pp': 'Pressure p [dyn cm⁻²]',
        'ee': 'Energy e [km² s⁻²]'
    }
    
    var_scales = {
        'rho': 'log',
        'ux': 'linear',
        'pp': 'log',
        'ee': 'log'
    }
    
    # Get units
    unit_dict = {}
    if 'params' in sim_data_list[0]:
        params = sim_data_list[0]['params']
        unit_dict['rho'] = params.unit_density
        unit_dict['ux'] = params.unit_velocity * 1e-5
        unit_dict['pp'] = params.unit_energy_density
        unit_dict['ee'] = params.unit_velocity ** 2
    else:
        unit_dict = {var: 1.0 for var in variables}
    
    # Create subplots with shared legend
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[var.upper() for var in variables],
        vertical_spacing=0.12,
        horizontal_spacing=0.10
    )
    
    # Calculate position mapping for subplots
    positions = [(1, 1), (1, 2), (2, 1), (2, 2)]
    
    # Prepare frames for animation
    frames = []
    
    for frame_idx, (sim_data, analytical_data) in enumerate(zip(sim_data_list, analytical_data_list)):
        frame_data = []
        
        for var_idx, var in enumerate(variables):
            row, col = positions[var_idx]
            
            if var in sim_data and var in analytical_data:
                # Analytical line (shown in all frames)
                # Note: Do NOT include xaxis/yaxis in frame traces - Plotly maps them automatically
                frame_data.append(
                    go.Scatter(
                        x=analytical_data['x'],
                        y=analytical_data[var] * unit_dict[var],
                        mode='lines',
                        name='Analytical',
                        line=dict(color='red', width=2.5, dash='dash'),
                        legendgroup='analytical',
                        showlegend=(var_idx == 0)  # Only show in legend once
                    )
                )
                
                # Numerical line
                frame_data.append(
                    go.Scatter(
                        x=sim_data['x'],
                        y=sim_data[var] * unit_dict[var],
                        mode='lines+markers',
                        name='Numerical',
                        line=dict(color='blue', width=2),
                        marker=dict(size=4),
                        legendgroup='numerical',
                        showlegend=(var_idx == 0)  # Only show in legend once
                    )
                )
        
        # Get VAR number from filename
        var_file_name = sim_data.get('var_file', f'VAR{frame_idx}')
        if 'VAR' in var_file_name:
            var_num = var_file_name.replace('VAR', '')
        else:
            var_num = str(frame_idx)
        
        formatted_title = format_experiment_title(run_name, max_line_length=60)
        frame_title = f"{formatted_title} - VAR {var_num}<br><sub>{var_file_name} | t = {sim_data['t']:.4e} s</sub>"
        
        frames.append(
            go.Frame(
                data=frame_data,
                name=str(frame_idx),
                layout=go.Layout(title_text=frame_title)
            )
        )
    
    # Set initial data (first frame)
    for var_idx, var in enumerate(variables):
        row, col = positions[var_idx]
        
        if var in sim_data_list[0] and var in analytical_data_list[0]:
            # Analytical
            fig.add_trace(
                go.Scatter(
                    x=analytical_data_list[0]['x'],
                    y=analytical_data_list[0][var] * unit_dict[var],
                    mode='lines',
                    name='Analytical',
                    line=dict(color='red', width=2.5, dash='dash'),
                    legendgroup='analytical',
                    showlegend=(var_idx == 0)
                ),
                row=row, col=col
            )
            
            # Numerical
            fig.add_trace(
                go.Scatter(
                    x=sim_data_list[0]['x'],
                    y=sim_data_list[0][var] * unit_dict[var],
                    mode='lines+markers',
                    name='Numerical',
                    line=dict(color='blue', width=2),
                    marker=dict(size=4),
                    legendgroup='numerical',
                    showlegend=(var_idx == 0)
                ),
                row=row, col=col
            )
    
    # Update axes labels and scales
    for var_idx, var in enumerate(variables):
        row, col = positions[var_idx]
        
        # Update x-axis
        fig.update_xaxes(title_text="x [kpc]", row=row, col=col)
        
        # Update y-axis with appropriate scale
        y_scale = var_scales.get(var, 'linear')
        fig.update_yaxes(
            title_text=var_labels.get(var, var),
            type=y_scale,
            row=row, col=col
        )
    
    # Update layout
    formatted_title = format_experiment_title(run_name, max_line_length=60)
    var_num_0 = sim_data_list[0].get('var_file', 'VAR0').replace('VAR', '')
    initial_title = f"{formatted_title} - VAR {var_num_0}<br><sub>{sim_data_list[0].get('var_file', 'VAR0')} | t = {sim_data_list[0]['t']:.4e} s</sub>"
    
    fig.update_layout(
        title_text=initial_title,
        title_x=0.5,
        title_font=dict(size=13),
        height=900,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="center",
            x=0.5
        ),
        updatemenus=[{
            'type': 'buttons',
            'showactive': False,
            'buttons': [
                {
                    'label': '▶ Play',
                    'method': 'animate',
                    'args': [None, {
                        'frame': {'duration': 500, 'redraw': True},
                        'fromcurrent': True,
                        'mode': 'immediate'
                    }]
                },
                {
                    'label': '⏸ Pause',
                    'method': 'animate',
                    'args': [[None], {
                        'frame': {'duration': 0, 'redraw': False},
                        'mode': 'immediate'
                    }]
                }
            ],
            'x': 0.1,
            'y': -0.15
        }],
        sliders=[{
            'active': 0,
            'yanchor': 'top',
            'y': -0.05,
            'xanchor': 'left',
            'currentvalue': {
                'prefix': 'Frame: ',
                'visible': True,
                'xanchor': 'right'
            },
            'pad': {'b': 10, 't': 50},
            'len': 0.9,
            'x': 0.1,
            'steps': [
                {
                    'args': [[frame.name], {
                        'frame': {'duration': 0, 'redraw': True},
                        'mode': 'immediate'
                    }],
                    'label': str(idx),
                    'method': 'animate'
                }
                for idx, frame in enumerate(frames)
            ]
        }]
    )
    
    # Add frames to figure
    fig.frames = frames
    
    # Save as HTML
    output_file = output_path / f"{run_name}_var_evolution.html"
    fig.write_html(output_file)
    logger.success(f"Saved interactive VAR evolution to {output_file}")


def create_error_evolution_plotly(
    spatial_errors: Dict,
    output_path: Path,
    run_name: str,
    unit_length: float = 1.0
):
    """
    Creates an interactive Plotly animation showing spatial error evolution.
    
    Args:
        spatial_errors: Dictionary containing spatial error data
        output_path: Directory to save the HTML animation
        run_name: Name of the run
        unit_length: Unit conversion factor for length
    """
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Validate unit_length
    if not np.isfinite(unit_length) or unit_length > 1e20 or unit_length == 0:
        logger.warning(f"Invalid unit_length value ({unit_length}). Using 1.0 instead.")
        unit_length = 1.0
    
    variables = ['rho', 'ux', 'pp', 'ee']
    var_labels = ['ρ', 'uₓ', 'p', 'e']
    
    # Filter to only variables with data
    valid_vars = [(var, label) for var, label in zip(variables, var_labels) if var in spatial_errors]
    
    if not valid_vars:
        logger.warning("No valid variables with spatial error data")
        return
    
    # Create subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[label for _, label in valid_vars],
        vertical_spacing=0.12,
        horizontal_spacing=0.10
    )
    
    positions = [(1, 1), (1, 2), (2, 1), (2, 2)]
    max_timesteps = max(len(spatial_errors[var]['errors_per_timestep']) for var, _ in valid_vars)
    
    # Prepare frames
    frames = []
    
    for frame_idx in range(max_timesteps):
        frame_data = []
        
        for var_idx, (var, label) in enumerate(valid_vars):
            row, col = positions[var_idx]
            
            # Safely convert x coordinates
            x_raw = spatial_errors[var]['x']
            try:
                x_coords = x_raw * unit_length
                if not np.all(np.isfinite(x_coords)):
                    x_coords = x_raw
            except (OverflowError, RuntimeWarning):
                x_coords = x_raw
            
            errors = spatial_errors[var]['errors_per_timestep'][frame_idx]
            
            # Note: Do NOT include xaxis/yaxis in frame traces - Plotly maps them automatically
            frame_data.append(
                go.Scatter(
                    x=x_coords,
                    y=errors,
                    mode='lines',
                    name='Spatial Error',
                    line=dict(color='#1f77b4', width=2),
                    legendgroup='error',
                    showlegend=(var_idx == 0)
                )
            )
        
        var_file = spatial_errors[list(spatial_errors.keys())[0]]['var_files'][frame_idx]
        timestep = spatial_errors[list(spatial_errors.keys())[0]]['timesteps'][frame_idx]
        var_num = var_file.replace('VAR', '') if 'VAR' in var_file else str(frame_idx)
        
        formatted_title = format_experiment_title(run_name, max_line_length=60)
        frame_title = f"{formatted_title} - VAR {var_num}<br><sub>{var_file} | t = {timestep:.4e} s</sub>"
        
        frames.append(
            go.Frame(
                data=frame_data,
                name=str(frame_idx),
                layout=go.Layout(title_text=frame_title)
            )
        )
    
    # Set initial data
    for var_idx, (var, label) in enumerate(valid_vars):
        row, col = positions[var_idx]
        
        x_raw = spatial_errors[var]['x']
        try:
            x_coords = x_raw * unit_length
            if not np.all(np.isfinite(x_coords)):
                x_coords = x_raw
        except (OverflowError, RuntimeWarning):
            x_coords = x_raw
        
        errors = spatial_errors[var]['errors_per_timestep'][0]
        
        fig.add_trace(
            go.Scatter(
                x=x_coords,
                y=errors,
                mode='lines',
                name='Spatial Error',
                line=dict(color='#1f77b4', width=2),
                legendgroup='error',
                showlegend=(var_idx == 0)
            ),
            row=row, col=col
        )
    
    # Calculate and set fixed axis limits (like matplotlib) to prevent jumping between frames
    x_label = 'x [kpc]' if unit_length != 1.0 else 'x [normalized]'
    for var_idx, (var, label) in enumerate(valid_vars):
        row, col = positions[var_idx]
        
        # Set x-axis range
        x_raw = spatial_errors[var]['x']
        try:
            x_coords = x_raw * unit_length
            if not np.all(np.isfinite(x_coords)):
                x_coords = x_raw
        except (OverflowError, RuntimeWarning):
            x_coords = x_raw
        
        fig.update_xaxes(
            title_text=x_label, 
            range=[x_coords.min(), x_coords.max()],
            row=row, col=col
        )
        
        # Calculate y-axis range across ALL timesteps (same as matplotlib)
        all_errors = np.concatenate(spatial_errors[var]['errors_per_timestep'])
        y_min = all_errors.min()
        y_max = all_errors.max()
        y_range = y_max - y_min if y_max > y_min else y_max * 0.1
        y_margin = 0.1 * y_range
        
        fig.update_yaxes(
            title_text=f"Error in {label}",
            range=[y_min - y_margin, y_max + y_margin],
            row=row, col=col
        )
    
    # Update layout
    var_file_0 = spatial_errors[list(spatial_errors.keys())[0]]['var_files'][0]
    timestep_0 = spatial_errors[list(spatial_errors.keys())[0]]['timesteps'][0]
    var_num_0 = var_file_0.replace('VAR', '') if 'VAR' in var_file_0 else '0'
    
    formatted_title = format_experiment_title(run_name, max_line_length=60)
    initial_title = f"{formatted_title} - VAR {var_num_0}<br><sub>{var_file_0} | t = {timestep_0:.4e} s</sub>"
    
    fig.update_layout(
        title_text=initial_title,
        title_x=0.5,
        title_font=dict(size=13),
        height=900,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="center",
            x=0.5
        ),
        updatemenus=[{
            'type': 'buttons',
            'showactive': False,
            'buttons': [
                {
                    'label': '▶ Play',
                    'method': 'animate',
                    'args': [None, {
                        'frame': {'duration': 500, 'redraw': True},
                        'fromcurrent': True,
                        'mode': 'immediate'
                    }]
                },
                {
                    'label': '⏸ Pause',
                    'method': 'animate',
                    'args': [[None], {
                        'frame': {'duration': 0, 'redraw': False},
                        'mode': 'immediate'
                    }]
                }
            ],
            'x': 0.1,
            'y': -0.15
        }],
        sliders=[{
            'active': 0,
            'yanchor': 'top',
            'y': -0.05,
            'xanchor': 'left',
            'currentvalue': {
                'prefix': 'Frame: ',
                'visible': True,
                'xanchor': 'right'
            },
            'pad': {'b': 10, 't': 50},
            'len': 0.9,
            'x': 0.1,
            'steps': [
                {
                    'args': [[frame.name], {
                        'frame': {'duration': 0, 'redraw': True},
                        'mode': 'immediate'
                    }],
                    'label': str(idx),
                    'method': 'animate'
                }
                for idx, frame in enumerate(frames)
            ]
        }]
    )
    
    fig.frames = frames
    
    # Save as HTML
    output_file = output_path / f"{run_name}_error_evolution.html"
    fig.write_html(output_file)
    logger.success(f"Saved interactive error evolution to {output_file}")


def create_combined_error_evolution_plotly(
    spatial_errors_dict: Dict[str, Dict],
    output_path: Path,
    run_name: str,
    unit_length: float = 1.0
):
    """
    Creates an interactive Plotly animation showing combined spatial error evolutions.
    
    Args:
        spatial_errors_dict: Dictionary where keys are error metric names and values are spatial error data
        output_path: Directory to save the HTML animation
        run_name: Name of the run
        unit_length: Unit conversion factor for length
    """
    output_path.mkdir(parents=True, exist_ok=True)
    
    if not np.isfinite(unit_length) or unit_length > 1e20 or unit_length == 0:
        logger.warning(f"Invalid unit_length value ({unit_length}). Using 1.0 instead.")
        unit_length = 1.0
    
    variables = ['rho', 'ux', 'pp', 'ee']
    var_labels = ['ρ', 'uₓ', 'p', 'e']
    
    # Color scheme for different error types
    colors = {
        'L1/LINF (Absolute)': '#1f77b4',
        'L2 (Squared)': '#ff7f0e',
        'Absolute': '#1f77b4',
        'Squared': '#ff7f0e',
        'L_inf': '#d62728'
    }
    
    linestyles = {
        'L1/LINF (Absolute)': 'solid',
        'L2 (Squared)': 'dash',
        'Absolute': 'solid',
        'Squared': 'dash',
        'L_inf': 'dot'
    }
    
    # Create subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=var_labels,
        vertical_spacing=0.12,
        horizontal_spacing=0.10
    )
    
    positions = [(1, 1), (1, 2), (2, 1), (2, 2)]
    first_error_type = list(spatial_errors_dict.keys())[0]
    max_timesteps = len(spatial_errors_dict[first_error_type]['rho']['errors_per_timestep'])
    
    # Prepare frames
    frames = []
    
    for frame_idx in range(max_timesteps):
        frame_data = []
        
        for var_idx, var in enumerate(variables):
            row, col = positions[var_idx]
            
            for error_type, spatial_errors in spatial_errors_dict.items():
                if var in spatial_errors:
                    x_coords = spatial_errors[var]['x'] * unit_length
                    errors = spatial_errors[var]['errors_per_timestep'][frame_idx]
                    
                    # Determine line style
                    dash_style = linestyles.get(error_type, 'solid')
                    color = colors.get(error_type, '#000000')
                    
                    # Note: Do NOT include xaxis/yaxis in frame traces - Plotly maps them automatically
                    frame_data.append(
                        go.Scatter(
                            x=x_coords,
                            y=errors,
                            mode='lines',
                            name=error_type,
                            line=dict(color=color, width=2.5, dash=dash_style),
                            legendgroup=error_type,
                            showlegend=(var_idx == 0)
                        )
                    )
        
        var_file = spatial_errors_dict[first_error_type]['rho']['var_files'][frame_idx]
        timestep = spatial_errors_dict[first_error_type]['rho']['timesteps'][frame_idx]
        var_num = var_file.replace('VAR', '') if 'VAR' in var_file else str(frame_idx)
        
        formatted_title = format_experiment_title(run_name, max_line_length=60)
        frame_title = f"{formatted_title} - VAR {var_num}<br><sub>{var_file} | t = {timestep:.4e} s</sub>"
        
        frames.append(
            go.Frame(
                data=frame_data,
                name=str(frame_idx),
                layout=go.Layout(title_text=frame_title)
            )
        )
    
    # Set initial data
    for var_idx, var in enumerate(variables):
        row, col = positions[var_idx]
        
        for error_type, spatial_errors in spatial_errors_dict.items():
            if var in spatial_errors:
                x_coords = spatial_errors[var]['x'] * unit_length
                errors = spatial_errors[var]['errors_per_timestep'][0]
                
                dash_style = linestyles.get(error_type, 'solid')
                color = colors.get(error_type, '#000000')
                
                fig.add_trace(
                    go.Scatter(
                        x=x_coords,
                        y=errors,
                        mode='lines',
                        name=error_type,
                        line=dict(color=color, width=2.5, dash=dash_style),
                        legendgroup=error_type,
                        showlegend=(var_idx == 0)
                    ),
                    row=row, col=col
                )
    
    # Calculate and set fixed axis limits (like matplotlib) to prevent jumping between frames
    for var_idx, (var, label) in enumerate(zip(variables, var_labels)):
        row, col = positions[var_idx]
        x_label = 'x [kpc]' if unit_length != 1.0 else 'x [normalized]'
        
        # Set x-axis range from first error type (all should have same x coords)
        x_coords = spatial_errors_dict[first_error_type][var]['x'] * unit_length
        fig.update_xaxes(
            title_text=x_label,
            range=[x_coords.min(), x_coords.max()],
            row=row, col=col
        )
        
        # Calculate y-axis range across ALL timesteps and ALL error types (same as matplotlib)
        all_errors = []
        for error_type, spatial_errors in spatial_errors_dict.items():
            if var in spatial_errors:
                all_errors.extend(np.concatenate(spatial_errors[var]['errors_per_timestep']))
        
        if all_errors:
            all_errors_array = np.array(all_errors)
            y_min = all_errors_array.min()
            y_max = all_errors_array.max()
            y_range = y_max - y_min if y_max > y_min else y_max * 0.1
            y_margin = 0.1 * y_range
            
            fig.update_yaxes(
                title_text=f"Error in {label}",
                range=[y_min - y_margin, y_max + y_margin],
                row=row, col=col
            )
        else:
            fig.update_yaxes(title_text=f"Error in {label}", row=row, col=col)
    
    # Update layout
    var_file_0 = spatial_errors_dict[first_error_type]['rho']['var_files'][0]
    timestep_0 = spatial_errors_dict[first_error_type]['rho']['timesteps'][0]
    var_num_0 = var_file_0.replace('VAR', '') if 'VAR' in var_file_0 else '0'
    
    formatted_title = format_experiment_title(run_name, max_line_length=60)
    initial_title = f"{formatted_title} - VAR {var_num_0}<br><sub>{var_file_0} | t = {timestep_0:.4e} s</sub>"
    
    fig.update_layout(
        title_text=initial_title,
        title_x=0.5,
        title_font=dict(size=13),
        height=900,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="center",
            x=0.5
        ),
        updatemenus=[{
            'type': 'buttons',
            'showactive': False,
            'buttons': [
                {
                    'label': '▶ Play',
                    'method': 'animate',
                    'args': [None, {
                        'frame': {'duration': 500, 'redraw': True},
                        'fromcurrent': True,
                        'mode': 'immediate'
                    }]
                },
                {
                    'label': '⏸ Pause',
                    'method': 'animate',
                    'args': [[None], {
                        'frame': {'duration': 0, 'redraw': False},
                        'mode': 'immediate'
                    }]
                }
            ],
            'x': 0.1,
            'y': -0.15
        }],
        sliders=[{
            'active': 0,
            'yanchor': 'top',
            'y': -0.05,
            'xanchor': 'left',
            'currentvalue': {
                'prefix': 'Frame: ',
                'visible': True,
                'xanchor': 'right'
            },
            'pad': {'b': 10, 't': 50},
            'len': 0.9,
            'x': 0.1,
            'steps': [
                {
                    'args': [[frame.name], {
                        'frame': {'duration': 0, 'redraw': True},
                        'mode': 'immediate'
                    }],
                    'label': str(idx),
                    'method': 'animate'
                }
                for idx, frame in enumerate(frames)
            ]
        }]
    )
    
    fig.frames = frames
    
    # Save as HTML
    output_file = output_path / f"{run_name}_combined_error_evolution.html"
    fig.write_html(output_file)
    logger.success(f"Saved interactive combined error evolution to {output_file}")


def show_3d_error_map(
    experiment_name: str,
    analysis_dir: Path,
    output_dir: Path,
    analyze_variables: List[str] = None
):
    """
    Create interactive 3D error map with 3-tier dropdowns during -a flag run.
    
    Creates a 3D surface plot showing error evolution with:
    - Dropdown 1: Branch name (from config)
    - Dropdown 2: Combination value in shortname form (parsed from run names)
    - Dropdown 3: Property of interest (rho, ux, pp, ee)
    
    Args:
        experiment_name: Name of the experiment
        analysis_dir: Root analysis directory
        output_dir: Directory to save the HTML output
        analyze_variables: List of variables to include (default: ['rho', 'ux', 'pp', 'ee'])
    """
    from src.core.constants import DIRS, FILES
    from src.experiment.naming import format_short_experiment_name
    import yaml
    import pickle
    
    if analyze_variables is None:
        analyze_variables = ['rho', 'ux', 'pp', 'ee']
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("Creating 3D error map with 3-tier dropdowns...")
    
    # Load config to get branches
    plan_file = DIRS.config / experiment_name / DIRS.plan_subdir / FILES.plan
    with open(plan_file, 'r') as f:
        plan = yaml.safe_load(f)
    
    # Extract branches from config
    branches = plan.get('branches', [])
    branch_names = [b['name'] for b in branches] if branches else ['default']
    
    # Load manifest to get all run names
    manifest_file = DIRS.runs / experiment_name / FILES.manifest
    with open(manifest_file, 'r') as f:
        all_run_names = [line.strip() for line in f if line.strip()]
    
    # Organize runs by branch
    runs_by_branch = {branch: [] for branch in branch_names}
    for run_name in all_run_names:
        matched = False
        for branch_name in branch_names:
            if branch_name in run_name:
                runs_by_branch[branch_name].append(run_name)
                matched = True
                break
        if not matched and 'default' in runs_by_branch:
            runs_by_branch['default'].append(run_name)
    
    # Remove empty branches
    runs_by_branch = {k: v for k, v in runs_by_branch.items() if v}
    
    if not runs_by_branch:
        logger.warning("No runs found for 3D error map")
        return
    
    # Variable labels
    var_labels = {
        'rho': 'Density (ρ)',
        'ux': 'Velocity (uₓ)',
        'pp': 'Pressure (p)',
        'ee': 'Energy (e)'
    }
    
    # Load cached error data for all runs
    cache_dir = analysis_dir / "error" / "cache"
    cached_data = {}
    
    for branch_name, run_names in runs_by_branch.items():
        for run_name in run_names:
            cache_file = cache_dir / f"{run_name}_normalized_errors.pkl"
            if cache_file.exists():
                try:
                    with open(cache_file, 'rb') as f:
                        normalized_errors = pickle.load(f)
                    cached_data[run_name] = {
                        'branch': branch_name,
                        'errors': normalized_errors,
                        'shortname': format_short_experiment_name(run_name, experiment_name)
                    }
                except Exception as e:
                    logger.warning(f"Failed to load cache for {run_name}: {e}")
    
    if not cached_data:
        logger.warning("No cached error data found for 3D error map")
        return
    
    # Select first available data for initial display
    first_branch = list(runs_by_branch.keys())[0]
    first_run = runs_by_branch[first_branch][0]
    first_var = analyze_variables[0]
    
    # Load initial surface
    initial_data = _create_3d_surface_from_cache(
        cached_data[first_run]['errors'], first_var
    )
    
    if initial_data is None:
        logger.error("Failed to create initial 3D surface")
        return
    
    # Create figure
    fig = go.Figure()
    
    # Add initial surface
    fig.add_trace(go.Surface(
        x=initial_data['x'],
        y=initial_data['y'],
        z=initial_data['z'],
        colorscale='Plasma',
        name=var_labels[first_var],
        colorbar=dict(title="Error<br>Magnitude")
    ))
    
    # Build dropdown buttons for 3-tier selection
    dropdown_buttons = []
    
    for branch_name in sorted(runs_by_branch.keys()):
        for run_name in sorted(runs_by_branch[branch_name]):
            if run_name not in cached_data:
                continue
            
            shortname = cached_data[run_name]['shortname']
            
            for var in analyze_variables:
                # Create surface data
                surface_data = _create_3d_surface_from_cache(
                    cached_data[run_name]['errors'], var
                )
                
                if surface_data is None:
                    continue
                
                # Create hierarchical button label
                button_label = f"{branch_name} > {shortname} > {var.upper()}"
                
                button = dict(
                    label=button_label,
                    method='update',
                    args=[
                        {
                            'x': [surface_data['x']],
                            'y': [surface_data['y']],
                            'z': [surface_data['z']]
                        },
                        {
                            'title': f"3D Error Map: {var_labels[var]}<br><sub>Branch: {branch_name} | {shortname}</sub>"
                        }
                    ]
                )
                dropdown_buttons.append(button)
    
    # Update layout with dropdown
    fig.update_layout(
        title=f"3D Error Map: {var_labels[first_var]}<br><sub>Branch: {first_branch} | {cached_data[first_run]['shortname']}</sub>",
        scene=dict(
            xaxis=dict(title='Position (x) [kpc]'),
            yaxis=dict(title='Time [code units]'),
            zaxis=dict(title='Error Magnitude', type='log'),
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.3)
            )
        ),
        updatemenus=[
            dict(
                buttons=dropdown_buttons,
                direction='down',
                pad={'r': 10, 't': 10},
                showactive=True,
                x=0.01,
                xanchor='left',
                y=1.15,
                yanchor='top',
                bgcolor='rgba(255, 255, 255, 0.9)',
                bordercolor='#888',
                borderwidth=1
            )
        ],
        height=800,
        width=1400,
        margin=dict(t=150)
    )
    
    # Save as HTML
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d")
    output_file = output_dir / f"{timestamp}_3d_error_map.html"
    fig.write_html(str(output_file))
    logger.success(f"Saved 3D error map with 3-tier dropdowns to {output_file}")


def _create_3d_surface_from_cache(
    normalized_errors: Dict,
    variable: str
) -> Optional[Dict[str, np.ndarray]]:
    """
    Create 3D surface data from cached normalized errors.
    
    Args:
        normalized_errors: Cached normalized error data
        variable: Variable to visualize
    
    Returns:
        Dictionary with 'x', 'y', 'z' arrays or None if failed
    """
    if variable not in normalized_errors:
        return None
    
    try:
        var_data = normalized_errors[variable]
        x_coords = var_data['x_coords']
        timesteps = var_data['timesteps']
        error_matrix = var_data['relative_error_field']
        
        # Create meshgrid for 3D surface
        X, Y = np.meshgrid(x_coords, timesteps)
        Z = error_matrix
        
        # Replace invalid values
        Z = np.where(np.isfinite(Z) & (Z > 0), Z, np.nan)
        
        return {
            'x': X,
            'y': Y,
            'z': Z
        }
    except Exception as e:
        logger.error(f"Failed to create 3D surface for {variable}: {e}")
        return None


__all__ = [
    'create_var_evolution_plotly',
    'create_error_evolution_plotly',
    'create_combined_error_evolution_plotly',
    'show_3d_error_map',
]

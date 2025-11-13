# src/visualization/plots_plotly.py
"""
Simplified Plotly-based visualization focused on cumulative normalized error analysis.

This module provides a single focused visualization: cumulative normalized error
over time with dual x-axes (time as primary, VAR file number as secondary).
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from pathlib import Path
from loguru import logger
from typing import Dict, List, Optional

from src.experiment.naming import format_experiment_title


def create_cumulative_error_over_time(
    normalized_errors: Dict,
    output_path: Path,
    run_name: str,
    unit_length: float = 1.0,
    variables: List[str] = ['rho', 'ux', 'pp', 'ee']
):
    """
    Creates an interactive plot showing cumulative normalized error over time.
    
    This visualization shows how the total error accumulates across the simulation,
    with time as the primary x-axis and VAR file numbers as a secondary reference.
    
    Args:
        normalized_errors: Dictionary containing normalized error data with structure:
            {
                'var_name': {
                    'relative_error_field': np.ndarray,  # [timestep, space]
                    'timesteps': list,                    # List of time values
                    'x_coords': np.ndarray               # Spatial coordinates
                }
            }
        output_path: Directory to save the HTML visualization
        run_name: Name of the run for title
        unit_length: Unit conversion factor for length
        variables: List of variables to plot
    """
    output_path.mkdir(parents=True, exist_ok=True)
    
    var_labels = {
        'rho': 'Density (ρ)',
        'ux': 'Velocity (uₓ)',
        'pp': 'Pressure (p)',
        'ee': 'Energy (e)'
    }
    
    # Filter to only variables with data
    valid_vars = [(var, var_labels.get(var, var)) for var in variables if var in normalized_errors]
    
    if not valid_vars:
        logger.warning(f"No valid variables with normalized error data for {run_name}")
        return
    
    # Create subplots (2x2 grid for up to 4 variables)
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[label for _, label in valid_vars],
        vertical_spacing=0.12,
        horizontal_spacing=0.10,
        specs=[[{"secondary_x": True}, {"secondary_x": True}],
               [{"secondary_x": True}, {"secondary_x": True}]]
    )
    
    positions = [(1, 1), (1, 2), (2, 1), (2, 2)]
    
    for var_idx, (var, label) in enumerate(valid_vars):
        row, col = positions[var_idx]
        
        var_data = normalized_errors[var]
        timesteps = np.array(var_data['timesteps'])
        error_field = var_data['relative_error_field']
        
        # Calculate cumulative normalized error (sum across spatial dimension for each timestep)
        cumulative_error = np.sum(error_field, axis=1) / error_field.shape[1]
        
        # Create VAR file numbers (0, 1, 2, ...)
        var_numbers = np.arange(len(timesteps))
        
        # Add trace for cumulative error
        fig.add_trace(
            go.Scatter(
                x=timesteps,
                y=cumulative_error,
                mode='lines+markers',
                name=label,
                line=dict(color='#1f77b4', width=2.5),
                marker=dict(size=6, symbol='circle'),
                legendgroup=var,
                showlegend=(var_idx == 0),
                hovertemplate=(
                    f'{label}<br>'
                    'Time: %{x:.4e} s<br>'
                    'Cumulative Error: %{y:.4e}<br>'
                    '<extra></extra>'
                )
            ),
            row=row, col=col
        )
        
        # Update primary x-axis (time)
        fig.update_xaxes(
            title_text="Time [s]",
            row=row, col=col
        )
        
        # Update secondary x-axis (VAR file numbers)
        # We'll add tick labels for VAR numbers
        var_tick_positions = timesteps[::max(1, len(timesteps)//10)]  # Show ~10 ticks
        var_tick_labels = [f"VAR{i}" for i in var_numbers[::max(1, len(timesteps)//10)]]
        
        fig.update_xaxes(
            title_text="VAR File Number",
            overlaying='x',
            side='top',
            tickmode='array',
            tickvals=var_tick_positions,
            ticktext=var_tick_labels,
            row=row, col=col,
            secondary_x=True
        )
        
        # Update y-axis
        fig.update_yaxes(
            title_text="Cumulative Normalized Error",
            type='log',
            row=row, col=col
        )
    
    # Update overall layout
    formatted_title = format_experiment_title(run_name, max_line_length=60)
    
    fig.update_layout(
        title_text=f"{formatted_title}<br><sub>Cumulative Normalized Error Over Time</sub>",
        title_x=0.5,
        title_font=dict(size=14),
        height=900,
        width=1400,
        showlegend=False,  # Remove legend since we have subplot titles
        hovermode='closest',
        plot_bgcolor='rgba(240, 240, 240, 0.5)'
    )
    
    # Add grid
    fig.update_xaxes(gridcolor='lightgray', griddash='dash')
    fig.update_yaxes(gridcolor='lightgray', griddash='dash')
    
    # Save as HTML
    output_file = output_path / f"{run_name}_cumulative_error_over_time.html"
    fig.write_html(str(output_file))
    logger.success(f"Saved cumulative error over time plot to {output_file}")


__all__ = [
    'create_cumulative_error_over_time',
]

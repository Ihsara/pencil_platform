"""
Spacetime Error Visualization Notebook - "Mind the Gap" Interactive Plot

This notebook creates an interactive Plotly visualization showing error evolution
across space and time, with the size of markers representing error magnitude at
each grid point and timestep. The play button allows animation through timesteps.

Usage:
    python notebooks/spacetime_error_visualization.py --experiment <experiment_name> --run <run_name>
    
Or run interactively in Jupyter:
    jupyter notebook notebooks/spacetime_error_visualization.ipynb
"""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from pathlib import Path
import sys
import argparse
import json

# Add project root to path
# Handle both script execution and interactive environments (Jupyter, IPython)
try:
    PROJECT_ROOT = Path(__file__).parent.parent
except NameError:
    # If __file__ is not defined (e.g., in Jupyter), use current working directory
    PROJECT_ROOT = Path.cwd()
    # If we're in the notebooks directory, go up one level
    if PROJECT_ROOT.name == 'notebooks':
        PROJECT_ROOT = PROJECT_ROOT.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis.data_prep import (
    prepare_spacetime_error_data,
    load_spacetime_data_from_json,
    get_error_statistics
)
from src.analysis.errors import calculate_normalized_spatial_errors
from src.workflows.analysis_pipeline import load_all_var_files, get_analytical_solution
from src.core.constants import DIRS
from loguru import logger


def create_mind_the_gap_plot(
    prepared_data: dict,
    title: str = "Spacetime Error Evolution",
    height: int = 800,
    width: int = 1400
) -> go.Figure:
    """
    Create interactive "mind the gap" visualization with Plotly.
    
    This creates a scatter plot where:
    - X-axis: Spatial position
    - Y-axis: Time
    - Marker size: Error magnitude
    - Marker color: Error magnitude (log scale)
    - Play button: Animate through timesteps
    
    Args:
        prepared_data: Dictionary from prepare_spacetime_error_data
        title: Plot title
        height: Plot height in pixels
        width: Plot width in pixels
        
    Returns:
        Plotly Figure object
    """
    x_coords = prepared_data['x_coords']
    timesteps = prepared_data['timesteps']
    error_matrix = prepared_data['error_matrix']
    variable = prepared_data['variable']
    error_type = prepared_data['error_type']
    
    # Get statistics for colorscale
    stats = get_error_statistics(error_matrix)
    
    # Create meshgrid for all points
    X, T_indices = np.meshgrid(x_coords, range(len(timesteps)))
    
    # Flatten arrays for scatter plot
    x_flat = X.flatten()
    t_indices_flat = T_indices.flatten()
    errors_flat = error_matrix.flatten()
    
    # Get corresponding timestep values
    t_values = np.array([timesteps[int(idx)] for idx in t_indices_flat])
    
    # Filter out invalid values
    valid_mask = np.isfinite(errors_flat) & (errors_flat > 0)
    x_valid = x_flat[valid_mask]
    t_valid = t_values[valid_mask]
    errors_valid = errors_flat[valid_mask]
    t_indices_valid = t_indices_flat[valid_mask]
    
    # Normalize marker sizes (use log scale for better visualization)
    log_errors = np.log10(errors_valid + 1e-10)
    size_min, size_max = 2, 30
    sizes = size_min + (size_max - size_min) * (log_errors - log_errors.min()) / (log_errors.max() - log_errors.min())
    
    # Create frames for animation
    frames = []
    for t_idx in range(len(timesteps)):
        # Get data for this timestep
        mask = t_indices_valid == t_idx
        
        frame_data = go.Scatter(
            x=x_valid[mask],
            y=t_valid[mask],
            mode='markers',
            marker=dict(
                size=sizes[mask],
                color=errors_valid[mask],
                colorscale='Plasma',
                cmin=stats['min'],
                cmax=stats['p99'],  # Use p99 to avoid outliers
                colorbar=dict(
                    title=f"{error_type.capitalize()}<br>Error",
                    tickformat='.2e'
                ),
                line=dict(width=0.5, color='white')
            ),
            text=[f"x={x:.3f} kpc<br>t={t:.3e}<br>error={e:.3e}" 
                  for x, t, e in zip(x_valid[mask], t_valid[mask], errors_valid[mask])],
            hovertemplate='%{text}<extra></extra>',
            name=f't={timesteps[t_idx]:.3e}'
        )
        
        frames.append(go.Frame(
            data=[frame_data],
            name=str(t_idx),
            layout=go.Layout(
                title_text=f"{title}<br>Timestep: {t_idx}/{len(timesteps)-1}, t={timesteps[t_idx]:.3e}"
            )
        ))
    
    # Create initial plot (all timesteps)
    fig = go.Figure(
        data=[go.Scatter(
            x=x_valid,
            y=t_valid,
            mode='markers',
            marker=dict(
                size=sizes,
                color=errors_valid,
                colorscale='Plasma',
                cmin=stats['min'],
                cmax=stats['p99'],
                colorbar=dict(
                    title=f"{error_type.capitalize()}<br>Error",
                    tickformat='.2e',
                    x=1.02
                ),
                line=dict(width=0.5, color='white')
            ),
            text=[f"x={x:.3f} kpc<br>t={t:.3e}<br>error={e:.3e}" 
                  for x, t, e in zip(x_valid, t_valid, errors_valid)],
            hovertemplate='%{text}<extra></extra>',
            name='All Timesteps'
        )],
        frames=frames
    )
    
    # Add max error marker
    if prepared_data['max_error']:
        max_err = prepared_data['max_error']
        fig.add_trace(go.Scatter(
            x=[max_err['x']],
            y=[max_err['time']],
            mode='markers',
            marker=dict(
                size=40,
                color='red',
                symbol='star',
                line=dict(width=2, color='white')
            ),
            text=[f"MAX ERROR<br>x={max_err['x']:.3f} kpc<br>t={max_err['time']:.3e}<br>error={max_err['value']:.3e}"],
            hovertemplate='%{text}<extra></extra>',
            name='Max Error',
            showlegend=True
        ))
    
    # Layout configuration
    fig.update_layout(
        title=dict(
            text=f"{title}<br><sub>Variable: {variable.upper()}, Error Type: {error_type.capitalize()}</sub>",
            x=0.5,
            xanchor='center'
        ),
        xaxis=dict(
            title='Position (x) [kpc]',
            gridcolor='lightgray',
            showgrid=True
        ),
        yaxis=dict(
            title='Time [code units]',
            gridcolor='lightgray',
            showgrid=True
        ),
        height=height,
        width=width,
        hovermode='closest',
        plot_bgcolor='rgba(240, 240, 240, 0.5)',
        updatemenus=[
            dict(
                type='buttons',
                showactive=False,
                buttons=[
                    dict(
                        label='Play',
                        method='animate',
                        args=[None, dict(
                            frame=dict(duration=500, redraw=True),
                            fromcurrent=True,
                            mode='immediate',
                            transition=dict(duration=300)
                        )]
                    ),
                    dict(
                        label='Pause',
                        method='animate',
                        args=[[None], dict(
                            frame=dict(duration=0, redraw=False),
                            mode='immediate',
                            transition=dict(duration=0)
                        )]
                    )
                ],
                x=0.1,
                y=1.15,
                xanchor='left',
                yanchor='top'
            )
        ],
        sliders=[dict(
            active=0,
            yanchor='top',
            y=-0.1,
            xanchor='left',
            currentvalue=dict(
                prefix='Timestep: ',
                visible=True,
                xanchor='center'
            ),
            pad=dict(b=10, t=50),
            len=0.9,
            x=0.05,
            steps=[
                dict(
                    args=[[f.name], dict(
                        frame=dict(duration=500, redraw=True),
                        mode='immediate',
                        transition=dict(duration=300)
                    )],
                    label=f"{i}",
                    method='animate'
                )
                for i, f in enumerate(frames)
            ]
        )]
    )
    
    # Add annotations for statistics
    stats_text = (
        f"Statistics:<br>"
        f"Mean: {stats['mean']:.3e}<br>"
        f"Median: {stats['median']:.3e}<br>"
        f"Max: {stats['max']:.3e}<br>"
        f"Std: {stats['std']:.3e}"
    )
    
    fig.add_annotation(
        text=stats_text,
        xref="paper", yref="paper",
        x=1.0, y=0.02,
        xanchor='right', yanchor='bottom',
        showarrow=False,
        bgcolor="white",
        bordercolor="gray",
        borderwidth=1,
        font=dict(size=10)
    )
    
    return fig


def create_multi_variable_dashboard(
    run_data: dict,
    experiment_name: str,
    run_name: str,
    variables: list = ['rho', 'ux', 'pp', 'ee']
) -> go.Figure:
    """
    Create dashboard with multiple variables in subplots.
    
    Args:
        run_data: Dictionary with normalized_errors
        experiment_name: Name of experiment
        run_name: Name of run
        variables: List of variables to plot
        
    Returns:
        Plotly Figure with subplots
    """
    from plotly.subplots import make_subplots
    
    # Create 2x2 subplot grid
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[f"{var.upper()}" for var in variables],
        vertical_spacing=0.12,
        horizontal_spacing=0.08
    )
    
    var_labels = {
        'rho': 'ρ [g cm⁻³]',
        'ux': 'uₓ [km s⁻¹]',
        'pp': 'p [dyn cm⁻²]',
        'ee': 'e [km² s⁻²]'
    }
    
    for idx, var in enumerate(variables):
        row = idx // 2 + 1
        col = idx % 2 + 1
        
        if var not in run_data:
            continue
        
        var_data = run_data[var]
        x_coords = var_data['x_coords']
        timesteps = var_data['timesteps']
        error_matrix = var_data['relative_error_field']
        
        # Create heatmap for this variable
        fig.add_trace(
            go.Heatmap(
                z=error_matrix,
                x=x_coords,
                y=list(range(len(timesteps))),
                colorscale='Plasma',
                colorbar=dict(
                    title="Relative<br>Error",
                    tickformat='.2e',
                    len=0.4,
                    y=0.75 - (idx // 2) * 0.5,
                    yanchor='middle'
                ),
                hovertemplate='x: %{x:.3f} kpc<br>Timestep: %{y}<br>Error: %{z:.3e}<extra></extra>'
            ),
            row=row, col=col
        )
        
        # Add max error marker
        if 'max_error_location' in var_data:
            max_loc = var_data['max_error_location']
            fig.add_trace(
                go.Scatter(
                    x=[max_loc['x']],
                    y=[max_loc['time_index']],
                    mode='markers',
                    marker=dict(size=15, color='red', symbol='star', line=dict(width=2, color='white')),
                    showlegend=False,
                    hovertext=f"Max: {max_loc['value']:.3e}",
                    hoverinfo='text'
                ),
                row=row, col=col
            )
    
    # Update axes
    for idx in range(1, 5):
        row = (idx - 1) // 2 + 1
        col = (idx - 1) % 2 + 1
        fig.update_xaxes(title_text="Position (x) [kpc]", row=row, col=col)
        fig.update_yaxes(title_text="Timestep Index", row=row, col=col)
    
    fig.update_layout(
        title_text=f"Spacetime Error Dashboard: {run_name}<br><sub>{experiment_name}</sub>",
        height=900,
        width=1600,
        showlegend=False
    )
    
    return fig


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description='Create spacetime error visualization')
    parser.add_argument('--experiment', required=True, help='Experiment name')
    parser.add_argument('--run', required=True, help='Run name')
    parser.add_argument('--variable', default='rho', help='Variable to visualize (default: rho)')
    parser.add_argument('--output', help='Output HTML file path (optional)')
    parser.add_argument('--dashboard', action='store_true', help='Create multi-variable dashboard')
    
    args = parser.parse_args()
    
    # Load data
    logger.info(f"Loading data for {args.experiment}/{args.run}")
    
    # Load from HPC directory
    import yaml
    plan_file = DIRS.config / args.experiment / DIRS.plan_subdir / "sweep.yaml"
    with open(plan_file, 'r') as f:
        plan = yaml.safe_load(f)
    
    hpc_run_base_dir = Path(plan['hpc']['run_base_dir'])
    run_path = hpc_run_base_dir / args.run
    
    # Load VAR files
    all_sim_data = load_all_var_files(run_path)
    if not all_sim_data:
        logger.error(f"Failed to load VAR files from {run_path}")
        return
    
    # Generate analytical solutions
    all_analytical_data = [
        get_analytical_solution(s['params'], s['x'], s['t']) 
        for s in all_sim_data
    ]
    
    # Calculate normalized errors
    normalized_errors = calculate_normalized_spatial_errors(
        all_sim_data,
        all_analytical_data,
        variables=['rho', 'ux', 'pp', 'ee']
    )
    
    # Get unit length
    unit_length = all_sim_data[0]['params'].unit_length if all_sim_data else 1.0
    
    if args.dashboard:
        # Create dashboard
        fig = create_multi_variable_dashboard(
            normalized_errors,
            args.experiment,
            args.run
        )
    else:
        # Prepare data for single variable
        prepared_data = prepare_spacetime_error_data(
            normalized_errors,
            args.variable,
            unit_length,
            use_relative=True
        )
        
        if not prepared_data:
            logger.error(f"Failed to prepare data for variable {args.variable}")
            return
        
        # Create visualization
        fig = create_mind_the_gap_plot(
            prepared_data,
            title=f"Mind the Gap: {args.run}"
        )
    
    # Save or show
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.write_html(str(output_path))
        logger.success(f"Saved visualization to {output_path}")
    else:
        fig.show()


if __name__ == '__main__':
    main()

"""
Spacetime Error Visualization Notebook - "Mind the Gap" Interactive Plot

This notebook creates an interactive Plotly visualization showing error evolution
across space and time, with the size of markers representing error magnitude at
each grid point and timestep. The play button allows animation through timesteps.

Usage:
    Command-line:
        python notebooks/spacetime_error_visualization.py --experiment <experiment_name> --run <run_name>
    
    Jupyter/Interactive:
        from notebooks.spacetime_error_visualization import create_visualization_for_run
        fig = create_visualization_for_run('shocktube_phase1', 'run_001')
        fig.show()
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
                cmax=stats['percentiles']['p99'],  # Use p99 to avoid outliers
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
                cmax=stats['percentiles']['p99'],
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


def create_visualization_for_run(
    experiment_name: str,
    run_name: str,
    variable: str = 'rho',
    output_path: str = None,
    dashboard: bool = False
) -> go.Figure:
    """
    Create visualization for a specific run (Jupyter-friendly API).
    
    Args:
        experiment_name: Name of the experiment
        run_name: Name of the run
        variable: Variable to visualize ('rho', 'ux', 'pp', 'ee')
        output_path: Path to save HTML file (optional)
        dashboard: If True, create multi-variable dashboard
        
    Returns:
        Plotly Figure object
        
    Example:
        >>> fig = create_visualization_for_run('shocktube_phase1', 'run_001')
        >>> fig.show()
    """
    import yaml
    
    # Load data
    logger.info(f"Loading data for {experiment_name}/{run_name}")
    
    # Load from HPC directory
    plan_file = DIRS.config / experiment_name / DIRS.plan_subdir / "sweep.yaml"
    with open(plan_file, 'r') as f:
        plan = yaml.safe_load(f)
    
    hpc_run_base_dir = Path(plan['hpc']['run_base_dir'])
    run_path = hpc_run_base_dir / run_name
    
    # Load VAR files
    all_sim_data = load_all_var_files(run_path)
    if not all_sim_data:
        logger.error(f"Failed to load VAR files from {run_path}")
        return None
    
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
    
    if dashboard:
        # Create dashboard
        fig = create_multi_variable_dashboard(
            normalized_errors,
            experiment_name,
            run_name
        )
    else:
        # Prepare data for single variable
        prepared_data = prepare_spacetime_error_data(
            normalized_errors,
            variable,
            unit_length,
            use_relative=True
        )
        
        if not prepared_data:
            logger.error(f"Failed to prepare data for variable {variable}")
            return None
        
        # Create visualization
        fig = create_mind_the_gap_plot(
            prepared_data,
            title=f"Mind the Gap: {run_name}"
        )
    
    # Save if output path specified
    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        fig.write_html(str(output_file))
        logger.success(f"Saved visualization to {output_file}")
    
    return fig


def list_available_runs(experiment_name: str) -> list:
    """
    List all available runs for an experiment.
    
    Args:
        experiment_name: Name of the experiment
        
    Returns:
        List of run names
    """
    import yaml
    
    try:
        plan_file = DIRS.config / experiment_name / DIRS.plan_subdir / "sweep.yaml"
        with open(plan_file, 'r') as f:
            plan = yaml.safe_load(f)
        
        manifest_file = DIRS.runs / experiment_name / "run_manifest.txt"
        if manifest_file.exists():
            with open(manifest_file, 'r') as f:
                run_names = [line.strip() for line in f if line.strip()]
            return run_names
        else:
            logger.warning(f"Manifest file not found: {manifest_file}")
            return []
    except Exception as e:
        logger.error(f"Failed to list runs: {e}")
        return []


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description='Create spacetime error visualization')
    parser.add_argument('--experiment', required=True, help='Experiment name')
    parser.add_argument('--run', help='Run name (optional - if not provided, processes all runs)')
    parser.add_argument('--variable', default='rho', help='Variable to visualize (default: rho)')
    parser.add_argument('--output-dir', help='Output directory for HTML files (optional)')
    parser.add_argument('--dashboard', action='store_true', help='Create multi-variable dashboard')
    parser.add_argument('--interactive', action='store_true', help='List available runs and prompt for selection')
    parser.add_argument('--list-runs', action='store_true', help='List available runs and exit')
    
    args = parser.parse_args()
    
    # Get available runs
    available_runs = list_available_runs(args.experiment)
    
    if not available_runs:
        logger.error(f"No runs found for experiment '{args.experiment}'")
        return
    
    # List runs and exit if requested
    if args.list_runs:
        logger.info(f"Available runs for '{args.experiment}':")
        for idx, run in enumerate(available_runs, 1):
            print(f"  {idx}. {run}")
        print(f"\nTotal: {len(available_runs)} runs")
        return
    
    # Interactive mode: let user select runs
    if args.interactive:
        logger.info(f"Available runs for '{args.experiment}':")
        for idx, run in enumerate(available_runs, 1):
            print(f"  {idx}. {run}")
        print(f"\nTotal: {len(available_runs)} runs")
        print("\nOptions:")
        print("  - Enter run number(s) separated by commas (e.g., 1,3,5)")
        print("  - Enter 'all' to process all runs")
        print("  - Press Enter to cancel")
        
        selection = input("\nYour selection: ").strip()
        
        if not selection:
            print("Cancelled.")
            return
        
        if selection.lower() == 'all':
            selected_runs = available_runs
        else:
            try:
                indices = [int(x.strip()) - 1 for x in selection.split(',')]
                selected_runs = [available_runs[i] for i in indices if 0 <= i < len(available_runs)]
                if not selected_runs:
                    logger.error("No valid run numbers selected")
                    return
            except (ValueError, IndexError) as e:
                logger.error(f"Invalid selection: {e}")
                return
    
    # Determine which runs to process
    elif args.run:
        # Single run specified
        if args.run not in available_runs:
            logger.error(f"Run '{args.run}' not found in experiment '{args.experiment}'")
            logger.info(f"Available runs: {', '.join(available_runs[:5])}{'...' if len(available_runs) > 5 else ''}")
            return
        selected_runs = [args.run]
    else:
        # No run specified - process all runs
        logger.info(f"No run specified - processing all {len(available_runs)} runs")
        selected_runs = available_runs
    
    # Process selected runs
    logger.info(f"Processing {len(selected_runs)} run(s)...")
    
    # Determine if we should save files
    save_files = args.output_dir or len(selected_runs) > 1
    
    for idx, run_name in enumerate(selected_runs, 1):
        logger.info(f"\n[{idx}/{len(selected_runs)}] Processing: {run_name}")
        
        # Determine output path
        if args.output_dir:
            # Use user-specified directory
            output_dir = Path(args.output_dir) / run_name
        else:
            # Use standard analysis directory structure:
            # analysis/<experiment>/error/mind_the_gap/<run_name>/
            output_dir = DIRS.root / "analysis" / args.experiment / "error" / "mind_the_gap" / run_name
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if save_files:
            # Save to organized structure
            filename = 'dashboard.html' if args.dashboard else f'{args.variable}.html'
            output_path = output_dir / filename
        else:
            # Single run, display only (don't save unless output_dir specified)
            output_path = None
        
        # Create visualization
        fig = create_visualization_for_run(
            experiment_name=args.experiment,
            run_name=run_name,
            variable=args.variable,
            output_path=str(output_path) if output_path else None,
            dashboard=args.dashboard
        )
        
        # Show first one if not saving to files
        if fig and not save_files:
            fig.show()
        elif fig and save_files:
            logger.success(f"  ✓ Saved: {output_path}")
    
    if save_files:
        base_dir = Path(args.output_dir) if args.output_dir else (DIRS.root / "analysis" / args.experiment / "error" / "mind_the_gap")
        logger.success(f"\n✓ All {len(selected_runs)} visualization(s) saved to: {base_dir}")


if __name__ == '__main__':
    main()

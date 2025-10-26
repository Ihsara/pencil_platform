"""
Discovery Visualization Module - 3D Interactive Error Maps

This module provides 3D interactive surface plots for exploring error patterns
with dropdown menus for experiment, branch, run, and element selection.

Based on: https://plotly.com/python/dropdowns/

Axes:
- X: Distance (spatial position)
- Y: Time
- Z: Error magnitude
"""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from pathlib import Path
import sys
import yaml
from typing import List, Dict, Optional, Tuple
import json

# Add project root to path
try:
    PROJECT_ROOT = Path(__file__).parent.parent
except NameError:
    PROJECT_ROOT = Path.cwd()
    if PROJECT_ROOT.name == 'notebooks':
        PROJECT_ROOT = PROJECT_ROOT.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis.errors import calculate_normalized_spatial_errors
from src.workflows.analysis_pipeline import load_all_var_files, get_analytical_solution
from src.core.constants import DIRS
from loguru import logger


def create_3d_error_map_with_dropdowns(
    experiment_names: Optional[List[str]] = None,
    default_experiment: Optional[str] = None,
    default_element: str = 'rho'
) -> go.Figure:
    """
    Create 3D error visualization with dropdown menus.
    
    Dropdowns control:
    1. Experiment name
    2. Branch (extracted from run names)
    3. Run name
    4. Element (rho, ux, pp, ee)
    
    Axes:
    - X: Distance (spatial position)
    - Y: Time (timestep)
    - Z: Magnitude of the selected element's error
    
    Args:
        experiment_names: List of experiments to include (if None, auto-detect)
        default_experiment: Default experiment to show
        default_element: Default element to show
        
    Returns:
        Plotly Figure with dropdown controls
    """
    # Auto-detect experiments if not provided
    if experiment_names is None:
        analysis_dir = DIRS.root / "analysis"
        if analysis_dir.exists():
            experiment_names = [d.name for d in analysis_dir.iterdir() if d.is_dir()]
        else:
            logger.error("Analysis directory not found")
            return None
    
    if not experiment_names:
        logger.error("No experiments found")
        return None
    
    # Use first experiment as default if not specified
    if default_experiment is None or default_experiment not in experiment_names:
        default_experiment = experiment_names[0]
    
    # Load data for all experiments
    all_data = {}
    
    for exp_name in experiment_names:
        logger.info(f"Loading experiment: {exp_name}")
        
        # Get run list
        try:
            manifest_file = DIRS.runs / exp_name / "run_manifest.txt"
            if not manifest_file.exists():
                logger.warning(f"No manifest for {exp_name}")
                continue
            
            with open(manifest_file, 'r') as f:
                run_names = [line.strip() for line in f if line.strip()]
            
            # Organize runs by branch (extract branch from run name pattern)
            branches = {}
            for run_name in run_names:
                # Try to extract branch identifier from run name
                # Pattern: res400_hyper3_nu9e-08_chi9e-08_r1_nu0.5_dg
                # Branch could be identified by hyper type, resolution, etc.
                parts = run_name.split('_')
                
                # Simple heuristic: use first few parts as branch identifier
                if len(parts) >= 3:
                    branch_id = '_'.join(parts[:3])  # e.g., "res400_hyper3_nu9e"
                else:
                    branch_id = "default"
                
                if branch_id not in branches:
                    branches[branch_id] = []
                branches[branch_id].append(run_name)
            
            all_data[exp_name] = {
                'branches': branches,
                'run_names': run_names
            }
            
        except Exception as e:
            logger.error(f"Failed to load experiment {exp_name}: {e}")
            continue
    
    if not all_data:
        logger.error("No valid experiment data loaded")
        return None
    
    # Elements to analyze
    elements = ['rho', 'ux', 'pp', 'ee']
    element_labels = {
        'rho': 'Density (ρ)',
        'ux': 'Velocity (uₓ)',
        'pp': 'Pressure (p)',
        'ee': 'Energy (e)'
    }
    
    # Create initial 3D surface for default experiment/branch/run/element
    initial_exp = default_experiment
    initial_branch = list(all_data[initial_exp]['branches'].keys())[0]
    initial_run = all_data[initial_exp]['branches'][initial_branch][0]
    initial_element = default_element
    
    # Load initial data
    initial_surface = _load_3d_error_surface(initial_exp, initial_run, initial_element)
    
    if initial_surface is None:
        logger.error("Failed to load initial surface data")
        return None
    
    # Create figure
    fig = go.Figure()
    
    # Add initial surface
    fig.add_trace(go.Surface(
        x=initial_surface['x'],
        y=initial_surface['y'],
        z=initial_surface['z'],
        colorscale='Plasma',
        name=f"{initial_element.upper()}",
        colorbar=dict(title="Error<br>Magnitude")
    ))
    
    # Build dropdown buttons for each combination
    dropdown_buttons = []
    
    for exp_name in sorted(all_data.keys()):
        for branch_name in sorted(all_data[exp_name]['branches'].keys()):
            for run_name in sorted(all_data[exp_name]['branches'][branch_name]):
                for element in elements:
                    # Load surface data
                    surface_data = _load_3d_error_surface(exp_name, run_name, element)
                    
                    if surface_data is None:
                        continue
                    
                    # Create button
                    button_label = f"{exp_name} | {branch_name} | {run_name[:30]}... | {element_labels[element]}"
                    
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
                                'title': f"3D Error Map: {element_labels[element]}<br><sub>{run_name}</sub>"
                            }
                        ]
                    )
                    dropdown_buttons.append(button)
    
    # Update layout with dropdown
    fig.update_layout(
        title=f"3D Error Map: {element_labels[initial_element]}<br><sub>{initial_run}</sub>",
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
                yanchor='top'
            )
        ],
        height=800,
        width=1400,
        margin=dict(t=150)
    )
    
    return fig


def _load_3d_error_surface(
    experiment_name: str,
    run_name: str,
    element: str,
    force_recompute: bool = False
) -> Optional[Dict[str, np.ndarray]]:
    """
    Load error data and prepare for 3D surface plot.
    
    Args:
        experiment_name: Name of the experiment
        run_name: Name of the run
        element: Element to visualize
        force_recompute: If True, recompute even if cached data exists
    
    Returns:
        Dictionary with 'x', 'y', 'z' arrays or None if failed
    """
    try:
        # Try to load from cache first unless force_recompute is True
        cache_dir = DIRS.root / "analysis" / experiment_name / "error" / "cache"
        cache_file = cache_dir / f"{run_name}_normalized_errors.pkl"
        
        normalized_errors = None
        
        if not force_recompute and cache_file.exists():
            try:
                import pickle
                with open(cache_file, 'rb') as f:
                    normalized_errors = pickle.load(f)
                logger.info(f"✓ Loaded cached error data for {run_name}")
            except Exception as e:
                logger.warning(f"Failed to load cache for {run_name}, recomputing: {e}")
                normalized_errors = None
        
        # If no cache or force_recompute, calculate from scratch
        if normalized_errors is None:
            logger.info(f"Computing error data for {run_name}...")
            
            # Load from HPC directory
            plan_file = DIRS.config / experiment_name / DIRS.plan_subdir / "sweep.yaml"
            with open(plan_file, 'r') as f:
                plan = yaml.safe_load(f)
            
            hpc_run_base_dir = Path(plan['hpc']['run_base_dir'])
            run_path = hpc_run_base_dir / run_name
            
            # Load VAR files
            all_sim_data = load_all_var_files(run_path)
            if not all_sim_data:
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
                variables=[element]
            )
        
        if element not in normalized_errors:
            return None
        
        # Extract data
        var_data = normalized_errors[element]
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
        logger.error(f"Failed to load 3D surface for {experiment_name}/{run_name}/{element}: {e}")
        return None


def create_error_evolution_animation(
    experiment_name: str,
    run_name: str,
    element: str = 'rho',
    force_recompute: bool = False
) -> Optional[go.Figure]:
    """
    Create animated line graph showing error evolution over time.
    
    Args:
        experiment_name: Name of the experiment
        run_name: Name of the run
        element: Element to visualize ('rho', 'ux', 'pp', 'ee')
        force_recompute: If True, recompute even if cached data exists
        
    Returns:
        Plotly Figure with animation controls or None if failed
    """
    element_labels = {
        'rho': 'Density (ρ)',
        'ux': 'Velocity (uₓ)',
        'pp': 'Pressure (p)',
        'ee': 'Energy (e)'
    }
    
    try:
        # Try to load from cache first unless force_recompute is True
        cache_dir = DIRS.root / "analysis" / experiment_name / "error" / "cache"
        cache_file = cache_dir / f"{run_name}_normalized_errors.pkl"
        
        normalized_errors = None
        
        if not force_recompute and cache_file.exists():
            try:
                import pickle
                with open(cache_file, 'rb') as f:
                    normalized_errors = pickle.load(f)
                logger.info(f"✓ Loaded cached error data for {run_name}")
            except Exception as e:
                logger.warning(f"Failed to load cache for {run_name}, recomputing: {e}")
                normalized_errors = None
        
        # If no cache or force_recompute, calculate from scratch
        if normalized_errors is None:
            logger.info(f"Computing error data for {run_name}...")
            
            # Load from HPC directory
            plan_file = DIRS.config / experiment_name / DIRS.plan_subdir / "sweep.yaml"
            with open(plan_file, 'r') as f:
                plan = yaml.safe_load(f)
            
            hpc_run_base_dir = Path(plan['hpc']['run_base_dir'])
            run_path = hpc_run_base_dir / run_name
            
            # Load VAR files
            all_sim_data = load_all_var_files(run_path)
            if not all_sim_data:
                logger.error(f"No VAR files found for {run_name}")
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
                variables=[element]
            )
        
        if element not in normalized_errors:
            logger.error(f"Element {element} not found in normalized errors")
            return None
        
        # Extract data
        var_data = normalized_errors[element]
        x_coords = var_data['x_coords']
        timesteps = var_data['timesteps']
        error_matrix = var_data['relative_error_field']
        
        # Create frames for animation
        frames = []
        for i, t in enumerate(timesteps):
            frame_data = go.Scatter(
                x=x_coords,
                y=error_matrix[i, :],
                mode='lines+markers',
                name=f't={t:.4f}',
                line=dict(color='blue', width=2),
                marker=dict(size=4)
            )
            frames.append(go.Frame(
                data=[frame_data],
                name=f'frame_{i}',
                layout=dict(title=f'Error vs Distance - {element_labels[element]}<br>Time: {t:.4f} [code units]')
            ))
        
        # Create initial figure with first timestep
        fig = go.Figure(
            data=[go.Scatter(
                x=x_coords,
                y=error_matrix[0, :],
                mode='lines+markers',
                name=f't={timesteps[0]:.4f}',
                line=dict(color='blue', width=2),
                marker=dict(size=4)
            )],
            frames=frames
        )
        
        # Add animation controls
        fig.update_layout(
            title=f'Error Evolution - {element_labels[element]}<br><sub>{run_name}</sub>',
            xaxis=dict(title='Position (x) [kpc]'),
            yaxis=dict(title='Relative Error', type='log'),
            height=600,
            width=1000,
            updatemenus=[
                dict(
                    type='buttons',
                    showactive=False,
                    buttons=[
                        dict(label='Play',
                             method='animate',
                             args=[None, dict(frame=dict(duration=100, redraw=True),
                                            fromcurrent=True,
                                            mode='immediate')]),
                        dict(label='Pause',
                             method='animate',
                             args=[[None], dict(frame=dict(duration=0, redraw=False),
                                              mode='immediate',
                                              transition=dict(duration=0))])
                    ],
                    x=0.1,
                    y=1.15,
                    xanchor='left',
                    yanchor='top'
                )
            ],
            sliders=[
                dict(
                    active=0,
                    yanchor='top',
                    y=0,
                    xanchor='left',
                    x=0.1,
                    currentvalue=dict(
                        prefix='Timestep: ',
                        visible=True,
                        xanchor='right'
                    ),
                    pad=dict(b=10, t=50),
                    len=0.9,
                    steps=[
                        dict(
                            args=[[f'frame_{i}'],
                                  dict(frame=dict(duration=100, redraw=True),
                                       mode='immediate',
                                       transition=dict(duration=0))],
                            method='animate',
                            label=f'{t:.4f}'
                        )
                        for i, t in enumerate(timesteps)
                    ]
                )
            ]
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"Failed to create error evolution animation for {experiment_name}/{run_name}/{element}: {e}")
        import traceback
        traceback.print_exc()
        return None


# Jupyter-friendly API
def show_error_evolution(
    experiment_name: str,
    run_name: str,
    element: str = 'rho',
    force_recompute: bool = False
) -> Optional[go.Figure]:
    """
    Show error evolution animation (Jupyter-friendly).
    
    Creates an animated line graph showing how error varies with distance
    at each timestep. Use the slider or play button to navigate through time.
    
    By default, uses cached data from --analyze runs for fast loading.
    Set force_recompute=True for exploratory work when you need fresh calculations.
    
    Args:
        experiment_name: Name of the experiment (e.g., 'shocktube_phase1')
        run_name: Name of the run
        element: Element to visualize - 'rho', 'ux', 'pp', or 'ee'
        force_recompute: If True, recalculate errors instead of using cache
        
    Returns:
        Plotly Figure object that can be displayed with fig.show()
        
    Example:
        >>> from notebooks.discovery_visualization import show_error_evolution
        >>> # Use cached data (fast)
        >>> fig = show_error_evolution('shocktube_phase1', 'res400_nohyper_...', 'rho')
        >>> fig.show()
        >>> 
        >>> # Force recomputation (for exploratory work)
        >>> fig = show_error_evolution('shocktube_phase1', 'res400_nohyper_...', 'rho', force_recompute=True)
        >>> fig.show()
    """
    return create_error_evolution_animation(experiment_name, run_name, element, force_recompute)


def show_3d_error_map(
    experiment_names: Optional[List[str]] = None,
    default_experiment: Optional[str] = None,
    force_recompute: bool = False
) -> go.Figure:
    """
    Show 3D error map with dropdowns (Jupyter-friendly).
    
    Creates an interactive 3D surface plot where you can select different
    experiments, branches, runs, and elements from dropdown menus.
    
    By default, uses cached data from --analyze runs for fast loading.
    Set force_recompute=True for exploratory work when you need fresh calculations.
    
    Args:
        experiment_names: List of experiments to include (if None, auto-detect)
        default_experiment: Default experiment to show
        force_recompute: If True, recalculate errors instead of using cache
        
    Returns:
        Plotly Figure object that can be displayed with fig.show()
        
    Example:
        >>> from notebooks.discovery_visualization import show_3d_error_map
        >>> # Use cached data (fast)
        >>> fig = show_3d_error_map(['shocktube_phase1', 'shocktube_phase2'])
        >>> fig.show()
        >>> 
        >>> # Force recomputation (for exploratory work)
        >>> fig = show_3d_error_map(['shocktube_phase1'], force_recompute=True)
        >>> fig.show()
    """
    # Note: Currently force_recompute is not passed down to create_3d_error_map_with_dropdowns
    # since that function loads all data at once. For now, the _load_3d_error_surface
    # internal function will use force_recompute=False by default
    return create_3d_error_map_with_dropdowns(experiment_names, default_experiment)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate 3D error map visualizations')
    parser.add_argument('--experiments', nargs='+', help='List of experiment names (optional, auto-detects if not provided)')
    parser.add_argument('--default-experiment', help='Default experiment to display')
    parser.add_argument('--element', default='rho', help='Default element to display')
    
    args = parser.parse_args()
    
    # Show 3D error map
    fig = show_3d_error_map(
        experiment_names=args.experiments,
        default_experiment=args.default_experiment
    )
    
    if fig:
        fig.show()
    else:
        print("Failed to generate 3D error map")

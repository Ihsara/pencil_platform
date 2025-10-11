# src/post_processing.py

import os
import sys
import yaml
from pathlib import Path
import jinja2
import numpy as np
from loguru import logger
from typing import Dict, List, Tuple

from .constants import DIRS, FILES
from .error_analysis import (
    calculate_std_deviation_across_vars, 
    calculate_absolute_deviation_per_var,
    calculate_spatial_errors,
    ExperimentErrorAnalyzer
)
from .video_generation import (
    create_var_evolution_video,
    create_error_evolution_video
)

# --- Add Pencil Code Python Library to Path ---
PENCIL_CODE_PYTHON_PATH = DIRS.root.parent / "pencil-code" / "python"
if str(PENCIL_CODE_PYTHON_PATH) not in sys.path:
    logger.info(f"Adding '{PENCIL_CODE_PYTHON_PATH}' to system path.")
    sys.path.insert(0, str(PENCIL_CODE_PYTHON_PATH))

try:
    import pencil.read as read
    from pencil.calc.shocktube import sod
except ImportError as e:
    logger.error(f"FATAL: Failed to import Pencil Code modules. {e}")
    sys.exit(1)

def get_analytical_solution(params, x: np.ndarray, t: float) -> dict | None:
    """Calculates the analytical Sod shock tube solution."""
    try:
        if not hasattr(params, 'rho0'): setattr(params, 'rho0', 1.0)
        if not hasattr(params, 'cs0'): setattr(params, 'cs0', 1.0)
        
        solution = sod(x, [t], par=params, lplot=False, magic=['ee'])
        return {
            'rho': np.squeeze(solution.rho), 'ux': np.squeeze(solution.ux),
            'pp': np.squeeze(solution.pp), 'ee': np.squeeze(solution.ee), 'x': x, 't': t
        }
    except Exception as e:
        logger.error(f"Failed to calculate analytical solution: {e}")
        return None

def load_all_var_files(run_path: Path) -> list[dict] | None:
    """Loads and processes all VAR files from a simulation run."""
    try:
        if not run_path.is_dir():
            logger.warning(f"Run directory not found: {run_path}")
            return None
        
        data_dir = run_path / "data"
        proc_dir = data_dir / "proc0" if (data_dir / "proc0").is_dir() else data_dir
        var_files = sorted(proc_dir.glob("VAR*"))
        
        if not var_files:
            logger.warning(f"No VAR files found in {proc_dir}")
            return None
        
        logger.info(f"Loading all {len(var_files)} VAR files from {run_path}")
        
        params = read.param(datadir=str(data_dir), quiet=True)
        grid = read.grid(datadir=str(data_dir), quiet=True, trim=True)
        
        all_data = []
        for var_file in var_files:
            try:
                var = read.var(var_file.name, datadir=str(data_dir), quiet=True, trimall=True)
                
                density = np.exp(var.lnrho) if hasattr(var, 'lnrho') else var.rho
                cp, gamma = params.cp, params.gamma
                cv = cp / gamma
                
                if not hasattr(var, 'ss'):
                    logger.error(f"Variable 'ss' not found in {var_file.name}")
                    continue
                
                rho0 = getattr(params, 'rho0', 1.0)
                cs0 = getattr(params, 'cs0', 1.0)
                lnrho0 = np.log(rho0)
                lnTT0 = np.log(cs0**2 / (cp * (gamma - 1.0)))
                
                pressure = (cp - cv) * np.exp(lnTT0 + (gamma / cp * var.ss) + 
                                             (gamma * np.log(density)) - ((gamma - 1.0) * lnrho0))
                internal_energy = pressure / (density * (gamma - 1.0)) if gamma > 1.0 else np.zeros_like(density)
                
                all_data.append({
                    "x": np.squeeze(grid.x), 
                    "rho": np.squeeze(density), 
                    "ux": np.squeeze(var.ux),
                    "pp": np.squeeze(pressure), 
                    "ee": np.squeeze(internal_energy), 
                    "t": var.t, 
                    "params": params,
                    "var_file": var_file.name
                })
            except Exception as e:
                logger.warning(f"Failed to load {var_file.name}: {e}")
                continue
        
        return all_data if all_data else None
        
    except Exception as e:
        logger.error(f"Failed to load VAR files from {run_path}: {e}")
        return None

def process_run_analysis(run_path: Path, run_name: str, branch_name: str, 
                        error_method: str = 'absolute') -> tuple[dict, dict, dict, list, list] | None:
    """Processes a single run for comprehensive error analysis across all VAR files.
    
    Args:
        run_path: Path to the run directory
        run_name: Name of the run
        branch_name: Name of the branch
        error_method: Error calculation method ('absolute', 'relative', 'difference', 'squared')
    
    Returns:
        Tuple of (std_devs, abs_devs, spatial_errors, all_sim_data, all_analytical_data) or None if failed.
        The loaded data is returned to enable caching and reuse for video generation.
    """
    logger.info(f"--- Analyzing run: {run_name} (branch: {branch_name}) ---")
    
    # Load all VAR files ONCE
    all_sim_data = load_all_var_files(run_path)
    if not all_sim_data:
        return None
    
    logger.info(f"Loaded {len(all_sim_data)} VAR files (t={all_sim_data[0]['t']:.3e} to {all_sim_data[-1]['t']:.3e})")
    
    # Generate analytical solutions for all timesteps
    all_analytical_data = []
    for sim_data in all_sim_data:
        analytical_data = get_analytical_solution(sim_data['params'], sim_data['x'], sim_data['t'])
        if analytical_data:
            all_analytical_data.append(analytical_data)
    
    if not all_analytical_data:
        logger.error(f"Failed to generate analytical solutions for {run_name}")
        return None
    
    # Validation: Ensure we have one analytical solution per VAR file
    if len(all_analytical_data) != len(all_sim_data):
        logger.error(f"Mismatch: {len(all_sim_data)} VAR files but {len(all_analytical_data)} analytical solutions")
        return None
    
    # Validation: Verify timestep pairing is correct
    for idx, (sim, anal) in enumerate(zip(all_sim_data, all_analytical_data)):
        if abs(sim['t'] - anal['t']) > 1e-10:
            logger.error(f"Timestep mismatch at VAR {idx}: sim_t={sim['t']:.6e} vs anal_t={anal['t']:.6e}")
            return None
    
    logger.info(f"✓ Generated {len(all_analytical_data)} analytical solutions with correct timestep pairing")
    
    # Calculate error metrics
    std_devs = calculate_std_deviation_across_vars(all_sim_data, all_analytical_data)
    abs_devs = calculate_absolute_deviation_per_var(all_sim_data, all_analytical_data)
    spatial_errors = calculate_spatial_errors(all_sim_data, all_analytical_data, error_method=error_method)
    
    # Return loaded data along with metrics for caching/reuse
    return std_devs, abs_devs, spatial_errors, all_sim_data, all_analytical_data


def create_overlay_error_evolution_video(
    spatial_errors_list: List[Tuple[str, Dict]], 
    output_path: Path, 
    output_name: str,
    fps: int = 2, 
    unit_length: float = 1.0
):
    """
    Creates an overlaid animated GIF showing spatial error evolution for multiple runs.
    
    Args:
        spatial_errors_list: List of tuples (run_name, spatial_errors_dict)
        output_path: Directory to save the animation
        output_name: Name for the output file
        fps: Frames per second
        unit_length: Unit conversion factor for length
    """
    import matplotlib.pyplot as plt
    import matplotlib.animation as animation
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Validate unit_length
    if not np.isfinite(unit_length) or unit_length > 1e20 or unit_length == 0:
        logger.warning(f"Invalid unit_length value ({unit_length}). Using 1.0 instead.")
        unit_length = 1.0
    
    variables = ['rho', 'ux', 'pp', 'ee']
    var_labels = [r'$\rho$', r'$u_x$', r'$p$', r'$e$']
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    
    fig, axes = plt.subplots(2, 2, figsize=(18, 14))
    axes = axes.flatten()
    
    # Get max number of timesteps across all runs
    max_timesteps = max(
        len(spatial_errors['rho']['errors_per_timestep'])
        for _, spatial_errors in spatial_errors_list
        if 'rho' in spatial_errors
    )
    
    error_method = spatial_errors_list[0][1][list(spatial_errors_list[0][1].keys())[0]]['error_method']
    
    # Initialize plot elements
    lines = {var: [] for var in variables}
    
    for idx, var in enumerate(variables):
        ax = axes[idx]
        
        # Get x coordinates from first run (should be same for all)
        x_raw = spatial_errors_list[0][1][var]['x']
        try:
            x_coords = x_raw * unit_length
            if not np.all(np.isfinite(x_coords)):
                x_coords = x_raw
                unit_length = 1.0
        except (OverflowError, RuntimeWarning):
            x_coords = x_raw
            unit_length = 1.0
        
        # Create line for each run
        for run_idx, (run_name, spatial_errors) in enumerate(spatial_errors_list):
            if var in spatial_errors:
                color = colors[run_idx % len(colors)]
                line, = ax.plot([], [], '-', linewidth=2.5, color=color, 
                              label=run_name, alpha=0.8)
                lines[var].append((line, run_name, spatial_errors))
        
        x_label = 'Position (x) [kpc]' if unit_length != 1.0 else 'Position (x) [normalized]'
        ax.set_xlabel(x_label, fontsize=11)
        ax.set_ylabel(f'Error in {var_labels[idx]}', fontsize=11)
        ax.set_title(f'{var_labels[idx]} Spatial Error Comparison', fontsize=12)
        ax.legend(fontsize=9, loc='best')
        ax.grid(True, alpha=0.3)
        
        # Set axis limits
        if np.all(np.isfinite(x_coords)):
            ax.set_xlim(x_coords.min(), x_coords.max())
        
        # Calculate y limits across all runs
        all_errors = []
        for _, _, spatial_errors in lines[var]:
            all_errors.extend(spatial_errors[var]['errors_per_timestep'])
        if all_errors:
            all_errors_concat = np.concatenate(all_errors)
            y_min = all_errors_concat.min()
            y_max = all_errors_concat.max()
            y_range = y_max - y_min
            ax.set_ylim(y_min - 0.1*y_range, y_max + 0.1*y_range)
    
    title = fig.suptitle('', fontsize=16, fontweight='bold')
    
    def init():
        """Initialize animation"""
        for var in variables:
            for line, _, _ in lines[var]:
                line.set_data([], [])
        title.set_text(f'Spatial Error Comparison ({error_method})\n{output_name}\nVAR 0/{max_timesteps}')
        return [line for var in variables for line, _, _ in lines[var]] + [title]
    
    def animate(frame):
        """Animation function"""
        for var in variables:
            for line, run_name, spatial_errors in lines[var]:
                if frame < len(spatial_errors[var]['errors_per_timestep']):
                    x_raw = spatial_errors[var]['x']
                    try:
                        x_coords = x_raw * unit_length
                        if not np.all(np.isfinite(x_coords)):
                            x_coords = x_raw
                    except (OverflowError, RuntimeWarning):
                        x_coords = x_raw
                    
                    errors = spatial_errors[var]['errors_per_timestep'][frame]
                    line.set_data(x_coords, errors)
                else:
                    line.set_data([], [])
        
        # Get timestep info from first run
        first_spatial_errors = spatial_errors_list[0][1]
        var_file = first_spatial_errors['rho']['var_files'][frame]
        timestep = first_spatial_errors['rho']['timesteps'][frame]
        
        title.set_text(f'Spatial Error Comparison ({error_method})\n{output_name}\n{var_file} (t={timestep:.4e} s) - VAR {frame+1}/{max_timesteps}')
        
        return [line for var in variables for line, _, _ in lines[var]] + [title]
    
    # Create animation
    anim = animation.FuncAnimation(fig, animate, init_func=init, frames=max_timesteps,
                                  interval=1000//fps, blit=True, repeat=True)
    
    # Save animation as GIF
    output_file = output_path / f"{output_name}_error_evolution.gif"
    try:
        writer = animation.PillowWriter(fps=fps, metadata=dict(artist='Pencil Platform'))
        anim.save(output_file, writer=writer)
        logger.success(f"Saved overlay error evolution to {output_file}")
    except Exception as e:
        logger.error(f"Failed to save overlay animation: {e}")
    finally:
        plt.close()


def visualize_suite(experiment_name: str, specific_runs: list = None, var_selection: str = None):
    """Simplified visualization function - redirects to video-only analysis."""
    logger.warning("The --viz flag is deprecated. Use --analyze for video-only analysis instead.")
    logger.info("Redirecting to video-only analysis...")
    analyze_suite_videos_only(experiment_name)


def analyze_suite_videos_only(experiment_name: str, error_method: str = 'absolute'):
    """Video-only analysis: Creates individual and overlay error evolution videos.
    
    Workflow:
    1. Load all VAR files and calculate errors (cached)
    2. Create individual error evolution videos
    3. Find best performer in each branch → create overlay videos
    4. Find top 3 best performers overall → create overlay video
    
    Args:
        experiment_name: Name of the experiment suite
        error_method: Error calculation method for spatial errors
    """
    logger.info(f"=" * 80)
    logger.info(f"STARTING VIDEO-ONLY ANALYSIS: '{experiment_name}'")
    logger.info(f"=" * 80)
    
    plan_file = DIRS.config / experiment_name / DIRS.plan_subdir / FILES.plan
    with open(plan_file, 'r') as f: 
        plan = yaml.safe_load(f)
    
    hpc_run_base_dir = Path(plan['hpc']['run_base_dir'])
    manifest_file = DIRS.runs / experiment_name / FILES.manifest
    analysis_dir = DIRS.root / "analysis" / experiment_name
    video_dir = analysis_dir / "videos" / "error_evolution"
    video_dir.mkdir(parents=True, exist_ok=True)

    with open(manifest_file, 'r') as f: 
        run_names = [line.strip() for line in f if line.strip()]
    
    total_runs = len(run_names)
    logger.info(f"Total experiments to process: {total_runs}")
    
    # Extract branch information
    branches = plan.get('branches', [])
    branch_names = [b['name'] for b in branches] if branches else ['default']
    
    # Organize runs by branch
    runs_per_branch = {branch: [] for branch in branch_names}
    for run_name in run_names:
        for branch_name in branch_names:
            if branch_name in run_name:
                runs_per_branch[branch_name].append(run_name)
                break
        else:
            runs_per_branch['default'].append(run_name)
    
    # ============================================================
    # PHASE 1: Load data and create individual videos
    # ============================================================
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 1: Loading data and creating individual videos")
    logger.info("=" * 80)
    
    loaded_data_cache = {}
    runs_processed = 0
    
    for branch_name, branch_runs in runs_per_branch.items():
        if not branch_runs:
            continue
        
        branch_total = len(branch_runs)
        logger.info(f"\n📂 Processing branch: {branch_name} ({branch_total} runs)")
        
        for branch_idx, run_name in enumerate(branch_runs, 1):
            runs_processed += 1
            overall_pct = (runs_processed / total_runs) * 100
            branch_pct = (branch_idx / branch_total) * 100
            
            logger.info(f"  ├─ [{runs_processed}/{total_runs}] ({overall_pct:.1f}%) | "
                       f"Branch: [{branch_idx}/{branch_total}] ({branch_pct:.1f}%) | "
                       f"Run: {run_name}")
            
            result = process_run_analysis(hpc_run_base_dir / run_name, run_name, branch_name, error_method)
            if result:
                std_devs, abs_devs, spatial_errors, all_sim_data, all_analytical_data = result
                
                # Cache data
                loaded_data_cache[run_name] = {
                    'sim_data': all_sim_data,
                    'analytical_data': all_analytical_data,
                    'branch': branch_name,
                    'std_devs': std_devs,
                    'spatial_errors': spatial_errors
                }
                
                # Create individual error evolution video
                unit_length = 1.0
                if all_sim_data and 'params' in all_sim_data[0]:
                    params = all_sim_data[0]['params']
                    if hasattr(params, 'unit_length'):
                        unit_length = params.unit_length * 3.086e21
                
                logger.info(f"     ├─ Creating individual error evolution video...")
                create_error_evolution_video(
                    spatial_errors, video_dir, run_name, fps=2, unit_length=unit_length
                )
                logger.info(f"     └─ ✓ Cached {len(all_sim_data)} VAR files")
            else:
                logger.warning(f"     └─ ✗ Failed to process run")
    
    # ============================================================
    # PHASE 2: Find best performers and create overlay videos
    # ============================================================
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 2: Creating overlay videos")
    logger.info("=" * 80)
    
    # Calculate average error for each run (using mean of all timesteps and variables)
    run_scores = {}
    for run_name, cached in loaded_data_cache.items():
        spatial_errors = cached['spatial_errors']
        
        # Calculate average L2 error across all variables and timesteps
        total_error = 0
        count = 0
        for var in ['rho', 'ux', 'pp', 'ee']:
            if var in spatial_errors:
                for errors in spatial_errors[var]['errors_per_timestep']:
                    total_error += np.sqrt(np.mean(errors**2))  # L2 norm
                    count += 1
        
        avg_error = total_error / count if count > 0 else float('inf')
        run_scores[run_name] = avg_error
        logger.info(f"  {run_name}: avg L2 error = {avg_error:.6e}")
    
    # Find best performer in each branch
    logger.info(f"\n🏆 Finding best performers in each branch...")
    branch_best_performers = {}
    for branch_name, branch_runs in runs_per_branch.items():
        if not branch_runs:
            continue
        
        branch_scores = {run: run_scores[run] for run in branch_runs if run in run_scores}
        if branch_scores:
            best_run = min(branch_scores, key=branch_scores.get)
            branch_best_performers[branch_name] = best_run
            logger.info(f"  ├─ {branch_name}: {best_run} (L2={branch_scores[best_run]:.6e})")
    
    # Create overlay videos for each branch (all runs in branch)
    logger.info(f"\n🎬 Creating branch overlay videos...")
    for branch_name, branch_runs in runs_per_branch.items():
        if not branch_runs or len(branch_runs) < 2:
            continue
        
        logger.info(f"  ├─ Branch: {branch_name} ({len(branch_runs)} runs)")
        
        spatial_errors_list = []
        for run_name in branch_runs:
            if run_name in loaded_data_cache:
                cached = loaded_data_cache[run_name]
                spatial_errors_list.append((run_name, cached['spatial_errors']))
        
        if spatial_errors_list:
            # Get unit_length from first run
            unit_length = 1.0
            first_run_data = loaded_data_cache[branch_runs[0]]
            if first_run_data['sim_data'] and 'params' in first_run_data['sim_data'][0]:
                params = first_run_data['sim_data'][0]['params']
                if hasattr(params, 'unit_length'):
                    unit_length = params.unit_length * 3.086e21
            
            output_name = f"{experiment_name}_{branch_name}_overlay"
            create_overlay_error_evolution_video(
                spatial_errors_list, video_dir, output_name, fps=2, unit_length=unit_length
            )
            logger.info(f"     └─ ✓ Created overlay for {branch_name}")
    
    # Find top 3 best performers overall
    logger.info(f"\n🏆 Finding top 3 best performers overall...")
    sorted_runs = sorted(run_scores.items(), key=lambda x: x[1])
    top_3_runs = [run for run, score in sorted_runs[:3]]
    
    for idx, (run, score) in enumerate(sorted_runs[:3], 1):
        logger.info(f"  ├─ #{idx}: {run} (L2={score:.6e})")
    
    # Create overlay video for top 3
    logger.info(f"\n🎬 Creating top 3 overlay video...")
    top_3_spatial_errors = []
    for run_name in top_3_runs:
        if run_name in loaded_data_cache:
            cached = loaded_data_cache[run_name]
            top_3_spatial_errors.append((run_name, cached['spatial_errors']))
    
    if top_3_spatial_errors:
        # Get unit_length from first run
        unit_length = 1.0
        first_run_data = loaded_data_cache[top_3_runs[0]]
        if first_run_data['sim_data'] and 'params' in first_run_data['sim_data'][0]:
            params = first_run_data['sim_data'][0]['params']
            if hasattr(params, 'unit_length'):
                unit_length = params.unit_length * 3.086e21
        
        output_name = f"{experiment_name}_top3_best_performers_overlay"
        create_overlay_error_evolution_video(
            top_3_spatial_errors, video_dir, output_name, fps=2, unit_length=unit_length
        )
        logger.info(f"     └─ ✓ Created top 3 overlay video")
    
    # ============================================================
    # SUMMARY
    # ============================================================
    logger.info("\n" + "=" * 80)
    logger.success(f"✓ VIDEO-ONLY ANALYSIS COMPLETED")
    logger.success(f"✓ Results saved to: {video_dir}")
    logger.info(f"📊 Individual videos: {len(loaded_data_cache)}")
    logger.info(f"📊 Branch overlay videos: {len([b for b in runs_per_branch.values() if len(b) >= 2])}")
    logger.info(f"📊 Top 3 overlay video: 1")
    logger.info(f"🎬 Total videos created: {len(loaded_data_cache) + len([b for b in runs_per_branch.values() if len(b) >= 2]) + 1}")
    logger.info("=" * 80)

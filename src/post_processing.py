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
    calculate_error_norms,
    ExperimentErrorAnalyzer
)
from .error_metrics import calculate_errors_over_time
from .video_generation import (
    create_var_evolution_video,
    create_error_evolution_video
)
from .experiment_name_decoder import format_experiment_title, format_short_experiment_name

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
    var_labels = [r'$\rho$ [g cm$^{-3}$]', r'$u_x$ [km s$^{-1}$]', r'$p$ [dyn cm$^{-2}$]', r'$e$ [km$^2$ s$^{-2}$]']
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


def analyze_suite_comprehensive(experiment_name: str, error_method: str = 'absolute'):
    """Legacy function name - redirects to video-only analysis for backward compatibility."""
    logger.warning("analyze_suite_comprehensive() is deprecated. Redirecting to video-only analysis...")
    analyze_suite_videos_only(experiment_name, error_method)


def analyze_suite_videos_only(experiment_name: str, error_method: str = 'absolute'):
    """Comprehensive analysis: Creates videos, calculates L1/L2 error norms, and generates final report.
    
    Workflow:
    1. Load all VAR files and calculate errors (cached)
    2. Create individual error evolution videos
    3. Find best performer in each branch → create overlay videos
    4. Find top 3 best performers overall → create overlay video
    5. Calculate L1/L2 error norms with combined scoring
    6. Create comprehensive visualizations
    7. Generate final Rich summary report
    
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
    
    # Create new directory structure
    var_evolution_dir = analysis_dir / "var_evolution"
    error_evolution_dir = analysis_dir / "error_evolution"
    var_frames_dir = analysis_dir / "var_frames"
    
    var_evolution_dir.mkdir(parents=True, exist_ok=True)
    error_evolution_dir.mkdir(parents=True, exist_ok=True)
    var_frames_dir.mkdir(parents=True, exist_ok=True)

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
                        unit_length = params.unit_length  # Already in cm
                
                logger.info(f"     ├─ Creating var evolution video...")
                create_var_evolution_video(
                    all_sim_data, all_analytical_data, var_evolution_dir, run_name, fps=2
                )
                
                logger.info(f"     ├─ Creating error evolution video...")
                create_error_evolution_video(
                    spatial_errors, error_evolution_dir, run_name, fps=2, unit_length=unit_length
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
                    unit_length = params.unit_length  # Already in cm
            
            output_name = f"{experiment_name}_{branch_name}_overlay"
            create_overlay_error_evolution_video(
                spatial_errors_list, error_evolution_dir, output_name, fps=2, unit_length=unit_length
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
                unit_length = params.unit_length  # Already in cm
        
        output_name = f"{experiment_name}_top3_best_performers_overlay"
        create_overlay_error_evolution_video(
            top_3_spatial_errors, error_evolution_dir, output_name, fps=2, unit_length=unit_length
        )
        logger.info(f"     └─ ✓ Created top 3 overlay video")
    
    # ============================================================
    # PHASE 3: Calculate L1/L2 error norms (reusing loaded data)
    # ============================================================
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 3: Calculating L1/L2 error norms")
    logger.info("=" * 80)
    
    metrics = ['l1', 'l2', 'linf']
    error_norms_dir = analysis_dir / "error_norms"
    error_norms_dir.mkdir(parents=True, exist_ok=True)
    plots_dir = error_norms_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    
    error_norms_cache = {}
    
    logger.info(f"Calculating error norms for {len(loaded_data_cache)} runs...")
    
    for run_name, cached in loaded_data_cache.items():
        all_sim_data = cached['sim_data']
        all_analytical_data = cached['analytical_data']
        
        logger.info(f"  ├─ {run_name}: calculating {', '.join([m.upper() for m in metrics])}...")
        error_norms = calculate_error_norms(all_sim_data, all_analytical_data, metrics=metrics)
        
        if error_norms:
            error_norms_cache[run_name] = {
                'branch': cached['branch'],
                'error_norms': error_norms,
                'n_timesteps': len(all_sim_data)
            }
    
    # Calculate combined scores
    logger.info(f"\nCalculating combined scores...")
    combined_scores = {}
    
    for run_name, cached in error_norms_cache.items():
        error_norms = cached['error_norms']
        scores_per_metric = {}
        
        for metric in metrics:
            metric_scores = []
            for var in ['rho', 'ux', 'pp', 'ee']:
                if var in error_norms and metric in error_norms[var]:
                    mean_val = error_norms[var][metric]['mean']
                    if np.isfinite(mean_val):
                        metric_scores.append(mean_val)
            
            if metric_scores:
                scores_per_metric[metric] = np.mean(metric_scores)
        
        if scores_per_metric:
            combined_score = np.mean(list(scores_per_metric.values()))
            combined_scores[run_name] = {
                'combined': combined_score,
                'per_metric': scores_per_metric,
                'branch': cached['branch']
            }
    
    # Find best performers
    sorted_runs = sorted(combined_scores.items(), key=lambda x: x[1]['combined'])
    
    # Best per branch
    branch_best = {}
    for branch_name, branch_runs in runs_per_branch.items():
        if not branch_runs:
            continue
        
        branch_scores = {run: combined_scores[run] for run in branch_runs if run in combined_scores}
        if branch_scores:
            best_run = min(branch_scores.items(), key=lambda x: x[1]['combined'])
            branch_best[branch_name] = best_run
    
    # ============================================================
    # PHASE 4: Create error norm visualizations
    # ============================================================
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 4: Creating error norm visualizations")
    logger.info("=" * 80)
    
    logger.info("  ├─ Combined scores comparison...")
    create_combined_scores_plot(combined_scores, plots_dir, experiment_name)
    
    logger.info("  ├─ Per-metric comparisons...")
    create_per_metric_plots(error_norms_cache, metrics, plots_dir, experiment_name)
    
    logger.info("  ├─ Top 5 detailed view...")
    create_best_performers_plot(sorted_runs[:5], error_norms_cache, metrics, plots_dir, experiment_name)
    
    logger.info("  ├─ Branch comparison...")
    create_branch_comparison_plot(branch_best, runs_per_branch, combined_scores, plots_dir, experiment_name)
    
    logger.info("  └─ Error evolution plots...")
    create_error_evolution_plots(sorted_runs[:3], error_norms_cache, metrics, plots_dir, experiment_name)
    
    # ============================================================
    # PHASE 5: Save reports
    # ============================================================
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 5: Generating reports")
    logger.info("=" * 80)
    
    save_error_norms_summary(sorted_runs, branch_best, error_norms_cache, 
                            combined_scores, metrics, error_norms_dir, experiment_name)
    
    # ============================================================
    # FINAL RICH REPORT
    # ============================================================
    logger.info("\n" + "=" * 80)
    logger.info("FINAL SUMMARY")
    logger.info("=" * 80)
    
    generate_final_rich_report(
        experiment_name, error_evolution_dir, error_norms_dir, 
        len(loaded_data_cache), sorted_runs[:5], branch_best, 
        combined_scores, metrics
    )


def analyze_suite_with_error_norms(experiment_name: str, metrics: List[str] = None):
    """
    Comprehensive analysis using L1, L2, and other error norms with combined scoring.
    
    This creates a NEW subfolder 'error_norms' with:
    - L1/L2 error calculations for all runs
    - Combined scoring from multiple metrics
    - Comparison visualizations
    - Best parameter identification
    
    Args:
        experiment_name: Name of the experiment suite
        metrics: List of error metrics to calculate (default: ['l1', 'l2', 'linf'])
    """
    if metrics is None:
        metrics = ['l1', 'l2', 'linf']
    
    logger.info(f"=" * 80)
    logger.info(f"STARTING L1/L2 ERROR NORM ANALYSIS: '{experiment_name}'")
    logger.info(f"=" * 80)
    
    plan_file = DIRS.config / experiment_name / DIRS.plan_subdir / FILES.plan
    with open(plan_file, 'r') as f: 
        plan = yaml.safe_load(f)
    
    hpc_run_base_dir = Path(plan['hpc']['run_base_dir'])
    manifest_file = DIRS.runs / experiment_name / FILES.manifest
    analysis_dir = DIRS.root / "analysis" / experiment_name
    
    # Create NEW subfolder for error norm results
    error_norms_dir = analysis_dir / "error_norms"
    error_norms_dir.mkdir(parents=True, exist_ok=True)
    
    plots_dir = error_norms_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    with open(manifest_file, 'r') as f: 
        run_names = [line.strip() for line in f if line.strip()]
    
    total_runs = len(run_names)
    logger.info(f"Total experiments to process: {total_runs}")
    logger.info(f"Error metrics to calculate: {', '.join(metrics)}")
    
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
    # PHASE 1: Calculate error norms for all runs
    # ============================================================
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 1: Calculating L1/L2 error norms for all runs")
    logger.info("=" * 80)
    
    error_norms_cache = {}
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
            
            # Load data
            all_sim_data = load_all_var_files(hpc_run_base_dir / run_name)
            if not all_sim_data:
                logger.warning(f"     └─ ✗ Failed to load VAR files")
                continue
            
            # Generate analytical solutions
            all_analytical_data = []
            for sim_data in all_sim_data:
                analytical_data = get_analytical_solution(sim_data['params'], sim_data['x'], sim_data['t'])
                if analytical_data:
                    all_analytical_data.append(analytical_data)
            
            if len(all_analytical_data) != len(all_sim_data):
                logger.warning(f"     └─ ✗ Analytical solution mismatch")
                continue
            
            # Calculate error norms
            logger.info(f"     ├─ Calculating error norms ({', '.join(metrics)})...")
            error_norms = calculate_error_norms(all_sim_data, all_analytical_data, metrics=metrics)
            
            if error_norms:
                error_norms_cache[run_name] = {
                    'branch': branch_name,
                    'error_norms': error_norms,
                    'n_timesteps': len(all_sim_data)
                }
                logger.info(f"     └─ ✓ Calculated {len(metrics)} metrics for {len(all_sim_data)} timesteps")
            else:
                logger.warning(f"     └─ ✗ Failed to calculate error norms")
    
    # ============================================================
    # PHASE 2: Calculate combined scores
    # ============================================================
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 2: Calculating combined scores")
    logger.info("=" * 80)
    
    combined_scores = {}
    
    for run_name, cached in error_norms_cache.items():
        error_norms = cached['error_norms']
        
        # Calculate combined score: average of mean values across all variables and metrics
        scores_per_metric = {}
        
        for metric in metrics:
            metric_scores = []
            for var in ['rho', 'ux', 'pp', 'ee']:
                if var in error_norms and metric in error_norms[var]:
                    mean_val = error_norms[var][metric]['mean']
                    if np.isfinite(mean_val):
                        metric_scores.append(mean_val)
            
            if metric_scores:
                scores_per_metric[metric] = np.mean(metric_scores)
        
        # Combined score is the average of all metric scores
        if scores_per_metric:
            combined_score = np.mean(list(scores_per_metric.values()))
            combined_scores[run_name] = {
                'combined': combined_score,
                'per_metric': scores_per_metric,
                'branch': cached['branch']
            }
            
            logger.info(f"  {run_name}:")
            for metric, score in scores_per_metric.items():
                logger.info(f"    ├─ {metric.upper()}: {score:.6e}")
            logger.info(f"    └─ Combined: {combined_score:.6e}")
    
    # ============================================================
    # PHASE 3: Find best performers
    # ============================================================
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 3: Identifying best performers")
    logger.info("=" * 80)
    
    # Overall best
    sorted_runs = sorted(combined_scores.items(), key=lambda x: x[1]['combined'])
    
    logger.info(f"\n🥇 TOP 5 OVERALL BEST PERFORMERS:")
    for idx, (run_name, scores) in enumerate(sorted_runs[:5], 1):
        logger.info(f"  #{idx}: {run_name}")
        logger.info(f"       Combined Score: {scores['combined']:.6e}")
        logger.info(f"       Branch: {scores['branch']}")
    
    # Best per branch
    logger.info(f"\n🏆 BEST PERFORMER PER BRANCH:")
    branch_best = {}
    for branch_name, branch_runs in runs_per_branch.items():
        if not branch_runs:
            continue
        
        branch_scores = {run: combined_scores[run] for run in branch_runs if run in combined_scores}
        if branch_scores:
            best_run = min(branch_scores.items(), key=lambda x: x[1]['combined'])
            branch_best[branch_name] = best_run
            logger.info(f"  {branch_name}:")
            logger.info(f"    └─ {best_run[0]} (score: {best_run[1]['combined']:.6e})")
    
    # ============================================================
    # PHASE 4: Create visualizations
    # ============================================================
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 4: Creating visualizations")
    logger.info("=" * 80)
    
    import matplotlib.pyplot as plt
    
    # 1. Combined scores comparison (all runs)
    logger.info("  ├─ Creating combined scores comparison...")
    create_combined_scores_plot(combined_scores, plots_dir, experiment_name)
    
    # 2. Per-metric comparison
    logger.info("  ├─ Creating per-metric comparison plots...")
    create_per_metric_plots(error_norms_cache, metrics, plots_dir, experiment_name)
    
    # 3. Best performers detailed view
    logger.info("  ├─ Creating best performers detailed view...")
    create_best_performers_plot(sorted_runs[:5], error_norms_cache, metrics, plots_dir, experiment_name)
    
    # 4. Branch comparison
    logger.info("  ├─ Creating branch comparison...")
    create_branch_comparison_plot(branch_best, runs_per_branch, combined_scores, plots_dir, experiment_name)
    
    # 5. Error evolution over time for top 3
    logger.info("  └─ Creating error evolution plots for top 3...")
    create_error_evolution_plots(sorted_runs[:3], error_norms_cache, metrics, plots_dir, experiment_name)
    
    # ============================================================
    # PHASE 5: Save summary report
    # ============================================================
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 5: Generating summary report")
    logger.info("=" * 80)
    
    save_error_norms_summary(
        sorted_runs, branch_best, error_norms_cache, 
        combined_scores, metrics, error_norms_dir, experiment_name
    )
    
    # ============================================================
    # SUMMARY
    # ============================================================
    logger.info("\n" + "=" * 80)
    logger.success(f"✓ L1/L2 ERROR NORM ANALYSIS COMPLETED")
    logger.success(f"✓ Results saved to: {error_norms_dir}")
    logger.info(f"📊 Runs analyzed: {len(error_norms_cache)}")
    logger.info(f"📊 Metrics calculated: {len(metrics)}")
    logger.info(f"📊 Plots created: {plots_dir}")
    logger.info(f"🏆 Best overall: {sorted_runs[0][0]}")
    logger.info("=" * 80)


def create_combined_scores_plot(combined_scores, output_dir, experiment_name):
    """Create bar plot comparing combined scores for all runs."""
    import matplotlib.pyplot as plt
    
    fig, ax = plt.subplots(figsize=(16, 8))
    
    # Sort by score
    sorted_items = sorted(combined_scores.items(), key=lambda x: x[1]['combined'])
    run_names = [item[0] for item in sorted_items]
    scores = [item[1]['combined'] for item in sorted_items]
    branches = [item[1]['branch'] for item in sorted_items]
    
    # Color by branch
    unique_branches = list(set(branches))
    colors = plt.cm.Set3(np.linspace(0, 1, len(unique_branches)))
    branch_colors = {branch: colors[i] for i, branch in enumerate(unique_branches)}
    bar_colors = [branch_colors[b] for b in branches]
    
    bars = ax.bar(range(len(run_names)), scores, color=bar_colors, alpha=0.8, edgecolor='black', linewidth=0.5)
    
    # Highlight top 3
    for i in range(min(3, len(bars))):
        bars[i].set_edgecolor('gold')
        bars[i].set_linewidth(3)
    
    ax.set_xlabel('Run Name', fontsize=12, fontweight='bold')
    ax.set_ylabel('Combined Error Score (lower is better)', fontsize=12, fontweight='bold')
    ax.set_title(f'{experiment_name}: Combined Error Scores (L1+L2+L∞)\nTop 3 highlighted in gold', 
                 fontsize=14, fontweight='bold')
    ax.set_xticks(range(len(run_names)))
    ax.set_xticklabels(run_names, rotation=45, ha='right', fontsize=8)
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_yscale('log')
    
    # Legend for branches
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=branch_colors[b], label=b, alpha=0.8) 
                      for b in unique_branches]
    ax.legend(handles=legend_elements, title='Branch', loc='upper left', fontsize=9)
    
    plt.tight_layout()
    output_file = output_dir / f"{experiment_name}_combined_scores.png"
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    logger.info(f"       └─ Saved to {output_file.name}")


def create_per_metric_plots(error_norms_cache, metrics, output_dir, experiment_name):
    """Create comparison plots for each metric separately."""
    import matplotlib.pyplot as plt
    
    variables = ['rho', 'ux', 'pp', 'ee']
    var_labels = [r'$\rho$ [g cm$^{-3}$]', r'$u_x$ [km s$^{-1}$]', r'$p$ [dyn cm$^{-2}$]', r'$e$ [km$^2$ s$^{-2}$]']
    
    for metric in metrics:
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f'{experiment_name}: {metric.upper()} Error Comparison', 
                    fontsize=16, fontweight='bold')
        axes = axes.flatten()
        
        for idx, (var, label) in enumerate(zip(variables, var_labels)):
            ax = axes[idx]
            
            run_names = []
            mean_errors = []
            
            for run_name, cached in error_norms_cache.items():
                error_norms = cached['error_norms']
                if var in error_norms and metric in error_norms[var]:
                    mean_val = error_norms[var][metric]['mean']
                    if np.isfinite(mean_val):
                        run_names.append(run_name)
                        mean_errors.append(mean_val)
            
            if run_names:
                # Sort by error
                sorted_indices = np.argsort(mean_errors)
                run_names = [run_names[i] for i in sorted_indices]
                mean_errors = [mean_errors[i] for i in sorted_indices]
                
                bars = ax.bar(range(len(run_names)), mean_errors, alpha=0.7, edgecolor='black', linewidth=0.5)
                
                # Highlight best
                bars[0].set_color('green')
                bars[0].set_alpha(1.0)
                
                ax.set_xlabel('Run Name', fontsize=10)
                ax.set_ylabel(f'{metric.upper()} Error', fontsize=10)
                ax.set_title(f'{label} - {metric.upper()} Error', fontsize=12)
                ax.set_xticks(range(len(run_names)))
                ax.set_xticklabels(run_names, rotation=45, ha='right', fontsize=7)
                ax.grid(True, alpha=0.3, axis='y')
                ax.set_yscale('log')
        
        plt.tight_layout()
        output_file = output_dir / f"{experiment_name}_{metric}_comparison.png"
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close()
        logger.info(f"       └─ Saved {metric.upper()} comparison to {output_file.name}")


def create_best_performers_plot(top_5, error_norms_cache, metrics, output_dir, experiment_name):
    """Create detailed comparison of top 5 performers."""
    import matplotlib.pyplot as plt
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle(f'{experiment_name}: Top 5 Performers - Detailed Comparison', 
                fontsize=16, fontweight='bold')
    axes = axes.flatten()
    
    variables = ['rho', 'ux', 'pp', 'ee']
    var_labels = [r'$\rho$ [g cm$^{-3}$]', r'$u_x$ [km s$^{-1}$]', r'$p$ [dyn cm$^{-2}$]', r'$e$ [km$^2$ s$^{-2}$]']
    
    colors = plt.cm.viridis(np.linspace(0, 1, 5))
    
    for idx, (var, label) in enumerate(zip(variables, var_labels)):
        ax = axes[idx]
        
        for rank, (run_name, scores) in enumerate(top_5, 1):
            if run_name not in error_norms_cache:
                continue
            
            error_norms = error_norms_cache[run_name]['error_norms']
            
            if var in error_norms:
                metric_values = []
                for metric in metrics:
                    if metric in error_norms[var]:
                        metric_values.append(error_norms[var][metric]['mean'])
                    else:
                        metric_values.append(np.nan)
                
                x_pos = np.arange(len(metrics)) + (rank-1)*0.15
                ax.bar(x_pos, metric_values, width=0.15, 
                      label=f'#{rank}: {run_name[:20]}...', 
                      color=colors[rank-1], alpha=0.8)
        
        ax.set_xlabel('Error Metric', fontsize=10)
        ax.set_ylabel('Error Value', fontsize=10)
        ax.set_title(f'{label} Comparison', fontsize=12)
        ax.set_xticks(np.arange(len(metrics)) + 0.3)
        ax.set_xticklabels([m.upper() for m in metrics])
        ax.legend(fontsize=8, loc='best')
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_yscale('log')
    
    plt.tight_layout()
    output_file = output_dir / f"{experiment_name}_top5_detailed.png"
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    logger.info(f"       └─ Saved top 5 detailed comparison to {output_file.name}")


def create_branch_comparison_plot(branch_best, runs_per_branch, combined_scores, output_dir, experiment_name):
    """Create comparison of best performers from each branch."""
    import matplotlib.pyplot as plt
    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    branch_names = []
    best_scores = []
    best_run_names = []
    
    for branch_name, (run_name, scores) in branch_best.items():
        branch_names.append(branch_name)
        best_scores.append(scores['combined'])
        best_run_names.append(run_name)
    
    bars = ax.bar(range(len(branch_names)), best_scores, alpha=0.8, edgecolor='black', linewidth=1.5)
    
    # Color the overall best
    min_idx = np.argmin(best_scores)
    bars[min_idx].set_color('gold')
    bars[min_idx].set_alpha(1.0)
    
    ax.set_xlabel('Branch', fontsize=12, fontweight='bold')
    ax.set_ylabel('Combined Error Score (lower is better)', fontsize=12, fontweight='bold')
    ax.set_title(f'{experiment_name}: Best Performer per Branch\nGold = Overall Best', 
                fontsize=14, fontweight='bold')
    ax.set_xticks(range(len(branch_names)))
    ax.set_xticklabels(branch_names, fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_yscale('log')
    
    # Add run names with decoded experiment details
    for i, (score, run_name) in enumerate(zip(best_scores, best_run_names)):
        # Show branch name at top
        ax.text(i, score * 1.2, f'{branch_names[i]}', ha='center', va='bottom', 
               fontsize=9, fontweight='bold', color='darkblue')
        # Show decoded experiment name below
        decoded_title = format_experiment_title(run_name, max_line_length=40)
        ax.text(i, score * 0.9, decoded_title, ha='center', va='top', 
               fontsize=7, rotation=0, style='italic', 
               bbox=dict(boxstyle='round,pad=0.5', facecolor='wheat', alpha=0.7))
    
    plt.tight_layout()
    output_file = output_dir / f"{experiment_name}_branch_best.png"
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    logger.info(f"       └─ Saved branch comparison to {output_file.name}")


def create_error_evolution_plots(top_3, error_norms_cache, metrics, output_dir, experiment_name):
    """Create time evolution plots for top 3 performers."""
    import matplotlib.pyplot as plt
    
    for metric in metrics:
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f'{experiment_name}: {metric.upper()} Error Evolution - Top 3 Performers', 
                    fontsize=16, fontweight='bold')
        axes = axes.flatten()
        
        variables = ['rho', 'ux', 'pp', 'ee']
        var_labels = [r'$\rho$ [g cm$^{-3}$]', r'$u_x$ [km s$^{-1}$]', r'$p$ [dyn cm$^{-2}$]', r'$e$ [km$^2$ s$^{-2}$]']
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
        
        for idx, (var, label) in enumerate(zip(variables, var_labels)):
            ax = axes[idx]
            
            for rank, (run_name, scores) in enumerate(top_3, 1):
                if run_name not in error_norms_cache:
                    continue
                
                error_norms = error_norms_cache[run_name]['error_norms']
                
                if var in error_norms and metric in error_norms[var]:
                    errors = error_norms[var][metric]['per_timestep']
                    timesteps = range(len(errors))
                    
                    ax.plot(timesteps, errors, 'o-', linewidth=2, markersize=4,
                           color=colors[rank-1], alpha=0.7, 
                           label=f'#{rank}: {run_name[:25]}...')
            
            ax.set_xlabel('Timestep (VAR index)', fontsize=10)
            ax.set_ylabel(f'{metric.upper()} Error', fontsize=10)
            ax.set_title(f'{label} Evolution', fontsize=12)
            ax.legend(fontsize=8, loc='best')
            ax.grid(True, alpha=0.3)
            ax.set_yscale('log')
        
        plt.tight_layout()
        output_file = output_dir / f"{experiment_name}_top3_{metric}_evolution.png"
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close()
        logger.info(f"       └─ Saved {metric.upper()} evolution to {output_file.name}")


def save_error_norms_summary(sorted_runs, branch_best, error_norms_cache, 
                             combined_scores, metrics, output_dir, experiment_name):
    """Save comprehensive summary report."""
    import json
    
    # Create summary dict
    summary = {
        'experiment': experiment_name,
        'metrics_used': metrics,
        'total_runs_analyzed': len(error_norms_cache),
        'top_5_overall': [],
        'best_per_branch': {},
        'detailed_scores': {}
    }
    
    # Top 5 overall
    for rank, (run_name, scores) in enumerate(sorted_runs[:5], 1):
        summary['top_5_overall'].append({
            'rank': rank,
            'run_name': run_name,
            'combined_score': float(scores['combined']),
            'branch': scores['branch'],
            'per_metric_scores': {k: float(v) for k, v in scores['per_metric'].items()}
        })
    
    # Best per branch
    for branch_name, (run_name, scores) in branch_best.items():
        summary['best_per_branch'][branch_name] = {
            'run_name': run_name,
            'combined_score': float(scores['combined']),
            'per_metric_scores': {k: float(v) for k, v in scores['per_metric'].items()}
        }
    
    # Detailed scores for all runs
    for run_name, scores in combined_scores.items():
        summary['detailed_scores'][run_name] = {
            'combined_score': float(scores['combined']),
            'branch': scores['branch'],
            'per_metric_scores': {k: float(v) for k, v in scores['per_metric'].items()}
        }
    
    # Save JSON
    json_file = output_dir / f"{experiment_name}_error_norms_summary.json"
    with open(json_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    # Save markdown report
    md_file = output_dir / f"{experiment_name}_error_norms_summary.md"
    with open(md_file, 'w') as f:
        f.write(f"# L1/L2 Error Norm Analysis Summary\n\n")
        f.write(f"**Experiment**: {experiment_name}\n\n")
        f.write(f"**Metrics Used**: {', '.join([m.upper() for m in metrics])}\n\n")
        f.write(f"**Total Runs Analyzed**: {len(error_norms_cache)}\n\n")
        
        f.write("## 🥇 Top 5 Overall Performers\n\n")
        for item in summary['top_5_overall']:
            f.write(f"### #{item['rank']}: {item['run_name']}\n")
            f.write(f"- **Branch**: {item['branch']}\n")
            f.write(f"- **Combined Score**: {item['combined_score']:.6e}\n")
            f.write(f"- **Per-Metric Scores**:\n")
            for metric, score in item['per_metric_scores'].items():
                f.write(f"  - {metric.upper()}: {score:.6e}\n")
            f.write("\n")
        
        f.write("## 🏆 Best Performer per Branch\n\n")
        for branch, data in summary['best_per_branch'].items():
            f.write(f"### {branch}\n")
            f.write(f"- **Run**: {data['run_name']}\n")
            f.write(f"- **Combined Score**: {data['combined_score']:.6e}\n")
            f.write(f"- **Per-Metric Scores**:\n")
            for metric, score in data['per_metric_scores'].items():
                f.write(f"  - {metric.upper()}: {score:.6e}\n")
            f.write("\n")
    
    logger.info(f"       ├─ Saved JSON summary to {json_file.name}")
    logger.info(f"       └─ Saved Markdown report to {md_file.name}")


def generate_final_rich_report(experiment_name, video_dir, error_norms_dir, 
                               n_runs_analyzed, top_5, branch_best, 
                               combined_scores, metrics):
    """Generate comprehensive final Rich report with all analysis results."""
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.text import Text
    
    console = Console()
    
    console.print("\n")
    console.print("╔" + "═" * 78 + "╗")
    console.print("║" + " " * 20 + "COMPREHENSIVE ANALYSIS COMPLETE" + " " * 27 + "║")
    console.print("╚" + "═" * 78 + "╝")
    console.print("\n")
    
    # ============ EXPERIMENT INFO ============
    console.print(Panel(
        f"[bold cyan]Experiment:[/bold cyan] {experiment_name}\n"
        f"[bold cyan]Runs Analyzed:[/bold cyan] {n_runs_analyzed}\n"
        f"[bold cyan]Error Metrics:[/bold cyan] {', '.join([m.upper() for m in metrics])}",
        title="📊 Experiment Information",
        border_style="cyan"
    ))
    
    # ============ TOP 5 OVERALL PERFORMERS ============
    console.print("\n")
    top_5_table = Table(
        title="🥇 Top 5 Overall Best Performers",
        title_style="bold yellow",
        border_style="yellow",
        show_header=True,
        header_style="bold"
    )
    
    top_5_table.add_column("Rank", style="bold", justify="center", width=6)
    top_5_table.add_column("Run Name", style="cyan")
    top_5_table.add_column("Branch", style="magenta")
    top_5_table.add_column("Combined Score", justify="right", style="green")
    
    rank_emojis = {1: "🥇", 2: "🥈", 3: "🥉", 4: "4️⃣", 5: "5️⃣"}
    
    for idx, (run_name, scores) in enumerate(top_5, 1):
        emoji = rank_emojis.get(idx, f"{idx}")
        top_5_table.add_row(
            emoji,
            run_name,
            scores['branch'],
            f"{scores['combined']:.6e}"
        )
    
    console.print(top_5_table)
    
    # ============ PER-METRIC SCORES FOR TOP 3 ============
    console.print("\n")
    metrics_table = Table(
        title="📈 Per-Metric Scores (Top 3)",
        title_style="bold blue",
        border_style="blue"
    )
    
    metrics_table.add_column("Rank", style="bold yellow", width=6)
    for metric in metrics:
        metrics_table.add_column(metric.upper(), justify="right", style="cyan")
    
    for idx, (run_name, scores) in enumerate(top_5[:3], 1):
        row_data = [rank_emojis[idx]]
        for metric in metrics:
            score = scores['per_metric'].get(metric, float('nan'))
            row_data.append(f"{score:.4e}")
        metrics_table.add_row(*row_data)
    
    console.print(metrics_table)
    
    # ============ BEST PER BRANCH ============
    console.print("\n")
    branch_table = Table(
        title="🏆 Best Performer per Branch",
        title_style="bold green",
        border_style="green"
    )
    
    branch_table.add_column("Branch", style="bold magenta", width=20)
    branch_table.add_column("Best Run", style="cyan")
    branch_table.add_column("Combined Score", justify="right", style="yellow")
    
    for branch_name, (run_name, scores) in branch_best.items():
        branch_table.add_row(
            branch_name,
            run_name,
            f"{scores['combined']:.6e}"
        )
    
    console.print(branch_table)
    
    # ============ OUTPUT LOCATIONS ============
    console.print("\n")
    console.print(Panel(
        f"[bold green]✓[/bold green] Video Analysis Results:\n"
        f"   📁 {video_dir}\n"
        f"   🎬 Individual error evolution videos\n"
        f"   🎬 Branch overlay comparison videos\n"
        f"   🎬 Top 3 performers overlay video\n\n"
        f"[bold green]✓[/bold green] Error Norm Analysis Results:\n"
        f"   📁 {error_norms_dir}\n"
        f"   📊 Combined scores comparison plot\n"
        f"   📊 Per-metric comparison plots (L1, L2, L∞)\n"
        f"   📊 Top 5 detailed comparison\n"
        f"   📊 Branch comparison plot\n"
        f"   📊 Error evolution plots (top 3)\n"
        f"   📄 JSON summary report\n"
        f"   📄 Markdown summary report",
        title="📂 Output Locations",
        border_style="green"
    ))
    
    # ============ KEY FINDINGS ============
    console.print("\n")
    
    best_run_name, best_scores = top_5[0]
    best_l1 = best_scores['per_metric'].get('l1', float('nan'))
    best_l2 = best_scores['per_metric'].get('l2', float('nan'))
    best_linf = best_scores['per_metric'].get('linf', float('nan'))
    
    findings_text = (
        f"[bold]🎯 Best Overall Parameter Set:[/bold]\n"
        f"   • Run: [cyan]{best_run_name}[/cyan]\n"
        f"   • Branch: [magenta]{best_scores['branch']}[/magenta]\n"
        f"   • Combined Score: [green]{best_scores['combined']:.6e}[/green]\n"
        f"   • L1 Error: [yellow]{best_l1:.6e}[/yellow]\n"
        f"   • L2 Error: [yellow]{best_l2:.6e}[/yellow]\n"
        f"   • L∞ Error: [yellow]{best_linf:.6e}[/yellow]\n\n"
        f"[bold]📊 Analysis Summary:[/bold]\n"
        f"   • Total runs analyzed: {n_runs_analyzed}\n"
        f"   • Branches evaluated: {len(branch_best)}\n"
        f"   • Error metrics used: {', '.join([m.upper() for m in metrics])}\n"
        f"   • Scoring method: Average of all metrics across all variables"
    )
    
    console.print(Panel(
        findings_text,
        title="🔍 Key Findings",
        border_style="bold green"
    ))
    
    # ============ RECOMMENDATIONS ============
    console.print("\n")
    
    improvement_pct = ((top_5[-1][1]['combined'] - best_scores['combined']) / best_scores['combined']) * 100
    
    recommendations_text = (
        f"[bold green]✓[/bold green] The best parameter set ([cyan]{best_run_name}[/cyan]) shows:\n"
        f"   • {improvement_pct:.1f}% better performance than the worst of top 5\n"
        f"   • Consistent low error across all metrics (L1, L2, L∞)\n"
        f"   • Recommended for production use\n\n"
        f"[bold yellow]📌 Next Steps:[/bold yellow]\n"
        f"   • Review detailed plots in [cyan]{error_norms_dir}/plots/[/cyan]\n"
        f"   • Check error evolution videos in [cyan]{video_dir}/[/cyan]\n"
        f"   • Compare branch-specific results if testing parameter variations\n"
        f"   • Consider running additional convergence studies with the best parameters"
    )
    
    console.print(Panel(
        recommendations_text,
        title="💡 Recommendations",
        border_style="yellow"
    ))
    
    console.print("\n")
    console.print(Panel(
        f"[bold green]✨ ANALYSIS COMPLETE! ✨[/bold green]\n\n"
        f"All results have been saved to:\n"
        f"[cyan]{DIRS.root / 'analysis' / experiment_name}/[/cyan]",
        border_style="bold green"
    ))
    console.print("\n")

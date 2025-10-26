# src/post_processing.py

import os
import sys
import yaml
from pathlib import Path
import jinja2
import numpy as np
from loguru import logger
from typing import Dict, List, Tuple

from src.core.constants import DIRS, FILES
from src.core.logging import setup_file_logging
from src.core.config_loader import create_config_loader
from src.analysis.errors import (
    calculate_std_deviation_across_vars, 
    calculate_absolute_deviation_per_var,
    calculate_spatial_errors,
    calculate_error_norms,
    calculate_normalized_spatial_errors,
    ExperimentErrorAnalyzer
)
from src.analysis.metrics import calculate_errors_over_time
from src.visualization.plots import (
    create_combined_scores_plot,
    create_per_metric_plots,
    create_best_performers_plot,
    create_branch_comparison_plot,
    create_error_evolution_plots,
)
from src.visualization.videos import (
    create_var_evolution_video,
    create_error_evolution_video,
    create_overlay_error_evolution_video,
    create_combined_error_evolution_video
)
from src.experiment.naming import format_experiment_title, format_short_experiment_name
from src.analysis.organizer import AnalysisOrganizer

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

def clear_directory(directory: Path):
    """Clears all files in a directory, creating it if it doesn't exist."""
    if directory.exists():
        import shutil
        logger.info(f"Clearing existing directory: {directory}")
        shutil.rmtree(directory)
    directory.mkdir(parents=True, exist_ok=True)


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
        
        # Sort VAR files numerically by extracting the number from filename
        var_files = sorted(proc_dir.glob("VAR*"), key=lambda p: int(p.stem.replace('VAR', '')))
        
        if not var_files:
            logger.warning(f"No VAR files found in {proc_dir}")
            return None
        
        logger.info(f"Loading all {len(var_files)} VAR files from {run_path}")
        
        # Read params once - it's the same for all VAR files
        params = read.param(datadir=str(data_dir), quiet=True, conflicts_quiet=True)
        
        all_data = []
        for var_file in var_files:
            try:
                # Read VAR file with trimall=True to remove ghost zones for 1D data
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
                
                # Use grid from VAR file (includes ghost zones)
                all_data.append({
                    "x": np.squeeze(var.x), 
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


def visualize_suite(experiment_name: str, specific_runs: list = None, var_selection: str = None):
    """Simplified visualization function - redirects to video-only analysis."""
    logger.warning("The --viz flag is deprecated. Use --analyze for video-only analysis instead.")
    logger.info("Redirecting to video-only analysis...")
    analyze_suite_videos_only(experiment_name)


def analyze_suite_comprehensive(experiment_name: str, error_method: str = 'absolute'):
    """Legacy function name - redirects to video-only analysis for backward compatibility."""
    logger.warning("analyze_suite_comprehensive() is deprecated. Redirecting to video-only analysis...")
    analyze_suite_videos_only(experiment_name, error_method)


def analyze_suite_videos_only(experiment_name: str, error_method: str = 'absolute', combined_video: bool = False):
    """Comprehensive analysis: Creates videos, calculates L1/L2 error norms, and generates final report.
    
    Workflow:
    1. Load all VAR files and calculate errors (cached)
    2. Create individual error evolution videos (and combined, if requested)
    3. Find best performer in each branch → create overlay videos
    4. Find top 3 best performers overall → create overlay video
    5. Calculate L1/L2 error norms with combined scoring
    6. Create comprehensive visualizations
    7. Generate final Rich summary report
    
    Args:
        experiment_name: Name of the experiment suite
        error_method: Error calculation method for spatial errors
        combined_video: If True, generate a combined error evolution video.
    """
    # Setup file logging for this analysis run
    setup_file_logging(experiment_name, 'analysis')
    
    logger.info(f"=" * 80)
    logger.info(f"STARTING VIDEO-ONLY ANALYSIS: '{experiment_name}'")
    if combined_video:
        logger.info("Combined error video generation ENABLED.")
    logger.info(f"=" * 80)
    
    plan_file = DIRS.config / experiment_name / DIRS.plan_subdir / FILES.plan
    with open(plan_file, 'r') as f: 
        plan = yaml.safe_load(f)
    
    # Read error analysis configuration from plan file
    error_config = plan.get('error_analysis', {})
    metrics = error_config.get('metrics', ['l1', 'l2', 'linf'])
    ranking_metric = error_config.get('ranking_metric', None)
    combine_in_videos = error_config.get('combine_in_videos', True)
    analyze_variables = error_config.get('analyze_variables', ['rho', 'ux', 'pp', 'ee'])
    
    # Validate and set ranking metric
    if ranking_metric is None:
        # Default to first metric if not specified
        ranking_metric = metrics[0] if metrics else 'l1'
        logger.warning(f"No ranking_metric specified in config, defaulting to first metric: {ranking_metric.upper()}")
    elif ranking_metric not in metrics:
        # Ranking metric must be in the metrics list
        logger.error(f"Configured ranking_metric '{ranking_metric}' not in metrics list {metrics}")
        logger.warning(f"Falling back to first metric: {metrics[0].upper()}")
        ranking_metric = metrics[0] if metrics else 'l1'
    
    # Load config loader to get variable configurations
    config_loader = create_config_loader(experiment_name, DIRS.config)
    analysis_config = config_loader.load_analysis_config()
    variables_config = analysis_config.get('variables', {})
    
    logger.info(f"Error analysis configuration:")
    logger.info(f"  ├─ Metrics to calculate: {', '.join([m.upper() for m in metrics])}")
    logger.info(f"  ├─ Ranking metric: {ranking_metric.upper()}")
    logger.info(f"  ├─ Variables: {', '.join(analyze_variables)}")
    logger.info(f"  └─ Combine in videos: {combine_in_videos}")
    
    hpc_run_base_dir = Path(plan['hpc']['run_base_dir'])
    manifest_file = DIRS.runs / experiment_name / FILES.manifest
    analysis_dir = DIRS.root / "analysis" / experiment_name
    
    # Create directory structure following the standard: var/, error/, best/
    var_dir = analysis_dir / "var"
    error_dir = analysis_dir / "error"
    
    var_evolution_dir = var_dir / "evolution"
    error_evolution_dir = error_dir / "evolution"
    error_frames_dir = error_dir / "frames"

    # Clear old visualizations before creating new ones
    logger.info("Clearing old visualization directories...")
    clear_directory(var_evolution_dir)
    clear_directory(error_evolution_dir)
    clear_directory(error_frames_dir)

    with open(manifest_file, 'r') as f: 
        run_names = [line.strip() for line in f if line.strip()]
    
    total_runs = len(run_names)
    logger.info(f"Total experiments to process: {total_runs}")
    
    # Extract branch information
    branches = plan.get('branches', [])
    branch_names = [b['name'] for b in branches] if branches else ['default']
    
    # Organize runs by branch
    runs_per_branch = {branch: [] for branch in branch_names}
    runs_per_branch['default'] = []  # Always include default for unmatched runs
    
    for run_name in run_names:
        matched = False
        for branch_name in branch_names:
            if branch_name in run_name:
                runs_per_branch[branch_name].append(run_name)
                matched = True
                break
        if not matched:
            runs_per_branch['default'].append(run_name)
    
    # ============================================================
    # Initialize organizer early to use correct directory structure
    # ============================================================
    organizer = AnalysisOrganizer(experiment_name, analysis_dir)
    organizer.create_structure()
    
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
            
            # --- START: Modified section for combined video ---
            all_sim_data = load_all_var_files(hpc_run_base_dir / run_name)
            if not all_sim_data:
                logger.warning(f"     └─ ✗ Failed to load VAR files")
                continue

            all_analytical_data = [get_analytical_solution(s['params'], s['x'], s['t']) for s in all_sim_data]
            if not all(all_analytical_data):
                logger.warning(f"     └─ ✗ Failed to generate analytical solutions")
                continue
            
            # Always calculate absolute error for caching
            spatial_errors_abs = calculate_spatial_errors(all_sim_data, all_analytical_data, error_method='absolute')

            # Cache the essential data
            loaded_data_cache[run_name] = {
                'sim_data': all_sim_data,
                'analytical_data': all_analytical_data,
                'branch': branch_name,
                'spatial_errors': spatial_errors_abs,
            }
            
            # Get unit length - respect use_code_units flag
            unit_length = 1.0
            if all_sim_data and 'params' in all_sim_data[0]:
                # Check if we should use code units (normalized) or physical units
                use_code_units = error_config.get('use_code_units', True)
                
                if use_code_units:
                    unit_length = 1.0  # Force code units for normalized calculations
                    logger.debug(f"     ├─ Using code units (unit_length=1.0) for normalized calculations")
                else:
                    unit_length = all_sim_data[0]['params'].unit_length
                    logger.debug(f"     ├─ Using physical units (unit_length={unit_length:.3e})")

            logger.info(f"     ├─ Creating var evolution video and frames...")
            create_var_evolution_video(
                all_sim_data, all_analytical_data, var_evolution_dir, run_name, fps=2, save_frames=True
            )
            
            # Create COMBINED error evolution with all configured metrics by DEFAULT
            logger.info(f"     ├─ Creating combined error evolution (L1, L2, LINF) video and frames...")
            if combine_in_videos and len(metrics) > 1:
                # Calculate spatial errors for each error calculation method
                spatial_errors_dict = {}
                
                # Map metrics to error calculation methods
                # L1 and LINF use absolute error, L2 uses squared error
                if 'l1' in metrics or 'linf' in metrics:
                    spatial_errors_dict['L1/LINF (Absolute)'] = spatial_errors_abs
                if 'l2' in metrics:
                    spatial_errors_sq = calculate_spatial_errors(all_sim_data, all_analytical_data, error_method='squared')
                    spatial_errors_dict['L2 (Squared)'] = spatial_errors_sq
                
                # Create combined video showing all metrics together
                create_combined_error_evolution_video(
                    spatial_errors_dict, error_evolution_dir, run_name, fps=2, 
                    unit_length=unit_length, save_frames=True
                )
                logger.info(f"     └─ ✓ Created combined error evolution with {len(spatial_errors_dict)} error types")
            else:
                # Fallback: create single error evolution video
                logger.info(f"     ├─ Creating single error evolution video and frames...")
                create_error_evolution_video(
                    spatial_errors_abs, error_evolution_dir, run_name, fps=2, 
                    unit_length=unit_length, save_frames=True
                )
                logger.info(f"     └─ ✓ Created error evolution video")
            # --- END: Modified section ---
            
            # Calculate normalized spatial-temporal errors (for notebook usage)
            logger.info(f"     ├─ Calculating normalized spatial-temporal errors...")
            normalized_errors = calculate_normalized_spatial_errors(
                all_sim_data,
                all_analytical_data,
                variables=analyze_variables,
                normalize_by_space=False,
                normalize_by_time=False
            )
            
            # Cache normalized errors for later use (e.g., in notebooks)
            loaded_data_cache[run_name]['normalized_errors'] = normalized_errors
            logger.info(f"     └─ ✓ Calculated errors for {len(normalized_errors)} variables (available for notebook visualization)")
            
            # Create and cache "mind the gap" spacetime data
            logger.info(f"     ├─ Creating 'mind the gap' spacetime data...")
            from src.analysis.data_prep import prepare_spacetime_error_data, export_spacetime_data_to_json
            
            mind_gap_dir = analysis_dir / "error" / "mind_the_gap" / run_name
            mind_gap_dir.mkdir(parents=True, exist_ok=True)
            
            # Prepare and save data for each variable
            for var in analyze_variables:
                prepared_data = prepare_spacetime_error_data(
                    normalized_errors,
                    var,
                    unit_length,
                    use_relative=True
                )
                if prepared_data:
                    export_spacetime_data_to_json(prepared_data, mind_gap_dir, run_name, var)
            
            logger.info(f"     └─ ✓ Saved spacetime data for interactive visualization")
    
    # ============================================================
    # PHASE 2: Find best performers and create overlay videos
    # ============================================================
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 2: Creating overlay videos")
    logger.info("=" * 80)
    
    # Use the explicitly configured ranking_metric (already validated above)
    logger.info(f"Using configured ranking metric: {ranking_metric.upper()}")
    
    # Calculate average error for each run using ONLY DENSITY (rho)
    run_scores = {}
    for run_name, cached in loaded_data_cache.items():
        spatial_errors = cached['spatial_errors']
        
        # Calculate average error for DENSITY ONLY across all timesteps using configured ranking metric
        total_error = 0
        count = 0
        if 'rho' in spatial_errors:
            for errors in spatial_errors['rho']['errors_per_timestep']:
                if ranking_metric == 'l1':
                    # L1 norm: mean absolute error
                    total_error += np.mean(np.abs(errors))
                elif ranking_metric == 'l2':
                    # L2 norm: root mean square error
                    total_error += np.sqrt(np.mean(errors**2))
                elif ranking_metric == 'linf':
                    # L∞ norm: maximum absolute error
                    total_error += np.max(np.abs(errors))
                else:
                    # Default to L1 if somehow an invalid metric got through
                    logger.warning(f"Unknown ranking metric '{ranking_metric}', using L1")
                    total_error += np.mean(np.abs(errors))
                count += 1
        
        avg_error = total_error / count if count > 0 else float('inf')
        run_scores[run_name] = avg_error
        logger.info(f"  {run_name}: avg {ranking_metric.upper()} error (rho only) = {avg_error:.6e}")
    
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
            logger.info(f"  ├─ {branch_name}: {best_run} ({ranking_metric.upper()}={branch_scores[best_run]:.6e})")
    
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
            # Get unit_length from first run - respect use_code_units flag
            unit_length = 1.0
            first_run_data = loaded_data_cache[branch_runs[0]]
            if first_run_data['sim_data'] and 'params' in first_run_data['sim_data'][0]:
                params = first_run_data['sim_data'][0]['params']
                use_code_units = error_config.get('use_code_units', True)
                
                if use_code_units:
                    unit_length = 1.0  # Force code units
                elif hasattr(params, 'unit_length'):
                    unit_length = params.unit_length
            
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
        logger.info(f"  ├─ #{idx}: {run} ({ranking_metric.upper()}={score:.6e})")
    
    # Create overlay video for top 3
    logger.info(f"\n🎬 Creating top 3 overlay video...")
    top_3_spatial_errors = []
    for run_name in top_3_runs:
        if run_name in loaded_data_cache:
            cached = loaded_data_cache[run_name]
            top_3_spatial_errors.append((run_name, cached['spatial_errors']))
    
    if top_3_spatial_errors:
        # Get unit_length from first run - respect use_code_units flag
        unit_length = 1.0
        first_run_data = loaded_data_cache[top_3_runs[0]]
        if first_run_data['sim_data'] and 'params' in first_run_data['sim_data'][0]:
            params = first_run_data['sim_data'][0]['params']
            use_code_units = error_config.get('use_code_units', True)
            
            if use_code_units:
                unit_length = 1.0  # Force code units
            elif hasattr(params, 'unit_length'):
                unit_length = params.unit_length
        
        output_name = f"{experiment_name}_top3_best_performers_overlay"
        create_overlay_error_evolution_video(
            top_3_spatial_errors, error_evolution_dir, output_name, fps=2, unit_length=unit_length
        )
        logger.info(f"     └─ ✓ Created top 3 overlay video")
    
    # ============================================================
    # PHASE 3: Calculate L1/L2 error norms (reusing loaded data)
    # ============================================================
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 3: Calculating error norms")
    logger.info("=" * 80)
    
    # Use correct directory structure from organizer
    error_norms_dir = organizer.error_norms_dir
    plots_dir = error_norms_dir / "plots"
    
    # Clear old error norm results before creating new ones
    logger.info("Clearing old error norm directories...")
    clear_directory(error_norms_dir)
    clear_directory(plots_dir)
    
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
    
    # Calculate combined scores using ONLY DENSITY (rho)
    logger.info(f"\nCalculating combined scores (using DENSITY only)...")
    combined_scores = {}
    
    for run_name, cached in error_norms_cache.items():
        error_norms = cached['error_norms']
        scores_per_metric = {}
        
        # Use ONLY density (rho) for all metrics
        for metric in metrics:
            if 'rho' in error_norms and metric in error_norms['rho']:
                mean_val = error_norms['rho'][metric]['mean']
                if np.isfinite(mean_val):
                    scores_per_metric[metric] = mean_val
        
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
    # PHASE 6: Populate best performers folders
    # ============================================================
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 6: Populating best performers folders")
    logger.info("=" * 80)
    
    organizer.populate_best_performers(
        error_norms_cache, combined_scores, top_n=3, metrics=metrics
    )
    
    # ============================================================
    # FINAL RICH REPORT
    # ============================================================
    logger.info("\n" + "=" * 80)
    logger.info("FINAL SUMMARY")
    logger.info("=" * 80)
    
    generate_final_rich_report(
        experiment_name, organizer.error_evolution_dir, organizer.error_norms_dir, 
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
    
    # Setup file logging for this analysis run
    setup_file_logging(experiment_name, 'analysis')
    
    logger.info("=" * 80)
    logger.info(f"STARTING L1/L2 ERROR NORM ANALYSIS: '{experiment_name}'")
    logger.info("=" * 80)
    
    plan_file = DIRS.config / experiment_name / DIRS.plan_subdir / FILES.plan
    with open(plan_file, 'r') as f: 
        plan = yaml.safe_load(f)
    
    hpc_run_base_dir = Path(plan['hpc']['run_base_dir'])
    manifest_file = DIRS.runs / experiment_name / FILES.manifest
    analysis_dir = DIRS.root / "analysis" / experiment_name
    
    # Create NEW subfolder for error norm results
    error_norms_dir = analysis_dir / "error_norms"
    plots_dir = error_norms_dir / "plots"
    
    # Clear old error norm results before creating new ones
    logger.info("Clearing old error norm directories...")
    clear_directory(error_norms_dir)
    clear_directory(plots_dir)

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
        
        # Calculate combined score using ONLY DENSITY (rho)
        scores_per_metric = {}
        
        # Use ONLY density (rho) for all metrics
        for metric in metrics:
            if 'rho' in error_norms and metric in error_norms['rho']:
                mean_val = error_norms['rho'][metric]['mean']
                if np.isfinite(mean_val):
                    scores_per_metric[metric] = mean_val
        
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

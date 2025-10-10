# src/post_processing.py

import os
import sys
import yaml
from pathlib import Path
import jinja2
import numpy as np
from loguru import logger

from .constants import DIRS, FILES
from .analysis import compare_simulation_to_analytical, format_comparison_table
from .visualization import plot_simulation_vs_analytical
from .error_analysis import (
    calculate_std_deviation_across_vars, 
    calculate_absolute_deviation_per_var,
    ExperimentErrorAnalyzer
)
from .visualization_collage import (
    create_var_evolution_collage,
    create_branch_var_evolution_collage,
    create_best_performers_var_evolution_collage,
    select_var_file_for_viz
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

def load_simulation_data(run_path: Path, var_file_name: str = None) -> dict | None:
    """Loads and processes snapshot data from a single simulation run.
    
    Args:
        run_path: Path to the run directory
        var_file_name: Specific VAR file name to load. If None, loads the middle VAR file.
    """
    try:
        if not run_path.is_dir():
            logger.warning(f"Run directory not found: {run_path}")
            return None
            
        data_dir = run_path / "data"
        proc_dir = data_dir / "proc0" if (data_dir / "proc0").is_dir() else data_dir
        var_files = sorted(proc_dir.glob("VAR*"))
        logger.info(f"Loading data from {run_path}, found {len(var_files)} VAR files.")
        if not var_files:
            logger.warning(f"No VAR files found in {proc_dir}")
            return None
        
        # Select which VAR file to load
        if var_file_name:
            selected_var = var_file_name
        else:
            # Default: select middle VAR file
            selected_var_path = select_var_file_for_viz(var_files, 'middle')
            selected_var = selected_var_path.name
        
        params = read.param(datadir=str(data_dir), quiet=True)
        var = read.var(selected_var, datadir=str(data_dir), quiet=True, trimall=True)
        grid = read.grid(datadir=str(data_dir), quiet=True, trim=True)
        
        density = np.exp(var.lnrho) if hasattr(var, 'lnrho') else var.rho
        cp, gamma = params.cp, params.gamma
        cv = cp / gamma
        
        if not hasattr(var, 'ss'):
            logger.error(f"Variable 'ss' not found for {run_path}. Cannot calculate pressure.")
            return None

        rho0 = getattr(params, 'rho0', 1.0)
        cs0 = getattr(params, 'cs0', 1.0)
        lnrho0 = np.log(rho0)
        lnTT0 = np.log(cs0**2 / (cp * (gamma - 1.0)))
        
        pressure = (cp - cv) * np.exp(lnTT0 + (gamma / cp * var.ss) + (gamma * np.log(density)) - ((gamma - 1.0) * lnrho0))
        internal_energy = pressure / (density * (gamma - 1.0)) if gamma > 1.0 else np.zeros_like(density)
        
        return {
            "x": np.squeeze(grid.x), "rho": np.squeeze(density), "ux": np.squeeze(var.ux),
            "pp": np.squeeze(pressure), "ee": np.squeeze(internal_energy), 
            "t": var.t, "params": params
        }
    except Exception as e:
        logger.error(f"Failed to load data from {run_path}: {e}")
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

def process_run_visualization(run_path: Path, report_dir: Path, run_name: str, 
                             var_selection: str = None) -> dict | None:
    """Processes a single run for visualization."""
    logger.info(f"--- Visualizing run: {run_name} ---")
    
    sim_data = load_simulation_data(run_path, var_selection)
    if not sim_data: return None

    analytical_data = get_analytical_solution(sim_data['params'], sim_data['x'], sim_data['t'])
    if not analytical_data: return None

    run_report_dir = report_dir / run_name
    run_report_dir.mkdir(parents=True, exist_ok=True)

    np.savez_compressed(run_report_dir / "simulation_data.npz", 
                       **{k: v for k, v in sim_data.items() if k not in ['params', 'var_file']})
    np.savez_compressed(run_report_dir / "analytical_data.npz", **analytical_data)
    
    plot_simulation_vs_analytical(sim_data, analytical_data, run_report_dir, run_name)
    
    return compare_simulation_to_analytical(sim_data, analytical_data)


def process_run_analysis(run_path: Path, run_name: str, branch_name: str) -> tuple[dict, dict, list, list] | None:
    """Processes a single run for comprehensive error analysis across all VAR files.
    
    Returns:
        Tuple of (std_devs, abs_devs, all_sim_data, all_analytical_data) or None if failed.
        The loaded data is returned to enable caching and reuse for collage generation.
    """
    logger.info(f"--- Analyzing run: {run_name} (branch: {branch_name}) ---")
    
    # Load all VAR files ONCE
    all_sim_data = load_all_var_files(run_path)
    if not all_sim_data:
        return None
    
    # Generate analytical solutions for all timesteps
    all_analytical_data = []
    for sim_data in all_sim_data:
        analytical_data = get_analytical_solution(sim_data['params'], sim_data['x'], sim_data['t'])
        if analytical_data:
            all_analytical_data.append(analytical_data)
    
    if not all_analytical_data:
        logger.error(f"Failed to generate analytical solutions for {run_name}")
        return None
    
    # Calculate error metrics
    std_devs = calculate_std_deviation_across_vars(all_sim_data, all_analytical_data)
    abs_devs = calculate_absolute_deviation_per_var(all_sim_data, all_analytical_data)
    
    # Return loaded data along with metrics for caching/reuse
    return std_devs, abs_devs, all_sim_data, all_analytical_data

def visualize_suite(experiment_name: str, specific_runs: list = None, var_selection: str = None):
    """Visualize an experiment suite (formerly analyze_suite)."""
    logger.info(f"--- STARTING VISUALIZATION for experiment: '{experiment_name}' ---")
    
    plan_file = DIRS.config / experiment_name / DIRS.plan_subdir / FILES.plan
    with open(plan_file, 'r') as f: plan = yaml.safe_load(f)
    
    hpc_run_base_dir = Path(plan['hpc']['run_base_dir'])
    manifest_file = DIRS.runs / experiment_name / FILES.manifest
    report_dir = DIRS.root / "reports" / experiment_name
    report_dir.mkdir(parents=True, exist_ok=True)

    with open(manifest_file, 'r') as f: run_names = [line.strip() for line in f if line.strip()]
    
    # Filter runs if specific ones requested
    if specific_runs:
        run_names = [r for r in run_names if r in specific_runs]
        logger.info(f"Visualizing specific runs: {run_names}")

    all_run_metrics = {}
    for run_name in run_names:
        metrics = process_run_visualization(hpc_run_base_dir / run_name, report_dir, run_name, var_selection)
        if metrics:
            all_run_metrics[run_name] = metrics
    
    if all_run_metrics:
        log_summary, markdown_table = format_comparison_table(all_run_metrics)
        logger.info(log_summary)
        
        # Save the consolidated markdown table for Quarto
        comparison_summary_path = report_dir / "comparison_summary.md"
        with open(comparison_summary_path, "w") as f:
            f.write(markdown_table)
        logger.success(f"Saved comparison summary to {comparison_summary_path}")
    
    generate_quarto_report(experiment_name, report_dir, run_names)
    
    logger.success(f"Visualization for '{experiment_name}' finished successfully.")


def analyze_suite_comprehensive(experiment_name: str):
    """Comprehensive error analysis across all VAR files for an experiment suite.
    
    OPTIMIZED: VAR files are loaded once and cached for reuse in all visualizations.
    """
    logger.info(f"--- STARTING COMPREHENSIVE ERROR ANALYSIS for experiment: '{experiment_name}' ---")
    
    plan_file = DIRS.config / experiment_name / DIRS.plan_subdir / FILES.plan
    with open(plan_file, 'r') as f: 
        plan = yaml.safe_load(f)
    
    hpc_run_base_dir = Path(plan['hpc']['run_base_dir'])
    manifest_file = DIRS.runs / experiment_name / FILES.manifest
    analysis_dir = DIRS.root / "analysis" / experiment_name
    analysis_dir.mkdir(parents=True, exist_ok=True)

    with open(manifest_file, 'r') as f: 
        run_names = [line.strip() for line in f if line.strip()]
    
    # Initialize error analyzer
    analyzer = ExperimentErrorAnalyzer(analysis_dir)
    
    # Extract branch information from run names (based on naming convention)
    branches = plan.get('branches', [])
    branch_names = [b['name'] for b in branches] if branches else ['default']
    
    # OPTIMIZATION: Cache all loaded VAR data to avoid redundant file loading
    logger.info("Loading and analyzing all VAR files (caching for reuse)...")
    loaded_data_cache = {}  # Structure: {run_name: {'sim_data': [...], 'analytical_data': [...]}}
    
    # Process each run and cache loaded data
    for run_name in run_names:
        # Determine which branch this run belongs to
        branch_name = 'default'
        for b_name in branch_names:
            if b_name in run_name:
                branch_name = b_name
                break
        
        result = process_run_analysis(hpc_run_base_dir / run_name, run_name, branch_name)
        if result:
            std_devs, abs_devs, all_sim_data, all_analytical_data = result
            
            # Add error metrics to analyzer
            analyzer.add_experiment_data(experiment_name, run_name, branch_name, std_devs, abs_devs)
            
            # Cache loaded data for reuse
            loaded_data_cache[run_name] = {
                'sim_data': all_sim_data,
                'analytical_data': all_analytical_data,
                'branch': branch_name
            }
            
            logger.info(f"✓ Cached {len(all_sim_data)} VAR files for {run_name}")
    
    # Save intermediate data
    analyzer.save_intermediate_data(experiment_name)
    
    # Generate all comparison plots
    logger.info("Generating error analysis visualizations...")
    
    # 1. Individual experiment plots
    logger.info("Creating individual experiment plots...")
    for branch_name, runs in analyzer.experiment_data[experiment_name].items():
        for run_name in runs.keys():
            analyzer.plot_individual_experiment_std(
                experiment_name, branch_name, run_name, 
                analysis_dir / "individual"
            )
    
    # 2. Branch comparison plots
    logger.info("Creating branch comparison plots...")
    analyzer.plot_branch_comparison(experiment_name, analysis_dir / "branch_comparison")
    
    # 3. Best performers comparison
    logger.info("Creating best performers comparison...")
    analyzer.plot_best_performers_comparison(analysis_dir / "best_performers")
    
    # 4. Generate VAR evolution collages (USING CACHED DATA - NO RELOADING)
    logger.info("Creating VAR evolution collages (using cached data)...")
    collage_dir = analysis_dir / "var_evolution"
    collage_dir.mkdir(parents=True, exist_ok=True)
    
    # Organize cached data by branch for collages
    branch_collage_data_by_branch = {}
    for run_name, cached in loaded_data_cache.items():
        branch_name = cached['branch']
        if branch_name not in branch_collage_data_by_branch:
            branch_collage_data_by_branch[branch_name] = {}
        
        # Individual run collage (using cached data)
        create_var_evolution_collage(
            cached['sim_data'], cached['analytical_data'], 
            collage_dir / "individual", run_name
        )
        
        # Store for branch collage
        branch_collage_data_by_branch[branch_name][run_name] = {
            'sim_data_list': cached['sim_data'],
            'analytical_data_list': cached['analytical_data']
        }
    
    # Branch-level collages for each variable (using cached data)
    for branch_name, branch_collage_data in branch_collage_data_by_branch.items():
        for var in ['rho', 'ux', 'pp', 'ee']:
            create_branch_var_evolution_collage(
                branch_collage_data, collage_dir / "branch", 
                experiment_name, branch_name, var
            )
    
    # 5. Best performers collages (USING CACHED DATA - NO RELOADING)
    logger.info("Creating best performers collages (using cached data)...")
    branch_best = analyzer.compare_branch_best_performers()
    best_performers_collage_data = {}
    
    for exp_name, branches_data in branch_best.items():
        for branch_name, best_info in branches_data.items():
            best_run = best_info['run']
            
            # Use cached data instead of reloading
            if best_run in loaded_data_cache:
                cached = loaded_data_cache[best_run]
                best_performers_collage_data[f"{exp_name}/{branch_name}"] = {
                    'sim_data_list': cached['sim_data'],
                    'analytical_data_list': cached['analytical_data'],
                    'run_name': best_run
                }
            else:
                logger.warning(f"Cached data not found for best performer: {best_run}")
    
    for var in ['rho', 'ux', 'pp', 'ee']:
        create_best_performers_var_evolution_collage(
            best_performers_collage_data, collage_dir / "best_performers", var
        )
    
    # 6. Generate summary report
    logger.info("Generating summary report...")
    analyzer.generate_summary_report(analysis_dir)
    
    logger.success(f"Comprehensive analysis for '{experiment_name}' finished successfully.")
    logger.info(f"Results saved to: {analysis_dir}")
    logger.info(f"Performance: Loaded {len(loaded_data_cache)} runs with cached VAR data (no redundant file loading)")

def generate_quarto_report(experiment_name: str, report_dir: Path, run_names: list):
    """Renders the Quarto report template."""
    logger.info("--- Generating Quarto Summary Report ---")
    
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(DIRS.templates))
    template = env.get_template("report.qmd.j2")
    
    rendered_content = template.render(
        experiment_name=experiment_name,
        run_names=run_names
    )
    
    report_path = report_dir / "analysis_report.qmd"
    with open(report_path, 'w') as f:
        f.write(rendered_content)
        
    logger.success(f"Quarto report template generated at '{report_path}'")
    logger.info(f"To render the final report, run: quarto render {report_path}")

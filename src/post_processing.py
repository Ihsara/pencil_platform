# src/post_processing.py

import os
import sys
import re
import yaml
import shutil
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import matplotlib.pyplot as plt
from loguru import logger

# Import the centralized constants to build paths correctly
from .constants import DIRS, FILES

# --- Add Pencil Code Python Library to Path ---
PENCIL_CODE_PYTHON_PATH = DIRS.root.parent / "pencil-code" / "python"
if str(PENCIL_CODE_PYTHON_PATH) not in sys.path:
    logger.info(f"Adding '{PENCIL_CODE_PYTHON_PATH}' to system path to find the 'pencil' module.")
    sys.path.insert(0, str(PENCIL_CODE_PYTHON_PATH))

try:
    import pencil.read as read
    from pencil.calc.shocktube import sod
except ImportError as e:
    logger.error(f"FATAL: Failed to import Pencil Code modules from '{PENCIL_CODE_PYTHON_PATH}'. {e}")
    sys.exit(1)


def get_analytical_solution(params, x: np.ndarray, t: float) -> Optional[Dict]:
    """Calculates the analytical Sod shock tube solution."""
    try:
        if not hasattr(params, 'rho0'): setattr(params, 'rho0', 1.0)
        if not hasattr(params, 'cs0'): setattr(params, 'cs0', 1.0)
        solution = sod(x, [t], par=params, lplot=False, magic=['ee'])
        return {
            'rho': np.squeeze(solution.rho), 'ux': np.squeeze(solution.ux),
            'pp': np.squeeze(solution.pp), 'ee': np.squeeze(solution.ee), 'x': x,
        }
    except Exception as e:
        logger.error(f"Failed to calculate analytical solution for t={t}: {e}")
        return None

def load_simulation_data(run_path: Path) -> Optional[Dict]:
    """Loads and processes the final snapshot data from a single simulation run."""
    try:
        if not run_path.is_dir():
            logger.warning(f"Run directory not found: {run_path}")
            return None
        data_dir = run_path / "data"
        proc_dir = data_dir / "proc0" if (data_dir / "proc0").is_dir() else data_dir
        var_files = sorted(proc_dir.glob("VAR*"), key=lambda p: int(re.search(r'(\d+)$', p.name).group(1)))
        if not var_files:
            logger.warning(f"No VAR files found in {proc_dir}")
            return None
        
        params = read.param(datadir=str(data_dir), quiet=True)
        var = read.var(var_files[-1].name, datadir=str(data_dir), quiet=True, trimall=True)
        grid = read.grid(datadir=str(data_dir), quiet=True, trim=True)
        
        density = np.exp(var.lnrho) if hasattr(var, 'lnrho') else var.rho
        rho0 = getattr(params, 'rho0', 1.0)
        cs0 = getattr(params, 'cs0', 1.0)
        cp, gamma = params.cp, params.gamma
        cv = cp / gamma
        lnrho0 = np.log(rho0)
        lnTT0 = np.log(cs0**2 / (cp * (gamma - 1.0)))
        
        pressure = (cp - cv) * np.exp(lnTT0 + (gamma / cp * var.ss) + (gamma * np.log(density)) - ((gamma - 1.0) * lnrho0))
        
        internal_energy = pressure / (density * (gamma - 1.0)) if gamma > 1.0 else np.zeros_like(density)

        return {
            "x": np.squeeze(grid.x), "rho": np.squeeze(density), "ux": np.squeeze(var.ux),
            "pp": np.squeeze(pressure), "ee": np.squeeze(internal_energy), "t": var.t, "params": params
        }
    except Exception as e:
        logger.error(f"Failed to load data from {run_path}: {e}")
        return None

def plot_simulation_vs_analytical(sim_data: dict, analytical_data: dict, output_path: Path, run_name: str):
    """Generates and saves the four core comparison plots for a single simulation."""
    # This function is unchanged.
    pass

def analyze_single_run(run_path: Path, report_dir: Path, run_name: str):
    """Analyzes a single simulation run, plots its results, and saves the processed data."""
    logger.info(f"Processing run: {run_name}")
    sim_data = load_simulation_data(run_path)
    if not sim_data: return
    analytical_data = get_analytical_solution(sim_data['params'], sim_data['x'], sim_data['t'])
    if not analytical_data: return
    run_report_dir = report_dir / run_name
    os.makedirs(run_report_dir, exist_ok=True)
    plot_simulation_vs_analytical(sim_data, analytical_data, run_report_dir, run_name)
    
    data_to_save = {'x': sim_data['x'], 'rho': sim_data['rho'], 'ux': sim_data['ux'], 'pp': sim_data['pp'], 'ee': sim_data['ee']}
    output_npz_path = run_report_dir / "processed_data.npz"
    try:
        np.savez_compressed(output_npz_path, **data_to_save)
        logger.success(f"Saved processed data for '{run_name}'")
    except Exception as e:
        logger.error(f"Failed to save processed data for '{run_name}': {e}")

def _generate_cross_branch_plots(report_dir: Path, all_runs: dict, output_dir: Path):
    """Generates plots comparing branches for each unique parameter set."""
    logger.info("Generating cross-branch comparison plots...")
    plot_definitions = {'density': 'rho', 'velocity': 'ux', 'pressure': 'pp', 'energy': 'ee'}
    branch_colors = {'massfix': '#1f77b4', 'nomassfix': '#ff7f0e'}

    for param_str, runs in all_runs['by_params'].items():
        if len(runs) < 2: continue
        fig, axes = plt.subplots(2, 2, figsize=(18, 14), sharex=True)
        axes = axes.flatten()
        fig.suptitle(f"Branch Comparison for Parameters: {param_str}", fontsize=20, y=0.97)

        for run_name, branch_name in runs.items():
            data = np.load(report_dir / run_name / "processed_data.npz")
            color = branch_colors.get(branch_name, 'gray')
            for ax, key in zip(axes, plot_definitions.values()):
                ax.plot(data['x'], data[key], label=branch_name, color=color, alpha=0.9, linewidth=2.5)
        
        for ax, title in zip(axes, plot_definitions.keys()):
            ax.set_title(title.capitalize(), fontsize=14)
            ax.set_xlabel('Position (x)', fontsize=12)
            ax.set_ylabel(title, fontsize=12)
            ax.grid(True, linestyle='--', alpha=0.6)
            ax.legend()
        
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        filename = output_dir / f"compare_branches_{param_str}.png"
        plt.savefig(filename, dpi=150)
        plt.close(fig)
    logger.success("Finished cross-branch plots.")

def _generate_intra_branch_plots(report_dir: Path, all_runs: dict, output_dir: Path):
    """Generates plots comparing different parameter sweeps within a single branch."""
    logger.info("Generating intra-branch (parameter sweep) comparison plots...")
    plot_definitions = {'density': 'rho', 'velocity': 'ux', 'pressure': 'pp', 'energy': 'ee'}

    for branch_name, runs in all_runs['by_branch'].items():
        fig, axes = plt.subplots(2, 2, figsize=(18, 14), sharex=True)
        axes = axes.flatten()
        fig.suptitle(f"Parameter Sweep Comparison within Branch: '{branch_name}'", fontsize=20, y=0.97)

        colormap = plt.cm.viridis
        colors = colormap(np.linspace(0, 0.9, len(runs)))

        for i, (run_name, param_str) in enumerate(runs.items()):
            data = np.load(report_dir / run_name / "processed_data.npz")
            for ax, key in zip(axes, plot_definitions.values()):
                ax.plot(data['x'], data[key], label=param_str, color=colors[i], alpha=0.8)

        for ax, title in zip(axes, plot_definitions.keys()):
            ax.set_title(title.capitalize(), fontsize=14)
            ax.set_xlabel('Position (x)', fontsize=12)
            ax.set_ylabel(title, fontsize=12)
            ax.legend(fontsize='small', loc='best')
            ax.grid(True, linestyle='--', alpha=0.6)

        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        filename = output_dir / f"compare_params_{branch_name}.png"
        plt.savefig(filename, dpi=150)
        plt.close(fig)
    logger.success(f"Finished intra-branch plots for '{branch_name}'.")

def analyze_suite(experiment_name: str):
    """
    Main function to find, analyze, and plot an entire experiment suite,
    and then generate comparison plots.
    """
    logger.info(f"--- STARTING ANALYSIS for experiment suite: '{experiment_name}' ---")
    
    plan_file = DIRS.config / experiment_name / DIRS.plan_subdir / FILES.plan
    if not plan_file.exists():
        logger.error(f"Plan file not found: {plan_file}.")
        return
    with open(plan_file, 'r') as f:
        plan = yaml.safe_load(f)
    
    hpc_run_base_dir = Path(plan['hpc']['run_base_dir'])
    manifest_file = DIRS.runs / experiment_name / FILES.manifest
    report_dir = DIRS.root / "reports" / experiment_name
    os.makedirs(report_dir, exist_ok=True)

    if not manifest_file.exists():
        logger.error(f"Manifest file not found: {manifest_file}.")
        return
    with open(manifest_file, 'r') as f:
        run_names = [line.strip() for line in f if line.strip()]

    # Step 1: Analyze each run individually
    for run_name in run_names:
        run_path = hpc_run_base_dir / run_name
        analyze_single_run(run_path, report_dir, run_name)

    # Step 2: Generate comparison plots
    logger.info("--- STARTING COMPARISON PLOT GENERATION ---")
    prefix = plan['output_prefix']
    branches = [b['name'] for b in plan.get('branches', [])]
    
    grouped_by_branch = {b: {} for b in branches}
    grouped_by_params = {}

    for run_name in run_names:
        for branch_name in branches:
            if run_name.startswith(f"{prefix}_{branch_name}_"):
                param_str = run_name.replace(f"{prefix}_{branch_name}_", "")
                grouped_by_branch[branch_name][run_name] = param_str
                if param_str not in grouped_by_params:
                    grouped_by_params[param_str] = {}
                grouped_by_params[param_str][run_name] = branch_name
                break
    
    all_runs_grouped = {'by_branch': grouped_by_branch, 'by_params': grouped_by_params}
    
    comparison_dir = report_dir / "_comparisons"
    os.makedirs(comparison_dir, exist_ok=True)
    logger.info(f"Comparison plots will be saved to: {comparison_dir}")

    _generate_cross_branch_plots(report_dir, all_runs_grouped, comparison_dir)
    _generate_intra_branch_plots(report_dir, all_runs_grouped, comparison_dir)
    
    logger.success(f"Analysis and comparison for '{experiment_name}' finished.")
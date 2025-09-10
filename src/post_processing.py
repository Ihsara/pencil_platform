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
    plot_definitions = {
        'density': ('rho', r'Density ($\rho$)'), 'velocity': ('ux', r'Velocity ($u_x$)'),
        'pressure': ('pp', r'Pressure ($p$)'), 'energy': ('ee', r'Internal Energy ($e$)')
    }
    for plot_key, (data_key, ylabel) in plot_definitions.items():
        plt.style.use('seaborn-v0_8-whitegrid')
        fig, ax = plt.subplots(figsize=(10, 7))
        ax.plot(analytical_data['x'], analytical_data[data_key], 'k--', linewidth=2.5, label='Analytical Solution')
        ax.plot(sim_data['x'], sim_data[data_key], 'o-', color='#1f77b4', markersize=4, label=f'Simulation (t={sim_data["t"]:.2e})')
        ax.set_title(f"{ylabel} Profile for\n{run_name}", fontsize=16, pad=15)
        ax.set_xlabel('Position (x) [code units]', fontsize=12)
        ax.set_ylabel(f'{ylabel} [code units]', fontsize=12)
        ax.legend(fontsize=11)
        ax.grid(True, which='major', linestyle='--', linewidth=0.5)
        plt.tight_layout()
        filename = output_path / f"{plot_key}.png"
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close(fig)
    logger.success(f"Generated {len(plot_definitions)} plots for run '{run_name}'")

def analyze_single_run(run_path: Path, report_dir: Path, run_name: str):
    """Analyzes a single run, plots its results, and saves the processed data."""
    logger.info(f"Processing run: {run_name}")
    sim_data = load_simulation_data(run_path)
    if not sim_data: return
    analytical_data = get_analytical_solution(sim_data['params'], sim_data['x'], sim_data['t'])
    if not analytical_data: return
    run_report_dir = report_dir / run_name
    os.makedirs(run_report_dir, exist_ok=True)
    plot_simulation_vs_analytical(sim_data, analytical_data, run_report_dir, run_name)
    data_to_save = {'x': sim_data['x'], 'rho': sim_data['rho'], 'ux': sim_data['ux'], 'pp': sim_data['pp'], 'ee': sim_data['ee'], 't': sim_data['t']}
    output_npz_path = run_report_dir / "processed_data.npz"
    np.savez_compressed(output_npz_path, **data_to_save)

def _generate_analytical_solutions_for_comparison(hpc_run_base_dir: Path, report_dir: Path, all_runs: dict):
    """Pre-calculates and saves the analytical solution for each parameter set."""
    logger.info("Pre-calculating analytical solutions for comparison plots...")
    comparison_dir = report_dir / "_comparisons"
    
    for param_str, runs in all_runs['by_params'].items():
        # Pick the first run in the group as a representative
        representative_run_name = list(runs.keys())[0]
        
        # Load its parameters and grid from the HPC data, and time from local processed data
        run_path = hpc_run_base_dir / representative_run_name
        processed_data_path = report_dir / representative_run_name / "processed_data.npz"

        if not (run_path.is_dir() and processed_data_path.exists()):
            logger.warning(f"Cannot generate analytical solution for '{param_str}': missing data.")
            continue
            
        params = read.param(datadir=str(run_path / "data"), quiet=True)
        grid = read.grid(datadir=str(run_path / "data"), quiet=True, trim=True)
        final_time = np.load(processed_data_path)['t']

        analytical_solution = get_analytical_solution(params, grid.x, final_time)
        if analytical_solution:
            analytical_file_path = comparison_dir / f"analytical_{param_str}.npz"
            np.savez_compressed(analytical_file_path, **analytical_solution)
            logger.success(f"Saved analytical solution for '{param_str}'")

def _generate_cross_branch_plots(report_dir: Path, all_runs: dict, output_dir: Path):
    """Generates plots comparing branches against a single analytical baseline."""
    logger.info("Generating cross-branch comparison plots...")
    plot_definitions = {'density': 'rho', 'velocity': 'ux', 'pressure': 'pp', 'energy': 'ee'}
    branch_colors = {'massfix': '#1f77b4', 'nomassfix': '#ff7f0e'}

    for param_str, runs in all_runs['by_params'].items():
        analytical_path = output_dir / f"analytical_{param_str}.npz"
        if not analytical_path.exists(): continue
        analytical_data = np.load(analytical_path)

        fig, axes = plt.subplots(2, 2, figsize=(18, 14), sharex=True)
        axes = axes.flatten()
        fig.suptitle(f"Branch Comparison for Parameters: {param_str}", fontsize=20, y=0.97)

        for run_name, branch_name in runs.items():
            data = np.load(report_dir / run_name / "processed_data.npz")
            color = branch_colors.get(branch_name, 'gray')
            for ax, key in zip(axes, plot_definitions.values()):
                ax.plot(data['x'], data[key], label=branch_name, color=color, alpha=0.9, linewidth=2.5)

        for ax, key in zip(axes, plot_definitions.values()):
            ax.plot(analytical_data['x'], analytical_data[key], 'k--', label='Analytical', linewidth=2.5)

        for ax, title in zip(axes, plot_definitions.keys()):
            ax.set_title(title.capitalize(), fontsize=14)
            ax.set_xlabel('Position (x)'); ax.set_ylabel(title)
            ax.grid(True, linestyle='--', alpha=0.6); ax.legend()
        
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        plt.savefig(output_dir / f"compare_branches_{param_str}.png", dpi=150)
        plt.close(fig)
    logger.success("Finished cross-branch plots.")

def _generate_intra_branch_plots(report_dir: Path, all_runs: dict, output_dir: Path):
    """Generates plots comparing parameter sweeps, each with its own analytical solution."""
    logger.info("Generating intra-branch (parameter sweep) comparison plots...")
    plot_definitions = {'density': 'rho', 'velocity': 'ux', 'pressure': 'pp', 'energy': 'ee'}

    for branch_name, runs in all_runs['by_branch'].items():
        fig, axes = plt.subplots(2, 2, figsize=(18, 14), sharex=True)
        axes = axes.flatten()
        fig.suptitle(f"Parameter Sweep Comparison within Branch: '{branch_name}'", fontsize=20, y=0.97)

        colormap = plt.cm.viridis
        colors = colormap(np.linspace(0, 0.9, len(runs)))

        for i, (run_name, param_str) in enumerate(runs.items()):
            sim_data = np.load(report_dir / run_name / "processed_data.npz")
            analytical_path = output_dir / f"analytical_{param_str}.npz"
            if not analytical_path.exists(): continue
            analytical_data = np.load(analytical_path)
            
            for ax, key in zip(axes, plot_definitions.values()):
                # Plot simulation as solid line, analytical as dashed line of the same color
                ax.plot(sim_data['x'], sim_data[key], label=f"Sim: {param_str}", color=colors[i], linestyle='-', alpha=0.85)
                ax.plot(analytical_data['x'], analytical_data[key], label=f"Anlyt: {param_str}", color=colors[i], linestyle='--', alpha=0.85)

        for ax, title in zip(axes, plot_definitions.keys()):
            ax.set_title(title.capitalize(), fontsize=14)
            ax.set_xlabel('Position (x)'); ax.set_ylabel(title)
            ax.legend(fontsize='small', loc='best'); ax.grid(True, linestyle='--', alpha=0.6)

        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        plt.savefig(output_dir / f"compare_params_{branch_name}.png", dpi=150)
        plt.close(fig)
    logger.success(f"Finished intra-branch plots for '{branch_name}'.")

def analyze_suite(experiment_name: str):
    """Main function to analyze an experiment suite and generate comparison plots."""
    logger.info(f"--- STARTING ANALYSIS & COMPARISON for experiment suite: '{experiment_name}' ---")
    
    plan_file = DIRS.config / experiment_name / DIRS.plan_subdir / FILES.plan
    if not plan_file.exists(): logger.error(f"Plan file not found: {plan_file}."); return
    with open(plan_file, 'r') as f: plan = yaml.safe_load(f)
    
    hpc_run_base_dir = Path(plan['hpc']['run_base_dir'])
    manifest_file = DIRS.runs / experiment_name / FILES.manifest
    report_dir = DIRS.root / "reports" / experiment_name
    os.makedirs(report_dir, exist_ok=True)

    if not manifest_file.exists(): logger.error(f"Manifest file not found: {manifest_file}."); return
    with open(manifest_file, 'r') as f: run_names = [line.strip() for line in f if line.strip()]

    # Step 1: Analyze each run individually and save its processed data
    for run_name in run_names:
        analyze_single_run(hpc_run_base_dir / run_name, report_dir, run_name)

    # Step 2: Group runs for comparison
    prefix = plan['output_prefix']
    branches = [b['name'] for b in plan.get('branches', [])]
    grouped_by_branch = {b: {} for b in branches}
    grouped_by_params = {}
    for run_name in run_names:
        for branch_name in branches:
            if run_name.startswith(f"{prefix}_{branch_name}_"):
                param_str = run_name.replace(f"{prefix}_{branch_name}_", "")
                grouped_by_branch[branch_name][run_name] = param_str
                if param_str not in grouped_by_params: grouped_by_params[param_str] = {}
                grouped_by_params[param_str][run_name] = branch_name
                break
    all_runs_grouped = {'by_branch': grouped_by_branch, 'by_params': grouped_by_params}
    
    # Step 3: Pre-calculate and save all necessary analytical solutions
    comparison_dir = report_dir / "_comparisons"
    os.makedirs(comparison_dir, exist_ok=True)
    _generate_analytical_solutions_for_comparison(hpc_run_base_dir, report_dir, all_runs_grouped)
    
    # Step 4: Generate the comparison plots
    logger.info("--- STARTING COMPARISON PLOT GENERATION ---")
    _generate_cross_branch_plots(report_dir, all_runs_grouped, comparison_dir)
    _generate_intra_branch_plots(report_dir, all_runs_grouped, comparison_dir)
    
    logger.success(f"Analysis and comparison for '{experiment_name}' finished.")
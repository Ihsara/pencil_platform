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
    """Calculates the analytical Sod shock tube solution for a given set of parameters."""
    try:
        if not hasattr(params, 'rho0'):
            setattr(params, 'rho0', 1.0)
        if not hasattr(params, 'cs0'):
            setattr(params, 'cs0', 1.0)
        
        solution = sod(x, [t], par=params, lplot=False, magic=['ee'])

        return {
            'rho': np.squeeze(solution.rho),
            'ux': np.squeeze(solution.ux),
            'pp': np.squeeze(solution.pp),
            'ee': np.squeeze(solution.ee),
            'x': x,
        }
    except Exception as e:
        logger.error(f"Failed to calculate analytical solution for t={t}: {e}")
        logger.exception("Traceback for analytical solution failure:")
        return None

def load_simulation_data(run_path: Path) -> Optional[Dict]:
    """Loads the final snapshot data from a single simulation run directory."""
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

        # Load parameters first to perform calculations
        params = read.param(datadir=str(data_dir), quiet=True)
        
        # Load the raw variable data without using fragile 'magic' calculations
        var = read.var(var_files[-1].name, datadir=str(data_dir), quiet=True, trimall=True)
        grid = read.grid(datadir=str(data_dir), quiet=True, trim=True)
        
        # --- Manually Calculate Pressure (pp) ---
        # This is the robust way to avoid the library bug.
        density = np.exp(var.lnrho) if hasattr(var, 'lnrho') else var.rho
        
        # Set default reference values if they are not in the param file
        rho0 = getattr(params, 'rho0', 1.0)
        cs0 = getattr(params, 'cs0', 1.0)
        
        # Calculate pressure from entropy and density
        cp = params.cp
        gamma = params.gamma
        cv = cp / gamma
        lnrho0 = np.log(rho0)
        lnTT0 = np.log(cs0**2 / (cp * (gamma - 1.0)))
        
        pressure = (cp - cv) * np.exp(
            lnTT0 + (gamma / cp * var.ss) + (gamma * np.log(density)) - ((gamma - 1.0) * lnrho0)
        )

        # Calculate internal energy from the ideal gas law (p = (gamma-1)*rho*e)
        internal_energy = np.zeros_like(density)
        if hasattr(params, 'gamma') and params.gamma > 1.0:
            non_zero_density_mask = density > 1e-18
            internal_energy[non_zero_density_mask] = pressure[non_zero_density_mask] / \
                (density[non_zero_density_mask] * (params.gamma - 1.0))

        return {
            "x": np.squeeze(grid.x),
            "rho": np.squeeze(density),
            "ux": np.squeeze(var.ux),
            "pp": np.squeeze(pressure),
            "ee": np.squeeze(internal_energy),
            "t": var.t,
            "params": params
        }
    except Exception as e:
        logger.error(f"Failed to load data from {run_path}: {e}")
        logger.exception("Traceback for data loading failure:")
        return None

def plot_simulation_vs_analytical(sim_data: dict, analytical_data: dict, output_path: Path, run_name: str):
    """Generates and saves the four core comparison plots for a single simulation."""
    plot_definitions = {
        'density': ('rho', r'Density ($\rho$)'),
        'velocity': ('ux', r'Velocity ($u_x$)'),
        'pressure': ('pp', r'Pressure ($p$)'),
        'energy': ('ee', r'Internal Energy ($e$)')
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

def copy_script_to_report(report_dir: Path):
    """Copies this analysis script into the report directory for provenance."""
    try:
        shutil.copy(Path(__file__), report_dir)
    except Exception as e:
        logger.warning(f"Could not copy analysis script to report directory: {e}")

def analyze_single_run(run_path: Path, report_dir: Path, run_name: str):
    """
    Analyzes a single simulation run: loads data, gets analytical solution, and plots.
    """
    logger.info(f"Processing run: {run_name}")
    
    sim_data = load_simulation_data(run_path)
    if not sim_data:
        return

    analytical_data = get_analytical_solution(sim_data['params'], sim_data['x'], sim_data['t'])
    if not analytical_data:
        return
    
    run_report_dir = report_dir / run_name
    os.makedirs(run_report_dir, exist_ok=True)
    
    plot_simulation_vs_analytical(sim_data, analytical_data, run_report_dir, run_name)

def analyze_suite(experiment_name: str):
    """
    Main function to find, analyze, and plot an entire experiment suite.
    """
    logger.info(f"--- STARTING ANALYSIS for experiment suite: '{experiment_name}' ---")
    
    plan_file = DIRS.config / experiment_name / DIRS.plan_subdir / FILES.plan
    if not plan_file.exists():
        logger.error(f"Plan file not found: {plan_file}. Cannot determine where simulation data is located.")
        return
    with open(plan_file, 'r') as f:
        plan = yaml.safe_load(f)
    
    hpc_run_base_dir = Path(plan['hpc']['run_base_dir'])
    
    local_suite_dir = DIRS.runs / experiment_name
    manifest_file = local_suite_dir / FILES.manifest
    report_dir = DIRS.root / "reports" / experiment_name
    os.makedirs(report_dir, exist_ok=True)

    if not manifest_file.exists():
        logger.error(f"Manifest file not found: {manifest_file}. Cannot proceed with analysis.")
        return

    with open(manifest_file, 'r') as f:
        run_names = [line.strip() for line in f if line.strip()]

    logger.info(f"Found {len(run_names)} runs to analyze from manifest.")

    for run_name in run_names:
        run_path = hpc_run_base_dir / run_name
        analyze_single_run(run_path, report_dir, run_name)

    copy_script_to_report(report_dir)
    logger.info(f"Copied analysis script to {report_dir} for provenance.")
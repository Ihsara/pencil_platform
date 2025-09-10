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
# This assumes the pencil-code repository is cloned alongside this project directory.
# Adjust the path if it is located elsewhere.
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
        solution = sod(x, [t], par=params, lplot=False)
        print(solution)
        return {
            'rho': np.squeeze(solution.rho),
            'ux': np.squeeze(solution.ux),
            'pp': np.squeeze(solution.pp)
        }
    except Exception as e:
        logger.error(f"Failed to calculate analytical solution for t={t}: {e}")
        return None

def load_simulation_data(run_path: Path) -> Optional[Dict]:
    """Loads the final snapshot data from a single simulation run directory."""
    try:
        if not run_path.is_dir():
            logger.warning(f"Run directory not found: {run_path}")
            return None

        data_dir = run_path / "data"
        # Check for proc0 first, which is standard for single-core runs
        proc_dir = data_dir / "proc0" if (data_dir / "proc0").is_dir() else data_dir
        
        # Find all VAR files and sort them numerically to get the last one
        var_files = sorted(proc_dir.glob("VAR*"), key=lambda p: int(re.search(r'(\d+)$', p.name).group(1)))
        if not var_files:
            logger.warning(f"No VAR files found in {proc_dir}")
            return None

        # Read the final snapshot
        var = read.var(var_files[-1].name, datadir=str(data_dir), quiet=True, magic=['pp'], trimall=True)
        grid = read.grid(datadir=str(data_dir), quiet=True, trim=True)
        params = read.param(datadir=str(data_dir), quiet=True)
        
        density = np.exp(var.lnrho) if hasattr(var, 'lnrho') else var.rho
        
        return {
            "x": np.squeeze(grid.x),
            "rho": np.squeeze(density),
            "ux": np.squeeze(var.ux),
            "pp": np.squeeze(var.pp),
            "t": var.t,
            "params": params
        }
    except Exception as e:
        logger.error(f"Failed to load data from {run_path}: {e}")
        return None

def plot_simulation_vs_analytical(sim_data: dict, analytical_data: dict, output_path: Path, run_name: str):
    """Generates and saves the three core comparison plots for a single simulation."""
    plot_definitions = {
        'density': ('rho', r'Density ($\rho$)'),
        'velocity': ('ux', r'Velocity ($u_x$)'),
        'pressure': ('pp', r'Pressure ($p$)')
    }

    for plot_key, (data_key, ylabel) in plot_definitions.items():
        plt.style.use('seaborn-v0_8-whitegrid')
        fig, ax = plt.subplots(figsize=(10, 7))

        # Plot Analytical Solution (dashed line)
        ax.plot(analytical_data['x'], analytical_data[data_key], 'k--', linewidth=2.5, label='Analytical Solution')
        
        # Plot Simulation Data (solid line with markers)
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
    
    logger.success(f"Generated 3 plots for run '{run_name}'")

def copy_script_to_report(report_dir: Path):
    """Copies this analysis script into the report directory for provenance."""
    this_script_path = Path(__file__)
    try:
        shutil.copy(this_script_path, report_dir)
    except Exception as e:
        logger.warning(f"Could not copy analysis script to report directory: {e}")

def analyze_suite(experiment_name: str):
    """
    Main function to find, analyze, and plot an entire experiment suite.
    It reads the plan file to locate the simulation data on the HPC.
    """
    logger.info(f"--- ANALYSIS MODE ---")
    logger.info(f"Starting analysis for experiment suite: '{experiment_name}'")
    
    # Load the experiment plan to get the correct HPC paths
    plan_file = DIRS.config / experiment_name / DIRS.plan_subdir / FILES.plan
    if not plan_file.exists():
        logger.error(f"Plan file not found: {plan_file}. Cannot determine where simulation data is located.")
        return
    with open(plan_file, 'r') as f:
        plan = yaml.safe_load(f)
    
    # Use the correct base directory for the RUNS, as defined in the plan
    hpc_run_base_dir = Path(plan['hpc']['run_base_dir'])
    
    # Define local paths for manifest and reports
    local_suite_dir = DIRS.runs / experiment_name
    manifest_file = local_suite_dir / FILES.manifest
    report_dir = DIRS.root / "reports" / experiment_name
    os.makedirs(report_dir, exist_ok=True)

    if not manifest_file.exists():
        logger.error(f"Manifest file not found: {manifest_file}. Cannot proceed with analysis.")
        return

    with open(manifest_file, 'r') as f:
        run_names = [line.strip() for line in f if line.strip()]

    logger.info(f"Found {len(run_names)} runs to analyze in the manifest.")

    for run_name in run_names:
        # Construct the absolute path to the ACTUAL simulation data on the scratch space
        run_path = hpc_run_base_dir / run_name
        
        logger.info(f"Analyzing run: {run_name}")
        sim_data = load_simulation_data(run_path)
        if not sim_data:
            continue
            
        analytical_data = get_analytical_solution(sim_data['params'], sim_data['x'], sim_data['t'])
        if not analytical_data:
            continue
        
        # Create a specific subdirectory for this run's reports
        run_report_dir = report_dir / run_name
        os.makedirs(run_report_dir, exist_ok=True)
        
        # Copy this script for provenance, as requested
        copy_script_to_report(run_report_dir)
        
        # Generate and save the plots
        plot_simulation_vs_analytical(sim_data, analytical_data, run_report_dir, run_name)
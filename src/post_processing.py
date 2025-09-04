# src/post_processing.py

import os, sys, re, glob
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from loguru import logger
from .constants import DIRS

# Add the project root to the path to allow finding the 'pencil' module
if str(DIRS.root) not in sys.path:
    sys.path.insert(0, str(DIRS.root))

try:
    import pencil.read as read
    from pencil.calc.shocktube import sod
except ImportError as e:
    logger.error(f"FATAL: Failed to import Pencil Code modules: {e}")
    sys.exit(1)

def get_analytical_solution(params, x, t):
    """Calculates the analytical Sod shock tube solution."""
    try:
        solution = sod(x, [t], par=params, lplot=False)
        return {
            'rho': np.squeeze(solution.rho),
            'ux': np.squeeze(solution.ux),
            'pp': np.squeeze(solution.pp)
        }
    except Exception as e:
        logger.error(f"Failed to calculate analytical solution for t={t}: {e}")
        return None

def load_simulation_data(run_path: Path):
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

        var = read.var(var_files[-1].name, datadir=str(data_dir), quiet=True, magic=['pp'], trimall=True)
        grid = read.grid(datadir=str(data_dir), quiet=True, trim=True)
        params = read.param(datadir=str(data_dir), quiet=True)
        
        density = np.exp(var.lnrho) if hasattr(var, 'lnrho') else var.rho
        
        return {
            "x": np.squeeze(grid.x), "rho": np.squeeze(density),
            "ux": np.squeeze(var.ux), "pp": np.squeeze(var.pp),
            "t": var.t, "params": params
        }
    except Exception as e:
        logger.error(f"Failed to load data from {run_path}: {e}")
        return None

def plot_simulation_vs_analytical(sim_data, analytical_data, output_path: Path, run_name: str):
    """Generates and saves the three core plots for a single simulation."""
    plot_definitions = {
        'density': ('rho', r'Density ($\rho$)'),
        'velocity': ('ux', r'Velocity ($u_x$)'),
        'pressure': ('pp', r'Pressure ($p$)')
    }

    for plot_key, (data_key, ylabel) in plot_definitions.items():
        plt.style.use('seaborn-v0_8-whitegrid')
        fig, ax = plt.subplots(figsize=(10, 7))

        ax.plot(analytical_data['x'], analytical_data[data_key], 'k--', linewidth=2.5, label='Analytical Solution')
        ax.plot(sim_data['x'], sim_data[data_key], 'o-', color='#1f77b4', markersize=4, label=f'Simulation (t={sim_data["t"]:.2e})')
        
        ax.set_title(f"{ylabel} Profile for\n{run_name}", fontsize=16)
        ax.set_xlabel('Position (x) [code units]', fontsize=12)
        ax.set_ylabel(f'{ylabel} [code units]', fontsize=12)
        ax.legend()
        ax.grid(True, which='major', linestyle='--', linewidth=0.5)
        plt.tight_layout()
        
        filename = output_path / f"{plot_key}.png"
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close(fig)
    logger.success(f"Generated 3 plots for {run_name}")

def analyze_suite(experiment_name: str):
    """Main function to find, analyze, and plot an entire experiment suite."""
    logger.info(f"Starting analysis for experiment suite: '{experiment_name}'")
    
    exp_run_dir = DIRS.runs / experiment_name
    manifest_file = exp_run_dir / "run_manifest.txt"
    report_dir = DIRS.root / "reports" / experiment_name
    os.makedirs(report_dir, exist_ok=True)

    if not manifest_file.exists():
        logger.error(f"Manifest file not found: {manifest_file}. Cannot proceed with analysis.")
        return

    with open(manifest_file, 'r') as f:
        run_names = [line.strip() for line in f if line.strip()]

    logger.info(f"Found {len(run_names)} runs to analyze in the manifest.")

    for run_name in run_names:
        run_path = DIRS.runs / experiment_name / "generated_configs" / run_name
        
        sim_data = load_simulation_data(run_path)
        if not sim_data:
            continue
            
        analytical_data = get_analytical_solution(sim_data['params'], sim_data['x'], sim_data['t'])
        if not analytical_data:
            continue
        
        run_report_dir = report_dir / run_name
        os.makedirs(run_report_dir, exist_ok=True)
        
        plot_simulation_vs_analytical(sim_data, analytical_data, run_report_dir, run_name)
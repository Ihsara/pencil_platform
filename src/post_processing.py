# src/post_processing.py

import os
import sys
import yaml
from pathlib import Path
import jinja2
import numpy as np
from loguru import logger

from .constants import DIRS, FILES
from .analysis import compare_simulation_to_analytical, format_report_tables
from .visualization import plot_simulation_vs_analytical

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

def load_simulation_data(run_path: Path) -> dict | None:
    """Loads and processes the final snapshot data from a single simulation run."""
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
        
        params = read.param(datadir=str(data_dir), quiet=True)
        var = read.var(var_files[-1].name, datadir=str(data_dir), quiet=True, trimall=True)
        grid = read.grid(datadir=str(data_dir), quiet=True, trim=True)
        
        # --- CORRECTED PRESSURE AND ENERGY CALCULATION ---
        
        density = np.exp(var.lnrho) if hasattr(var, 'lnrho') else var.rho
        
        # Get necessary parameters from the param file
        cp, gamma = params.cp, params.gamma
        cv = cp / gamma
        
        # Check if entropy 'ss' is available, as temperature 'TT' is not.
        if not hasattr(var, 'ss'):
            logger.error(f"Variable 'ss' (entropy) not found in VAR file for {run_path}. Cannot calculate pressure.")
            return None

        # Reconstruct pressure from entropy using the Pencil Code's equation of state.
        # This requires reference values, which we get from the params object.
        rho0 = getattr(params, 'rho0', 1.0)
        cs0 = getattr(params, 'cs0', 1.0)
        lnrho0 = np.log(rho0)
        lnTT0 = np.log(cs0**2 / (cp * (gamma - 1.0)))
        
        # This formula reconstructs temperature from entropy and density, then pressure is derived from it.
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

def process_and_analyze_run(run_path: Path, report_dir: Path, run_name: str):
    """Processes a single run: loads data, runs analysis, saves artifacts."""
    logger.info(f"--- Processing run: {run_name} ---")
    
    sim_data = load_simulation_data(run_path)
    if not sim_data: return

    analytical_data = get_analytical_solution(sim_data['params'], sim_data['x'], sim_data['t'])
    if not analytical_data: return

    run_report_dir = report_dir / run_name
    run_report_dir.mkdir(parents=True, exist_ok=True)

    np.savez_compressed(run_report_dir / "simulation_data.npz", **{k: v for k, v in sim_data.items() if k != 'params'})
    np.savez_compressed(run_report_dir / "analytical_data.npz", **analytical_data)

    metrics = compare_simulation_to_analytical(sim_data, analytical_data)
    log_summary, markdown_table = format_report_tables(metrics)
    
    logger.info(log_summary)
    with open(run_report_dir / "analysis_summary.md", "w") as f:
        f.write(f"# Analysis Report for {run_name}\n\n")
        f.write(markdown_table)
    
    plot_simulation_vs_analytical(sim_data, analytical_data, run_report_dir, run_name)

def generate_quarto_report(experiment_name: str, report_dir: Path, run_names: list):
    """Renders the Quarto report template with the list of processed runs."""
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

def analyze_suite(experiment_name: str):
    """Main function to analyze an experiment suite, generate reports, and create a Quarto summary."""
    logger.info(f"--- STARTING ANALYSIS for experiment: '{experiment_name}' ---")
    
    plan_file = DIRS.config / experiment_name / DIRS.plan_subdir / FILES.plan
    with open(plan_file, 'r') as f: plan = yaml.safe_load(f)
    
    hpc_run_base_dir = Path(plan['hpc']['run_base_dir'])
    manifest_file = DIRS.runs / experiment_name / FILES.manifest
    report_dir = DIRS.root / "reports" / experiment_name
    report_dir.mkdir(parents=True, exist_ok=True)

    with open(manifest_file, 'r') as f: run_names = [line.strip() for line in f if line.strip()]

    for run_name in run_names:
        process_and_analyze_run(hpc_run_base_dir / run_name, report_dir, run_name)
    
    generate_quarto_report(experiment_name, report_dir, run_names)
    
    logger.success(f"Analysis for '{experiment_name}' finished successfully.")
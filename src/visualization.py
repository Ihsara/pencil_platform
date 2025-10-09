# src/visualization.py

import matplotlib.pyplot as plt
from pathlib import Path
from loguru import logger
import numpy as np

def plot_simulation_vs_analytical(sim_data: dict, analytical_data: dict, output_path: Path, run_name: str):
    """
    Generates and saves the four core comparison plots for a single simulation run.
    This function is designed to be called from a reporting tool like Quarto or a Jupyter notebook.

    Args:
        sim_data (dict): A dictionary containing the processed simulation data.
        analytical_data (dict): A dictionary containing the analytical solution data.
        output_path (Path): The directory where the plot images will be saved.
        run_name (str): The name of the simulation run, used for plot titles.
    """
    output_path.mkdir(parents=True, exist_ok=True)
    
    plot_definitions = {
        'density': ('rho', r'$\rho$ [g cm$^{-3}$]', sim_data['params'].unit_density),
        'velocity': ('ux', r'$u_x$ [km s$^{-1}$] ', sim_data['params'].unit_velocity*1e-5),
        'pressure': ('pp', r'$p$ [dyn cm$^{-2}$]',   sim_data['params'].unit_energy_density),
        'energy': ('ee', r'$e$ [km$^2$ s$^{-2}$] ', sim_data['params'].unit_velocity**2), 
        
    }

    for plot_key, (data_key, ylabel, unit) in plot_definitions.items():
        plt.style.use('seaborn-v0_8-whitegrid')
        fig, ax = plt.subplots(figsize=(10, 7))
        
        # Plot analytical solution as a dashed black line for reference
        ax.plot(analytical_data['x'], analytical_data[data_key]*unit, 'k--', linewidth=2.5, label='Analytical Solution')
        
        # Plot simulation data with markers
        ax.plot(sim_data['x'], sim_data[data_key]*unit, 'o-', color='#1f77b4', markersize=4, label=f'Simulation (t={sim_data["t"]:.2e})')
        
        ax.set_title(f"{ylabel} Profile for\n{run_name}", fontsize=16, pad=15)
        ax.set_xlabel('Position (x) [kpc]', fontsize=12)
        ax.set_ylabel(f'{ylabel}', fontsize=12)
        ax.legend(fontsize=11)
        ax.grid(True, which='major', linestyle='--', linewidth=0.5)
        
        plt.tight_layout()
        filename = output_path / f"{plot_key}.png"
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close(fig)
        
    logger.success(f"Generated {len(plot_definitions)} plots for run '{run_name}' in '{output_path}'")
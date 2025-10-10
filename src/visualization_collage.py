# src/visualization_collage.py

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
from pathlib import Path
from loguru import logger
from typing import Dict, List, Optional
import random

def create_var_evolution_collage(sim_data_list: List[dict], analytical_data_list: List[dict], 
                                 output_path: Path, run_name: str, 
                                 variables: List[str] = ['rho', 'ux', 'pp', 'ee']):
    """
    Creates a collage showing evolution of variables across all VAR files.
    
    Args:
        sim_data_list: List of simulation data from all VAR files
        analytical_data_list: List of analytical solutions for all VAR files
        output_path: Directory to save the collage
        run_name: Name of the run for title
        variables: List of variables to plot
    """
    output_path.mkdir(parents=True, exist_ok=True)
    
    var_labels = {
        'rho': r'$\rho$ [g cm$^{-3}$]',
        'ux': r'$u_x$ [km s$^{-1}$]',
        'pp': r'$p$ [dyn cm$^{-2}$]',
        'ee': r'$e$ [km$^2$ s$^{-2}$]'
    }
    
    var_scales = {
        'rho': 'log',
        'ux': 'linear',
        'pp': 'log',
        'ee': 'log'
    }
    
    # Create figure with subplots for each variable
    fig, axes = plt.subplots(2, 2, figsize=(18, 15))
    n_vars = len(sim_data_list)
    fig.suptitle(f'Variable Evolution Across {n_vars} VAR Files\n{run_name}', 
                 fontsize=16, fontweight='bold')
    axes = axes.flatten()
    
    # Color map for different timesteps
    colors = plt.cm.viridis(np.linspace(0, 1, n_vars))
    
    for idx, var in enumerate(variables):
        ax = axes[idx]
        
        # Get unit from first sim_data that has params
        unit = 1.0
        for sim_data in sim_data_list:
            if 'params' in sim_data:
                if var == 'rho':
                    unit = sim_data['params'].unit_density
                elif var == 'ux':
                    unit = sim_data['params'].unit_velocity * 1e-5
                elif var == 'pp':
                    unit = sim_data['params'].unit_energy_density
                elif var == 'ee':
                    unit = sim_data['params'].unit_velocity ** 2
                break
        
        # Plot analytical solution for first and last timestep ONLY
        if analytical_data_list:
            ax.plot(analytical_data_list[0]['x'], analytical_data_list[0][var]*unit, 
                   'k--', linewidth=2.5, alpha=0.9, label='Analytical (t₀)', zorder=10)
            if len(analytical_data_list) > 1:
                ax.plot(analytical_data_list[-1]['x'], analytical_data_list[-1][var]*unit, 
                       'k:', linewidth=2.5, alpha=0.9, label=f'Analytical (t_final)', zorder=10)
        
        # Plot simulation data evolution with clear labels showing count
        label_every = max(1, n_vars // 8)  # Show ~8 labels max
        for var_idx, (sim_data, color) in enumerate(zip(sim_data_list, colors)):
            if var in sim_data:
                alpha = 0.3 + 0.7 * (var_idx / max(1, n_vars-1))  # Increase alpha with time
                var_file_name = sim_data.get('var_file', f'VAR{var_idx}')
                
                # Create label for selected timesteps
                if var_idx % label_every == 0 or var_idx == n_vars - 1:
                    label = f'{var_file_name} (t={sim_data["t"]:.2e})'
                else:
                    label = None
                    
                ax.plot(sim_data['x'], sim_data[var]*unit, 
                       color=color, linewidth=1.8, alpha=alpha, label=label)
        
        ax.set_xlabel('Position (x) [kpc]', fontsize=12)
        ax.set_ylabel(var_labels.get(var, var), fontsize=12)
        ax.set_yscale(var_scales.get(var, 'linear'))
        ax.set_title(f'{var.upper()} Evolution (Numerical: {n_vars} VAR files, Analytical: 2 times)', 
                    fontsize=12, pad=10)
        ax.legend(fontsize=7, loc='best', ncol=1, framealpha=0.9)
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    output_file = output_path / f"{run_name}_var_evolution_collage.png"
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    logger.info(f"Saved VAR evolution collage to {output_file}")


def create_branch_var_evolution_collage(branch_data: Dict[str, Dict], output_path: Path, 
                                        experiment_name: str, branch_name: str,
                                        var_to_plot: str = 'rho'):
    """
    Creates a collage comparing VAR evolution across all runs in a branch.
    
    Args:
        branch_data: Dictionary mapping run_name to {'sim_data_list', 'analytical_data_list'}
        output_path: Directory to save the collage
        experiment_name: Name of the experiment
        branch_name: Name of the branch
        var_to_plot: Variable to visualize
    """
    output_path.mkdir(parents=True, exist_ok=True)
    
    n_runs = len(branch_data)
    if n_runs == 0:
        logger.warning(f"No data available for branch {branch_name}")
        return
    
    # Create grid of subplots
    ncols = min(3, n_runs)
    nrows = (n_runs + ncols - 1) // ncols
    
    fig, axes = plt.subplots(nrows, ncols, figsize=(6*ncols, 5*nrows))
    fig.suptitle(f'{var_to_plot.upper()} Evolution - {experiment_name}/{branch_name}', 
                 fontsize=16, fontweight='bold')
    
    if n_runs == 1:
        axes = np.array([axes])
    axes = axes.flatten()
    
    var_labels = {
        'rho': r'$\rho$ [g cm$^{-3}$]',
        'ux': r'$u_x$ [km s$^{-1}$]',
        'pp': r'$p$ [dyn cm$^{-2}$]',
        'ee': r'$e$ [km$^2$ s$^{-2}$]'
    }
    
    var_scales = {'rho': 'log', 'ux': 'linear', 'pp': 'log', 'ee': 'log'}
    
    for ax_idx, (run_name, data) in enumerate(branch_data.items()):
        if ax_idx >= len(axes):
            break
        
        ax = axes[ax_idx]
        sim_data_list = data['sim_data_list']
        analytical_data_list = data['analytical_data_list']
        
        # Get unit
        unit = 1.0
        for sim_data in sim_data_list:
            if 'params' in sim_data:
                if var_to_plot == 'rho':
                    unit = sim_data['params'].unit_density
                elif var_to_plot == 'ux':
                    unit = sim_data['params'].unit_velocity * 1e-5
                elif var_to_plot == 'pp':
                    unit = sim_data['params'].unit_energy_density
                elif var_to_plot == 'ee':
                    unit = sim_data['params'].unit_velocity ** 2
                break
        
        # Color map
        n_vars = len(sim_data_list)
        colors = plt.cm.plasma(np.linspace(0, 1, n_vars))
        
        # Plot analytical
        if analytical_data_list:
            ax.plot(analytical_data_list[-1]['x'], analytical_data_list[-1][var_to_plot]*unit, 
                   'k--', linewidth=2, alpha=0.7, label='Analytical')
        
        # Plot simulation evolution
        for var_idx, (sim_data, color) in enumerate(zip(sim_data_list, colors)):
            if var_to_plot in sim_data:
                alpha = 0.3 + 0.7 * (var_idx / max(1, n_vars-1))
                ax.plot(sim_data['x'], sim_data[var_to_plot]*unit, 
                       color=color, linewidth=1.5, alpha=alpha)
        
        ax.set_xlabel('Position (x) [kpc]', fontsize=10)
        ax.set_ylabel(var_labels.get(var_to_plot, var_to_plot), fontsize=10)
        ax.set_yscale(var_scales.get(var_to_plot, 'linear'))
        ax.set_title(run_name, fontsize=11)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
    
    # Hide empty subplots
    for ax_idx in range(len(branch_data), len(axes)):
        axes[ax_idx].axis('off')
    
    plt.tight_layout()
    output_file = output_path / f"{experiment_name}_{branch_name}_{var_to_plot}_evolution.png"
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    logger.info(f"Saved branch VAR evolution collage to {output_file}")


def create_best_performers_var_evolution_collage(best_performers_data: Dict, output_path: Path,
                                                 var_to_plot: str = 'rho'):
    """
    Creates a collage comparing VAR evolution for best performers from each branch.
    
    Args:
        best_performers_data: Dictionary mapping 'exp/branch' to data
        output_path: Directory to save the collage
        var_to_plot: Variable to visualize
    """
    output_path.mkdir(parents=True, exist_ok=True)
    
    n_performers = len(best_performers_data)
    if n_performers == 0:
        logger.warning("No best performers data available")
        return
    
    # Create grid
    ncols = min(3, n_performers)
    nrows = (n_performers + ncols - 1) // ncols
    
    fig, axes = plt.subplots(nrows, ncols, figsize=(6*ncols, 5*nrows))
    fig.suptitle(f'{var_to_plot.upper()} Evolution - Best Performers from Each Branch', 
                 fontsize=16, fontweight='bold')
    
    if n_performers == 1:
        axes = np.array([axes])
    axes = axes.flatten()
    
    var_labels = {
        'rho': r'$\rho$ [g cm$^{-3}$]',
        'ux': r'$u_x$ [km s$^{-1}$]',
        'pp': r'$p$ [dyn cm$^{-2}$]',
        'ee': r'$e$ [km$^2$ s$^{-2}$]'
    }
    
    var_scales = {'rho': 'log', 'ux': 'linear', 'pp': 'log', 'ee': 'log'}
    
    for ax_idx, (branch_label, data) in enumerate(best_performers_data.items()):
        if ax_idx >= len(axes):
            break
        
        ax = axes[ax_idx]
        sim_data_list = data['sim_data_list']
        analytical_data_list = data['analytical_data_list']
        run_name = data['run_name']
        
        # Get unit
        unit = 1.0
        for sim_data in sim_data_list:
            if 'params' in sim_data:
                if var_to_plot == 'rho':
                    unit = sim_data['params'].unit_density
                elif var_to_plot == 'ux':
                    unit = sim_data['params'].unit_velocity * 1e-5
                elif var_to_plot == 'pp':
                    unit = sim_data['params'].unit_energy_density
                elif var_to_plot == 'ee':
                    unit = sim_data['params'].unit_velocity ** 2
                break
        
        # Color map
        n_vars = len(sim_data_list)
        colors = plt.cm.viridis(np.linspace(0, 1, n_vars))
        
        # Plot analytical
        if analytical_data_list:
            ax.plot(analytical_data_list[-1]['x'], analytical_data_list[-1][var_to_plot]*unit, 
                   'k--', linewidth=2.5, alpha=0.8, label='Analytical')
        
        # Plot simulation evolution
        for var_idx, (sim_data, color) in enumerate(zip(sim_data_list, colors)):
            if var_to_plot in sim_data:
                alpha = 0.3 + 0.7 * (var_idx / max(1, n_vars-1))
                ax.plot(sim_data['x'], sim_data[var_to_plot]*unit, 
                       color=color, linewidth=2, alpha=alpha)
        
        ax.set_xlabel('Position (x) [kpc]', fontsize=10)
        ax.set_ylabel(var_labels.get(var_to_plot, var_to_plot), fontsize=10)
        ax.set_yscale(var_scales.get(var_to_plot, 'linear'))
        ax.set_title(f'{branch_label}\n{run_name}', fontsize=11)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
    
    # Hide empty subplots
    for ax_idx in range(len(best_performers_data), len(axes)):
        axes[ax_idx].axis('off')
    
    plt.tight_layout()
    output_file = output_path / f"best_performers_{var_to_plot}_evolution.png"
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    logger.info(f"Saved best performers VAR evolution collage to {output_file}")


def select_var_file_for_viz(var_files: List[Path], selection: Optional[str] = None) -> Path:
    """
    Select a VAR file for visualization.
    
    Args:
        var_files: List of available VAR files
        selection: 'random', 'middle', 'last', or specific VAR number (e.g., 'VAR5')
        
    Returns:
        Selected VAR file path
    """
    if not var_files:
        raise ValueError("No VAR files available")
    
    if selection is None or selection == 'middle':
        # Default: middle of the pack
        mid_idx = len(var_files) // 2
        selected = var_files[mid_idx]
        logger.info(f"Selected middle VAR file: {selected.name} (index {mid_idx}/{len(var_files)})")
        
    elif selection == 'random':
        selected = random.choice(var_files)
        logger.info(f"Randomly selected VAR file: {selected.name}")
        
    elif selection == 'last':
        selected = var_files[-1]
        logger.info(f"Selected last VAR file: {selected.name}")
        
    elif selection == 'first':
        selected = var_files[0]
        logger.info(f"Selected first VAR file: {selected.name}")
        
    else:
        # Try to find specific VAR file
        for var_file in var_files:
            if selection.upper() in var_file.name.upper():
                selected = var_file
                logger.info(f"Selected specified VAR file: {selected.name}")
                break
        else:
            logger.warning(f"Could not find VAR file matching '{selection}', using middle")
            mid_idx = len(var_files) // 2
            selected = var_files[mid_idx]
    
    return selected

# src/advanced_analysis.py
"""
Advanced analysis module implementing the three-task directive for 1D hydrodynamic simulation analysis:
1. Error Norm Analysis (L1, L2, L∞)
2. Hovmöller Diagrams (space-time evolution)
3. Integrated Quantities Conservation Analysis
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from loguru import logger
from typing import Dict, List, Tuple
import matplotlib.colors as mcolors


def calculate_error_norms(numerical_data: np.ndarray, analytical_data: np.ndarray,
                         variables: List[str] = ['rho', 'ux', 'pp', 'ee']) -> Dict:
    """
    Task 1: Calculate L1, L2, and L∞ error norms for each variable at every timestep.
    
    Args:
        numerical_data: 3D array of shape (num_timesteps, num_variables, num_spatial_points)
        analytical_data: 3D array with same structure as numerical_data
        variables: List of variable names ['rho', 'ux', 'pp', 'ee']
    
    Returns:
        Dictionary containing error norms for each variable across all timesteps:
        {
            'rho': {'L1': [...], 'L2': [...], 'Linf': [...]},
            'ux': {...},
            ...
        }
    """
    logger.info("Calculating error norms (L1, L2, L∞) across all timesteps...")
    
    num_timesteps, num_variables, num_spatial_points = numerical_data.shape
    
    # Initialize error storage
    error_norms = {var: {'L1': [], 'L2': [], 'Linf': []} for var in variables}
    
    # Iterate through each timestep
    for t in range(num_timesteps):
        # Iterate through each variable
        for v, var in enumerate(variables):
            # Extract 1D spatial arrays
            num_solution = numerical_data[t, v, :]
            ana_solution = analytical_data[t, v, :]
            
            # Calculate point-wise absolute error
            abs_error_vector = np.abs(num_solution - ana_solution)
            
            # Calculate L1 norm (Mean Absolute Error)
            l1_norm = np.mean(abs_error_vector)
            
            # Calculate L2 norm (Root Mean Square Error)
            l2_norm = np.sqrt(np.mean(abs_error_vector**2))
            
            # Calculate L∞ norm (Maximum Absolute Error)
            linf_norm = np.max(abs_error_vector)
            
            # Store results
            error_norms[var]['L1'].append(l1_norm)
            error_norms[var]['L2'].append(l2_norm)
            error_norms[var]['Linf'].append(linf_norm)
    
    logger.success(f"Calculated error norms for {num_timesteps} timesteps and {num_variables} variables")
    return error_norms


def plot_error_norms(error_norms: Dict, time_coords: np.ndarray, 
                    output_path: Path, run_name: str):
    """
    Task 1 Output: Plot error norm evolution for each variable.
    
    Creates a 4-panel figure showing L1, L2, and L∞ norms vs time.
    """
    output_path.mkdir(parents=True, exist_ok=True)
    
    fig, axes = plt.subplots(2, 2, figsize=(17, 13))
    fig.suptitle(f'Error Norm Analysis (L1, L2, L∞)\n{run_name}', 
                 fontsize=16, fontweight='bold')
    axes = axes.flatten()
    
    variables = ['rho', 'ux', 'pp', 'ee']
    var_labels = [r'Density ($\rho$)', r'Velocity ($u_x$)', 
                  r'Pressure ($p$)', r'Energy ($e$)']
    
    for idx, (var, label) in enumerate(zip(variables, var_labels)):
        if var in error_norms:
            ax = axes[idx]
            
            # Plot each norm type
            ax.plot(time_coords, error_norms[var]['L1'], 
                   'o-', linewidth=2, markersize=5, label='L1 (Mean Abs Error)', alpha=0.8)
            ax.plot(time_coords, error_norms[var]['L2'], 
                   's-', linewidth=2, markersize=5, label='L2 (RMS Error)', alpha=0.8)
            ax.plot(time_coords, error_norms[var]['Linf'], 
                   '^-', linewidth=2, markersize=5, label='L∞ (Max Abs Error)', alpha=0.8)
            
            ax.set_xlabel('Time', fontsize=11)
            ax.set_ylabel('Error Value', fontsize=11)
            ax.set_yscale('log')
            ax.set_title(f'Error Norms for {label}', fontsize=12)
            ax.legend(fontsize=9, loc='best')
            ax.grid(True, alpha=0.3, which='both')
    
    plt.tight_layout()
    output_file = output_path / f"{run_name}_error_norms.png"
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    logger.info(f"Saved error norms plot to {output_file}")


def create_hovmoller_diagrams(numerical_data: np.ndarray, analytical_data: np.ndarray,
                              x_coords: np.ndarray, time_coords: np.ndarray,
                              output_path: Path, run_name: str,
                              variables: List[str] = ['rho', 'ux', 'pp', 'ee']):
    """
    Task 2: Create Hovmöller (space-time) diagrams for each variable.
    
    Creates 2D space-time plots showing:
    1. Numerical solution
    2. Analytical solution
    3. Error (difference)
    
    Args:
        numerical_data: 3D array (num_timesteps, num_variables, num_spatial_points)
        analytical_data: 3D array with same structure
        x_coords: 1D array of spatial coordinates
        time_coords: 1D array of time values
        output_path: Directory to save plots
        run_name: Name of the run
        variables: List of variable names
    """
    output_path.mkdir(parents=True, exist_ok=True)
    logger.info("Creating Hovmöller diagrams (space-time plots)...")
    
    var_labels = {
        'rho': r'Density ($\rho$)',
        'ux': r'Velocity ($u_x$)',
        'pp': r'Pressure ($p$)',
        'ee': r'Energy ($e$)'
    }
    
    num_timesteps, num_variables, num_spatial_points = numerical_data.shape
    
    # Create meshgrid for plotting
    X, T = np.meshgrid(x_coords, time_coords)
    
    for v, var in enumerate(variables):
        fig, axes = plt.subplots(1, 3, figsize=(20, 6))
        fig.suptitle(f'Hovmöller Diagram for {var_labels.get(var, var)}\n{run_name}',
                     fontsize=14, fontweight='bold')
        
        # Extract 2D space-time matrices
        numerical_matrix = numerical_data[:, v, :]
        analytical_matrix = analytical_data[:, v, :]
        error_matrix = numerical_matrix - analytical_matrix
        
        # Subplot 1: Numerical Solution
        im1 = axes[0].pcolormesh(X, T, numerical_matrix, 
                                 cmap='viridis', shading='auto')
        axes[0].set_xlabel('Position (x)', fontsize=11)
        axes[0].set_ylabel('Time (t)', fontsize=11)
        axes[0].set_title('Numerical Solution', fontsize=12)
        cbar1 = plt.colorbar(im1, ax=axes[0])
        cbar1.set_label(var_labels.get(var, var), fontsize=10)
        
        # Subplot 2: Analytical Solution
        # Use same color scale as numerical for direct comparison
        vmin, vmax = im1.get_clim()
        im2 = axes[1].pcolormesh(X, T, analytical_matrix, 
                                 cmap='viridis', shading='auto',
                                 vmin=vmin, vmax=vmax)
        axes[1].set_xlabel('Position (x)', fontsize=11)
        axes[1].set_ylabel('Time (t)', fontsize=11)
        axes[1].set_title('Analytical Solution', fontsize=12)
        cbar2 = plt.colorbar(im2, ax=axes[1])
        cbar2.set_label(var_labels.get(var, var), fontsize=10)
        
        # Subplot 3: Error (Numerical - Analytical)
        # Use diverging colormap centered at zero
        error_abs_max = np.max(np.abs(error_matrix))
        im3 = axes[2].pcolormesh(X, T, error_matrix, 
                                 cmap='coolwarm', shading='auto',
                                 vmin=-error_abs_max, vmax=error_abs_max)
        axes[2].set_xlabel('Position (x)', fontsize=11)
        axes[2].set_ylabel('Time (t)', fontsize=11)
        axes[2].set_title('Numerical - Analytical Error', fontsize=12)
        cbar3 = plt.colorbar(im3, ax=axes[2])
        cbar3.set_label('Error', fontsize=10)
        
        plt.tight_layout()
        output_file = output_path / f"{run_name}_hovmoller_{var}.png"
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close()
        logger.info(f"Saved Hovmöller diagram for {var}")
    
    logger.success(f"Created Hovmöller diagrams for all variables")


def calculate_integrated_quantities(numerical_data: np.ndarray, x_coords: np.ndarray,
                                    time_coords: np.ndarray) -> Dict:
    """
    Task 3: Calculate integrated quantities (mass, momentum, energy) vs time.
    
    Verifies conservation by integrating over space at each timestep.
    
    Args:
        numerical_data: 3D array (num_timesteps, num_variables, num_spatial_points)
                       Variables ordered as [rho, ux, p, e]
        x_coords: 1D array of spatial coordinates
        time_coords: 1D array of time values
    
    Returns:
        Dictionary containing time series of integrated quantities:
        {
            'mass': [...],
            'momentum': [...],
            'energy': [...]
        }
    """
    logger.info("Calculating integrated quantities (mass, momentum, energy)...")
    
    num_timesteps = numerical_data.shape[0]
    
    # Calculate grid spacing (assume uniform)
    dx = x_coords[1] - x_coords[0]
    
    # Initialize storage
    total_mass = []
    total_momentum = []
    total_energy = []
    
    # Iterate through each timestep
    for t in range(num_timesteps):
        # Extract required variables
        rho = numerical_data[t, 0, :]  # Density
        ux = numerical_data[t, 1, :]   # Velocity
        e = numerical_data[t, 3, :]    # Energy
        
        # Calculate integrated quantities (approximate integral as sum * dx)
        mass_t = np.sum(rho * dx)
        momentum_t = np.sum(rho * ux * dx)
        energy_t = np.sum(e * dx)
        
        total_mass.append(mass_t)
        total_momentum.append(momentum_t)
        total_energy.append(energy_t)
    
    integrated_quantities = {
        'mass': np.array(total_mass),
        'momentum': np.array(total_momentum),
        'energy': np.array(total_energy)
    }
    
    logger.success(f"Calculated integrated quantities for {num_timesteps} timesteps")
    return integrated_quantities


def plot_conservation_analysis(integrated_quantities: Dict, time_coords: np.ndarray,
                               output_path: Path, run_name: str):
    """
    Task 3 Output: Plot percent change in conserved quantities vs time.
    
    Creates a single plot showing conservation of mass, momentum, and energy.
    """
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Calculate percent change from initial value
    mass_change = 100 * (integrated_quantities['mass'] - integrated_quantities['mass'][0]) / integrated_quantities['mass'][0]
    momentum_change = 100 * (integrated_quantities['momentum'] - integrated_quantities['momentum'][0]) / integrated_quantities['momentum'][0]
    energy_change = 100 * (integrated_quantities['energy'] - integrated_quantities['energy'][0]) / integrated_quantities['energy'][0]
    
    fig, ax = plt.subplots(figsize=(12, 7))
    
    ax.plot(time_coords, mass_change, 'o-', linewidth=2, markersize=5, 
            label='Mass', alpha=0.8)
    ax.plot(time_coords, momentum_change, 's-', linewidth=2, markersize=5, 
            label='Momentum', alpha=0.8)
    ax.plot(time_coords, energy_change, '^-', linewidth=2, markersize=5, 
            label='Energy', alpha=0.8)
    
    # Add horizontal line at y=0 for perfect conservation
    ax.axhline(y=0, color='black', linestyle='--', linewidth=1.5, 
              label='Perfect Conservation', alpha=0.5)
    
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Percent Change from Initial Value (%)', fontsize=12)
    ax.set_title(f'Conservation of Integrated Quantities\n{run_name}', 
                fontsize=14, fontweight='bold')
    ax.legend(fontsize=11, loc='best')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    output_file = output_path / f"{run_name}_conservation.png"
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    logger.info(f"Saved conservation analysis plot to {output_file}")


def perform_comprehensive_analysis(sim_data_list: List[dict], 
                                   analytical_data_list: List[dict],
                                   output_path: Path, run_name: str) -> Dict:
    """
    Performs all three analysis tasks on simulation data.
    
    Args:
        sim_data_list: List of simulation data dictionaries from all VAR files
        analytical_data_list: List of corresponding analytical solutions
        output_path: Directory to save analysis results
        run_name: Name of the run
    
    Returns:
        Dictionary containing all analysis results
    """
    logger.info(f"Starting comprehensive analysis for {run_name}...")
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Convert data lists to numpy arrays
    variables = ['rho', 'ux', 'pp', 'ee']
    num_timesteps = len(sim_data_list)
    num_spatial_points = len(sim_data_list[0]['x'])
    num_variables = len(variables)
    
    # Initialize 3D arrays
    numerical_data = np.zeros((num_timesteps, num_variables, num_spatial_points))
    analytical_data = np.zeros((num_timesteps, num_variables, num_spatial_points))
    
    # Extract coordinates
    x_coords = sim_data_list[0]['x']
    time_coords = np.array([sim_data['t'] for sim_data in sim_data_list])
    
    # Fill arrays
    for t, (sim_data, ana_data) in enumerate(zip(sim_data_list, analytical_data_list)):
        for v, var in enumerate(variables):
            numerical_data[t, v, :] = sim_data[var]
            analytical_data[t, v, :] = ana_data[var]
    
    # Task 1: Error Norm Analysis
    error_norms = calculate_error_norms(numerical_data, analytical_data, variables)
    plot_error_norms(error_norms, time_coords, output_path, run_name)
    
    # Task 2: Hovmöller Diagrams
    create_hovmoller_diagrams(numerical_data, analytical_data, x_coords, time_coords,
                             output_path, run_name, variables)
    
    # Task 3: Integrated Quantities Conservation
    integrated_quantities = calculate_integrated_quantities(numerical_data, x_coords, time_coords)
    plot_conservation_analysis(integrated_quantities, time_coords, output_path, run_name)
    
    logger.success(f"Comprehensive analysis completed for {run_name}")
    
    return {
        'error_norms': error_norms,
        'integrated_quantities': integrated_quantities,
        'time_coords': time_coords
    }


def find_best_performer_by_error_norms(analysis_results: Dict, metric: str = 'L2') -> Tuple[str, float]:
    """
    Find the best performing experiment based on error norms.
    
    Args:
        analysis_results: Dictionary mapping run_name -> analysis results
        metric: Which error norm to use ('L1', 'L2', or 'Linf')
    
    Returns:
        Tuple of (best_run_name, best_score)
    """
    best_run = None
    best_score = float('inf')
    
    for run_name, results in analysis_results.items():
        if 'error_norms' in results:
            # Calculate average error across all variables and timesteps
            avg_error = np.mean([
                np.mean(results['error_norms'][var][metric])
                for var in results['error_norms'].keys()
            ])
            
            if avg_error < best_score:
                best_score = avg_error
                best_run = run_name
    
    return best_run, best_score


def compare_branch_performers_by_error_norms(analysis_results: Dict, 
                                            branch_mapping: Dict,
                                            metric: str = 'L2') -> Dict:
    """
    Compare best performers from each branch based on error norms.
    
    Args:
        analysis_results: Dictionary mapping run_name -> analysis results
        branch_mapping: Dictionary mapping run_name -> branch_name
        metric: Which error norm to use ('L1', 'L2', or 'Linf')
    
    Returns:
        Dictionary mapping branch_name -> (best_run, score)
    """
    branch_best = {}
    
    # Organize runs by branch
    branches = {}
    for run_name, branch_name in branch_mapping.items():
        if branch_name not in branches:
            branches[branch_name] = []
        branches[branch_name].append(run_name)
    
    # Find best in each branch
    for branch_name, run_names in branches.items():
        best_run = None
        best_score = float('inf')
        
        for run_name in run_names:
            if run_name in analysis_results and 'error_norms' in analysis_results[run_name]:
                avg_error = np.mean([
                    np.mean(analysis_results[run_name]['error_norms'][var][metric])
                    for var in analysis_results[run_name]['error_norms'].keys()
                ])
                
                if avg_error < best_score:
                    best_score = avg_error
                    best_run = run_name
        
        if best_run:
            branch_best[branch_name] = (best_run, best_score)
    
    return branch_best

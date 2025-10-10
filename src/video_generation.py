# src/video_generation.py

import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
from pathlib import Path
from loguru import logger
from typing import Dict, List


def create_var_evolution_video(sim_data_list: List[dict], analytical_data_list: List[dict],
                               output_path: Path, run_name: str,
                               variables: List[str] = ['rho', 'ux', 'pp', 'ee'],
                               fps: int = 2):
    """
    Creates an animated GIF showing evolution of variables across all VAR files using matplotlib.
    
    Args:
        sim_data_list: List of simulation data from all VAR files
        analytical_data_list: List of analytical solutions for all VAR files
        output_path: Directory to save the animation
        run_name: Name of the run for title
        variables: List of variables to plot
        fps: Frames per second for the animation
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
    
    n_vars = len(sim_data_list)
    
    # Get units
    unit_dict = {}
    if 'params' in sim_data_list[0]:
        params = sim_data_list[0]['params']
        unit_dict['rho'] = params.unit_density
        unit_dict['ux'] = params.unit_velocity * 1e-5
        unit_dict['pp'] = params.unit_energy_density
        unit_dict['ee'] = params.unit_velocity ** 2
    else:
        unit_dict = {var: 1.0 for var in variables}
    
    # Create figure
    fig, axes = plt.subplots(2, 2, figsize=(16, 14))
    axes = axes.flatten()
    
    # Initialize lines for each variable
    lines = {}
    analytical_lines = {}
    text_annotations = {}
    
    for idx, var in enumerate(variables):
        ax = axes[idx]
        
        # Create line objects
        lines[var], = ax.plot([], [], 'b-', linewidth=2, label='Numerical', alpha=0.8)
        analytical_lines[var], = ax.plot([], [], 'r--', linewidth=2.5, label='Analytical', alpha=0.9)
        
        ax.set_xlabel('Position (x) [kpc]', fontsize=11)
        ax.set_ylabel(var_labels.get(var, var), fontsize=11)
        ax.set_yscale(var_scales.get(var, 'linear'))
        ax.set_title(f'{var.upper()} Evolution', fontsize=12)
        ax.legend(fontsize=10, loc='best')
        ax.grid(True, alpha=0.3)
        
        # Set axis limits based on data range
        if analytical_data_list:
            x_data = analytical_data_list[0]['x']
            ax.set_xlim(x_data.min(), x_data.max())
            
            # Calculate y-limits across all timesteps
            all_sim_vals = [sd[var]*unit_dict[var] for sd in sim_data_list if var in sd]
            all_anal_vals = [ad[var]*unit_dict[var] for ad in analytical_data_list if var in ad]
            
            if all_sim_vals and all_anal_vals:
                all_vals = np.concatenate([np.concatenate(all_sim_vals), np.concatenate(all_anal_vals)])
                if var_scales.get(var) == 'log':
                    y_min = np.min(all_vals[all_vals > 0]) * 0.5
                    y_max = np.max(all_vals) * 2.0
                else:
                    y_range = all_vals.max() - all_vals.min()
                    y_min = all_vals.min() - 0.1 * y_range
                    y_max = all_vals.max() + 0.1 * y_range
                ax.set_ylim(y_min, y_max)
        
        # Add text annotation for timestep info
        text_annotations[var] = ax.text(0.02, 0.98, '', transform=ax.transAxes,
                                       verticalalignment='top', fontsize=10,
                                       bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    # Main title
    title = fig.suptitle('', fontsize=16, fontweight='bold')
    
    def init():
        """Initialize animation"""
        for var in variables:
            lines[var].set_data([], [])
            analytical_lines[var].set_data([], [])
            text_annotations[var].set_text('')
        title.set_text(f'Variable Evolution\n{run_name}\nVAR 0/{n_vars}')
        return list(lines.values()) + list(analytical_lines.values()) + list(text_annotations.values()) + [title]
    
    def animate(frame):
        """Animation function"""
        sim_data = sim_data_list[frame]
        analytical_data = analytical_data_list[frame]
        
        for var in variables:
            if var in sim_data and var in analytical_data:
                lines[var].set_data(sim_data['x'], sim_data[var] * unit_dict[var])
                analytical_lines[var].set_data(analytical_data['x'], analytical_data[var] * unit_dict[var])
                
                var_file_name = sim_data.get('var_file', f'VAR{frame}')
                text_annotations[var].set_text(
                    f'{var_file_name}\nt = {sim_data["t"]:.4e} s'
                )
        
        title.set_text(f'Variable Evolution\n{run_name}\nVAR {frame+1}/{n_vars}')
        
        return list(lines.values()) + list(analytical_lines.values()) + list(text_annotations.values()) + [title]
    
    # Create animation
    anim = animation.FuncAnimation(fig, animate, init_func=init, frames=n_vars,
                                  interval=1000//fps, blit=True, repeat=True)
    
    # Save animation as GIF using PillowWriter
    output_file = output_path / f"{run_name}_var_evolution.gif"
    try:
        writer = animation.PillowWriter(fps=fps, metadata=dict(artist='Pencil Platform'))
        anim.save(output_file, writer=writer)
        logger.success(f"Saved VAR evolution animation to {output_file}")
    except Exception as e:
        logger.error(f"Failed to save animation: {e}")
        logger.info("Creating individual frames instead...")
        create_var_evolution_frames(sim_data_list, analytical_data_list, output_path, run_name, variables)
    finally:
        plt.close()


def create_var_evolution_frames(sim_data_list: List[dict], analytical_data_list: List[dict],
                                output_path: Path, run_name: str,
                                variables: List[str] = ['rho', 'ux', 'pp', 'ee']):
    """
    Creates individual PNG frames showing evolution of variables.
    
    Args:
        sim_data_list: List of simulation data from all VAR files
        analytical_data_list: List of analytical solutions for all VAR files
        output_path: Directory to save the frames
        run_name: Name of the run for title
        variables: List of variables to plot
    """
    frames_dir = output_path / f"{run_name}_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    
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
    
    n_vars = len(sim_data_list)
    
    # Get units
    unit_dict = {}
    if 'params' in sim_data_list[0]:
        params = sim_data_list[0]['params']
        unit_dict['rho'] = params.unit_density
        unit_dict['ux'] = params.unit_velocity * 1e-5
        unit_dict['pp'] = params.unit_energy_density
        unit_dict['ee'] = params.unit_velocity ** 2
    else:
        unit_dict = {var: 1.0 for var in variables}
    
    logger.info(f"Creating {n_vars} individual frames...")
    
    for frame_idx, (sim_data, analytical_data) in enumerate(zip(sim_data_list, analytical_data_list)):
        fig, axes = plt.subplots(2, 2, figsize=(16, 14))
        fig.suptitle(f'Variable Evolution\n{run_name}\nVAR {frame_idx+1}/{n_vars} (t={sim_data["t"]:.4e})', 
                     fontsize=16, fontweight='bold')
        axes = axes.flatten()
        
        for idx, var in enumerate(variables):
            ax = axes[idx]
            
            if var in sim_data and var in analytical_data:
                ax.plot(sim_data['x'], sim_data[var] * unit_dict[var], 
                       'b-', linewidth=2, label='Numerical', alpha=0.8)
                ax.plot(analytical_data['x'], analytical_data[var] * unit_dict[var], 
                       'r--', linewidth=2.5, label='Analytical', alpha=0.9)
                
                ax.set_xlabel('Position (x) [kpc]', fontsize=11)
                ax.set_ylabel(var_labels.get(var, var), fontsize=11)
                ax.set_yscale(var_scales.get(var, 'linear'))
                ax.set_title(f'{var.upper()} - {sim_data.get("var_file", f"VAR{frame_idx}")}', fontsize=12)
                ax.legend(fontsize=10, loc='best')
                ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        frame_file = frames_dir / f"frame_{frame_idx:04d}.png"
        plt.savefig(frame_file, dpi=100, bbox_inches='tight')
        plt.close()
    
    logger.success(f"Saved {n_vars} frames to {frames_dir}")


def create_error_evolution_video(spatial_errors: Dict, output_path: Path, run_name: str, 
                                fps: int = 2, unit_length: float = 1.0):
    """
    Creates an animated GIF showing spatial error evolution across VAR files using matplotlib.
    Shows x position (kpc) vs error at each point.
    
    Args:
        spatial_errors: Dictionary containing spatial error data from calculate_spatial_errors()
        output_path: Directory to save the animation
        run_name: Name of the run
        fps: Frames per second
        unit_length: Unit conversion factor for length (e.g., to kpc)
    """
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Validate unit_length to prevent overflow
    if not np.isfinite(unit_length) or unit_length > 1e20 or unit_length == 0:
        logger.warning(f"Invalid unit_length value ({unit_length}). Using 1.0 instead.")
        unit_length = 1.0
    
    variables = ['rho', 'ux', 'pp', 'ee']
    var_labels = [r'$\rho$', r'$u_x$', r'$p$', r'$e$']
    
    # Filter to only variables with data
    valid_vars = [(var, label) for var, label in zip(variables, var_labels) if var in spatial_errors]
    
    if not valid_vars:
        logger.warning("No valid variables with spatial error data")
        return
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    axes = axes.flatten()
    
    # Get max number of timesteps and x coordinates
    max_timesteps = max(len(spatial_errors[var]['errors_per_timestep']) for var, _ in valid_vars)
    error_method = spatial_errors[list(spatial_errors.keys())[0]]['error_method']
    
    # Initialize plot elements
    lines = {}
    annotations = {}
    
    for idx, (var, label) in enumerate(valid_vars):
        ax = axes[idx]
        
        # Safely convert x coordinates to physical units
        x_raw = spatial_errors[var]['x']
        try:
            x_coords = x_raw * unit_length
            # Check for overflow
            if not np.all(np.isfinite(x_coords)):
                logger.warning(f"Overflow in x coordinate conversion for {var}. Using normalized coordinates.")
                x_coords = x_raw
                unit_length = 1.0
        except (OverflowError, RuntimeWarning):
            logger.warning(f"Cannot convert x coordinates for {var}. Using normalized coordinates.")
            x_coords = x_raw
            unit_length = 1.0
        
        # Create empty line object
        lines[var], = ax.plot([], [], '-', linewidth=2, color='#1f77b4', alpha=0.8)
        
        # Determine appropriate x-axis label
        x_label = 'Position (x) [kpc]' if unit_length != 1.0 else 'Position (x) [normalized]'
        ax.set_xlabel(x_label, fontsize=11)
        ax.set_ylabel(f'Error in {label}', fontsize=11)
        ax.set_title(f'{label} Spatial Error Evolution', fontsize=12)
        
        if np.all(np.isfinite(x_coords)):
            ax.set_xlim(x_coords.min(), x_coords.max())
        
        # Set y limits based on all timesteps
        all_errors = np.concatenate(spatial_errors[var]['errors_per_timestep'])
        y_min = all_errors.min()
        y_max = all_errors.max()
        y_range = y_max - y_min
        ax.set_ylim(y_min - 0.1*y_range, y_max + 0.1*y_range)
        
        ax.grid(True, alpha=0.3)
        
        # Annotation for statistics
        annotations[var] = ax.text(0.02, 0.98, '', transform=ax.transAxes,
                                   verticalalignment='top', fontsize=9,
                                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    title = fig.suptitle('', fontsize=16, fontweight='bold')
    
    def init():
        """Initialize animation"""
        for var, _ in valid_vars:
            lines[var].set_data([], [])
            annotations[var].set_text('')
        title.set_text(f'Spatial Error Evolution ({error_method})\n{run_name}\nVAR 0/{max_timesteps}')
        return list(lines.values()) + list(annotations.values()) + [title]
    
    def animate(frame):
        """Animation function"""
        for var, label in valid_vars:
            if var in spatial_errors:
                # Safely convert x coordinates
                x_raw = spatial_errors[var]['x']
                try:
                    x_coords = x_raw * unit_length
                    if not np.all(np.isfinite(x_coords)):
                        x_coords = x_raw
                except (OverflowError, RuntimeWarning):
                    x_coords = x_raw
                
                errors = spatial_errors[var]['errors_per_timestep'][frame]
                var_file = spatial_errors[var]['var_files'][frame]
                timestep = spatial_errors[var]['timesteps'][frame]
                
                lines[var].set_data(x_coords, errors)
                
                # Calculate statistics for annotation
                mean_err = np.mean(errors)
                max_err = np.max(errors)
                min_err = np.min(errors)
                std_err = np.std(errors)
                
                annotations[var].set_text(
                    f'{var_file}\nt = {timestep:.4e} s\n'
                    f'Mean: {mean_err:.4e}\n'
                    f'Max: {max_err:.4e}\n'
                    f'Min: {min_err:.4e}\n'
                    f'Std: {std_err:.4e}'
                )
        
        title.set_text(f'Spatial Error Evolution ({error_method})\n{run_name}\nVAR {frame+1}/{max_timesteps}')
        
        return list(lines.values()) + list(annotations.values()) + [title]
    
    # Create animation
    anim = animation.FuncAnimation(fig, animate, init_func=init, frames=max_timesteps,
                                  interval=1000//fps, blit=True, repeat=True)
    
    # Save animation as GIF using PillowWriter
    output_file = output_path / f"{run_name}_error_evolution.gif"
    try:
        writer = animation.PillowWriter(fps=fps, metadata=dict(artist='Pencil Platform'))
        anim.save(output_file, writer=writer)
        logger.success(f"Saved error evolution animation to {output_file}")
    except Exception as e:
        logger.error(f"Failed to save animation: {e}")
        logger.info("Creating individual frames instead...")
        create_error_evolution_frames(spatial_errors, output_path, run_name, unit_length)
    finally:
        plt.close()


def create_error_evolution_frames(spatial_errors: Dict, output_path: Path, run_name: str,
                                  unit_length: float = 1.0):
    """
    Creates individual PNG frames showing spatial error evolution.
    
    Args:
        spatial_errors: Dictionary containing spatial error data from calculate_spatial_errors()
        output_path: Directory to save the frames
        run_name: Name of the run
        unit_length: Unit conversion factor for length (e.g., to kpc)
    """
    frames_dir = output_path / f"{run_name}_error_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    
    variables = ['rho', 'ux', 'pp', 'ee']
    var_labels = [r'$\rho$', r'$u_x$', r'$p$', r'$e$']
    
    # Filter to only variables with data
    valid_vars = [(var, label) for var, label in zip(variables, var_labels) if var in spatial_errors]
    
    if not valid_vars:
        logger.warning("No valid variables with spatial error data")
        return
    
    # Validate unit_length to prevent overflow
    if not np.isfinite(unit_length) or unit_length > 1e20 or unit_length == 0:
        logger.warning(f"Invalid unit_length value ({unit_length}). Using 1.0 instead.")
        unit_length = 1.0
    
    # Get max number of timesteps and error method
    max_timesteps = max(len(spatial_errors[var]['errors_per_timestep']) for var, _ in valid_vars)
    error_method = spatial_errors[list(spatial_errors.keys())[0]]['error_method']
    
    logger.info(f"Creating {max_timesteps} spatial error evolution frames...")
    
    for frame in range(max_timesteps):
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f'Spatial Error Evolution ({error_method})\n{run_name}\nVAR {frame+1}/{max_timesteps}', 
                     fontsize=16, fontweight='bold')
        axes = axes.flatten()
        
        for idx, (var, label) in enumerate(valid_vars):
            ax = axes[idx]
            
            if var in spatial_errors:
                # Safely convert x coordinates to physical units
                x_raw = spatial_errors[var]['x']
                try:
                    x_coords = x_raw * unit_length
                    # Check for overflow
                    if not np.all(np.isfinite(x_coords)):
                        logger.warning(f"Overflow in x coordinate conversion for {var}. Using normalized coordinates.")
                        x_coords = x_raw
                except (OverflowError, RuntimeWarning):
                    logger.warning(f"Cannot convert x coordinates for {var}. Using normalized coordinates.")
                    x_coords = x_raw
                
                errors = spatial_errors[var]['errors_per_timestep'][frame]
                var_file = spatial_errors[var]['var_files'][frame]
                timestep = spatial_errors[var]['timesteps'][frame]
                
                # Plot spatial error distribution
                ax.plot(x_coords, errors, '-', linewidth=2, color='#1f77b4', alpha=0.8)
                
                # Calculate statistics for annotation
                mean_err = np.mean(errors)
                max_err = np.max(errors)
                min_err = np.min(errors)
                std_err = np.std(errors)
                
                # Add text annotation
                ax.text(0.02, 0.98, 
                       f'{var_file}\nt = {timestep:.4e} s\n'
                       f'Mean: {mean_err:.4e}\n'
                       f'Max: {max_err:.4e}\n'
                       f'Min: {min_err:.4e}\n'
                       f'Std: {std_err:.4e}',
                       transform=ax.transAxes, verticalalignment='top', fontsize=9,
                       bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
                
                # Determine appropriate x-axis label
                x_label = 'Position (x) [kpc]' if unit_length != 1.0 else 'Position (x) [normalized]'
                ax.set_xlabel(x_label, fontsize=11)
                ax.set_ylabel(f'Error in {label}', fontsize=11)
                ax.set_title(f'{label} Spatial Error', fontsize=12)
                
                # Set limits safely
                if np.all(np.isfinite(x_coords)):
                    ax.set_xlim(x_coords.min(), x_coords.max())
                else:
                    logger.warning(f"Non-finite x coordinates for {var}, skipping xlim")
                
                all_errors = np.concatenate(spatial_errors[var]['errors_per_timestep'])
                if np.all(np.isfinite(all_errors)):
                    y_min = all_errors.min()
                    y_max = all_errors.max()
                    y_range = y_max - y_min
                    ax.set_ylim(y_min - 0.1*y_range, y_max + 0.1*y_range)
                
                ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        frame_file = frames_dir / f"frame_{frame:04d}.png"
        plt.savefig(frame_file, dpi=100, bbox_inches='tight')
        plt.close()
    
    logger.success(f"Saved {max_timesteps} error evolution frames to {frames_dir}")

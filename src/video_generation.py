# src/video_generation.py

import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
from pathlib import Path
from loguru import logger
from typing import Dict, List

from .experiment_name_decoder import format_experiment_title, format_short_experiment_name


def create_var_evolution_video(sim_data_list: List[dict], analytical_data_list: List[dict],
                               output_path: Path, run_name: str,
                               variables: List[str] = ['rho', 'ux', 'pp', 'ee'],
                               fps: int = 2, save_frames: bool = False):
    """
    Creates an animated GIF showing evolution of variables across all VAR files using matplotlib.
    
    Args:
        sim_data_list: List of simulation data from all VAR files
        analytical_data_list: List of analytical solutions for all VAR files
        output_path: Directory to save the animation
        run_name: Name of the run for title
        variables: List of variables to plot
        fps: Frames per second for the animation
        save_frames: Whether to save individual PNG frames (default: False to save resources)
    """
    output_path.mkdir(parents=True, exist_ok=True)
    
    var_labels = {
        'rho': r'Density $\rho$ [g cm$^{-3}$]',
        'ux': r'Velocity $u_x$ [km s$^{-1}$]',
        'pp': r'Pressure $p$ [dyn cm$^{-2}$]',
        'ee': r'Energy $e$ [km$^2$ s$^{-2}$]'
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
    
    # Create figure with space for legend
    fig = plt.figure(figsize=(17, 13))
    gs = fig.add_gridspec(2, 2, left=0.08, right=0.98, top=0.93, bottom=0.12, hspace=0.25, wspace=0.25)
    axes = [fig.add_subplot(gs[i, j]) for i in range(2) for j in range(2)]
    
    # Initialize lines for each variable
    lines = {}
    analytical_lines = {}
    
    for idx, var in enumerate(variables):
        ax = axes[idx]
        
        # Create line objects
        lines[var], = ax.plot([], [], 'b-', linewidth=2, alpha=0.8)
        analytical_lines[var], = ax.plot([], [], 'r--', linewidth=2.5, alpha=0.9)
        
        ax.set_xlabel('Position (x) [kpc]', fontsize=11)
        ax.set_ylabel(var_labels.get(var, var), fontsize=11)
        ax.set_yscale(var_scales.get(var, 'linear'))
        ax.set_title(f'{var.upper()}', fontsize=12, fontweight='bold')
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
    
    # Single legend placed at bottom center
    fig.legend([lines[variables[0]], analytical_lines[variables[0]]], 
              ['Numerical', 'Analytical'], 
              loc='lower center', ncol=2, fontsize=11, frameon=True,
              bbox_to_anchor=(0.5, 0.02))
    
    # Info text at bottom left
    info_text = fig.text(0.08, 0.05, '', fontsize=10, verticalalignment='bottom')
    
    # Main title with decoded experiment name
    formatted_title = format_experiment_title(run_name, max_line_length=60)
    title = fig.suptitle('', fontsize=13, fontweight='bold', y=0.97)
    
    def init():
        """Initialize animation"""
        for var in variables:
            lines[var].set_data([], [])
            analytical_lines[var].set_data([], [])
        info_text.set_text('')
        title.set_text(f'{formatted_title}\nVariable Evolution | VAR 0')
        return list(lines.values()) + list(analytical_lines.values()) + [info_text, title]
    
    def animate(frame):
        """Animation function"""
        sim_data = sim_data_list[frame]
        analytical_data = analytical_data_list[frame]
        
        for var in variables:
            if var in sim_data and var in analytical_data:
                lines[var].set_data(sim_data['x'], sim_data[var] * unit_dict[var])
                analytical_lines[var].set_data(analytical_data['x'], analytical_data[var] * unit_dict[var])
        
        var_file_name = sim_data.get('var_file', f'VAR{frame}')
        info_text.set_text(f'{var_file_name} | t = {sim_data["t"]:.4e} s')
        
        # Update title with current VAR number
        title.set_text(f'{formatted_title}\nVariable Evolution | VAR {frame}')
        
        return list(lines.values()) + list(analytical_lines.values()) + [info_text, title]
    
    # Create animation
    anim = animation.FuncAnimation(fig, animate, init_func=init, frames=n_vars,
                                  interval=1000//fps, blit=True, repeat=True)
    
    # Optionally create individual frames (disabled by default to save resources)
    if save_frames:
        logger.info("Creating individual frames...")
        create_var_evolution_frames(sim_data_list, analytical_data_list, output_path, run_name, variables)
    else:
        logger.debug("Skipping individual frame generation (save_frames=False)")
    
    # Save animation as GIF using PillowWriter
    output_file = output_path / f"{run_name}_var_evolution.gif"
    try:
        writer = animation.PillowWriter(fps=fps, metadata=dict(artist='Pencil Platform'))
        anim.save(output_file, writer=writer)
        logger.success(f"Saved VAR evolution animation to {output_file}")
    except Exception as e:
        logger.error(f"Failed to save animation: {e}")
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
        output_path: Directory to save the frames (should be var_frames base directory)
        run_name: Name of the run for title
        variables: List of variables to plot
    """
    # Save frames in var_frames/{run_name}/ directory
    frames_dir = output_path.parent / "var_frames" / run_name
    frames_dir.mkdir(parents=True, exist_ok=True)
    
    var_labels = {
        'rho': r'Density $\rho$ [g cm$^{-3}$]',
        'ux': r'Velocity $u_x$ [km s$^{-1}$]',
        'pp': r'Pressure $p$ [dyn cm$^{-2}$]',
        'ee': r'Energy $e$ [km$^2$ s$^{-2}$]'
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
        fig = plt.figure(figsize=(17, 13))
        gs = fig.add_gridspec(2, 2, left=0.08, right=0.98, top=0.93, bottom=0.12, hspace=0.25, wspace=0.25)
        axes = [fig.add_subplot(gs[i, j]) for i in range(2) for j in range(2)]
        
        var_file_name = sim_data.get('var_file', f'VAR{frame_idx}')
        fig.suptitle(f'Variable Evolution - {run_name}', fontsize=14, fontweight='bold', y=0.97)
        fig.text(0.08, 0.05, f'{var_file_name} | t = {sim_data["t"]:.4e} s | Frame {frame_idx+1}/{n_vars}', 
                fontsize=10, verticalalignment='bottom')
        
        for idx, var in enumerate(variables):
            ax = axes[idx]
            
            if var in sim_data and var in analytical_data:
                ax.plot(sim_data['x'], sim_data[var] * unit_dict[var], 
                       'b-', linewidth=2, alpha=0.8)
                ax.plot(analytical_data['x'], analytical_data[var] * unit_dict[var], 
                       'r--', linewidth=2.5, alpha=0.9)
                
                ax.set_xlabel('Position (x) [kpc]', fontsize=11)
                ax.set_ylabel(var_labels.get(var, var), fontsize=11)
                ax.set_yscale(var_scales.get(var, 'linear'))
                ax.set_title(f'{var.upper()}', fontsize=12, fontweight='bold')
                ax.grid(True, alpha=0.3)
        
        # Single legend at bottom center
        fig.legend(['Numerical', 'Analytical'], loc='lower center', ncol=2, fontsize=11, 
                  frameon=True, bbox_to_anchor=(0.5, 0.02))
        
        frame_file = frames_dir / f"frame_{frame_idx:04d}.png"
        plt.savefig(frame_file, dpi=100, bbox_inches='tight')
        plt.close()
    
    logger.success(f"Saved {n_vars} frames to {frames_dir}")


def create_error_evolution_video(spatial_errors: Dict, output_path: Path, run_name: str, 
                                fps: int = 2, unit_length: float = 1.0, save_frames: bool = False):
    """
    Creates an animated GIF showing spatial error evolution across VAR files using matplotlib.
    Shows x position (kpc) vs error at each point.
    
    Args:
        spatial_errors: Dictionary containing spatial error data from calculate_spatial_errors()
        output_path: Directory to save the animation
        run_name: Name of the run
        fps: Frames per second
        unit_length: Unit conversion factor for length (e.g., to kpc)
        save_frames: Whether to save individual PNG frames (default: False to save disk space and time)
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
    
    # Create figure with space for info
    fig = plt.figure(figsize=(17, 11))
    gs = fig.add_gridspec(2, 2, left=0.08, right=0.98, top=0.94, bottom=0.12, hspace=0.25, wspace=0.25)
    axes = [fig.add_subplot(gs[i, j]) for i in range(2) for j in range(2)]
    
    # Get max number of timesteps and x coordinates
    max_timesteps = max(len(spatial_errors[var]['errors_per_timestep']) for var, _ in valid_vars)
    error_method = spatial_errors[list(spatial_errors.keys())[0]]['error_method']
    
    # Initialize plot elements
    lines = {}
    
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
        ax.set_title(f'{label}', fontsize=12, fontweight='bold')
        
        if np.all(np.isfinite(x_coords)):
            ax.set_xlim(x_coords.min(), x_coords.max())
        
        # Set y limits based on all timesteps
        all_errors = np.concatenate(spatial_errors[var]['errors_per_timestep'])
        y_min = all_errors.min()
        y_max = all_errors.max()
        y_range = y_max - y_min
        ax.set_ylim(y_min - 0.1*y_range, y_max + 0.1*y_range)
        
        ax.grid(True, alpha=0.3)
    
    # Single statistics box at bottom
    stats_text = fig.text(0.08, 0.02, '', fontsize=9, verticalalignment='bottom', family='monospace',
                         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8, pad=0.5))
    
    # Improved title with clear formatting and decoded experiment name
    formatted_title = format_experiment_title(run_name, max_line_length=60)
    title = fig.suptitle('', fontsize=13, fontweight='bold', y=0.97)
    
    def init():
        """Initialize animation"""
        for var, _ in valid_vars:
            lines[var].set_data([], [])
        stats_text.set_text('')
        title.set_text(f'{formatted_title}\nError Evolution ({error_method.capitalize()}) | VAR 0')
        return list(lines.values()) + [stats_text, title]
    
    def animate(frame):
        """Animation function"""
        stats_lines = []
        
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
                lines[var].set_data(x_coords, errors)
                
                # Collect statistics
                mean_err = np.mean(errors)
                max_err = np.max(errors)
                stats_lines.append(f'{label}: Mean={mean_err:.3e}, Max={max_err:.3e}')
        
        var_file = spatial_errors[list(spatial_errors.keys())[0]]['var_files'][frame]
        timestep = spatial_errors[list(spatial_errors.keys())[0]]['timesteps'][frame]
        
        stats_text.set_text(f'{var_file} | t={timestep:.4e} s\n' + 
                           '  |  '.join(stats_lines))
        
        # Update title with current VAR number
        title.set_text(f'{formatted_title}\nError Evolution ({error_method.capitalize()}) | VAR {frame}')
        
        return list(lines.values()) + [stats_text, title]
    
    # Create animation
    anim = animation.FuncAnimation(fig, animate, init_func=init, frames=max_timesteps,
                                  interval=1000//fps, blit=True, repeat=True)
    
    # Optionally create individual frames (disabled by default to save resources)
    if save_frames:
        logger.info("Creating individual frames...")
        create_error_evolution_frames(spatial_errors, output_path, run_name, unit_length)
    else:
        logger.debug("Skipping individual frame generation (save_frames=False)")
    
    # Save animation as GIF using PillowWriter
    output_file = output_path / f"{run_name}_error_evolution.gif"
    try:
        writer = animation.PillowWriter(fps=fps, metadata=dict(artist='Pencil Platform'))
        anim.save(output_file, writer=writer)
        logger.success(f"Saved error evolution animation to {output_file}")
    except Exception as e:
        logger.error(f"Failed to save animation: {e}")
    finally:
        plt.close()


def create_error_evolution_frames(spatial_errors: Dict, output_path: Path, run_name: str,
                                  unit_length: float = 1.0):
    """
    Creates individual PNG frames showing spatial error evolution.
    
    Args:
        spatial_errors: Dictionary containing spatial error data from calculate_spatial_errors()
        output_path: Directory to save the frames (should be error_evolution base directory)
        run_name: Name of the run
        unit_length: Unit conversion factor for length (e.g., to kpc)
    """
    # Save frames in error_frames/{run_name}/ directory
    frames_dir = output_path.parent / "error_frames" / run_name
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
        fig = plt.figure(figsize=(17, 11))
        gs = fig.add_gridspec(2, 2, left=0.08, right=0.98, top=0.94, bottom=0.12, hspace=0.25, wspace=0.25)
        axes = [fig.add_subplot(gs[i, j]) for i in range(2) for j in range(2)]
        
        fig.suptitle(f'Spatial Error Evolution ({error_method.capitalize()})\n{run_name}', 
                     fontsize=14, fontweight='bold', y=0.97)
        
        stats_lines = []
        
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
                
                # Calculate statistics
                mean_err = np.mean(errors)
                max_err = np.max(errors)
                stats_lines.append(f'{label}: Mean={mean_err:.3e}, Max={max_err:.3e}')
                
                # Determine appropriate x-axis label
                x_label = 'Position (x) [kpc]' if unit_length != 1.0 else 'Position (x) [normalized]'
                ax.set_xlabel(x_label, fontsize=11)
                ax.set_ylabel(f'Error in {label}', fontsize=11)
                ax.set_title(f'{label}', fontsize=12, fontweight='bold')
                
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
        
        # Single statistics box at bottom
        fig.text(0.08, 0.02, f'{var_file} | t={timestep:.4e} s | Frame {frame+1}/{max_timesteps}\n' + 
                '  |  '.join(stats_lines), fontsize=9, verticalalignment='bottom', family='monospace',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8, pad=0.5))
        
        frame_file = frames_dir / f"frame_{frame:04d}.png"
        plt.savefig(frame_file, dpi=100, bbox_inches='tight')
        plt.close()
    
    logger.success(f"Saved {max_timesteps} error evolution frames to {frames_dir}")

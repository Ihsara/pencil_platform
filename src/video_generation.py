# src/video_generation.py

import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
from pathlib import Path
from loguru import logger
from typing import Dict, List
import shutil


def create_var_evolution_video(sim_data_list: List[dict], analytical_data_list: List[dict],
                               output_path: Path, run_name: str,
                               variables: List[str] = ['rho', 'ux', 'pp', 'ee'],
                               fps: int = 2):
    """
    Creates an animated video showing evolution of variables across all VAR files.
    
    Args:
        sim_data_list: List of simulation data from all VAR files
        analytical_data_list: List of analytical solutions for all VAR files
        output_path: Directory to save the video
        run_name: Name of the run for title
        variables: List of variables to plot
        fps: Frames per second for the video
    """
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Check if ffmpeg is available
    if not shutil.which('ffmpeg'):
        logger.warning("ffmpeg not found. Cannot create video. Please install ffmpeg.")
        logger.info("Creating individual frames instead...")
        create_var_evolution_frames(sim_data_list, analytical_data_list, output_path, run_name, variables)
        return
    
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
    
    # Save video
    output_file = output_path / f"{run_name}_var_evolution.mp4"
    try:
        Writer = animation.writers['ffmpeg']
        writer = Writer(fps=fps, metadata=dict(artist='Pencil Platform'), bitrate=1800)
        anim.save(output_file, writer=writer)
        logger.success(f"Saved VAR evolution video to {output_file}")
    except Exception as e:
        logger.error(f"Failed to save video: {e}")
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
    logger.info(f"To create video manually, run: ffmpeg -framerate 2 -i {frames_dir}/frame_%04d.png -c:v libx264 -pix_fmt yuv420p {output_path}/{run_name}_var_evolution.mp4")


def create_error_evolution_video(std_devs: Dict, output_path: Path, run_name: str, fps: int = 2):
    """
    Creates an animated video showing error evolution across VAR files with point-to-point tracking.
    
    Args:
        std_devs: Dictionary containing standard deviation metrics
        output_path: Directory to save the video
        run_name: Name of the run
        fps: Frames per second
    """
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Check if ffmpeg is available
    if not shutil.which('ffmpeg'):
        logger.warning("ffmpeg not found. Cannot create video. Creating individual frames instead...")
        create_error_evolution_frames(std_devs, output_path, run_name)
        return
    
    variables = ['rho', 'ux', 'pp', 'ee']
    var_labels = [r'$\rho$', r'$u_x$', r'$p$', r'$e$']
    
    # Filter to only variables with data
    valid_vars = [(var, label) for var, label in zip(variables, var_labels) if var in std_devs]
    
    if not valid_vars:
        logger.warning("No valid variables with std_dev data")
        return
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    axes = axes.flatten()
    
    # Get max number of timesteps
    max_timesteps = max(len(std_devs[var]['per_timestep']) for var, _ in valid_vars)
    
    # Initialize plot elements
    lines = {}
    scatter_current = {}
    scatter_mean = {}
    scatter_max = {}
    scatter_min = {}
    annotations = {}
    
    for idx, (var, label) in enumerate(valid_vars):
        ax = axes[idx]
        timesteps = range(len(std_devs[var]['per_timestep']))
        
        # Create empty line and scatter objects
        lines[var], = ax.plot([], [], 'o-', linewidth=2, markersize=6, color='#1f77b4', alpha=0.7)
        scatter_current[var] = ax.scatter([], [], s=150, c='red', marker='o', zorder=5, label='Current VAR')
        scatter_mean[var] = ax.scatter([], [], s=100, c='green', marker='s', zorder=4, label='Mean')
        scatter_max[var] = ax.scatter([], [], s=100, c='orange', marker='^', zorder=4, label='Max')
        scatter_min[var] = ax.scatter([], [], s=100, c='blue', marker='v', zorder=4, label='Min')
        
        ax.set_xlabel('VAR File Index', fontsize=11)
        ax.set_ylabel(f'Std Dev of {label}', fontsize=11)
        ax.set_title(f'{label} Standard Deviation Evolution', fontsize=12)
        ax.set_xlim(-0.5, len(timesteps) - 0.5)
        
        # Set y limits
        all_vals = std_devs[var]['per_timestep']
        y_range = max(all_vals) - min(all_vals)
        ax.set_ylim(min(all_vals) - 0.1*y_range, max(all_vals) + 0.2*y_range)
        
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8, loc='upper right')
        
        # Annotation for statistics
        annotations[var] = ax.text(0.02, 0.98, '', transform=ax.transAxes,
                                   verticalalignment='top', fontsize=9,
                                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    title = fig.suptitle('', fontsize=16, fontweight='bold')
    
    def init():
        """Initialize animation"""
        for var, _ in valid_vars:
            lines[var].set_data([], [])
            scatter_current[var].set_offsets(np.empty((0, 2)))
            scatter_mean[var].set_offsets(np.empty((0, 2)))
            scatter_max[var].set_offsets(np.empty((0, 2)))
            scatter_min[var].set_offsets(np.empty((0, 2)))
            annotations[var].set_text('')
        title.set_text(f'Error Evolution\n{run_name}\nVAR 0/{max_timesteps}')
        return (list(lines.values()) + list(scatter_current.values()) + 
                list(scatter_mean.values()) + list(scatter_max.values()) + 
                list(scatter_min.values()) + list(annotations.values()) + [title])
    
    def animate(frame):
        """Animation function"""
        for var, label in valid_vars:
            if var in std_devs:
                per_timestep = std_devs[var]['per_timestep']
                timesteps = list(range(len(per_timestep)))
                
                # Show data up to current frame
                current_frame = min(frame, len(timesteps) - 1)
                x_data = timesteps[:current_frame + 1]
                y_data = per_timestep[:current_frame + 1]
                
                lines[var].set_data(x_data, y_data)
                
                # Highlight current point
                if x_data:
                    scatter_current[var].set_offsets([[x_data[-1], y_data[-1]]])
                
                # Calculate and show mean/max/min so far
                if y_data:
                    mean_val = np.mean(y_data)
                    max_val = np.max(y_data)
                    min_val = np.min(y_data)
                    max_idx = x_data[np.argmax(y_data)]
                    min_idx = x_data[np.argmin(y_data)]
                    
                    scatter_mean[var].set_offsets([[x_data[-1], mean_val]])
                    scatter_max[var].set_offsets([[max_idx, max_val]])
                    scatter_min[var].set_offsets([[min_idx, min_val]])
                    
                    annotations[var].set_text(
                        f'Current: {y_data[-1]:.4e}\n'
                        f'Mean: {mean_val:.4e}\n'
                        f'Max: {max_val:.4e} (VAR {max_idx})\n'
                        f'Min: {min_val:.4e} (VAR {min_idx})'
                    )
        
        title.set_text(f'Error Evolution\n{run_name}\nVAR {frame+1}/{max_timesteps}')
        
        return (list(lines.values()) + list(scatter_current.values()) + 
                list(scatter_mean.values()) + list(scatter_max.values()) + 
                list(scatter_min.values()) + list(annotations.values()) + [title])
    
    # Create animation
    anim = animation.FuncAnimation(fig, animate, init_func=init, frames=max_timesteps,
                                  interval=1000//fps, blit=True, repeat=True)
    
    # Save video
    output_file = output_path / f"{run_name}_error_evolution.mp4"
    try:
        Writer = animation.writers['ffmpeg']
        writer = Writer(fps=fps, metadata=dict(artist='Pencil Platform'), bitrate=1800)
        anim.save(output_file, writer=writer)
        logger.success(f"Saved error evolution video to {output_file}")
    except Exception as e:
        logger.error(f"Failed to save video: {e}")
        logger.info("Creating individual frames instead...")
        create_error_evolution_frames(std_devs, output_path, run_name)
    finally:
        plt.close()


def create_error_evolution_frames(std_devs: Dict, output_path: Path, run_name: str):
    """
    Creates individual PNG frames showing error evolution.
    
    Args:
        std_devs: Dictionary containing standard deviation metrics
        output_path: Directory to save the frames
        run_name: Name of the run
    """
    frames_dir = output_path / f"{run_name}_error_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    
    variables = ['rho', 'ux', 'pp', 'ee']
    var_labels = [r'$\rho$', r'$u_x$', r'$p$', r'$e$']
    
    # Filter to only variables with data
    valid_vars = [(var, label) for var, label in zip(variables, var_labels) if var in std_devs]
    
    if not valid_vars:
        logger.warning("No valid variables with std_dev data")
        return
    
    # Get max number of timesteps
    max_timesteps = max(len(std_devs[var]['per_timestep']) for var, _ in valid_vars)
    
    logger.info(f"Creating {max_timesteps} error evolution frames...")
    
    for frame in range(max_timesteps):
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f'Error Evolution\n{run_name}\nVAR {frame+1}/{max_timesteps}', 
                     fontsize=16, fontweight='bold')
        axes = axes.flatten()
        
        for idx, (var, label) in enumerate(valid_vars):
            ax = axes[idx]
            
            if var in std_devs:
                per_timestep = std_devs[var]['per_timestep']
                timesteps = list(range(len(per_timestep)))
                
                # Show data up to current frame
                current_frame = min(frame, len(timesteps) - 1)
                x_data = timesteps[:current_frame + 1]
                y_data = per_timestep[:current_frame + 1]
                
                # Plot line
                ax.plot(x_data, y_data, 'o-', linewidth=2, markersize=6, 
                       color='#1f77b4', alpha=0.7)
                
                # Highlight current point
                if x_data:
                    ax.scatter([x_data[-1]], [y_data[-1]], s=150, c='red', 
                             marker='o', zorder=5, label='Current VAR')
                
                # Calculate and show mean/max/min so far
                if y_data:
                    mean_val = np.mean(y_data)
                    max_val = np.max(y_data)
                    min_val = np.min(y_data)
                    max_idx = x_data[np.argmax(y_data)]
                    min_idx = x_data[np.argmin(y_data)]
                    
                    ax.scatter([x_data[-1]], [mean_val], s=100, c='green', 
                             marker='s', zorder=4, label='Mean')
                    ax.scatter([max_idx], [max_val], s=100, c='orange', 
                             marker='^', zorder=4, label='Max')
                    ax.scatter([min_idx], [min_val], s=100, c='blue', 
                             marker='v', zorder=4, label='Min')
                    
                    # Add text annotation
                    ax.text(0.02, 0.98, 
                           f'Current: {y_data[-1]:.4e}\n'
                           f'Mean: {mean_val:.4e}\n'
                           f'Max: {max_val:.4e} (VAR {max_idx})\n'
                           f'Min: {min_val:.4e} (VAR {min_idx})',
                           transform=ax.transAxes, verticalalignment='top', fontsize=9,
                           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
                
                ax.set_xlabel('VAR File Index', fontsize=11)
                ax.set_ylabel(f'Std Dev of {label}', fontsize=11)
                ax.set_title(f'{label} Standard Deviation Evolution', fontsize=12)
                ax.set_xlim(-0.5, len(timesteps) - 0.5)
                
                # Set y limits
                all_vals = per_timestep
                y_range = max(all_vals) - min(all_vals)
                ax.set_ylim(min(all_vals) - 0.1*y_range, max(all_vals) + 0.2*y_range)
                
                ax.grid(True, alpha=0.3)
                ax.legend(fontsize=8, loc='upper right')
        
        plt.tight_layout()
        frame_file = frames_dir / f"frame_{frame:04d}.png"
        plt.savefig(frame_file, dpi=100, bbox_inches='tight')
        plt.close()
    
    logger.success(f"Saved {max_timesteps} error evolution frames to {frames_dir}")
    logger.info(f"To create video manually, run: ffmpeg -framerate 2 -i {frames_dir}/frame_%04d.png -c:v libx264 -pix_fmt yuv420p {output_path}/{run_name}_error_evolution.mp4")

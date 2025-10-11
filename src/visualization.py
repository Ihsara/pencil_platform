# src/visualization.py
"""
Centralized visualization module for all plotting and animation functions.

This module contains all visualization functionality including:
- Basic comparison plots
- Error norm visualizations  
- Animation/video generation
- Collage plots
- Standard deviation plots

All matplotlib-based plotting should be done through functions in this module
to maintain consistency and avoid code duplication.
"""

import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.gridspec as gridspec
import numpy as np
from pathlib import Path
from loguru import logger
from typing import Dict, List, Tuple, Optional
import random

from .experiment_name_decoder import format_experiment_title, format_short_experiment_name


# ============================================================================
# SECTION 1: BASIC COMPARISON PLOTS
# ============================================================================

def plot_simulation_vs_analytical(sim_data: dict, analytical_data: dict, output_path: Path, run_name: str):
    """
    Generates and saves the four core comparison plots for a single simulation run.
    
    Args:
        sim_data: Dictionary containing the processed simulation data
        analytical_data: Dictionary containing the analytical solution data
        output_path: Directory where the plot images will be saved
        run_name: Name of the simulation run, used for plot titles
    """
    output_path.mkdir(parents=True, exist_ok=True)
    
    plot_definitions = {
        'density': ('rho', r'$\rho$ [g cm$^{-3}$]', sim_data['params'].unit_density, 'log'),
        'velocity': ('ux', r'$u_x$ [km s$^{-1}$]', sim_data['params'].unit_velocity*1e-5, 'linear'),
        'pressure': ('pp', r'$p$ [dyn cm$^{-2}$]', sim_data['params'].unit_energy_density, 'log'),
        'energy': ('ee', r'$e$ [km$^2$ s$^{-2}$]', sim_data['params'].unit_velocity**2, 'log'), 
    }

    for plot_key, (data_key, ylabel, unit, yscale) in plot_definitions.items():
        plt.style.use('seaborn-v0_8-whitegrid')
        fig, ax = plt.subplots(figsize=(10, 7))
        
        ax.plot(analytical_data['x'], analytical_data[data_key]*unit, 'k--', linewidth=2.5, label='Analytical Solution')
        ax.plot(sim_data['x'], sim_data[data_key]*unit, 'o-', color='#1f77b4', markersize=4, label=f'Simulation (t={sim_data["t"]:.2e})')
        
        ax.set_title(f"{ylabel} Profile for\n{run_name}", fontsize=16, pad=15)
        ax.set_xlabel('Position (x) [kpc]', fontsize=12)
        ax.set_ylabel(f'{ylabel}', fontsize=12)
        ax.set_yscale(yscale)
        ax.legend(fontsize=11)
        ax.grid(True, which='major', linestyle='--', linewidth=0.5)
        
        plt.tight_layout()
        filename = output_path / f"{plot_key}.png"
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close(fig)
        
    logger.success(f"Generated {len(plot_definitions)} plots for run '{run_name}' in '{output_path}'")


# ============================================================================
# SECTION 2: ERROR NORM VISUALIZATIONS
# ============================================================================

def create_combined_scores_plot(combined_scores, output_dir, experiment_name):
    """Create bar plot comparing combined scores for all runs."""
    fig, ax = plt.subplots(figsize=(16, 8))
    
    sorted_items = sorted(combined_scores.items(), key=lambda x: x[1]['combined'])
    run_names = [item[0] for item in sorted_items]
    scores = [item[1]['combined'] for item in sorted_items]
    branches = [item[1]['branch'] for item in sorted_items]
    
    unique_branches = list(set(branches))
    colors = plt.cm.Set3(np.linspace(0, 1, len(unique_branches)))
    branch_colors = {branch: colors[i] for i, branch in enumerate(unique_branches)}
    bar_colors = [branch_colors[b] for b in branches]
    
    bars = ax.bar(range(len(run_names)), scores, color=bar_colors, alpha=0.8, edgecolor='black', linewidth=0.5)
    
    for i in range(min(3, len(bars))):
        bars[i].set_edgecolor('gold')
        bars[i].set_linewidth(3)
    
    ax.set_xlabel('Run Name', fontsize=12, fontweight='bold')
    ax.set_ylabel('Combined Error Score (lower is better)', fontsize=12, fontweight='bold')
    ax.set_title(f'{experiment_name}: Combined Error Scores (L1+L2+L∞)\nTop 3 highlighted in gold', 
                 fontsize=14, fontweight='bold')
    ax.set_xticks(range(len(run_names)))
    ax.set_xticklabels(run_names, rotation=45, ha='right', fontsize=8)
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_yscale('log')
    
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=branch_colors[b], label=b, alpha=0.8) for b in unique_branches]
    ax.legend(handles=legend_elements, title='Branch', loc='upper left', fontsize=9)
    
    plt.tight_layout()
    output_file = output_dir / f"{experiment_name}_combined_scores.png"
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    logger.info(f"       └─ Saved to {output_file.name}")


def create_per_metric_plots(error_norms_cache, metrics, output_dir, experiment_name):
    """Create comparison plots for each metric separately."""
    variables = ['rho', 'ux', 'pp', 'ee']
    var_labels = [r'$\rho$ [g cm$^{-3}$]', r'$u_x$ [km s$^{-1}$]', r'$p$ [dyn cm$^{-2}$]', r'$e$ [km$^2$ s$^{-2}$]']
    
    for metric in metrics:
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f'{experiment_name}: {metric.upper()} Error Comparison', fontsize=16, fontweight='bold')
        axes = axes.flatten()
        
        for idx, (var, label) in enumerate(zip(variables, var_labels)):
            ax = axes[idx]
            run_names = []
            mean_errors = []
            
            for run_name, cached in error_norms_cache.items():
                error_norms = cached['error_norms']
                if var in error_norms and metric in error_norms[var]:
                    mean_val = error_norms[var][metric]['mean']
                    if np.isfinite(mean_val):
                        run_names.append(run_name)
                        mean_errors.append(mean_val)
            
            if run_names:
                sorted_indices = np.argsort(mean_errors)
                run_names = [run_names[i] for i in sorted_indices]
                mean_errors = [mean_errors[i] for i in sorted_indices]
                
                bars = ax.bar(range(len(run_names)), mean_errors, alpha=0.7, edgecolor='black', linewidth=0.5)
                bars[0].set_color('green')
                bars[0].set_alpha(1.0)
                
                ax.set_xlabel('Run Name', fontsize=10)
                ax.set_ylabel(f'{metric.upper()} Error', fontsize=10)
                ax.set_title(f'{label} - {metric.upper()} Error', fontsize=12)
                ax.set_xticks(range(len(run_names)))
                ax.set_xticklabels(run_names, rotation=45, ha='right', fontsize=7)
                ax.grid(True, alpha=0.3, axis='y')
                ax.set_yscale('log')
        
        plt.tight_layout()
        output_file = output_dir / f"{experiment_name}_{metric}_comparison.png"
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close()
        logger.info(f"       └─ Saved {metric.upper()} comparison to {output_file.name}")


def create_best_performers_plot(top_5, error_norms_cache, metrics, output_dir, experiment_name):
    """Create detailed comparison of top 5 performers."""
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle(f'{experiment_name}: Top 5 Performers - Detailed Comparison', fontsize=16, fontweight='bold')
    axes = axes.flatten()
    
    variables = ['rho', 'ux', 'pp', 'ee']
    var_labels = [r'$\rho$ [g cm$^{-3}$]', r'$u_x$ [km s$^{-1}$]', r'$p$ [dyn cm$^{-2}$]', r'$e$ [km$^2$ s$^{-2}$]']
    colors = plt.cm.viridis(np.linspace(0, 1, 5))
    
    for idx, (var, label) in enumerate(zip(variables, var_labels)):
        ax = axes[idx]
        
        for rank, (run_name, scores) in enumerate(top_5, 1):
            if run_name not in error_norms_cache:
                continue
            
            error_norms = error_norms_cache[run_name]['error_norms']
            
            if var in error_norms:
                metric_values = []
                for metric in metrics:
                    if metric in error_norms[var]:
                        metric_values.append(error_norms[var][metric]['mean'])
                    else:
                        metric_values.append(np.nan)
                
                x_pos = np.arange(len(metrics)) + (rank-1)*0.15
                ax.bar(x_pos, metric_values, width=0.15, label=f'#{rank}: {run_name[:20]}...', 
                      color=colors[rank-1], alpha=0.8)
        
        ax.set_xlabel('Error Metric', fontsize=10)
        ax.set_ylabel('Error Value', fontsize=10)
        ax.set_title(f'{label} Comparison', fontsize=12)
        ax.set_xticks(np.arange(len(metrics)) + 0.3)
        ax.set_xticklabels([m.upper() for m in metrics])
        ax.legend(fontsize=8, loc='best')
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_yscale('log')
    
    plt.tight_layout()
    output_file = output_dir / f"{experiment_name}_top5_detailed.png"
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    logger.info(f"       └─ Saved top 5 detailed comparison to {output_file.name}")


def create_branch_comparison_plot(branch_best, runs_per_branch, combined_scores, output_dir, experiment_name):
    """Create comparison of best performers from each branch."""
    fig, ax = plt.subplots(figsize=(14, 8))
    
    branch_names = []
    best_scores = []
    best_run_names = []
    
    for branch_name, (run_name, scores) in branch_best.items():
        branch_names.append(branch_name)
        best_scores.append(scores['combined'])
        best_run_names.append(run_name)
    
    bars = ax.bar(range(len(branch_names)), best_scores, alpha=0.8, edgecolor='black', linewidth=1.5)
    
    min_idx = np.argmin(best_scores)
    bars[min_idx].set_color('gold')
    bars[min_idx].set_alpha(1.0)
    
    ax.set_xlabel('Branch', fontsize=12, fontweight='bold')
    ax.set_ylabel('Combined Error Score (lower is better)', fontsize=12, fontweight='bold')
    ax.set_title(f'{experiment_name}: Best Performer per Branch\nGold = Overall Best', fontsize=14, fontweight='bold')
    ax.set_xticks(range(len(branch_names)))
    ax.set_xticklabels(branch_names, fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_yscale('log')
    
    for i, (score, run_name) in enumerate(zip(best_scores, best_run_names)):
        ax.text(i, score * 1.2, f'{branch_names[i]}', ha='center', va='bottom', 
               fontsize=9, fontweight='bold', color='darkblue')
        decoded_title = format_experiment_title(run_name, max_line_length=40)
        ax.text(i, score * 0.9, decoded_title, ha='center', va='top', fontsize=7, rotation=0, style='italic', 
               bbox=dict(boxstyle='round,pad=0.5', facecolor='wheat', alpha=0.7))
    
    plt.tight_layout()
    output_file = output_dir / f"{experiment_name}_branch_best.png"
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    logger.info(f"       └─ Saved branch comparison to {output_file.name}")


def create_error_evolution_plots(top_3, error_norms_cache, metrics, output_dir, experiment_name):
    """Create time evolution plots for top 3 performers."""
    for metric in metrics:
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f'{experiment_name}: {metric.upper()} Error Evolution - Top 3 Performers', 
                    fontsize=16, fontweight='bold')
        axes = axes.flatten()
        
        variables = ['rho', 'ux', 'pp', 'ee']
        var_labels = [r'$\rho$ [g cm$^{-3}$]', r'$u_x$ [km s$^{-1}$]', r'$p$ [dyn cm$^{-2}$]', r'$e$ [km$^2$ s$^{-2}$]']
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
        
        for idx, (var, label) in enumerate(zip(variables, var_labels)):
            ax = axes[idx]
            
            for rank, (run_name, scores) in enumerate(top_3, 1):
                if run_name not in error_norms_cache:
                    continue
                
                error_norms = error_norms_cache[run_name]['error_norms']
                
                if var in error_norms and metric in error_norms[var]:
                    errors = error_norms[var][metric]['per_timestep']
                    timesteps = range(len(errors))
                    
                    ax.plot(timesteps, errors, 'o-', linewidth=2, markersize=4,
                           color=colors[rank-1], alpha=0.7, label=f'#{rank}: {run_name[:25]}...')
            
            ax.set_xlabel('Timestep (VAR index)', fontsize=10)
            ax.set_ylabel(f'{metric.upper()} Error', fontsize=10)
            ax.set_title(f'{label} Evolution', fontsize=12)
            ax.legend(fontsize=8, loc='best')
            ax.grid(True, alpha=0.3)
            ax.set_yscale('log')
        
        plt.tight_layout()
        output_file = output_dir / f"{experiment_name}_top3_{metric}_evolution.png"
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close()
        logger.info(f"       └─ Saved {metric.upper()} evolution to {output_file.name}")


# ============================================================================
# SECTION 3: ANIMATION/VIDEO GENERATION
# ============================================================================

def create_var_evolution_video(sim_data_list: List[dict], analytical_data_list: List[dict],
                               output_path: Path, run_name: str,
                               variables: List[str] = ['rho', 'ux', 'pp', 'ee'],
                               fps: int = 2, save_frames: bool = False):
    """Creates an animated GIF showing evolution of variables across all VAR files."""
    output_path.mkdir(parents=True, exist_ok=True)
    
    var_labels = {
        'rho': r'Density $\rho$ [g cm$^{-3}$]',
        'ux': r'Velocity $u_x$ [km s$^{-1}$]',
        'pp': r'Pressure $p$ [dyn cm$^{-2}$]',
        'ee': r'Energy $e$ [km$^2$ s$^{-2}$]'
    }
    
    var_scales = {'rho': 'log', 'ux': 'linear', 'pp': 'log', 'ee': 'log'}
    n_vars = len(sim_data_list)
    
    unit_dict = {}
    if 'params' in sim_data_list[0]:
        params = sim_data_list[0]['params']
        unit_dict['rho'] = params.unit_density
        unit_dict['ux'] = params.unit_velocity * 1e-5
        unit_dict['pp'] = params.unit_energy_density
        unit_dict['ee'] = params.unit_velocity ** 2
    else:
        unit_dict = {var: 1.0 for var in variables}
    
    fig = plt.figure(figsize=(17, 13))
    gs = fig.add_gridspec(2, 2, left=0.08, right=0.98, top=0.93, bottom=0.12, hspace=0.25, wspace=0.25)
    axes = [fig.add_subplot(gs[i, j]) for i in range(2) for j in range(2)]
    
    lines = {}
    analytical_lines = {}
    
    for idx, var in enumerate(variables):
        ax = axes[idx]
        lines[var], = ax.plot([], [], 'b-', linewidth=2, alpha=0.8)
        analytical_lines[var], = ax.plot([], [], 'r--', linewidth=2.5, alpha=0.9

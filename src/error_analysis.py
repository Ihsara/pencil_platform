# src/error_analysis.py

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from loguru import logger
import json
from typing import Dict, List, Tuple, Optional
import seaborn as sns

from .error_metrics import METRIC_REGISTRY, calculate_error, calculate_all_errors


def calculate_error_norms(sim_data_list: List[dict], analytical_data_list: List[dict],
                         variables: List[str] = ['rho', 'ux', 'pp', 'ee'],
                         metrics: List[str] = None) -> Dict:
    """
    Calculate L1, L2, and other error norms between numerical and analytical solutions.
    
    This function uses the modular error metric system to calculate various error norms
    as described in Gent et al. (2018) for convergence analysis.
    
    Args:
        sim_data_list: List of simulation data dictionaries from all VAR files
        analytical_data_list: List of corresponding analytical solutions
        variables: List of variable names to analyze
        metrics: List of metric names to calculate (default: ['l1', 'l2'])
        
    Returns:
        Dictionary containing error norms for each variable across all timesteps
        Structure:
        {
            'var_name': {
                'l1': {
                    'per_timestep': [...],
                    'mean': float,
                    'max': float,
                    'min': float
                },
                'l2': {...},
                ...
            }
        }
        
    Reference:
        Gent et al. (2018), Section 3, Equation (23) for L1 norm
    """
    if metrics is None:
        metrics = ['l1', 'l2']
    
    # Validation
    if len(sim_data_list) != len(analytical_data_list):
        logger.error(f"List length mismatch: {len(sim_data_list)} sim vs {len(analytical_data_list)} analytical")
        return {}
    
    logger.debug(f"Calculating error norms ({', '.join(metrics)}) for {len(sim_data_list)} timesteps")
    
    error_norms = {}
    
    for var in variables:
        error_norms[var] = {}
        
        for metric in metrics:
            errors_per_timestep = []
            
            for sim_data, analytical_data in zip(sim_data_list, analytical_data_list):
                if var in sim_data and var in analytical_data:
                    try:
                        error_val = calculate_error(sim_data[var], analytical_data[var], metric=metric)
                        errors_per_timestep.append(error_val)
                    except Exception as e:
                        logger.warning(f"Failed to calculate {metric} for {var}: {e}")
                        errors_per_timestep.append(np.nan)
            
            if errors_per_timestep:
                valid_errors = [e for e in errors_per_timestep if np.isfinite(e)]
                
                error_norms[var][metric] = {
                    'per_timestep': errors_per_timestep,
                    'mean': np.mean(valid_errors) if valid_errors else np.nan,
                    'max': np.max(valid_errors) if valid_errors else np.nan,
                    'min': np.min(valid_errors) if valid_errors else np.nan,
                    'std': np.std(valid_errors) if valid_errors else np.nan,
                    'timesteps': [sim_data_list[i]['t'] for i in range(len(errors_per_timestep))],
                    'var_files': [sim_data_list[i].get('var_file', f'VAR{i}') for i in range(len(errors_per_timestep))]
                }
    
    return error_norms


def calculate_spatial_errors(sim_data_list: List[dict], analytical_data_list: List[dict],
                            variables: List[str] = ['rho', 'ux', 'pp', 'ee'],
                            error_method: str = 'absolute') -> Dict:
    """
    Calculate spatial errors (point-by-point) between numerical and analytical solutions.
    
    Args:
        sim_data_list: List of simulation data dictionaries from all VAR files
        analytical_data_list: List of corresponding analytical solutions
        variables: List of variable names to analyze
        error_method: Error calculation method:
            - 'absolute': |sim - analytical|
            - 'relative': |sim - analytical| / |analytical|
            - 'difference': sim - analytical (signed)
            - 'squared': (sim - analytical)^2
            
    Returns:
        Dictionary containing spatial errors for each variable across all timesteps
    """
    # Validation logging
    if len(sim_data_list) != len(analytical_data_list):
        logger.error(f"List length mismatch: {len(sim_data_list)} sim vs {len(analytical_data_list)} analytical")
        return {}
    
    logger.debug(f"Calculating spatial errors for {len(sim_data_list)} timesteps using method: {error_method}")
    
    spatial_errors = {}
    
    for var in variables:
        errors_per_timestep = []
        x_coords = None
        
        for idx, (sim_data, analytical_data) in enumerate(zip(sim_data_list, analytical_data_list)):
            if var in sim_data and var in analytical_data:
                if x_coords is None:
                    x_coords = sim_data['x']
                
                # Calculate error based on specified method
                if error_method == 'absolute':
                    error = np.abs(sim_data[var] - analytical_data[var])
                elif error_method == 'relative':
                    # Avoid division by zero
                    analytical_safe = np.where(np.abs(analytical_data[var]) < 1e-10, 1e-10, analytical_data[var])
                    error = np.abs(sim_data[var] - analytical_data[var]) / np.abs(analytical_safe)
                elif error_method == 'difference':
                    error = sim_data[var] - analytical_data[var]
                elif error_method == 'squared':
                    error = (sim_data[var] - analytical_data[var])**2
                else:
                    logger.warning(f"Unknown error method '{error_method}', using 'absolute'")
                    error = np.abs(sim_data[var] - analytical_data[var])
                
                errors_per_timestep.append(error)
        
        if errors_per_timestep and x_coords is not None:
            spatial_errors[var] = {
                'x': x_coords,
                'errors_per_timestep': errors_per_timestep,
                'timesteps': [sim_data_list[i]['t'] for i in range(len(errors_per_timestep))],
                'var_files': [sim_data_list[i].get('var_file', f'VAR{i}') for i in range(len(errors_per_timestep))],
                'error_method': error_method
            }
    
    return spatial_errors


def calculate_std_deviation_across_vars(sim_data_list: List[dict], analytical_data_list: List[dict], 
                                        variables: List[str] = ['rho', 'ux', 'pp', 'ee']) -> Dict:
    """
    Calculate standard deviation between numerical and analytical solutions across all VAR files.
    
    Args:
        sim_data_list: List of simulation data dictionaries from all VAR files
        analytical_data_list: List of corresponding analytical solutions
        variables: List of variable names to analyze
        
    Returns:
        Dictionary containing standard deviation metrics for each variable across all timesteps
    """
    # Validation logging
    if len(sim_data_list) != len(analytical_data_list):
        logger.error(f"List length mismatch: {len(sim_data_list)} sim vs {len(analytical_data_list)} analytical")
        return {}
    
    logger.debug(f"Calculating std deviations for {len(sim_data_list)} timesteps")
    
    std_devs = {}
    
    for var in variables:
        deviations = []
        for idx, (sim_data, analytical_data) in enumerate(zip(sim_data_list, analytical_data_list)):
            if var in sim_data and var in analytical_data:
                diff = sim_data[var] - analytical_data[var]
                deviations.append(np.std(diff))
        
        if deviations:
            std_devs[var] = {
                'mean_std': np.mean(deviations),
                'max_std': np.max(deviations),
                'min_std': np.min(deviations),
                'std_of_std': np.std(deviations),
                'per_timestep': deviations
            }
    
    return std_devs


def calculate_absolute_deviation_per_var(sim_data_list: List[dict], analytical_data_list: List[dict],
                                         variables: List[str] = ['rho', 'ux', 'pp', 'ee']) -> Dict:
    """
    Calculate absolute deviation for each VAR file and find the worst performing VAR.
    
    Returns:
        Dictionary with absolute deviations per VAR and identification of worst performing VAR
    """
    results = {}
    
    for var in variables:
        var_results = []
        for idx, (sim_data, analytical_data) in enumerate(zip(sim_data_list, analytical_data_list)):
            if var in sim_data and var in analytical_data:
                abs_dev = np.mean(np.abs(sim_data[var] - analytical_data[var]))
                max_abs_dev = np.max(np.abs(sim_data[var] - analytical_data[var]))
                var_results.append({
                    'var_idx': idx,
                    'timestep': sim_data.get('t', idx),
                    'mean_abs_dev': abs_dev,
                    'max_abs_dev': max_abs_dev
                })
        
        if var_results:
            # Find worst performing VAR
            worst_mean = max(var_results, key=lambda x: x['mean_abs_dev'])
            worst_max = max(var_results, key=lambda x: x['max_abs_dev'])
            
            results[var] = {
                'per_var': var_results,
                'worst_mean_deviation': worst_mean,
                'worst_max_deviation': worst_max
            }
    
    return results


class ExperimentErrorAnalyzer:
    """
    Analyzes and compares errors across multiple experiments and branches.
    """
    
    def __init__(self, results_dir: Path):
        self.results_dir = results_dir
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.experiment_data = {}
        
    def add_experiment_data(self, experiment_name: str, run_name: str, branch_name: str,
                           std_devs: Dict, abs_devs: Dict):
        """Add error data for a single experiment run."""
        if experiment_name not in self.experiment_data:
            self.experiment_data[experiment_name] = {}
        
        if branch_name not in self.experiment_data[experiment_name]:
            self.experiment_data[experiment_name][branch_name] = {}
        
        self.experiment_data[experiment_name][branch_name][run_name] = {
            'std_devs': std_devs,
            'abs_devs': abs_devs
        }
    
    def save_intermediate_data(self, experiment_name: str):
        """Save intermediate data for an experiment."""
        output_file = self.results_dir / f"{experiment_name}_error_analysis.json"
        
        # Convert numpy types to Python native types for JSON serialization
        def convert_to_serializable(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, dict):
                return {k: convert_to_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_serializable(item) for item in obj]
            else:
                return obj
        
        serializable_data = convert_to_serializable(self.experiment_data[experiment_name])
        
        with open(output_file, 'w') as f:
            json.dump(serializable_data, f, indent=2)
        
        logger.success(f"Saved intermediate error analysis data to {output_file}")
    
    def load_experiment_data(self, experiment_name: str) -> bool:
        """Load previously saved experiment data."""
        input_file = self.results_dir / f"{experiment_name}_error_analysis.json"
        
        if not input_file.exists():
            return False
        
        with open(input_file, 'r') as f:
            self.experiment_data[experiment_name] = json.load(f)
        
        logger.info(f"Loaded error analysis data from {input_file}")
        return True
    
    def find_top_performers(self, metric: str = 'mean_std', top_n: int = 3) -> List[Tuple[str, str, float]]:
        """
        Find top N performing experiments based on specified metric.
        
        Returns:
            List of tuples (experiment_name, run_name, score)
        """
        all_scores = []
        
        for exp_name, branches in self.experiment_data.items():
            for branch_name, runs in branches.items():
                for run_name, data in runs.items():
                    # Calculate average metric across all variables
                    avg_score = np.mean([
                        data['std_devs'][var][metric] 
                        for var in data['std_devs'].keys()
                    ])
                    all_scores.append((f"{exp_name}/{branch_name}", run_name, avg_score))
        
        # Sort by score (lower is better)
        all_scores.sort(key=lambda x: x[2])
        return all_scores[:top_n]
    
    def find_worst_deviations(self) -> Dict:
        """Find runs and VARs with highest absolute deviations."""
        worst_per_var = {}
        
        for exp_name, branches in self.experiment_data.items():
            for branch_name, runs in branches.items():
                for run_name, data in runs.items():
                    for var, abs_dev_data in data['abs_devs'].items():
                        if var not in worst_per_var:
                            worst_per_var[var] = {
                                'worst_mean': None,
                                'worst_max': None
                            }
                        
                        worst_mean = abs_dev_data['worst_mean_deviation']
                        worst_max = abs_dev_data['worst_max_deviation']
                        
                        if (worst_per_var[var]['worst_mean'] is None or 
                            worst_mean['mean_abs_dev'] > worst_per_var[var]['worst_mean']['value']):
                            worst_per_var[var]['worst_mean'] = {
                                'experiment': f"{exp_name}/{branch_name}/{run_name}",
                                'var_idx': worst_mean['var_idx'],
                                'timestep': worst_mean['timestep'],
                                'value': worst_mean['mean_abs_dev']
                            }
                        
                        if (worst_per_var[var]['worst_max'] is None or 
                            worst_max['max_abs_dev'] > worst_per_var[var]['worst_max']['value']):
                            worst_per_var[var]['worst_max'] = {
                                'experiment': f"{exp_name}/{branch_name}/{run_name}",
                                'var_idx': worst_max['var_idx'],
                                'timestep': worst_max['timestep'],
                                'value': worst_max['max_abs_dev']
                            }
        
        return worst_per_var
    
    def compare_branch_best_performers(self) -> Dict:
        """Compare best performers from each branch."""
        branch_best = {}
        
        for exp_name, branches in self.experiment_data.items():
            if exp_name not in branch_best:
                branch_best[exp_name] = {}
            
            for branch_name, runs in branches.items():
                # Find best run in this branch
                best_run = None
                best_score = float('inf')
                
                for run_name, data in runs.items():
                    avg_score = np.mean([
                        data['std_devs'][var]['mean_std'] 
                        for var in data['std_devs'].keys()
                    ])
                    
                    if avg_score < best_score:
                        best_score = avg_score
                        best_run = run_name
                
                branch_best[exp_name][branch_name] = {
                    'run': best_run,
                    'score': best_score,
                    'data': runs[best_run]
                }
        
        return branch_best
    
    def plot_individual_experiment_std(self, experiment_name: str, branch_name: str, 
                                       run_name: str, output_dir: Path):
        """Plot standard deviation evolution for individual experiment with enhanced labeling."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        data = self.experiment_data[experiment_name][branch_name][run_name]
        std_devs = data['std_devs']
        
        fig, axes = plt.subplots(2, 2, figsize=(17, 13))
        
        # Get total number of VAR files for title
        n_vars = len(std_devs.get('rho', std_devs.get('ux', std_devs.get('pp', std_devs.get('ee', {})))).get('per_timestep', []))
        fig.suptitle(f'Standard Deviation Evolution Across {n_vars} VAR Files\n{experiment_name}/{branch_name}/{run_name}', 
                     fontsize=16, fontweight='bold')
        
        axes = axes.flatten()
        variables = ['rho', 'ux', 'pp', 'ee']
        var_labels = [r'$\rho$ [g cm$^{-3}$]', r'$u_x$ [km s$^{-1}$]', r'$p$ [dyn cm$^{-2}$]', r'$e$ [km$^2$ s$^{-2}$]']
        
        for idx, (var, label) in enumerate(zip(variables, var_labels)):
            if var in std_devs:
                per_timestep = std_devs[var]['per_timestep']
                timesteps = list(range(len(per_timestep)))
                
                # Plot main line
                axes[idx].plot(timesteps, per_timestep, 
                              'o-', linewidth=2, markersize=6, color='#1f77b4', alpha=0.7,
                              label='Per-VAR Std Dev')
                
                # Highlight mean
                mean_val = std_devs[var]['mean_std']
                axes[idx].axhline(y=mean_val, color='green', linewidth=2,
                                 linestyle='--', label=f'Mean: {mean_val:.4e}', zorder=3)
                
                # Highlight max
                max_val = std_devs[var]['max_std']
                max_idx = np.argmax(per_timestep)
                axes[idx].scatter([max_idx], [max_val], s=150, c='orange', marker='^', 
                                 zorder=5, label=f'Max: {max_val:.4e} (VAR {max_idx})',
                                 edgecolors='black', linewidths=1.5)
                
                # Highlight min
                min_val = std_devs[var]['min_std']
                min_idx = np.argmin(per_timestep)
                axes[idx].scatter([min_idx], [min_val], s=150, c='blue', marker='v', 
                                 zorder=5, label=f'Min: {min_val:.4e} (VAR {min_idx})',
                                 edgecolors='black', linewidths=1.5)
                
                axes[idx].set_xlabel('VAR File Index (0 to N-1)', fontsize=11)
                axes[idx].set_ylabel(f'Std Dev of {label}', fontsize=11)
                axes[idx].set_title(f'{label} Standard Deviation Evolution', fontsize=12)
                axes[idx].legend(fontsize=8, loc='best', framealpha=0.9)
                axes[idx].grid(True, alpha=0.3)
                
                # Add text box with statistics
                stats_text = (f'Range: [{min_val:.3e}, {max_val:.3e}]\n'
                            f'Std of Std: {std_devs[var]["std_of_std"]:.3e}')
                axes[idx].text(0.02, 0.98, stats_text, transform=axes[idx].transAxes,
                              verticalalignment='top', fontsize=8,
                              bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.7))
        
        plt.tight_layout()
        output_file = output_dir / f"{run_name}_std_evolution.png"
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close()
        logger.info(f"Saved individual experiment plot to {output_file}")
    
    def plot_branch_comparison(self, experiment_name: str, output_dir: Path):
        """Plot comparison of all runs within branches."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        branches = self.experiment_data[experiment_name]
        variables = ['rho', 'ux', 'pp', 'ee']
        var_labels = [r'$\rho$ [g cm$^{-3}$]', r'$u_x$ [km s$^{-1}$]', r'$p$ [dyn cm$^{-2}$]', r'$e$ [km$^2$ s$^{-2}$]']
        
        for var, label in zip(variables, var_labels):
            fig, axes = plt.subplots(1, len(branches), figsize=(6*len(branches), 5))
            if len(branches) == 1:
                axes = [axes]
            
            fig.suptitle(f'Branch Comparison: {label} Standard Deviation\n{experiment_name}', 
                        fontsize=14, fontweight='bold')
            
            for ax, (branch_name, runs) in zip(axes, branches.items()):
                for run_name, data in runs.items():
                    if var in data['std_devs']:
                        mean_std = data['std_devs'][var]['mean_std']
                        ax.bar(run_name, mean_std, alpha=0.7, label=run_name)
                
                ax.set_title(f'Branch: {branch_name}', fontsize=11)
                ax.set_ylabel(f'Mean Std Dev', fontsize=10)
                ax.tick_params(axis='x', rotation=45, labelsize=8)
                ax.grid(True, alpha=0.3, axis='y')
            
            plt.tight_layout()
            output_file = output_dir / f"{experiment_name}_branch_comparison_{var}.png"
            plt.savefig(output_file, dpi=150, bbox_inches='tight')
            plt.close()
            logger.info(f"Saved branch comparison plot to {output_file}")
    
    def plot_best_performers_comparison(self, output_dir: Path):
        """Plot comparison of best performers from each branch."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        branch_best = self.compare_branch_best_performers()
        variables = ['rho', 'ux', 'pp', 'ee']
        var_labels = [r'$\rho$ [g cm$^{-3}$]', r'$u_x$ [km s$^{-1}$]', r'$p$ [dyn cm$^{-2}$]', r'$e$ [km$^2$ s$^{-2}$]']
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Best Performers Comparison Across Branches', fontsize=16, fontweight='bold')
        axes = axes.flatten()
        
        for idx, (var, label) in enumerate(zip(variables, var_labels)):
            labels = []
            scores = []
            
            for exp_name, branches in branch_best.items():
                for branch_name, best_data in branches.items():
                    if var in best_data['data']['std_devs']:
                        labels.append(f"{exp_name}\n{branch_name}")
                        scores.append(best_data['data']['std_devs'][var]['mean_std'])
            
            if scores:
                bars = axes[idx].bar(range(len(labels)), scores, alpha=0.7)
                axes[idx].set_xticks(range(len(labels)))
                axes[idx].set_xticklabels(labels, rotation=45, ha='right', fontsize=9)
                axes[idx].set_ylabel(f'Mean Std Dev of {label}', fontsize=11)
                axes[idx].set_title(f'{label} - Best in Each Branch', fontsize=12)
                axes[idx].grid(True, alpha=0.3, axis='y')
                
                # Color the best overall
                if scores:
                    best_idx = np.argmin(scores)
                    bars[best_idx].set_color('green')
                    bars[best_idx].set_alpha(1.0)
        
        plt.tight_layout()
        output_file = output_dir / "best_performers_comparison.png"
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close()
        logger.info(f"Saved best performers comparison to {output_file}")
    
    def generate_summary_report(self, output_dir: Path):
        """Generate a comprehensive summary report with rich formatting."""
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        from rich.text import Text
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        console = Console()
        
        # Find top performers
        top_3 = self.find_top_performers(top_n=3)
        
        # Find worst deviations
        worst_devs = self.find_worst_deviations()
        
        # Compare branch best performers
        branch_best = self.compare_branch_best_performers()
        
        # === RICH CONSOLE OUTPUT ===
        console.print("\n")
        console.print(Panel.fit(
            "[bold cyan]Error Analysis Summary Report[/bold cyan]",
            border_style="cyan"
        ))
        
        # Top 3 Performers Table
        console.print("\n")
        top_table = Table(title="🏆 Top 3 Overall Performers", 
                         title_style="bold green",
                         border_style="green")
        top_table.add_column("Rank", style="bold yellow", justify="center", width=6)
        top_table.add_column("Experiment/Branch/Run", style="cyan")
        top_table.add_column("Mean Std Dev", justify="right", style="magenta")
        
        for idx, (exp_branch, run, score) in enumerate(top_3, 1):
            rank_emoji = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉"
            top_table.add_row(
                f"{rank_emoji} {idx}",
                f"{exp_branch}/{run}",
                f"{score:.6e}"
            )
        
        console.print(top_table)
        
        # Worst Deviations by Variable
        console.print("\n")
        for var, worst_data in worst_devs.items():
            var_panel = Panel(
                f"[bold red]Worst Mean:[/bold red] {worst_data['worst_mean']['experiment']}\n"
                f"  └─ VAR {worst_data['worst_mean']['var_idx']}, "
                f"t={worst_data['worst_mean']['timestep']:.4e}, "
                f"value=[bold]{worst_data['worst_mean']['value']:.6e}[/bold]\n\n"
                f"[bold red]Worst Max:[/bold red] {worst_data['worst_max']['experiment']}\n"
                f"  └─ VAR {worst_data['worst_max']['var_idx']}, "
                f"t={worst_data['worst_max']['timestep']:.4e}, "
                f"value=[bold]{worst_data['worst_max']['value']:.6e}[/bold]",
                title=f"⚠️  Variable: {var.upper()}",
                title_align="left",
                border_style="red"
            )
            console.print(var_panel)
        
        # Best Performers by Branch
        console.print("\n")
        for exp_name, branches in branch_best.items():
            branch_table = Table(
                title=f"✨ Best Performers: {exp_name}",
                title_style="bold blue",
                border_style="blue"
            )
            branch_table.add_column("Branch", style="cyan", width=20)
            branch_table.add_column("Best Run", style="green")
            branch_table.add_column("Score", justify="right", style="yellow")
            
            for branch_name, best_data in branches.items():
                branch_table.add_row(
                    branch_name,
                    best_data['run'],
                    f"{best_data['score']:.6e}"
                )
            
            console.print(branch_table)
        
        console.print("\n")
        console.print(Panel(
            f"[green]✓[/green] Analysis complete! Results saved to:\n"
            f"[cyan]{output_dir}[/cyan]",
            border_style="green"
        ))
        
        # === SAVE MARKDOWN REPORT ===
        report = ["# Error Analysis Summary Report\n"]
        report.append("## Top 3 Overall Performers\n")
        for idx, (exp_branch, run, score) in enumerate(top_3, 1):
            report.append(f"{idx}. **{exp_branch}/{run}** - Mean Std Dev: {score:.6e}\n")
        
        report.append("\n## Worst Deviations by Variable\n")
        for var, worst_data in worst_devs.items():
            report.append(f"\n### Variable: {var}\n")
            report.append(f"- **Worst Mean Deviation**: {worst_data['worst_mean']['experiment']} ")
            report.append(f"(VAR {worst_data['worst_mean']['var_idx']}, t={worst_data['worst_mean']['timestep']:.4e}, ")
            report.append(f"value={worst_data['worst_mean']['value']:.6e})\n")
            report.append(f"- **Worst Max Deviation**: {worst_data['worst_max']['experiment']} ")
            report.append(f"(VAR {worst_data['worst_max']['var_idx']}, t={worst_data['worst_max']['timestep']:.4e}, ")
            report.append(f"value={worst_data['worst_max']['value']:.6e})\n")
        
        report.append("\n## Best Performers by Branch\n")
        for exp_name, branches in branch_best.items():
            report.append(f"\n### Experiment: {exp_name}\n")
            for branch_name, best_data in branches.items():
                report.append(f"- **{branch_name}**: {best_data['run']} (score: {best_data['score']:.6e})\n")
        
        # Save markdown report
        report_file = output_dir / "error_analysis_summary.md"
        with open(report_file, 'w') as f:
            f.writelines(report)
        
        logger.success(f"Generated summary report at {report_file}")

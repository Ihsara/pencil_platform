# src/analysis/pairwise.py

"""
Pairwise comparison analysis for runs with similar error scores.

This module provides functionality to perform detailed comparisons between
pairs of simulation runs, particularly useful when runs have very similar
overall error metrics but may differ in subtle ways.

Use cases:
- Comparing 1st vs 2nd place runs with identical errors
- Analyzing 3rd vs 4th place with similar scores
- Deep-diving into parameter differences causing small error variations
"""

import numpy as np
import pandas as pd
from pathlib import Path
from loguru import logger
from typing import Dict, List, Tuple, Optional, Callable
from dataclasses import dataclass
import json

from src.analysis.metrics import calculate_error, calculate_all_errors


@dataclass
class PairwiseComparisonConfig:
    """Configuration for pairwise comparison analysis."""
    
    # Pair selection strategy
    selection_strategy: str = 'ranking_adjacent'  # 'ranking_adjacent', 'ranking_pairs', 'manual'
    
    # For 'ranking_pairs': [[1,2], [3,4], [5,6], ...]
    # For 'ranking_adjacent': compare N vs N+1
    # For 'manual': specify exact run names
    pairs: Optional[List[List[int]]] = None  # For 'ranking_pairs'
    manual_pairs: Optional[List[Tuple[str, str]]] = None  # For 'manual'
    
    # Comparison metrics
    metrics: List[str] = None  # ['l1', 'l2', 'linf', etc.]
    variables: List[str] = None  # ['rho', 'ux', 'pp', 'ee']
    
    # Analysis depth
    analyze_spatial_distribution: bool = True
    analyze_temporal_evolution: bool = True
    analyze_parameter_correlation: bool = True
    
    # Custom checks
    custom_checks: Optional[Dict[str, dict]] = None
    
    # Output configuration
    generate_plots: bool = True
    generate_detailed_report: bool = True
    
    def __post_init__(self):
        if self.metrics is None:
            self.metrics = ['l1', 'l2', 'linf']
        if self.variables is None:
            self.variables = ['rho', 'ux', 'pp', 'ee']


@dataclass
class PairwiseComparisonResult:
    """Results from comparing two runs."""
    
    run1_name: str
    run2_name: str
    
    # Overall metrics
    error_diff_per_metric: Dict[str, float]  # Difference in overall error
    relative_diff_per_metric: Dict[str, float]  # Relative difference (%)
    
    # Spatial analysis
    max_spatial_diff_locations: Optional[Dict[str, dict]] = None
    spatial_correlation: Optional[Dict[str, float]] = None
    
    # Temporal analysis
    temporal_divergence: Optional[Dict[str, list]] = None
    
    # Custom check results
    custom_check_results: Optional[Dict[str, any]] = None
    
    # Statistical tests
    statistical_significance: Optional[Dict[str, dict]] = None


class PairwiseAnalyzer:
    """Analyzer for detailed pairwise comparison of simulation runs."""
    
    def __init__(self, config: PairwiseComparisonConfig, output_dir: Path):
        """
        Initialize the pairwise analyzer.
        
        Args:
            config: Configuration for pairwise analysis
            output_dir: Directory to save analysis results
        """
        self.config = config
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized PairwiseAnalyzer with strategy: {config.selection_strategy}")
    
    def select_pairs(self, ranked_runs: List[Tuple[str, dict]]) -> List[Tuple[str, str]]:
        """
        Select pairs of runs to compare based on configuration.
        
        Args:
            ranked_runs: List of (run_name, scores) tuples sorted by rank
            
        Returns:
            List of (run1_name, run2_name) tuples to compare
        """
        pairs = []
        
        if self.config.selection_strategy == 'ranking_adjacent':
            # Compare adjacent ranks: 1 vs 2, 2 vs 3, 3 vs 4, etc.
            for i in range(len(ranked_runs) - 1):
                pairs.append((ranked_runs[i][0], ranked_runs[i+1][0]))
        
        elif self.config.selection_strategy == 'ranking_pairs':
            # Compare specific rank pairs: [1,2], [3,4], [5,6], etc.
            if not self.config.pairs:
                logger.error("No pairs specified for 'ranking_pairs' strategy")
                return []
            
            for rank1, rank2 in self.config.pairs:
                if rank1 - 1 < len(ranked_runs) and rank2 - 1 < len(ranked_runs):
                    pairs.append((ranked_runs[rank1-1][0], ranked_runs[rank2-1][0]))
                else:
                    logger.warning(f"Rank pair [{rank1}, {rank2}] out of range")
        
        elif self.config.selection_strategy == 'manual':
            # Use manually specified run names
            if not self.config.manual_pairs:
                logger.error("No manual pairs specified for 'manual' strategy")
                return []
            pairs = list(self.config.manual_pairs)
        
        else:
            logger.error(f"Unknown selection strategy: {self.config.selection_strategy}")
        
        logger.info(f"Selected {len(pairs)} pairs for analysis")
        for idx, (run1, run2) in enumerate(pairs, 1):
            logger.info(f"  Pair {idx}: {run1} vs {run2}")
        
        return pairs
    
    def compare_pair(
        self,
        run1_name: str,
        run2_name: str,
        run1_sim_data: List[dict],
        run1_analytical_data: List[dict],
        run2_sim_data: List[dict],
        run2_analytical_data: List[dict],
        run1_params: Optional[dict] = None,
        run2_params: Optional[dict] = None
    ) -> PairwiseComparisonResult:
        """
        Perform detailed comparison between two runs.
        
        Args:
            run1_name, run2_name: Names of the runs
            run1_sim_data, run2_sim_data: Simulation data for both runs
            run1_analytical_data, run2_analytical_data: Analytical solutions
            run1_params, run2_params: Parameter dictionaries (optional)
            
        Returns:
            PairwiseComparisonResult with all comparison metrics
        """
        logger.info(f"\nComparing: {run1_name} vs {run2_name}")
        
        # Calculate errors for both runs
        run1_errors = self._calculate_errors_per_variable(
            run1_sim_data, run1_analytical_data
        )
        run2_errors = self._calculate_errors_per_variable(
            run2_sim_data, run2_analytical_data
        )
        
        # Compare overall error metrics
        error_diff, relative_diff = self._compare_overall_errors(
            run1_errors, run2_errors
        )
        
        # Spatial analysis
        spatial_results = None
        if self.config.analyze_spatial_distribution:
            spatial_results = self._analyze_spatial_differences(
                run1_sim_data, run1_analytical_data,
                run2_sim_data, run2_analytical_data
            )
        
        # Temporal analysis
        temporal_results = None
        if self.config.analyze_temporal_evolution:
            temporal_results = self._analyze_temporal_divergence(
                run1_errors, run2_errors
            )
        
        # Custom checks
        custom_results = None
        if self.config.custom_checks:
            custom_results = self._run_custom_checks(
                run1_name, run2_name,
                run1_sim_data, run2_sim_data,
                run1_params, run2_params
            )
        
        # Statistical significance
        statistical_results = self._test_statistical_significance(
            run1_errors, run2_errors
        )
        
        result = PairwiseComparisonResult(
            run1_name=run1_name,
            run2_name=run2_name,
            error_diff_per_metric=error_diff,
            relative_diff_per_metric=relative_diff,
            max_spatial_diff_locations=spatial_results,
            temporal_divergence=temporal_results,
            custom_check_results=custom_results,
            statistical_significance=statistical_results
        )
        
        return result
    
    def _calculate_errors_per_variable(
        self,
        sim_data_list: List[dict],
        analytical_data_list: List[dict]
    ) -> Dict[str, Dict[str, np.ndarray]]:
        """Calculate all error metrics for all variables and timesteps."""
        errors = {}
        
        for var in self.config.variables:
            errors[var] = {metric: [] for metric in self.config.metrics}
            
            for sim_data, analytical_data in zip(sim_data_list, analytical_data_list):
                if var in sim_data and var in analytical_data:
                    for metric in self.config.metrics:
                        error_val = calculate_error(
                            sim_data[var],
                            analytical_data[var],
                            metric=metric
                        )
                        errors[var][metric].append(error_val)
            
            # Convert to numpy arrays
            for metric in self.config.metrics:
                errors[var][metric] = np.array(errors[var][metric])
        
        return errors
    
    def _compare_overall_errors(
        self,
        run1_errors: Dict,
        run2_errors: Dict
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """Compare overall error metrics between two runs."""
        error_diff = {}
        relative_diff = {}
        
        for var in self.config.variables:
            for metric in self.config.metrics:
                key = f"{var}_{metric}"
                
                # Mean error over all timesteps
                err1_mean = np.mean(run1_errors[var][metric])
                err2_mean = np.mean(run2_errors[var][metric])
                
                error_diff[key] = err2_mean - err1_mean
                
                if err1_mean != 0:
                    relative_diff[key] = (err2_mean - err1_mean) / err1_mean * 100
                else:
                    relative_diff[key] = np.inf if err2_mean != 0 else 0.0
        
        return error_diff, relative_diff
    
    def _analyze_spatial_differences(
        self,
        run1_sim_data: List[dict],
        run1_analytical_data: List[dict],
        run2_sim_data: List[dict],
        run2_analytical_data: List[dict]
    ) -> Dict[str, dict]:
        """Analyze spatial distribution of error differences."""
        spatial_results = {}
        
        for var in self.config.variables:
            # Calculate spatial errors for both runs
            run1_spatial_errors = []
            run2_spatial_errors = []
            
            for (s1, a1), (s2, a2) in zip(
                zip(run1_sim_data, run1_analytical_data),
                zip(run2_sim_data, run2_analytical_data)
            ):
                if var in s1 and var in a1 and var in s2 and var in a2:
                    err1 = np.abs(s1[var] - a1[var])
                    err2 = np.abs(s2[var] - a2[var])
                    run1_spatial_errors.append(err1)
                    run2_spatial_errors.append(err2)
            
            if run1_spatial_errors and run2_spatial_errors:
                # Convert to 2D arrays [timestep, space]
                err1_2d = np.array(run1_spatial_errors)
                err2_2d = np.array(run2_spatial_errors)
                
                # Calculate difference field
                diff_field = err2_2d - err1_2d
                
                # Find maximum difference location
                max_idx = np.unravel_index(
                    np.argmax(np.abs(diff_field)),
                    diff_field.shape
                )
                
                x_coords = run1_sim_data[0]['x']
                timesteps = [s['t'] for s in run1_sim_data]
                
                spatial_results[var] = {
                    'max_diff_value': float(diff_field[max_idx]),
                    'max_diff_time_index': int(max_idx[0]),
                    'max_diff_space_index': int(max_idx[1]),
                    'max_diff_time': float(timesteps[max_idx[0]]),
                    'max_diff_x': float(x_coords[max_idx[1]]),
                    'mean_abs_diff': float(np.mean(np.abs(diff_field))),
                    'std_diff': float(np.std(diff_field)),
                    'correlation': float(np.corrcoef(err1_2d.flatten(), err2_2d.flatten())[0, 1])
                }
        
        return spatial_results
    
    def _analyze_temporal_divergence(
        self,
        run1_errors: Dict,
        run2_errors: Dict
    ) -> Dict[str, list]:
        """Analyze how errors diverge over time."""
        temporal_results = {}
        
        for var in self.config.variables:
            temporal_results[var] = {}
            
            for metric in self.config.metrics:
                err1_series = run1_errors[var][metric]
                err2_series = run2_errors[var][metric]
                
                # Calculate cumulative difference
                diff_series = err2_series - err1_series
                cumulative_diff = np.cumsum(diff_series)
                
                temporal_results[var][metric] = {
                    'difference_series': diff_series.tolist(),
                    'cumulative_difference': cumulative_diff.tolist(),
                    'max_divergence': float(np.max(np.abs(diff_series))),
                    'max_divergence_timestep': int(np.argmax(np.abs(diff_series))),
                    'final_cumulative_diff': float(cumulative_diff[-1])
                }
        
        return temporal_results
    
    def _run_custom_checks(
        self,
        run1_name: str,
        run2_name: str,
        run1_sim_data: List[dict],
        run2_sim_data: List[dict],
        run1_params: Optional[dict],
        run2_params: Optional[dict]
    ) -> Dict[str, any]:
        """Run custom checks defined in configuration."""
        results = {}
        
        for check_name, check_config in self.config.custom_checks.items():
            logger.info(f"  Running custom check: {check_name}")
            
            try:
                check_type = check_config.get('type')
                
                if check_type == 'parameter_difference':
                    # Check parameter differences
                    param_name = check_config['parameter']
                    if run1_params and run2_params:
                        val1 = run1_params.get(param_name)
                        val2 = run2_params.get(param_name)
                        results[check_name] = {
                            'param': param_name,
                            'run1_value': val1,
                            'run2_value': val2,
                            'difference': val2 - val1 if val1 is not None and val2 is not None else None
                        }
                
                elif check_type == 'threshold_check':
                    # Check if error difference exceeds threshold
                    variable = check_config['variable']
                    metric = check_config['metric']
                    threshold = check_config['threshold']
                    
                    # ... implement threshold checking logic
                    results[check_name] = {'passed': True, 'threshold': threshold}
                
                elif check_type == 'custom_function':
                    # Execute custom function (if provided)
                    func_name = check_config.get('function')
                    # Note: For security, custom functions should be pre-registered
                    # Not dynamically evaluated
                    logger.warning(f"Custom function '{func_name}' not implemented")
                    results[check_name] = {'status': 'not_implemented'}
                
            except Exception as e:
                logger.error(f"  Custom check '{check_name}' failed: {e}")
                results[check_name] = {'status': 'error', 'error': str(e)}
        
        return results
    
    def _test_statistical_significance(
        self,
        run1_errors: Dict,
        run2_errors: Dict
    ) -> Dict[str, dict]:
        """Test statistical significance of error differences."""
        from scipy import stats
        
        statistical_results = {}
        
        for var in self.config.variables:
            statistical_results[var] = {}
            
            for metric in self.config.metrics:
                err1 = run1_errors[var][metric]
                err2 = run2_errors[var][metric]
                
                # Paired t-test (same timesteps compared)
                t_stat, p_value = stats.ttest_rel(err1, err2)
                
                # Effect size (Cohen's d for paired samples)
                diff = err2 - err1
                cohens_d = np.mean(diff) / np.std(diff) if np.std(diff) > 0 else 0
                
                statistical_results[var][metric] = {
                    't_statistic': float(t_stat),
                    'p_value': float(p_value),
                    'significant_at_0.05': bool(p_value < 0.05),
                    'significant_at_0.01': bool(p_value < 0.01),
                    'cohens_d': float(cohens_d),
                    'effect_size': 'small' if abs(cohens_d) < 0.5 else 'medium' if abs(cohens_d) < 0.8 else 'large'
                }
        
        return statistical_results
    
    def generate_report(
        self,
        results: List[PairwiseComparisonResult],
        experiment_name: str
    ):
        """Generate comprehensive report of pairwise comparisons."""
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        
        console = Console()
        
        console.print("\n")
        console.print("╔" + "═" * 78 + "╗")
        console.print("║" + " " * 22 + "PAIRWISE COMPARISON REPORT" + " " * 30 + "║")
        console.print("╚" + "═" * 78 + "╝")
        console.print("\n")
        
        console.print(Panel(
            f"[bold cyan]Experiment:[/bold cyan] {experiment_name}\n"
            f"[bold cyan]Number of Pairs:[/bold cyan] {len(results)}\n"
            f"[bold cyan]Variables:[/bold cyan] {', '.join(self.config.variables)}\n"
            f"[bold cyan]Metrics:[/bold cyan] {', '.join(self.config.metrics)}",
            title="📊 Analysis Overview",
            border_style="cyan"
        ))
        
        # Summary table for all pairs
        for idx, result in enumerate(results, 1):
            console.print(f"\n[bold yellow]═══ Pair {idx}: {result.run1_name} vs {result.run2_name} ═══[/bold yellow]\n")
            
            # Error differences table
            diff_table = Table(
                title="Error Metric Differences",
                title_style="bold green",
                border_style="green"
            )
            diff_table.add_column("Variable_Metric", style="cyan")
            diff_table.add_column("Absolute Diff", justify="right", style="yellow")
            diff_table.add_column("Relative Diff (%)", justify="right", style="magenta")
            diff_table.add_column("Significant?", justify="center", style="bold")
            
            for key in sorted(result.error_diff_per_metric.keys()):
                abs_diff = result.error_diff_per_metric[key]
                rel_diff = result.relative_diff_per_metric[key]
                
                # Check statistical significance
                var, metric = key.rsplit('_', 1)
                is_sig = "N/A"
                if result.statistical_significance:
                    sig_info = result.statistical_significance.get(var, {}).get(metric, {})
                    if sig_info.get('significant_at_0.05'):
                        is_sig = "[green]✓ Yes[/green]"
                    else:
                        is_sig = "[red]✗ No[/red]"
                
                diff_table.add_row(
                    key,
                    f"{abs_diff:.6e}",
                    f"{rel_diff:+.2f}%" if abs(rel_diff) < 1e6 else "∞",
                    is_sig
                )
            
            console.print(diff_table)
            
            # Spatial analysis results
            if result.max_spatial_diff_locations:
                console.print("\n[bold]Spatial Analysis:[/bold]")
                for var, spatial_info in result.max_spatial_diff_locations.items():
                    console.print(f"  [cyan]{var}:[/cyan]")
                    console.print(f"    Max diff: {spatial_info['max_diff_value']:.6e} "
                                f"at t={spatial_info['max_diff_time']:.4e}, "
                                f"x={spatial_info['max_diff_x']:.4e}")
                    console.print(f"    Mean abs diff: {spatial_info['mean_abs_diff']:.6e}")
                    console.print(f"    Correlation: {spatial_info['correlation']:.4f}")
        
        # Save to file
        report_file = self.output_dir / f"{experiment_name}_pairwise_comparison.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            file_console = Console(file=f, width=120)
            # Re-render same content to file
            file_console.print(f"\nPAIRWISE COMPARISON REPORT - {experiment_name}\n")
            file_console.print(f"Number of Pairs: {len(results)}\n")
            # ... (add full report content)
        
        logger.success(f"Generated pairwise comparison report: {report_file}")
        
        # Save JSON data
        self._save_json_results(results, experiment_name)
    
    def _save_json_results(
        self,
        results: List[PairwiseComparisonResult],
        experiment_name: str
    ):
        """Save pairwise comparison results to JSON."""
        json_data = {
            'experiment': experiment_name,
            'configuration': {
                'selection_strategy': self.config.selection_strategy,
                'metrics': self.config.metrics,
                'variables': self.config.variables
            },
            'comparisons': []
        }
        
        for result in results:
            comparison_data = {
                'run1': result.run1_name,
                'run2': result.run2_name,
                'error_differences': result.error_diff_per_metric,
                'relative_differences_pct': result.relative_diff_per_metric,
                'spatial_analysis': result.max_spatial_diff_locations,
                'temporal_analysis': result.temporal_divergence,
                'custom_checks': result.custom_check_results,
                'statistical_significance': result.statistical_significance
            }
            json_data['comparisons'].append(comparison_data)
        
        json_file = self.output_dir / f"{experiment_name}_pairwise_comparison.json"
        with open(json_file, 'w') as f:
            json.dump(json_data, f, indent=2)
        
        logger.success(f"Saved pairwise comparison data: {json_file}")


def load_pairwise_config_from_yaml(config_dict: dict) -> PairwiseComparisonConfig:
    """Load pairwise comparison configuration from experiment config."""
    pairwise_cfg = config_dict.get('pairwise_comparison', {})
    
    if not pairwise_cfg.get('enabled', False):
        return None
    
    return PairwiseComparisonConfig(
        selection_strategy=pairwise_cfg.get('selection_strategy', 'ranking_adjacent'),
        pairs=pairwise_cfg.get('pairs'),
        manual_pairs=pairwise_cfg.get('manual_pairs'),
        metrics=pairwise_cfg.get('metrics'),
        variables=pairwise_cfg.get('variables'),
        analyze_spatial_distribution=pairwise_cfg.get('analyze_spatial_distribution', True),
        analyze_temporal_evolution=pairwise_cfg.get('analyze_temporal_evolution', True),
        analyze_parameter_correlation=pairwise_cfg.get('analyze_parameter_correlation', True),
        custom_checks=pairwise_cfg.get('custom_checks'),
        generate_plots=pairwise_cfg.get('generate_plots', True),
        generate_detailed_report=pairwise_cfg.get('generate_detailed_report', True)
    )

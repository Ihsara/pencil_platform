"""
Jupyter-Friendly Interface for "Mind the Gap" Visualization

This module provides easy-to-use functions for creating spacetime error visualizations
directly from Jupyter notebooks, with automatic data caching and reuse capabilities.

Quick Start:
    from notebooks.mind_the_gap_jupyter import MindTheGapVisualizer
    
    viz = MindTheGapVisualizer('shocktube_phase1')
    viz.show_available_runs()
    fig = viz.plot('run_001', variable='rho')
    fig.show()
"""

import numpy as np
import plotly.graph_objects as go
from pathlib import Path
import sys
import json
from typing import Optional, List, Dict
from loguru import logger

# Add project root to path
try:
    PROJECT_ROOT = Path(__file__).parent.parent
except NameError:
    PROJECT_ROOT = Path.cwd()
    if PROJECT_ROOT.name == 'notebooks':
        PROJECT_ROOT = PROJECT_ROOT.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.constants import DIRS
from src.analysis.data_prep import load_spacetime_data_from_json, prepare_spacetime_error_data
from notebooks.spacetime_error_visualization import create_mind_the_gap_plot, create_multi_variable_dashboard


class MindTheGapVisualizer:
    """
    Jupyter-friendly visualizer for spacetime error analysis.
    
    Features:
    - Automatic data availability checking
    - Data caching and reuse
    - Simple dropdown-style interface
    - Interactive Plotly visualizations
    
    Example:
        >>> viz = MindTheGapVisualizer('shocktube_phase1')
        >>> viz.show_available_runs()
        >>> fig = viz.plot('run_001')
        >>> fig.show()
    """
    
    def __init__(self, experiment_name: str):
        """
        Initialize visualizer for an experiment.
        
        Args:
            experiment_name: Name of the experiment (e.g., 'shocktube_phase1')
        """
        self.experiment_name = experiment_name
        self.analysis_dir = DIRS.root / "analysis" / experiment_name
        self.mind_gap_dir = self.analysis_dir / "error" / "mind_the_gap"
        
        # Check if experiment exists
        config_dir = DIRS.config / experiment_name
        if not config_dir.exists():
            raise ValueError(f"Experiment '{experiment_name}' not found in config directory")
        
        logger.info(f"Initialized visualizer for experiment: {experiment_name}")
    
    def get_available_runs(self) -> List[str]:
        """
        Get list of all runs in the experiment.
        
        Returns:
            List of run names
        """
        manifest_file = DIRS.runs / self.experiment_name / "run_manifest.txt"
        
        if not manifest_file.exists():
            logger.warning(f"Manifest file not found: {manifest_file}")
            return []
        
        with open(manifest_file, 'r') as f:
            run_names = [line.strip() for line in f if line.strip()]
        
        return run_names
    
    def show_available_runs(self, show_data_status: bool = True):
        """
        Display available runs with data availability status.
        
        Args:
            show_data_status: If True, show whether data is cached for each run
        """
        runs = self.get_available_runs()
        
        if not runs:
            print(f"No runs found for experiment '{self.experiment_name}'")
            return
        
        print(f"\n{'='*70}")
        print(f"Available runs for '{self.experiment_name}': {len(runs)} total")
        print(f"{'='*70}\n")
        
        if show_data_status:
            for idx, run_name in enumerate(runs, 1):
                data_status = self._check_data_availability(run_name)
                status_icon = "✓" if data_status['available'] else "✗"
                status_color = "\033[92m" if data_status['available'] else "\033[91m"
                reset_color = "\033[0m"
                
                print(f"{idx:3d}. {status_color}[{status_icon}]{reset_color} {run_name}")
                
                if data_status['available']:
                    vars_available = ", ".join(data_status['variables'])
                    print(f"      └─ Data cached: {vars_available}")
        else:
            for idx, run_name in enumerate(runs, 1):
                print(f"{idx:3d}. {run_name}")
        
        print(f"\n{'='*70}")
        print(f"Total: {len(runs)} runs")
        
        # Show summary
        if show_data_status:
            available_count = sum(1 for run in runs if self._check_data_availability(run)['available'])
            print(f"Data cached: {available_count}/{len(runs)} runs")
            
            if available_count < len(runs):
                print(f"\n💡 Tip: Run analysis to cache data for missing runs:")
                print(f"   python main.py --experiment {self.experiment_name} --analyze")
        
        print(f"{'='*70}\n")
    
    def _check_data_availability(self, run_name: str) -> Dict:
        """
        Check if spacetime data is available for a run.
        
        Args:
            run_name: Name of the run
            
        Returns:
            Dictionary with availability status and details
        """
        run_dir = self.mind_gap_dir / run_name
        
        if not run_dir.exists():
            return {'available': False, 'variables': []}
        
        # Check for JSON files
        variables = []
        for var in ['rho', 'ux', 'pp', 'ee']:
            json_file = run_dir / f"{run_name}_{var}_spacetime_data.json"
            if json_file.exists():
                variables.append(var)
        
        return {
            'available': len(variables) > 0,
            'variables': variables,
            'path': run_dir
        }
    
    def check_data(self, run_name: str) -> bool:
        """
        Check if data is available for a specific run.
        
        Args:
            run_name: Name of the run
            
        Returns:
            True if data is available, False otherwise
        """
        status = self._check_data_availability(run_name)
        
        if status['available']:
            print(f"✓ Data is available for '{run_name}'")
            print(f"  Variables: {', '.join(status['variables'])}")
            print(f"  Location: {status['path']}")
            return True
        else:
            print(f"✗ Data is NOT available for '{run_name}'")
            print(f"\n💡 To generate data, run:")
            print(f"   python main.py --experiment {self.experiment_name} --analyze")
            print(f"\n   Or use: viz.analyze_and_cache()")
            return False
    
    def plot(self, run_name: str, variable: str = 'rho', 
             auto_analyze: bool = False, **kwargs) -> Optional[go.Figure]:
        """
        Create "mind the gap" plot for a specific run and variable.
        
        Args:
            run_name: Name of the run to visualize
            variable: Variable to plot ('rho', 'ux', 'pp', 'ee')
            auto_analyze: If True, automatically run analysis if data not available
            **kwargs: Additional arguments passed to create_mind_the_gap_plot
            
        Returns:
            Plotly Figure object, or None if data not available
            
        Example:
            >>> fig = viz.plot('run_001', variable='rho')
            >>> fig.show()
        """
        # Check data availability
        status = self._check_data_availability(run_name)
        
        if not status['available']:
            print(f"✗ Data not available for '{run_name}'")
            
            if auto_analyze:
                print(f"🔄 Running analysis automatically...")
                success = self.analyze_and_cache([run_name])
                if not success:
                    return None
            else:
                print(f"\n💡 Options:")
                print(f"   1. Set auto_analyze=True: viz.plot('{run_name}', auto_analyze=True)")
                print(f"   2. Run: viz.analyze_and_cache(['{run_name}'])")
                print(f"   3. Run full analysis: python main.py --experiment {self.experiment_name} --analyze")
                return None
        
        # Check if variable is available
        if variable not in status['variables']:
            print(f"✗ Variable '{variable}' not available for '{run_name}'")
            print(f"  Available variables: {', '.join(status['variables'])}")
            return None
        
        # Load cached data
        json_file = status['path'] / f"{run_name}_{variable}_spacetime_data.json"
        
        try:
            prepared_data = load_spacetime_data_from_json(json_file)
            
            # Create plot
            fig = create_mind_the_gap_plot(
                prepared_data,
                title=f"Mind the Gap: {run_name}",
                **kwargs
            )
            
            print(f"✓ Created visualization for '{run_name}' - {variable.upper()}")
            return fig
            
        except Exception as e:
            logger.error(f"Failed to create plot: {e}")
            print(f"✗ Error creating plot: {e}")
            return None
    
    def dashboard(self, run_name: str, auto_analyze: bool = False, 
                  **kwargs) -> Optional[go.Figure]:
        """
        Create multi-variable dashboard for a run.
        
        Args:
            run_name: Name of the run to visualize
            auto_analyze: If True, automatically run analysis if data not available
            **kwargs: Additional arguments passed to create_multi_variable_dashboard
            
        Returns:
            Plotly Figure object with 2x2 subplot grid
            
        Example:
            >>> fig = viz.dashboard('run_001')
            >>> fig.show()
        """
        # Check data availability
        status = self._check_data_availability(run_name)
        
        if not status['available']:
            print(f"✗ Data not available for '{run_name}'")
            
            if auto_analyze:
                print(f"🔄 Running analysis automatically...")
                success = self.analyze_and_cache([run_name])
                if not success:
                    return None
            else:
                print(f"\n💡 Run: viz.analyze_and_cache(['{run_name}']) or set auto_analyze=True")
                return None
        
        # Load all variables
        run_data = {}
        for var in status['variables']:
            json_file = status['path'] / f"{run_name}_{var}_spacetime_data.json"
            try:
                data = load_spacetime_data_from_json(json_file)
                
                # Convert to format expected by dashboard
                run_data[var] = {
                    'x_coords': data['x_coords'],
                    'timesteps': data['timesteps'],
                    'relative_error_field': data['error_matrix'],
                    'max_error_location': data['max_error'] if data['max_error'] else {}
                }
            except Exception as e:
                logger.warning(f"Failed to load data for {var}: {e}")
        
        if not run_data:
            print(f"✗ No data could be loaded for '{run_name}'")
            return None
        
        # Create dashboard
        try:
            fig = create_multi_variable_dashboard(
                run_data,
                self.experiment_name,
                run_name,
                variables=list(run_data.keys()),
                **kwargs
            )
            
            print(f"✓ Created dashboard for '{run_name}'")
            return fig
            
        except Exception as e:
            logger.error(f"Failed to create dashboard: {e}")
            print(f"✗ Error creating dashboard: {e}")
            return None
    
    def analyze_and_cache(self, run_names: Optional[List[str]] = None) -> bool:
        """
        Run analysis to generate and cache spacetime data.
        
        This will run the full analysis pipeline for the specified runs.
        
        Args:
            run_names: List of run names to analyze, or None for all runs
            
        Returns:
            True if successful, False otherwise
            
        Example:
            >>> viz.analyze_and_cache(['run_001', 'run_002'])
            >>> viz.analyze_and_cache()  # All runs
        """
        import subprocess
        
        print(f"🔄 Running analysis for '{self.experiment_name}'...")
        
        if run_names:
            print(f"   Analyzing {len(run_names)} specific runs")
        else:
            print(f"   Analyzing all runs in experiment")
        
        # Run analysis command
        cmd = [sys.executable, "main.py", "--experiment", self.experiment_name, "--analyze"]
        
        print(f"\nCommand: {' '.join(cmd)}\n")
        print(f"{'='*70}")
        
        try:
            result = subprocess.run(cmd, cwd=DIRS.root, check=True, 
                                   capture_output=False, text=True)
            
            print(f"{'='*70}")
            print(f"✓ Analysis completed successfully!")
            print(f"  Data cached in: {self.mind_gap_dir}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"{'='*70}")
            print(f"✗ Analysis failed with error code {e.returncode}")
            return False
    
    def get_dropdown_widget(self):
        """
        Create an ipywidgets dropdown for run selection (requires ipywidgets).
        
        Returns:
            Dropdown widget
            
        Example:
            >>> dropdown = viz.get_dropdown_widget()
            >>> display(dropdown)
        """
        try:
            import ipywidgets as widgets
        except ImportError:
            print("⚠ ipywidgets not installed. Install with: pip install ipywidgets")
            return None
        
        runs = self.get_available_runs()
        
        dropdown = widgets.Dropdown(
            options=runs,
            description='Run:',
            disabled=False,
            style={'description_width': '100px'}
        )
        
        return dropdown
    
    def create_interactive_viewer(self):
        """
        Create an interactive viewer with dropdowns (requires ipywidgets).
        
        Example:
            >>> viz.create_interactive_viewer()
        """
        try:
            import ipywidgets as widgets
            from IPython.display import display
        except ImportError:
            print("⚠ ipywidgets not installed. Install with: pip install ipywidgets")
            return
        
        runs = self.get_available_runs()
        
        run_dropdown = widgets.Dropdown(
            options=runs,
            description='Run:',
            disabled=False,
            style={'description_width': '100px'}
        )
        
        var_dropdown = widgets.Dropdown(
            options=['rho', 'ux', 'pp', 'ee'],
            value='rho',
            description='Variable:',
            disabled=False,
            style={'description_width': '100px'}
        )
        
        plot_button = widgets.Button(
            description='Plot',
            button_style='success',
            icon='chart-line'
        )
        
        dashboard_button = widgets.Button(
            description='Dashboard',
            button_style='info',
            icon='th'
        )
        
        output = widgets.Output()
        
        def on_plot_clicked(b):
            with output:
                output.clear_output()
                fig = self.plot(run_dropdown.value, var_dropdown.value, auto_analyze=False)
                if fig:
                    fig.show()
        
        def on_dashboard_clicked(b):
            with output:
                output.clear_output()
                fig = self.dashboard(run_dropdown.value, auto_analyze=False)
                if fig:
                    fig.show()
        
        plot_button.on_click(on_plot_clicked)
        dashboard_button.on_click(on_dashboard_clicked)
        
        controls = widgets.HBox([run_dropdown, var_dropdown, plot_button, dashboard_button])
        
        display(widgets.VBox([controls, output]))
        
        print(f"Interactive viewer created for '{self.experiment_name}'")
        print(f"Select a run and variable, then click 'Plot' or 'Dashboard'")


# Convenience function for quick access
def quick_plot(experiment_name: str, run_name: str, variable: str = 'rho', 
               auto_analyze: bool = True) -> Optional[go.Figure]:
    """
    Quick one-liner to create a plot.
    
    Args:
        experiment_name: Name of the experiment
        run_name: Name of the run
        variable: Variable to plot
        auto_analyze: If True, run analysis if data not available
        
    Returns:
        Plotly Figure object
        
    Example:
        >>> from notebooks.mind_the_gap_jupyter import quick_plot
        >>> fig = quick_plot('shocktube_phase1', 'run_001', 'rho')
        >>> fig.show()
    """
    viz = MindTheGapVisualizer(experiment_name)
    return viz.plot(run_name, variable, auto_analyze=auto_analyze)


def quick_dashboard(experiment_name: str, run_name: str, 
                    auto_analyze: bool = True) -> Optional[go.Figure]:
    """
    Quick one-liner to create a dashboard.
    
    Args:
        experiment_name: Name of the experiment
        run_name: Name of the run
        auto_analyze: If True, run analysis if data not available
        
    Returns:
        Plotly Figure object with dashboard
        
    Example:
        >>> from notebooks.mind_the_gap_jupyter import quick_dashboard
        >>> fig = quick_dashboard('shocktube_phase1', 'run_001')
        >>> fig.show()
    """
    viz = MindTheGapVisualizer(experiment_name)
    return viz.dashboard(run_name, auto_analyze=auto_analyze)

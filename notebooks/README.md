# Notebooks Directory

This directory contains interactive visualization notebooks for advanced error analysis.

## Available Notebooks

### spacetime_error_visualization.py

An interactive "Mind the Gap" visualization using Plotly that shows error evolution across space and time. This replaces the static spacetime heatmaps that were previously generated in the pipeline.

#### Features

- **Interactive Scatter Plot**: Error at each grid point and timestep represented by marker size
- **Animation**: Play button to animate through timesteps
- **Color Coding**: Plasma colorscale for error magnitude
- **Max Error Highlighting**: Red star marks the maximum error location
- **Multi-Variable Dashboard**: View all 4 variables (ρ, uₓ, p, e) simultaneously
- **Statistics Panel**: Real-time statistics display

#### Command-Line Usage

Run for a single variable:
```bash
python notebooks/spacetime_error_visualization.py \
    --experiment shocktube_phase1 \
    --run <run_name> \
    --variable rho \
    --output analysis/shocktube_phase1/spacetime_viz.html
```

Run dashboard with all variables:
```bash
python notebooks/spacetime_error_visualization.py \
    --experiment shocktube_phase1 \
    --run <run_name> \
    --dashboard \
    --output analysis/shocktube_phase1/spacetime_dashboard.html
```

Display in browser (no save):
```bash
python notebooks/spacetime_error_visualization.py \
    --experiment shocktube_phase1 \
    --run <run_name>
```

#### Parameters

- `--experiment`: Name of the experiment (required)
- `--run`: Name of the simulation run (required)
- `--variable`: Variable to visualize: 'rho', 'ux', 'pp', 'ee' (default: 'rho')
- `--dashboard`: Create multi-variable dashboard instead of single variable plot
- `--output`: Path to save HTML file (optional, shows in browser if not provided)

#### Interactive Features

1. **Play/Pause**: Use the play button to animate through timesteps
2. **Slider**: Manually scrub through timesteps
3. **Hover**: Hover over points to see detailed information (x, t, error value)
4. **Zoom**: Use mouse to zoom into regions of interest
5. **Pan**: Click and drag to pan around the plot

#### Data Source

The visualization automatically loads VAR files and computes analytical solutions. The normalized error data is calculated on-the-fly using the same functions as the main pipeline.

## Data Preparation

The `src/analysis/data_prep.py` module provides utilities for preparing error data for visualization:

```python
from src.analysis.data_prep import prepare_spacetime_error_data

# Prepare data for visualization
prepared_data = prepare_spacetime_error_data(
    normalized_errors,
    variable='rho',
    unit_length=1.0,
    use_relative=True
)
```

## Integration with Pipeline

The main analysis pipeline (`src/workflows/analysis_pipeline.py`) now calculates and caches normalized spatial-temporal errors but **does not** generate static heatmaps. Instead, errors are cached for notebook usage:

```python
# In analysis_pipeline.py
normalized_errors = calculate_normalized_spatial_errors(
    all_sim_data,
    all_analytical_data,
    variables=['rho', 'ux', 'pp', 'ee']
)

# Cached for notebook access
loaded_data_cache[run_name]['normalized_errors'] = normalized_errors
```

## Requirements

The notebooks require the following additional packages beyond the main platform requirements:

- `plotly`: Interactive plotting library
- `numpy`: Numerical computations (already in platform)

Install Plotly if not already available:
```bash
pip install plotly
```

Or with uv:
```bash
uv pip install plotly
```

## Tips

1. **Performance**: For runs with many timesteps (>50), the animation may be slow. Consider reducing timesteps or using the dashboard view.

2. **Large Files**: The HTML output can be large (10-50 MB) for runs with many grid points and timesteps. Consider compressing before sharing.

3. **Custom Analysis**: Import the functions directly in your own scripts:
   ```python
   from notebooks.spacetime_error_visualization import create_mind_the_gap_plot
   ```

4. **Export Options**: The generated HTML files are standalone and can be shared/opened in any browser without requiring Python or Plotly installation.

## Jupyter-Friendly Interface

### mind_the_gap_jupyter.py

A Jupyter-friendly Python module that provides easy-to-use functions for creating "Mind the Gap" visualizations directly from Jupyter notebooks, with automatic data caching and reuse.

#### Quick Start

```python
from notebooks.mind_the_gap_jupyter import MindTheGapVisualizer

# Initialize visualizer
viz = MindTheGapVisualizer('shocktube_phase1')

# Check available runs and data status
viz.show_available_runs()

# Create plot
fig = viz.plot('run_001', variable='rho')
fig.show()

# Create dashboard with all variables
fig = viz.dashboard('run_001')
fig.show()
```

#### Key Features

- **Automatic Data Caching**: Analysis results are saved as JSON and reused
- **Data Availability Checking**: Know which runs have cached data
- **Auto-analyze Option**: Automatically run analysis if data is missing
- **Interactive Widgets**: Optional ipywidgets dropdown interface
- **Quick Access Functions**: One-liner convenience functions

#### Example Notebook

See `mind_the_gap_example.ipynb` for a complete interactive tutorial.

#### API Reference

**MindTheGapVisualizer Class:**

- `show_available_runs()` - Display all runs with data availability status
- `check_data(run_name)` - Check if data is available for a specific run
- `plot(run_name, variable, auto_analyze=False)` - Create single-variable plot
- `dashboard(run_name, auto_analyze=False)` - Create multi-variable dashboard
- `analyze_and_cache(run_names=None)` - Run analysis to generate cached data
- `create_interactive_viewer()` - Create interactive widget interface (requires ipywidgets)

**Quick Access Functions:**

```python
from notebooks.mind_the_gap_jupyter import quick_plot, quick_dashboard

# One-liner to plot (auto-analyze enabled by default)
fig = quick_plot('shocktube_phase1', 'run_001', 'rho')
fig.show()

# One-liner for dashboard
fig = quick_dashboard('shocktube_phase1', 'run_001')
fig.show()
```

#### Data Caching

When you run analysis with `--analyze` flag, spacetime data is automatically cached as JSON files:

```
analysis/<experiment>/error/mind_the_gap/<run_name>/<run_name>_<variable>_spacetime_data.json
```

These JSON files contain pre-computed spacetime error data that can be quickly loaded for visualization without re-running the full analysis.

#### Workflow

1. **Run Analysis Once**: `python main.py --experiment shocktube_phase1 --analyze`
2. **Use in Jupyter**: Open `mind_the_gap_example.ipynb` and create visualizations
3. **Data is Reused**: No need to re-run analysis for subsequent visualizations

## Future Enhancements

Potential future additions:
- Comparison plots for multiple runs side-by-side
- Export to video format (MP4)
- Additional plot types (contour, surface, etc.)
- Statistical comparison tools
- Time-series analysis of error evolution

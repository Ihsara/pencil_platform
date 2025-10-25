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

## Future Enhancements

Potential future additions:
- Jupyter notebook (.ipynb) version for interactive exploration
- Comparison plots for multiple runs
- Export to video format (MP4)
- Additional plot types (contour, surface, etc.)

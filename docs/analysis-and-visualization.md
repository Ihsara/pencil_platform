# Analysis and Visualization Guide

This guide explains the comprehensive error analysis and visualization features for examining simulation results across all VAR files.

## Overview

The platform now supports two distinct post-processing modes:

1. **Visualization Mode (`--viz`)**: Quick visualization of specific VAR files from experiments
2. **Comprehensive Analysis Mode (`--analyze`)**: Deep error analysis across all VAR files with statistical comparisons

## Command Structure

### Basic Usage

```bash
# Visualization mode (formerly --analyze)
python main.py <experiment_name> --viz

# Comprehensive error analysis (new)
python main.py <experiment_name> --analyze

# Check job status
python main.py <experiment_name> --check
```

## Visualization Mode (`--viz`)

Generates comparison plots for simulation vs analytical solutions using selected VAR files.

### Usage Examples

```bash
# Visualize all runs (uses middle VAR file by default)
python main.py shocktube_phase1 --viz

# Visualize specific runs
python main.py shocktube_phase1 --viz run1 run2 run3

# Interactive mode - select runs interactively
python main.py shocktube_phase1 --viz ?

# Visualize with specific VAR file selection
python main.py shocktube_phase1 --viz --var random
python main.py shocktube_phase1 --viz --var last
python main.py shocktube_phase1 --viz --var VAR5
```

### VAR File Selection Options

The `--var` flag controls which VAR file to use for visualization:

- `middle` (default): Selects the VAR file in the middle of the sequence
- `random`: Randomly selects a VAR file
- `last`: Uses the final VAR file
- `first`: Uses the first VAR file
- `VAR<N>`: Specify exact VAR file (e.g., `VAR5`, `VAR10`)

### Output

Visualization mode creates the following in `reports/<experiment_name>/`:

- Individual plots for each variable (density, velocity, pressure, energy)
- Comparison summary table (MSE metrics)
- Quarto report template

## Comprehensive Analysis Mode (`--analyze`)

Performs deep error analysis across **all VAR files** for each run, generating:

1. Standard deviation calculations across timesteps
2. Absolute deviation metrics per VAR file
3. Experiment-wide comparisons
4. Branch comparisons
5. Best performer identification
6. **Enhanced VAR evolution collages with clear VAR file counting**
7. **Animated videos showing VAR evolution over time** (NEW)
8. **Animated videos showing error evolution with point tracking** (NEW)

### Usage

```bash
# Run comprehensive analysis on an experiment
python main.py shocktube_phase1 --analyze
```

### What Gets Analyzed

The analysis processes:

- **All VAR files** from each simulation run
- **All runs** in the experiment
- **All branches** defined in the sweep configuration

For each variable (ρ, u_x, p, e), it calculates:

- Standard deviation between numerical and analytical solutions
- Mean, max, min, and std of standard deviations
- Absolute deviations per timestep
- Worst performing VAR files

### Output Structure

All analysis results are saved to `analysis/<experiment_name>/`:

```
analysis/
└── shocktube_phase1/
    ├── shocktube_phase1_error_analysis.json    # Intermediate data
    ├── error_analysis_summary.md                # Summary report
    ├── individual/                              # Individual run plots
    │   ├── run1_std_evolution.png
    │   ├── run2_std_evolution.png
    │   └── ...
    ├── branch_comparison/                       # Branch-level comparisons
    │   ├── shocktube_phase1_branch_comparison_rho.png
    │   ├── shocktube_phase1_branch_comparison_ux.png
    │   ├── shocktube_phase1_branch_comparison_pp.png
    │   └── shocktube_phase1_branch_comparison_ee.png
    ├── best_performers/                         # Best performers comparison
    │   └── best_performers_comparison.png
    ├── var_evolution/                           # VAR evolution collages (ENHANCED)
    │   ├── individual/                          # Individual run collages
    │   │   ├── run1_var_evolution_collage.png  # Now shows "N VAR files" clearly
    │   │   └── ...
    │   ├── branch/                              # Branch-level collages
    │   │   ├── exp_branch1_rho_evolution.png
    │   │   └── ...
    │   └── best_performers/                     # Best performers collages
    │       ├── best_performers_rho_evolution.png
    │       ├── best_performers_ux_evolution.png
    │       ├── best_performers_pp_evolution.png
    │       └── best_performers_ee_evolution.png
    └── videos/                                  # NEW: Animated videos
        ├── var_evolution/                       # VAR evolution videos
        │   ├── run1_var_evolution.mp4          # Shows evolution across all VAR files
        │   ├── run1_frames/                    # Individual frames (if ffmpeg unavailable)
        │   └── ...
        └── error_evolution/                     # Error evolution videos
            ├── run1_error_evolution.mp4        # Shows error with mean/max/min tracking
            ├── run1_error_frames/              # Individual frames (if ffmpeg unavailable)
            └── ...
```

### Understanding the Results

#### 1. Top Performers

The summary report lists the top 3 overall performing experiments based on mean standard deviation across all variables.

**Lower values are better** - indicating closer agreement with analytical solutions.

#### 2. Worst Deviations

For each variable, identifies:
- Which experiment/run has the worst mean deviation
- Which specific VAR file (timestep) shows the worst error
- The magnitude of that error

This helps identify problematic regions in parameter space.

#### 3. Branch Comparison

Compares all runs within each branch to identify:
- Most robust configurations within a branch
- Parameter sensitivity within branches
- Branch-level performance patterns

#### 4. Best Performers by Branch

For each branch, identifies the best performing run and compares these across branches to:
- Determine scientifically significant differences between branches
- Identify optimal branch configurations
- Guide future parameter selection

#### 5. VAR Evolution Collages (ENHANCED)

Visual representations showing how each variable evolves across all timesteps:

- **Individual collages**: Show how a single run evolves over time
  - **NEW**: Title clearly states "N VAR files" analyzed
  - **NEW**: Shows exactly 2 analytical solutions (initial & final) to avoid confusion
  - **NEW**: Selective VAR file labeling (~8 labels) with file names and timesteps
  - **FIX**: Previous versions showed misleading label counts
- **Branch collages**: Compare evolution across different runs in the same branch  
- **Best performer collages**: Compare evolution of the best run from each branch

These help identify:
- Convergence behavior
- Stability issues  
- Temporal error growth
- **NEW**: Exact VAR file count being analyzed

#### 6. Animated Evolution Videos (NEW)

Two types of videos are automatically generated for each run:

**VAR Evolution Videos** (`videos/var_evolution/*.mp4`):
- Animates all 4 variables (ρ, u_x, p, e) frame-by-frame through all VAR files
- Each frame shows numerical (blue) vs analytical (red dashed) solution
- Title displays progress: "VAR N/Total"
- Each subplot annotated with VAR file name and timestamp
- Default: 2 fps, adjustable
- Requires ffmpeg (falls back to individual PNG frames if unavailable)

**Error Evolution Videos** (`videos/error_evolution/*.mp4`):
- Animates standard deviation evolution for all 4 variables
- **Point-to-point tracking** shows error progression through VAR files
- **Real-time statistics** with visual markers:
  - 🔴 **Current VAR** (red circle): Error at current timestep
  - 🟢 **Mean** (green square): Running mean error  
  - 🟠 **Max** (orange triangle): Peak error with VAR index
  - 🔵 **Min** (blue triangle): Lowest error with VAR index
- Text box shows numerical values for current/mean/max/min
- **Identifies problematic VAR files** where errors spike
- Default: 2 fps, adjustable
- Requires ffmpeg (falls back to individual PNG frames if unavailable)

**Why Videos?**
- See temporal evolution patterns at a glance
- Identify problematic timesteps quickly
- Great for presentations and sharing results
- Review many VAR files without manual clicking

## Summary Report

The analysis generates `error_analysis_summary.md` containing:

```markdown
# Error Analysis Summary Report

## Top 3 Overall Performers
1. **experiment/branch/run1** - Mean Std Dev: 1.234e-05
2. **experiment/branch/run2** - Mean Std Dev: 1.456e-05
3. **experiment/branch/run3** - Mean Std Dev: 1.678e-05

## Worst Deviations by Variable

### Variable: rho
- **Worst Mean Deviation**: exp/branch/run (VAR 42, t=1.23e-01, value=5.67e-04)
- **Worst Max Deviation**: exp/branch/run (VAR 38, t=1.10e-01, value=8.90e-04)

### Variable: ux
...

## Best Performers by Branch

### Experiment: shocktube_phase1
- **massfix_default_gamma**: run_nu0.1_chi0.1 (score: 1.234e-05)
- **massfix_gamma_is_1**: run_nu0.5_chi0.5 (score: 2.345e-05)
- **nomassfix**: run_nu1.0_chi1.0 (score: 3.456e-05)
```

This report is also logged to the console during analysis.

## Auto-Processing Flags

You can configure automatic post-processing reminders in `sweep.yaml`:

```yaml
# --- Post-Processing Automation (Optional) ---
auto_check: true               # Check job status after submission
auto_postprocessing: true      # Display post-processing reminders
```

When enabled:
- `auto_check`: Automatically runs `--check` after job submission
- `auto_postprocessing`: Displays reminders to run analysis after jobs complete

**Note**: These flags provide reminders only. Actual post-processing must be run manually after jobs complete, as the data needs to be generated first.

## Workflow Example

Complete workflow for running and analyzing an experiment:

```bash
# 1. Generate and submit experiment
python main.py shocktube_phase1

# 2. Check job status periodically
python main.py shocktube_phase1 --check

# 3. After jobs complete, run comprehensive analysis
python main.py shocktube_phase1 --analyze

# 4. Optionally, visualize specific runs
python main.py shocktube_phase1 --viz ? --var random
```

## Performance Considerations

### Visualization Mode
- Fast: Only loads one VAR file per run
- Suitable for quick checks
- Memory efficient

### Analysis Mode
- Intensive: Loads **all** VAR files from **all** runs
- May take significant time for large experiments
- Requires sufficient memory
- Recommended to run on HPC or powerful workstation

**Tip**: For very large experiments, consider:
1. Running analysis on a compute node
2. Processing branches separately
3. Using the intermediate JSON data for iterative analysis

## Interpreting Standard Deviation Plots (ENHANCED)

### Individual Experiment Plots

Shows how error evolves over time (across VAR files) with enhanced visual markers:

- **Blue line with points**: Per-VAR standard deviation evolution
- **Green dashed line**: Mean standard deviation across all VARs
- **Orange triangle** (🔺): Maximum error point with VAR index label
- **Blue triangle** (🔻): Minimum error point with VAR index label
- **Text box**: Statistical summary showing value ranges and std of std
- **X-axis**: "VAR File Index (0 to N-1)" - clearly labeled
- **Title**: Shows total number of VAR files analyzed

**Trends to look for**:
- Flat line: Consistent error throughout simulation
- Increasing trend: Error accumulation over time
- Spikes: Identify specific VAR files with issues (now labeled!)
- Max/min markers: Quickly see best and worst performing timesteps

### Branch Comparison Plots

Bar charts comparing mean standard deviation across runs:

- **Lower bars**: Better performance
- **Similar heights**: Robust to parameter variations
- **One outlier**: Specific parameter combination issue

### Best Performers Plot

Compares the champion from each branch:

- **Green bar**: Overall best performer
- **Height differences**: Scientific significance between branches
- **Similar heights**: Branches perform comparably

## Tips and Best Practices

1. **Start with visualization** (`--viz`) for quick sanity checks
2. **Run comprehensive analysis** (`--analyze`) for detailed investigation
3. **Use interactive mode** (`--viz ?`) to explore specific runs
4. **Check summary report first** before diving into individual plots
5. **Compare branch best performers** to guide methodology decisions
6. **Look for temporal trends** in evolution collages **and videos** 🎥
7. **Investigate worst deviations** to find parameter space boundaries
8. **Watch error evolution videos** to spot when/where errors spike
9. **Check VAR file counts** in titles to ensure all data was analyzed
10. **Use frame sequences** if ffmpeg is unavailable - can still create videos manually

## Troubleshooting

### "No VAR files found"
- Ensure simulations completed successfully
- Check HPC paths in sweep.yaml
- Verify data directory structure

### "Failed to load VAR file"
- Corrupted output files
- Insufficient disk space during simulation
- Check specific VAR file mentioned in error

### Analysis takes too long
- Reduce number of runs with `--viz specific_runs`
- Process one branch at a time
- Run on compute node with more resources
- **Video generation adds time but runs in parallel with collages**

### Out of memory
- Process smaller subsets of runs
- Use visualization mode instead
- Increase available RAM or use HPC

### Videos not generating
- **Install ffmpeg**: `conda install ffmpeg` or system package manager
- **Check ffmpeg**: Run `ffmpeg -version` to verify installation
- **Use frame sequences**: Even without ffmpeg, individual PNG frames are generated
- **Manual video creation**: Use provided ffmpeg command in logs to create videos from frames

### ffmpeg not found
- Platform automatically falls back to generating individual PNG frames
- Frames saved in `*_frames/` directories
- Console will show ffmpeg command to manually create videos
- Example: `ffmpeg -framerate 2 -i frames/frame_%04d.png -c:v libx264 -pix_fmt yuv420p output.mp4`

## Advanced Usage

### Programmatic Access

The error analysis can be accessed programmatically:

```python
from src.error_analysis import ExperimentErrorAnalyzer
from pathlib import Path

# Load existing analysis
analyzer = ExperimentErrorAnalyzer(Path("analysis/shocktube_phase1"))
analyzer.load_experiment_data("shocktube_phase1")

# Find top performers
top_3 = analyzer.find_top_performers(metric='mean_std', top_n=3)

# Get branch best performers
branch_best = analyzer.compare_branch_best_performers()

# Find worst deviations
worst = analyzer.find_worst_deviations()
```

This allows custom analysis and integration with other tools.

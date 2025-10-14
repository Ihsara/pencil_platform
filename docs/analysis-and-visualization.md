# Analysis and Visualization Guide

This guide covers the comprehensive analysis and visualization capabilities of the Pencil Code Automated Experiment Manager.

## Overview

The platform provides powerful post-processing tools to analyze simulation results, identify optimal parameters, and visualize error evolution. Two main analysis modes are available:

1. **Comprehensive Video Analysis** (`--analyze`): Creates error evolution videos, overlay comparisons, and calculates error norms
2. **Error Norms Analysis** (`--error-norms`): Focuses on L1/L2/L∞ error calculations without video generation

## Quick Start

```bash
# After simulations complete, run comprehensive analysis
python main.py shocktube_phase1 --analyze

# Or calculate error norms only
python main.py shocktube_phase1 --error-norms

# Automated workflow: submit, wait, then analyze
python main.py shocktube_phase1 --wait --analyze
```

## Comprehensive Video Analysis

### Command

```bash
python main.py <experiment_name> --analyze
```

### What It Does

The comprehensive analysis performs the following workflow:

**Phase 1: Individual Analysis**
- Loads all VAR files from each simulation run
- Calculates spatial errors against analytical solutions
- Creates individual error evolution videos for each run
- Generates video frames for detailed inspection

**Phase 2: Comparative Analysis**
- Identifies best performer in each branch
- Creates overlay comparison videos for branches
- Finds top 3 overall best performers
- Generates top 3 overlay comparison video

**Phase 3: Error Norm Calculations**
- Calculates L1, L2, and L∞ error norms
- Computes combined scores across all metrics
- Ranks runs by performance

**Phase 4: Visualization**
- Creates comparison plots for all runs
- Generates per-metric analysis charts
- Produces detailed views of top performers
- Creates branch comparison visualizations

**Phase 5: Organization and Reporting**
- Organizes results into structured folders
- Populates "best" folders with top performers
- Generates JSON and Markdown summary reports
- Displays comprehensive Rich terminal report

### Output Structure

```
analysis/<experiment_name>/
├── var/
│   ├── evolution/              # VAR evolution videos
│   │   ├── run_001.mp4
│   │   ├── run_002.mp4
│   │   └── ...
│   └── frames/                 # Video frames
│       ├── run_001/
│       └── ...
├── error/
│   ├── evolution/              # Error evolution videos
│   │   ├── run_001.mp4         # Individual runs
│   │   ├── run_002.mp4
│   │   ├── <exp>_<branch>_overlay.mp4  # Branch comparisons
│   │   └── <exp>_top3_best_performers_overlay.mp4
│   ├── frames/                 # Video frames
│   │   ├── run_001/
│   │   └── ...
│   └── best/                   # Best performers
│       ├── videos/             # Best performers' videos
│       ├── plots/              # Comparison plots
│       └── summary.json        # Performance summary
└── error_norms/                # Error norm analysis
    ├── plots/
    │   ├── combined_scores.png
    │   ├── per_metric_l1.png
    │   ├── per_metric_l2.png
    │   ├── per_metric_linf.png
    │   ├── top5_detailed.png
    │   ├── branch_comparison.png
    │   └── error_evolution_*.png
    ├── <experiment>_error_norms_summary.json
    └── <experiment>_error_norms_summary.md
```

### Error Metrics

Three error norms are calculated for each variable (ρ, u_x, p, e):

**L1 Norm (Mean Absolute Error)**
```
L1 = (1/N) Σ |numerical - analytical|
```
- Measures average absolute deviation
- Sensitive to all errors equally
- Good for overall error assessment

**L2 Norm (Root Mean Square Error)**
```
L2 = √[(1/N) Σ (numerical - analytical)²]
```
- Emphasizes larger errors
- Most commonly used metric
- Good for comparing solutions

**L∞ Norm (Maximum Absolute Error)**
```
L∞ = max |numerical - analytical|
```
- Captures worst-case error
- Important for stability analysis
- Identifies problematic regions

### Combined Scoring

The platform calculates a combined score to rank runs:

1. For each metric (L1, L2, L∞), calculate mean across all variables
2. Average all metric scores to get combined score
3. Lower score = better performance

This multi-metric approach ensures robust parameter identification.

### Video Features

**Individual Error Evolution Videos**
- Show all four variables (ρ, u_x, p, e) evolving over time
- Display both numerical and analytical solutions
- Include absolute error visualization
- Annotated with timestep and physical time

**Combined Error Videos**
- When configured, show L1, L2, and L∞ errors simultaneously
- Side-by-side comparison of different error types
- Helps understand error behavior across metrics

**Overlay Comparison Videos**
- Compare multiple runs on the same plot
- Useful for branch comparison
- Highlights performance differences
- Shows top performers together

### Configuration

Control analysis behavior in `sweep.yaml`:

```yaml
error_analysis:
  metrics: ['l1', 'l2', 'linf']    # Which metrics to calculate
  combine_in_videos: true          # Show all metrics in one video
```

## Error Norms Analysis Only

### Command

```bash
python main.py <experiment_name> --error-norms
```

### Purpose

This mode focuses exclusively on error norm calculations without video generation. Use it when:
- You only need numerical metrics
- Video generation is too time-consuming
- You want faster analysis turnaround
- Storage space is limited

### What It Does

1. Loads all VAR files from all runs
2. Calculates L1, L2, and L∞ error norms
3. Computes combined scores
4. Identifies best performers (overall and per branch)
5. Creates comparison plots only (no videos)
6. Generates summary reports

### Output

Results are saved to `analysis/<experiment_name>/error_norms/`:
- Comparison plots for all metrics
- Top 5 detailed performance analysis
- Branch comparison visualization
- Error evolution plots for top 3
- JSON and Markdown summary reports

## Understanding Results

### Best Performers

The analysis identifies best performers at multiple levels:

**Overall Best**
- Top 5 runs across entire experiment
- Ranked by combined score
- Displayed with individual metric scores

**Per Branch Best**
- Best run in each branch
- Useful for comparing branch strategies
- Shows branch-specific optimization

### Reading Summary Reports

**JSON Format** (`*_summary.json`)
```json
{
  "experiment": "shocktube_phase1",
  "metrics_used": ["l1", "l2", "linf"],
  "total_runs_analyzed": 18,
  "top_5_overall": [
    {
      "rank": 1,
      "run_name": "shocktube_phase1_nu_0.5_chi_1.0",
      "combined_score": 1.234e-03,
      "branch": "default",
      "per_metric_scores": {
        "l1": 1.1e-03,
        "l2": 1.3e-03,
        "linf": 1.3e-03
      }
    }
  ],
  "best_per_branch": {...},
  "detailed_scores": {...}
}
```

**Markdown Format** (`*_summary.md`)
- Human-readable report
- Top 5 overall performers with metrics
- Best performer per branch
- Easy to review and share

### Interpreting Plots

**Combined Scores Plot**
- Bar chart comparing all runs
- Lower bars = better performance
- Color-coded by branch
- Helps identify optimal parameters

**Per-Metric Plots**
- Separate plots for L1, L2, L∞
- Compare metric-specific performance
- May reveal trade-offs between metrics
- Identify metric-specific outliers

**Top 5 Detailed View**
- Radar/spider plot showing all metrics
- Visual comparison of top performers
- Highlights relative strengths
- Easy comparison of trade-offs

**Branch Comparison**
- Compare best run from each branch
- Evaluate branch strategies
- Identify most promising approach
- Support decision-making

**Error Evolution Plots**
- Show how errors change over time
- Identify convergence behavior
- Detect stability issues
- Compare temporal performance

## Advanced Usage

### Custom Error Calculation

The `error_method` parameter controls spatial error calculation:

```python
# In the code (for developers)
spatial_errors = calculate_spatial_errors(
    sim_data, 
    analytical_data, 
    error_method='absolute'  # or 'relative', 'difference', 'squared'
)
```

**Available methods:**
- `absolute`: |numerical - analytical|
- `relative`: |numerical - analytical| / |analytical|
- `difference`: numerical - analytical
- `squared`: (numerical - analytical)²

### Automated Analysis Workflow

```bash
# Submit jobs, wait for completion, then analyze automatically
python main.py my_experiment --wait --analyze
```

This is ideal for:
- Overnight runs
- Automated testing
- CI/CD pipelines
- Batch processing

### Selective Analysis

To analyze specific branches or runs, modify the manifest file:

```bash
# Create custom manifest with selected runs
cat > runs/my_experiment/manifest_custom.txt << EOF
run_001
run_005
run_010
EOF

# Then modify the analysis script to use custom manifest
```

## Performance Considerations

### Memory Requirements

Analysis loads all VAR files into memory:
- Each VAR file: ~10-100 MB (depends on resolution)
- Total memory needed: N_runs × N_vars × VAR_size
- For 20 runs with 50 VAR files each: ~10-100 GB

**Tips for large experiments:**
- Use `--error-norms` instead of `--analyze` to skip videos
- Analyze branches separately
- Use HPC nodes with sufficient RAM
- Consider downsampling VAR files

### Time Requirements

**Comprehensive Analysis** (`--analyze`):
- VAR loading: 1-5 minutes per run
- Video generation: 2-10 minutes per run
- Total: ~5-20 minutes per run
- For 20 runs: 2-7 hours

**Error Norms Only** (`--error-norms`):
- VAR loading: 1-5 minutes per run
- No video generation
- Total: ~1-5 minutes per run
- For 20 runs: 20 minutes - 2 hours

### Optimization Tips

1. **Use test mode first**: Verify with `--test 2 --analyze`
2. **Parallel processing**: Run analysis on HPC compute node
3. **Selective frames**: Modify FPS in video generation
4. **Batch analysis**: Analyze branches sequentially
5. **Storage**: Use fast storage for I/O-intensive operations

## Troubleshooting

### "No VAR files found"

**Problem**: Cannot find simulation output

**Solutions:**
```bash
# Check data directory path in sweep.yaml
cat config/my_experiment/plan/sweep.yaml | grep run_base_dir

# Verify files exist
ls /path/to/run_base_dir/run_001/data/

# Check proc0 directory
ls /path/to/run_base_dir/run_001/data/proc0/
```

### "Memory error during analysis"

**Problem**: Not enough RAM to load all VAR files

**Solutions:**
1. Use `--error-norms` (no video generation)
2. Analyze fewer runs at once
3. Request more memory on HPC
4. Downsample VAR files before analysis

### "Video generation fails"

**Problem**: FFmpeg not installed or configured

**Solutions:**
```bash
# Check FFmpeg installation
ffmpeg -version

# Install if missing
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
choco install ffmpeg
```

### "Analytical solution mismatch"

**Problem**: Parameters don't match expected values

**Solutions:**
- Verify problem type (shock tube, etc.)
- Check initial conditions in start_in.yaml
- Ensure correct gamma, cs0, rho0 values
- Review run_in.yaml for consistency

## Best Practices

1. **Test first**: Always use `--test` with analysis on small subset
2. **Check one run**: Manually verify one run before batch analysis
3. **Document parameters**: Keep notes on what parameters were tested
4. **Version results**: Use git to track experiment configurations
5. **Archive strategically**: Keep best performers, archive or delete others
6. **Review videos**: Watch videos to understand error behavior qualitatively
7. **Cross-validate**: Compare multiple metrics for robust conclusions
8. **Iterate**: Use results to inform next parameter sweep

## Examples

### Example 1: Quick Check

```bash
# Test analysis on first 2 runs
python main.py my_experiment --test 2
# ... wait for simulations ...
python main.py my_experiment --test 2 --analyze

# Review results
ls analysis/my_experiment/error/evolution/
```

### Example 2: Full Analysis

```bash
# Run full experiment
python main.py my_experiment

# After completion, comprehensive analysis
python main.py my_experiment --analyze

# Review summary
cat analysis/my_experiment/error_norms/*_summary.md

# Check best performer video
vlc analysis/my_experiment/error/best/videos/rank_1.mp4
```

### Example 3: Automated Workflow

```bash
# Complete automation: generate, submit, wait, analyze
python main.py my_experiment --wait --analyze

# Results will be ready when done
ls analysis/my_experiment/
```

### Example 4: Branch Comparison

```bash
# Run experiment with multiple branches
python main.py my_experiment_branches

# Analyze
python main.py my_experiment_branches --analyze

# Compare branch overlay videos
ls analysis/my_experiment_branches/error/evolution/*_overlay.mp4

# Review branch comparison plot
open analysis/my_experiment_branches/error_norms/plots/branch_comparison.png
```

## See Also

- [CLI Reference](cli-reference.md) - Complete command options
- [User Guide](user-guide/index.md) - General usage patterns
- [Troubleshooting](troubleshooting.md) - Common issues and solutions

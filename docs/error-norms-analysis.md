# L1/L2 Error Norm Analysis Guide

## Overview

The platform now includes a modular error calculation system with L1, L2, and L∞ error norms based on Gent et al. (2018) "Modelling supernova driven turbulence" for comprehensive shock tube analysis.

## Quick Start

### Run Comprehensive Analysis (Videos + Error Norms)
```bash
python main.py shocktube_phase1 --analyze
```

This single command performs:
1. ✅ Creates individual error evolution videos
2. ✅ Creates branch overlay videos
3. ✅ Creates top 3 performers overlay video
4. ✅ Calculates L1, L2, L∞ error norms for all runs
5. ✅ Generates combined scores to find best parameters
6. ✅ Creates comprehensive comparison visualizations
7. ✅ Generates final Rich summary report

### Run Standalone Error Norm Analysis
```bash
python main.py shocktube_phase1 --error-norms
```

This runs only the L1/L2 error norm analysis without videos.

## Error Metrics

### L1 Norm (Mean Absolute Error)
```
L1 = (1/N) * Σ|qi - q̃i|
```
- Measures average magnitude of errors
- Reference: Gent et al. (2018), Equation (23)
- Use case: Overall accuracy assessment

### L2 Norm (Root Mean Square Error)
```
L2 = sqrt((1/N) * Σ(qi - q̃i)²)
```
- Measures RMS deviation
- Gives more weight to larger errors
- Use case: Penalty for outliers

### L∞ Norm (Maximum Absolute Error)
```
L∞ = max|qi - q̃i|
```
- Measures worst-case error
- Use case: Robustness assessment

## Output Structure

```
analysis/
└── {experiment_name}/
    ├── videos/
    │   └── error_evolution/
    │       ├── {run}_error_evolution.gif          # Individual videos
    │       ├── {branch}_overlay_error_evolution.gif
    │       └── top3_best_performers_overlay_error_evolution.gif
    │
    └── error_norms/                                # NEW SUBFOLDER
        ├── plots/
        │   ├── {experiment}_combined_scores.png    # All runs ranked
        │   ├── {experiment}_l1_comparison.png      # L1 per variable
        │   ├── {experiment}_l2_comparison.png      # L2 per variable
        │   ├── {experiment}_linf_comparison.png    # L∞ per variable
        │   ├── {experiment}_top5_detailed.png      # Top 5 side-by-side
        │   ├── {experiment}_branch_best.png        # Branch comparison
        │   ├── {experiment}_top3_l1_evolution.png  # Time evolution
        │   ├── {experiment}_top3_l2_evolution.png
        │   └── {experiment}_top3_linf_evolution.png
        ├── {experiment}_error_norms_summary.json   # Machine-readable
        └── {experiment}_error_norms_summary.md     # Human-readable
```

## Combined Scoring

The combined score is calculated as:

1. For each metric (L1, L2, L∞):
   - Calculate mean error across all variables (ρ, ux, p, e)
   
2. Average all metric scores:
   - Combined Score = (L1_avg + L2_avg + L∞_avg) / 3

3. Rank runs by combined score (lower is better)

## Programmatic Usage

### Calculate Error Metrics
```python
from src.error_metrics import calculate_error, calculate_all_errors

# Single metric
l1_error = calculate_error(numerical, analytical, metric='l1')
l2_error = calculate_error(numerical, analytical, metric='l2')

# All metrics at once
errors = calculate_all_errors(numerical, analytical)
print(f"L1: {errors['l1']:.6e}")
print(f"L2: {errors['l2']:.6e}")
print(f"L∞: {errors['linf']:.6e}")
```

### Batch Processing
```python
from src.error_metrics import calculate_errors_over_time

# Calculate errors across multiple timesteps
errors_over_time = calculate_errors_over_time(
    sim_data_list, 
    analytical_data_list,
    metrics=['l1', 'l2', 'linf']
)

# Plot evolution
import matplotlib.pyplot as plt
plt.plot(errors_over_time['l1'], label='L1')
plt.plot(errors_over_time['l2'], label='L2')
plt.legend()
plt.show()
```

### Convergence Analysis
```python
from src.error_metrics import calculate_convergence_rate

# Errors at different resolutions
resolutions = [1/64, 1/128, 1/256, 1/512]
l1_errors = [0.01, 0.005, 0.0025, 0.00125]

# Calculate convergence rate
rate = calculate_convergence_rate(l1_errors, resolutions, metric_name='L1')
# Output: "Convergence rate for L1: 1.000 (error ∝ dx^1.000)"
```

### Add Custom Metrics
```python
from src.error_metrics import register_custom_metric

def weighted_l2_norm(numerical, analytical):
    """Custom weighted L2 norm."""
    weights = np.linspace(0.5, 1.5, len(numerical))
    return np.sqrt(np.mean(weights * (numerical - analytical)**2))

register_custom_metric(
    'weighted_l2', 
    weighted_l2_norm, 
    'Weighted L2 norm with position-dependent weights'
)

# Now use it
error = calculate_error(num, ana, metric='weighted_l2')
```

## Interpreting Results

### Final Rich Report
The comprehensive analysis generates a beautiful Rich-formatted report showing:

1. **Experiment Information**
   - Total runs analyzed
   - Error metrics used
   
2. **Top 5 Overall Performers**
   - Ranked by combined score
   - Includes branch and individual metric scores
   
3. **Per-Metric Scores (Top 3)**
   - Side-by-side comparison of L1, L2, L∞
   
4. **Best Performer per Branch**
   - Identifies optimal parameters within each branch
   
5. **Output Locations**
   - Direct links to all generated files
   
6. **Key Findings**
   - Best parameter set identified
   - Detailed scores for all metrics
   
7. **Recommendations**
   - Next steps for analysis
   - Suggestions for production use

### Reading the Plots

- **Combined Scores Plot**: Lower bars are better, top 3 have gold borders
- **Per-Metric Plots**: Green bar = best performer for that metric
- **Top 5 Detailed**: Compare how top performers rank across different metrics
- **Branch Comparison**: Gold bar = overall best across all branches
- **Error Evolution**: Check temporal stability of error metrics

## Best Practices

1. **Always run comprehensive analysis first** (`--analyze`)
   - Loads data once, performs all analyses
   - More efficient than running separately
   
2. **Use standalone mode** (`--error-norms`) only when:
   - Videos already exist
   - You want to re-run with different metrics
   - You're testing new custom metrics

3. **Interpret combined scores holistically**:
   - Consider all three metrics (L1, L2, L∞)
   - Check per-variable performance
   - Review temporal evolution

4. **Validate convergence**:
   - Run at multiple resolutions
   - Use `calculate_convergence_rate()`
   - Compare with theoretical rates

## References

- Gent, F.A. et al. (2018). "Modelling supernova driven turbulence." 
  *Geophysical and Astrophysical Fluid Dynamics.*
  - Equation (23): L1 error norm definition
  - Section 3: Convergence analysis methodology
  - Figure 7: Example convergence plots

## Examples

### Example 1: Simple L1/L2 Comparison
```python
from src.error_metrics import calculate_error

l1 = calculate_error(sim_rho, ana_rho, metric='l1')
l2 = calculate_error(sim_rho, ana_rho, metric='l2')

print(f"L1 (average error): {l1:.6e}")
print(f"L2 (RMS error): {l2:.6e}")
print(f"L2/L1 ratio: {l2/l1:.3f}")  # > 1 indicates outliers
```

### Example 2: Variable-Specific Analysis
```python
from src.error_analysis import calculate_error_norms

error_norms = calculate_error_norms(
    all_sim_data,
    all_analytical_data,
    metrics=['l1', 'l2']
)

# Access results
rho_l1_mean = error_norms['rho']['l1']['mean']
rho_l2_mean = error_norms['rho']['l2']['mean']
ux_l1_mean = error_norms['ux']['l1']['mean']

print(f"ρ - L1: {rho_l1_mean:.6e}, L2: {rho_l2_mean:.6e}")
print(f"ux - L1: {ux_l1_mean:.6e}")
```

### Example 3: Convergence Study
```python
from src.error_metrics import calculate_convergence_rate

# Run simulations at different resolutions
resolutions = [4, 2, 1, 0.5]  # pc
l1_errors = []

for res in resolutions:
    # ... run simulation ...
    error = calculate_error(sim_data, ana_data, metric='l1')
    l1_errors.append(error)

# Calculate convergence rate
rate = calculate_convergence_rate(l1_errors, resolutions)
print(f"Convergence rate: {rate:.3f}")
print(f"Expected for 1st order: ~1.0")
print(f"Expected for 2nd order: ~2.0")
```

## Troubleshooting

### Issue: High L∞ but low L1/L2
**Diagnosis**: Localized spike errors but overall good accuracy
**Action**: Check error evolution videos to identify spike locations

### Issue: All metrics similar magnitude
**Diagnosis**: Uniform error distribution (no outliers)
**Action**: Good! Indicates stable solution

### Issue: L2 >> L1
**Diagnosis**: Significant outliers present
**Action**: Review spatial error plots, consider increasing resolution

### Issue: Metrics don't improve with resolution
**Diagnosis**: May have hit accuracy limit or numerical instability
**Action**: Check artificial viscosity parameters, review shock handling

## CLI Reference

```bash
# Comprehensive analysis (recommended)
python main.py <experiment> --analyze

# Standalone error norms only
python main.py <experiment> --error-norms

# Test with sample data
python test_error_metrics.py
```

## See Also

- `src/error_metrics.py` - Core error metric implementations
- `src/error_analysis.py` - Analysis functions
- `docs/analysis-and-visualization.md` - General analysis guide

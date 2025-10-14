# Shocktube Phase 2 Configuration

## Overview
Phase 2 focuses on finding the optimal hyperdiffusion parameters (`nu_hyper3` and `chi_hyper3`) while keeping shock parameters fixed at their optimal values from Phase 1.

## Key Configuration

### Fixed Parameters (from Phase 1 results)
- `diffrho_shock = 1.0`
- `nu_shock = 1.0`
- `chi_shock = 1.0`
- `lgamma_is_1 = false` (F)

### Swept Parameters
The following hyperdiffusion parameters are swept together (linked sweep):
- `nu_hyper3 = chi_hyper3` ∈ [9e-15, 9e-14, 9e-13, 9e-12]

This creates 4 runs testing different hyperdiffusion strengths.

## Configuration Inheritance

The configuration follows this hierarchy:

```
shocktube_base (base configuration)
    ↓
shocktube_phase2/in/run_in.yaml (specific overrides)
    ↓
shocktube_phase2/plan/sweep.yaml (sweep modifications)
    ↓
Generated run configurations
```

### What Phase 2 Inherits from Base:
- Basic run parameters (timestep, boundary conditions, etc.)
- Shock detection parameters
- EOS and hydro parameters
- File I/O settings

### What Phase 2 Overrides:
- Fixed shock parameters (diffrho_shock, nu_shock, chi_shock = 1.0)
- Hyperdiffusion parameters (swept values)
- lgamma_is_1 = false

## Error Analysis Configuration

Phase 2 uses the same error analysis as Phase 1:
- **Error Metric**: L1 norm (mean absolute error)
- **Combine in Videos**: True (creates combined error evolution videos)
- **Analysis Output**: Same format as Phase 1

The `--analyze` command for phase2 will produce:
- Individual error evolution videos for each run
- Combined error evolution videos showing all metrics
- Error norm analysis with L1 metric
- Best performer identification
- Branch comparison plots

## Sweep Method

- **Type**: Linked sweep
- **Variables**: `[nu_hyper3, chi_hyper3]`
- **Values**: `[9.0e-15, 9.0e-14, 9.0e-13, 9.0e-12]`

This ensures `nu_hyper3` always equals `chi_hyper3`, testing 4 different hyperdiffusion strengths.

## Branch Configuration

- **Branch Name**: `gamma_default`
- **Settings**: `lgamma_is_1 = false` (non-isothermal case)

## Expected Output

Running this configuration will generate:
- 4 simulation runs (one for each hyperdiffusion value)
- Run names follow pattern: `res400_hyper3_nu{value}_chi{value}_gamma_default`

## Verification Checklist

✓ Inheritance from shocktube_base is correctly configured
✓ Shock parameters are fixed at 1.0 (diffrho_shock, nu_shock, chi_shock)
✓ lgamma_is_1 = false (F) as specified
✓ Hyperdiffusion parameters use linked sweep (nu_hyper3 = chi_hyper3)
✓ L1 error metric is configured for analysis
✓ Analysis output format matches Phase 1

# Base Experiments Guide

## Overview

The configuration system uses a hierarchical structure where experiments can inherit from a base experiment. This allows you to:
- Define common parameters once in a base experiment
- Create multiple derived experiments that override/add specific parameters
- Easily swap between different base configurations

## How It Works

### 1. Deep Merge Process

When you run an experiment (e.g., `shocktube_phase1`), the system:
1. Loads all config files from the **base experiment** (e.g., `shocktube_base`)
2. Loads config files from the **specific experiment** (e.g., `shocktube_phase1`)
3. **Deep merges** them: specific experiment overrides/adds to base parameters
4. Applies parameter sweeps and branch settings

### 2. Specifying the Base Experiment

In your experiment's plan file (`config/<experiment>/plan/sweep.yaml`), simply set:

```yaml
base_experiment: 'shocktube_base'
```

**That's it!** Change this single line to use a different base.

## Example: Creating a 3D Base

### Step 1: Create the 3D Base Directory

```
config/
└── shocktube_base_3D/
    ├── in/
    │   ├── run_in.yaml
    │   ├── start_in.yaml
    │   ├── cparam_local.yaml
    │   └── ... (other config files)
    └── plan/
        └── sweep.yaml (optional)
```

### Step 2: Define 3D-Specific Parameters

In `config/shocktube_base_3D/in/cparam_local.yaml`:
```yaml
format: makefile
data:
  MPICOMM: MPICOMM_WORLD
  nxgrid: 128
  nygrid: 128
  nzgrid: 128  # 3D grid!
  ncpus: 512
  nprocx: 8
  nprocy: 8
  nprocz: 8
```

In `config/shocktube_base_3D/in/start_in.yaml`:
```yaml
format: namelist
data:
  init_pars:
    lperi: [false, false, false]  # 3D boundaries
    xyz0: [-0.5, -0.5, -0.5]
    Lxyz: [1.0, 1.0, 1.0]
  # ... other 3D-specific parameters
```

### Step 3: Use the 3D Base in Phase1

In `config/shocktube_phase1/plan/sweep.yaml`:
```yaml
# Change this line:
base_experiment: 'shocktube_base_3D'

# Everything else stays the same!
# The phase1 configs will override/add to the 3D base
```

### Step 4: Use the 3D Base in Phase2

In `config/shocktube_phase2/plan/sweep.yaml`:
```yaml
base_experiment: 'shocktube_base_3D'
```

## Example: Switching Between Bases

You can easily test different configurations:

```bash
# Test with 1D base
# Edit config/shocktube_phase1/plan/sweep.yaml:
# base_experiment: 'shocktube_base'
python main.py shocktube_phase1 --test

# Test with 3D base
# Edit config/shocktube_phase1/plan/sweep.yaml:
# base_experiment: 'shocktube_base_3D'
python main.py shocktube_phase1 --test
```

## Configuration Hierarchy

```
Final Configuration = Base + Specific + Sweeps + Branches

Example for shocktube_phase1:
1. Load shocktube_base (all namelists, all parameters)
2. Apply shocktube_phase1 overrides:
   - iheatcond: ['shock', 'hyper3'] → ['shock']
   - tmax: 1.0e-4 → 0.002
   - Add: unit_length, unit_velocity, etc.
3. Apply sweep values (nu_shock=0.1, etc.)
4. Apply branch settings (lmassdiff_fix, etc.)
```

## Best Practices

### 1. Base Experiments Should Be Complete

Your base should contain **all** necessary namelists and parameters:
```yaml
# ✓ Good base
data:
  run_pars: { cdt: 0.1, tmax: 1.0e-4, nt: 6000, ... }
  density_run_pars: { diffrho_shock: 1.0, ... }
  entropy_run_pars: { chi_shock: 1.0, ... }
  eos_run_pars: {}
  hydro_run_pars: {}
```

### 2. Derived Experiments Override Selectively

Only specify what changes:
```yaml
# ✓ Good derived experiment
data:
  run_pars: { tmax: 0.002, nt: 120000 }  # Only override these
  entropy_run_pars: { iheatcond: ['shock'] }  # Remove hyper3
  # Other namelists inherited from base
```

### 3. Use Descriptive Base Names

- `shocktube_base` - 1D baseline configuration
- `shocktube_base_3D` - 3D configuration
- `shocktube_base_highres` - High-resolution grid
- `shocktube_base_mhd` - With magnetic fields

## Multiple Experiments, One Base

```
config/
├── shocktube_base_3D/       # Single 3D base
├── shocktube_phase1/        # Uses 3D base
│   └── plan/sweep.yaml → base_experiment: 'shocktube_base_3D'
├── shocktube_phase2/        # Uses 3D base
│   └── plan/sweep.yaml → base_experiment: 'shocktube_base_3D'
└── shocktube_phase3/        # Uses 3D base
    └── plan/sweep.yaml → base_experiment: 'shocktube_base_3D'
```

All phases automatically use the 3D configuration!

## Troubleshooting

### Verify Merge Results

After running with `--test`, check the generated files:
```bash
# Check what was actually generated
cat runs/shocktube_phase1/generated_configs/<run_name>/run.in
cat runs/shocktube_phase1/generated_configs/<run_name>/start.in
```

### Check Merge Logs

The system logs what it's merging:
```
INFO | Loaded 7 config file(s) from base experiment 'shocktube_base_3D'
INFO | Loaded 7 config file(s) from specific experiment 'shocktube_phase1'
INFO |   Merging 'run_in.yaml': base + specific overrides
INFO |   Merging 'start_in.yaml': base + specific overrides
```

## Summary

**To use a different base experiment:**
1. Create the base directory: `config/<base_name>/in/`
2. Add all config YAML files
3. In your experiment's sweep.yaml, set: `base_experiment: '<base_name>'`
4. Run: `python main.py <experiment> --test`

**That's it!** No code changes needed - the system automatically handles the deep merge.

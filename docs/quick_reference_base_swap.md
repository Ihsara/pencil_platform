# Quick Reference: Swapping Base Experiments

## TL;DR - How to Use a Different Base

**One line change in your experiment's sweep.yaml:**

```yaml
# In config/shocktube_phase1/plan/sweep.yaml
base_experiment: 'shocktube_base_3D'  # Change this line only!
```

That's it! Run with `python main.py shocktube_phase1 --test`

---

## Complete Example: Using 3D Base for Phase1 and Phase2

### 1. Your Directory Structure
```
config/
├── shocktube_base/          # 1D base (original)
├── shocktube_base_3D/       # 3D base (new)
├── shocktube_phase1/
│   ├── in/                  # Phase1-specific configs
│   └── plan/
│       └── sweep.yaml       # ← Edit this
└── shocktube_phase2/
    ├── in/                  # Phase2-specific configs
    └── plan/
        └── sweep.yaml       # ← Edit this
```

### 2. Switch Phase1 to 3D

**File:** `config/shocktube_phase1/plan/sweep.yaml`

```yaml
# Change from:
base_experiment: 'shocktube_base'

# To:
base_experiment: 'shocktube_base_3D'
```

### 3. Switch Phase2 to 3D

**File:** `config/shocktube_phase2/plan/sweep.yaml`

```yaml
# Change from:
base_experiment: 'shocktube_base'

# To:
base_experiment: 'shocktube_base_3D'
```

### 4. Test It

```bash
python main.py shocktube_phase1 --test
python main.py shocktube_phase2 --test
```

---

## What Happens Behind the Scenes

The system automatically:
1. Loads ALL configs from `shocktube_base_3D`
2. Deep merges with phase1/phase2 specific configs
3. Applies parameter sweeps
4. Applies branch settings

**Result:** Your phase experiments inherit all 3D parameters (grid size, MPI setup, boundary conditions) while keeping their specific modifications.

---

## Creating a New Base

### Minimal Example

```bash
# 1. Create directory
mkdir -p config/my_custom_base/in

# 2. Copy from existing base
cp config/shocktube_base/in/*.yaml config/my_custom_base/in/

# 3. Edit the parameters you want to change
# e.g., Edit cparam_local.yaml for grid size
# e.g., Edit start_in.yaml for initial conditions

# 4. Use it
# In any experiment's sweep.yaml:
base_experiment: 'my_custom_base'
```

---

## Common Use Cases

### Use Case 1: Resolution Study
```
config/
├── shocktube_base_lowres/    # nxgrid: 64
├── shocktube_base_midres/    # nxgrid: 128
├── shocktube_base_highres/   # nxgrid: 256
└── shocktube_phase1/
    └── plan/sweep.yaml → base_experiment: 'shocktube_base_highres'
```

### Use Case 2: Dimensionality
```
config/
├── shocktube_base_1D/        # lperi: [false, true, true]
├── shocktube_base_2D/        # lperi: [false, false, true]
├── shocktube_base_3D/        # lperi: [false, false, false]
└── shocktube_phase1/
    └── plan/sweep.yaml → base_experiment: 'shocktube_base_3D'
```

### Use Case 3: Physical Setup
```
config/
├── shocktube_base_hydro/     # Just hydro
├── shocktube_base_mhd/       # Add magnetic fields
└── shocktube_phase1/
    └── plan/sweep.yaml → base_experiment: 'shocktube_base_mhd'
```

---

## Verification

After changing the base, verify the merge:

```bash
# Generate configs
python main.py shocktube_phase1 --test

# Check the logs - should show:
# "Loaded X config file(s) from base experiment 'your_base_name'"
# "Merging 'run_in.yaml': base + specific overrides"

# Inspect generated files
cat runs/shocktube_phase1/generated_configs/*/run.in
cat runs/shocktube_phase1/generated_configs/*/start.in
```

---

## Key Points

✅ **No Code Changes** - Everything is configuration-driven  
✅ **One Line Change** - Just edit `base_experiment:` in sweep.yaml  
✅ **Deep Merge** - Base parameters + specific overrides  
✅ **Reusable Bases** - Multiple experiments can share one base  
✅ **Easy Testing** - Use `--test` flag to preview without submitting  

---

## Full Documentation

See [Base Experiments Guide](base-experiments.md) for detailed explanations.

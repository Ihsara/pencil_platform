# Parameter Sweeps

Parameter sweeps are the core feature of the Pencil Code Automated Experiment Manager. This guide covers everything you need to know about defining and using parameter sweeps.

## Introduction

A parameter sweep automatically generates multiple simulation configurations by varying specified parameters across a range of values. Instead of manually creating hundreds of configuration files, you define the sweep once in YAML and let the tool generate all combinations.

## Sweep Types

The platform supports two fundamental types of sweeps that can be combined to create complex parameter spaces.

### Product Sweep

A **product sweep** generates all possible combinations of independent parameters. This is the most common type of sweep.

**Mathematical concept**: For parameters A and B, generate the Cartesian product A × B.

**Example 1: Two Independent Parameters**

```yaml
parameter_sweeps:
  - type: product
    variable: nu_shock
    values: [0.1, 0.5]
  
  - type: product
    variable: chi_shock
    values: [1.0, 5.0]
```

**Result**: 2 × 2 = 4 combinations
```
nu0.1_chi1.0
nu0.1_chi5.0
nu0.5_chi1.0
nu0.5_chi5.0
```

**Example 2: Three Independent Parameters**

```yaml
parameter_sweeps:
  - type: product
    variable: nxgrid
    values: [400, 800, 1600]
  
  - type: product
    variable: hyper_C
    values: [0.2, 1.0, 5.0]
  
  - type: product
    variable: dt
    values: [0.001, 0.0001]
```

**Result**: 3 × 3 × 2 = 18 combinations

### Linked Sweep

A **linked sweep** varies multiple parameters together, keeping them synchronized. All specified variables take the same value for each run.

**Mathematical concept**: For parameters A, B, C, generate tuples (a₁, a₁, a₁), (a₂, a₂, a₂), ...

**Example 1: Three Linked Parameters**

```yaml
parameter_sweeps:
  - type: linked
    variables: [nu_shock, chi_shock, diffrho_shock]
    values: [0.1, 0.5, 1.0, 5.0]
```

**Result**: 4 combinations (not 4³ = 64!)
```
nu0.1_chi0.1_diffrho0.1
nu0.5_chi0.5_diffrho0.5
nu1.0_chi1.0_diffrho1.0
nu5.0_chi5.0_diffrho5.0
```

**When to use linked sweeps**:
- Testing scaling relationships (e.g., all diffusion coefficients proportional)
- Maintaining physical relationships between parameters
- Reducing the parameter space size

**Example 2: Resolution and Timestep**

```yaml
parameter_sweeps:
  - type: linked
    variables: [nxgrid, dt]
    values: 
      - [400, 0.001]
      - [800, 0.0005]
      - [1600, 0.00025]
```

This keeps the CFL number approximately constant across different resolutions.

## Combining Sweep Types

You can combine multiple sweep blocks. The system computes each block independently, then creates the Cartesian product of the results.

**Example: Linked + Product**

```yaml
parameter_sweeps:
  # Block 1: Linked sweep (4 combinations)
  - type: linked
    variables: [nu_shock, chi_shock]
    values: [0.1, 0.5, 1.0, 5.0]
  
  # Block 2: Product sweep (2 combinations)
  - type: product
    variable: nxgrid
    values: [400, 800]
```

**Result**: 4 × 2 = 8 total combinations

Each linked set is combined with each resolution:
```
nu0.1_chi0.1_nx400
nu0.1_chi0.1_nx800
nu0.5_chi0.5_nx400
nu0.5_chi0.5_nx800
nu1.0_chi1.0_nx400
...
```

## Advanced Sweep Patterns

### Multi-Dimensional Grids

Explore parameter spaces systematically:

```yaml
parameter_sweeps:
  - type: product
    variable: reynolds_number
    values: [100, 1000, 10000]
  
  - type: product
    variable: mach_number
    values: [0.1, 0.5, 1.0, 2.0]
  
  - type: product
    variable: resolution
    values: [256, 512, 1024]
```

Result: 3 × 4 × 3 = 36 simulations exploring the Re-Ma-resolution space.

### Resolution Studies

Common pattern for convergence testing:

```yaml
parameter_sweeps:
  - type: product
    variable: nxgrid
    values: [128, 256, 512, 1024, 2048]
  
  - type: linked
    variables: [dt, cfl]
    values:
      - [0.002, 0.4]
      - [0.001, 0.4]
      - [0.0005, 0.4]
      - [0.00025, 0.4]
      - [0.000125, 0.4]
```

### Sparse Sampling

Test specific parameter combinations:

```yaml
parameter_sweeps:
  - type: linked
    variables: [param_a, param_b, param_c]
    values:
      - [1.0, 2.0, 3.0]   # Configuration 1
      - [1.5, 2.5, 3.5]   # Configuration 2
      - [2.0, 4.0, 5.0]   # Configuration 3
```

This avoids the combinatorial explosion of a full product sweep when you only need specific points.

## Specifying Parameter Paths

Parameters are located in nested YAML structures. Use dot notation to specify their location.

### Basic Path

For a parameter in `run_in.yaml`:

```yaml
# run_in.yaml structure:
density_run_pars:
  ldensity: true
  lmass_diffusion: true
  
# Sweep specification:
parameter_sweeps:
  - type: product
    variable: density_run_pars.lmass_diffusion
    values: [true, false]
```

### Nested Paths

For deeply nested parameters:

```yaml
# Configuration structure:
viscosity_run_pars:
  shock:
    nu_shock: 0.5
    chi_shock: 1.0

# Sweep specification:
parameter_sweeps:
  - type: product
    variable: viscosity_run_pars.shock.nu_shock
    values: [0.1, 0.5, 1.0]
```

### Array Indices

For parameters that are arrays:

```yaml
# Configuration:
boundary_conditions:
  bc_field: ['p', 'p', 's', 's']

# Sweep (not commonly used):
parameter_sweeps:
  - type: product
    variable: boundary_conditions.bc_field[2]
    values: ['p', 's', 'a']
```

## Value Formatting in Directory Names

The system automatically formats parameter values for directory names:

| Value Type | Example Value | Directory Name |
|------------|--------------|----------------|
| Integer | `400` | `nx400` |
| Float | `1.0` | `C1p0` |
| Float | `0.5` | `C0p5` |
| Scientific | `1e-3` | `C1em3` |
| Boolean | `true` | `with_feature` |
| Boolean | `false` | `no_feature` |
| String | `"periodic"` | `periodic` |

### Custom Name Formatting

You can control how values appear in directory names (advanced feature, requires code modification).

## Sweep File Structure

Complete anatomy of a `sweep.yaml` file:

```yaml
# Experiment metadata
base_experiment: shocktube_base
output_base_dir: "/scratch/project_2008296/shocktube"

# SLURM configuration
slurm:
  account: "project_2008296"
  partition: "small"
  time: "00:30:00"
  nodes: 1
  ntasks_per_node: 128

# Parameter sweeps
parameter_sweeps:
  - type: product
    variable: param1
    values: [val1, val2, val3]
  
  - type: linked
    variables: [param2, param3]
    values: [v1, v2, v3]

# Optional: Branches (see Branches guide)
branches:
  - name: branch1
    settings:
      run_in.yaml:
        param: value
```

## Practical Examples

### Example 1: Shock Tube Study

```yaml
parameter_sweeps:
  # Test different shock viscosities
  - type: product
    variable: viscosity_run_pars.shock.nu_shock
    values: [0.1, 0.5, 1.0, 2.0, 5.0]
  
  # Test different shock heat conductivities
  - type: product
    variable: viscosity_run_pars.shock.chi_shock
    values: [0.1, 0.5, 1.0, 2.0, 5.0]
```

Result: 5 × 5 = 25 simulations exploring the shock parameter space.

### Example 2: Convergence Study

```yaml
parameter_sweeps:
  # Resolutions
  - type: product
    variable: nxgrid
    values: [200, 400, 800, 1600]
  
  # Hyperdiffusion coefficients
  - type: product
    variable: hyper_C
    values: [0.2, 1.0, 5.0]
```

Result: 4 × 3 = 12 simulations for resolution-hyperdiffusion study.

### Example 3: Physical Parameter Study

```yaml
parameter_sweeps:
  # Keep all shock parameters synchronized
  - type: linked
    variables: 
      - viscosity_run_pars.shock.nu_shock
      - viscosity_run_pars.shock.chi_shock
      - density_run_pars.shock.diffrho_shock
    values: [0.1, 0.5, 1.0, 5.0]
  
  # But vary resolution independently
  - type: product
    variable: nxgrid
    values: [400, 800, 1600]
```

Result: 4 × 3 = 12 simulations, but with shock parameters always equal.

## Validation and Testing

### Preview Without Generating

Use test mode to see what will be generated:

```bash
python main.py my_experiment --test 3
```

### Check Parameter Counts

The generator logs how many runs will be created:

```
INFO: Parameter sweep will generate 25 combinations
INFO: With 2 branches, total runs: 50
```

### Verify Generated Configs

After generation, spot-check configuration files:

```bash
# Check first run
cat runs/my_experiment/generated_configs/run_001/run.in

# Check last run
cat runs/my_experiment/generated_configs/run_050/run.in

# Compare two runs
diff runs/my_experiment/generated_configs/run_{001,002}/run.in
```

## Best Practices

### 1. Start Small

Begin with a small sweep to verify behavior:

```yaml
parameter_sweeps:
  - type: product
    variable: my_param
    values: [1.0, 2.0]  # Just 2 values initially
```

### 2. Use Logarithmic Spacing

For parameters spanning orders of magnitude:

```yaml
parameter_sweeps:
  - type: product
    variable: reynolds_number
    values: [10, 100, 1000, 10000]  # Log spacing
```

### 3. Document Your Sweeps

Add comments explaining the physics:

```yaml
parameter_sweeps:
  # Testing turbulent vs laminar regime
  - type: product
    variable: reynolds_number
    values: [100, 1000, 10000]
```

### 4. Consider Computational Cost

A 5×5×5 sweep = 125 simulations. Ensure you have:
- Sufficient HPC allocation
- Adequate storage space
- Realistic time estimates

### 5. Use Linked Sweeps to Reduce Space

Instead of exploring N^3 combinations, linked sweeps explore N:

```yaml
# Bad: 5³ = 125 combinations
- type: product
  variable: param1
  values: [1, 2, 3, 4, 5]
- type: product
  variable: param2
  values: [1, 2, 3, 4, 5]
- type: product
  variable: param3
  values: [1, 2, 3, 4, 5]

# Good: 5 combinations
- type: linked
  variables: [param1, param2, param3]
  values: [1, 2, 3, 4, 5]
```

## Common Pitfalls

### Pitfall 1: Combinatorial Explosion

```yaml
# This creates 5×5×5×5 = 625 runs!
parameter_sweeps:
  - type: product
    variable: param1
    values: [1, 2, 3, 4, 5]
  - type: product
    variable: param2
    values: [1, 2, 3, 4, 5]
  - type: product
    variable: param3
    values: [1, 2, 3, 4, 5]
  - type: product
    variable: param4
    values: [1, 2, 3, 4, 5]
```

**Solution**: Use linked sweeps or reduce the number of values.

### Pitfall 2: Wrong Parameter Path

```yaml
# Wrong - missing intermediate level
variable: nu_shock

# Correct - full path
variable: viscosity_run_pars.shock.nu_shock
```

### Pitfall 3: Type Mismatches

```yaml
# Configuration expects boolean
lmass_diffusion: true

# Wrong - string instead of boolean
values: ["true", "false"]

# Correct - actual booleans
values: [true, false]
```

## Troubleshooting

### "Parameter not found"

Check the full path in the base configuration:

```bash
# View the structure
cat config/my_experiment/in/run_in.yaml
```

### Unexpected Number of Runs

```bash
# The tool logs the calculation
python main.py my_experiment --test

# Output shows:
# "3 (sweep1) × 2 (sweep2) = 6 total runs"
```

### Directory Names Too Long

Reduce the number of parameters or use shorter variable names.

## Next Steps

- Learn about [Branches](branches.md) to run sweeps under different conditions
- See [Examples](examples.md) for real-world sweep configurations
- Explore [Workflow Management](workflow-management.md) for automation

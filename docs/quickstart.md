# Quick Start

Get started with the Pencil Code Automated Experiment Manager in minutes.

## Your First Experiment

This tutorial walks you through running your first parameter sweep experiment.

### Step 1: Activate Your Environment

```bash
# Navigate to the project directory
cd platform

# Activate your virtual environment
source .venv/bin/activate
```

### Step 2: Explore Available Experiments

```bash
# Run the tool in interactive mode
python main.py
```

You'll see a list of available experiments:
```
Available experiments:
  1: shocktube_phase1
  2: shocktube_phase2
Please choose an experiment number:
```

### Step 3: Run a Test

Before generating hundreds of simulations, test with just a few runs:

```bash
# Generate only the first 2 runs
python main.py shocktube_phase1 --test
```

This creates:
- Configuration files in `runs/shocktube_phase1/generated_configs/`
- A SLURM submission script

### Step 4: Review Generated Files

```bash
# List generated configurations
ls runs/shocktube_phase1/generated_configs/

# View a sample configuration
cat runs/shocktube_phase1/generated_configs/run_001/run.in
```

### Step 5: Run the Full Experiment

Once satisfied with the test:

```bash
# Generate all configurations
python main.py shocktube_phase1
```

## Common Workflows

### Test → Review → Run

The recommended workflow for any experiment:

```bash
# 1. Test with a small subset
python main.py my_experiment --test 2

# 2. Review the generated files
ls runs/my_experiment/generated_configs/

# 3. If satisfied, generate the full suite
python main.py my_experiment
```

### Using Snakemake for Full Automation

For HPC clusters, Snakemake manages job submission:

```bash
# Dry run to preview all jobs
snakemake --profile .config/slurm --config experiment_name=shocktube_phase1 -n

# Submit the full workflow
snakemake --profile .config/slurm --config experiment_name=shocktube_phase1
```

### Check Job Status

```bash
# Check status of submitted jobs
python main.py shocktube_phase1 --check
```

## Understanding the Output

After running an experiment, you'll find:

```
platform/
├── runs/
│   └── shocktube_phase1/
│       ├── generated_configs/
│       │   ├── run_001/
│       │   │   ├── run.in
│       │   │   ├── start.in
│       │   │   ├── print.in
│       │   │   ├── cparam.local
│       │   │   └── Makefile.local
│       │   ├── run_002/
│       │   └── ...
│       └── submit_jobs.sh  # SLURM submission script
```

## Key Command Options

### Basic Usage

```bash
# Interactive mode
python main.py

# Direct experiment selection
python main.py <experiment_name>

# Test mode (first N runs)
python main.py <experiment_name> --test [N]
```

### Advanced Options

```bash
# Force rebuild of executables
python main.py <experiment_name> --rebuild

# Run analysis and plotting
python main.py <experiment_name> --analyze

# Check job status
python main.py <experiment_name> --check

# View all options
python main.py --help
```

## Example: Running shocktube_phase2

Here's a complete example workflow:

```bash
# 1. Activate environment
source .venv/bin/activate

# 2. Test with 3 runs
python main.py shocktube_phase2 --test 3

# 3. Review what was generated
ls -la runs/shocktube_phase2/generated_configs/

# 4. Inspect a configuration
cat runs/shocktube_phase2/generated_configs/run_001/run.in

# 5. Generate full suite (18 runs total)
python main.py shocktube_phase2

# 6. Submit to SLURM (on HPC)
cd runs/shocktube_phase2
sbatch submit_jobs.sh
```

## Modifying Experiments

### Quick Modifications

To change parameters for an experiment:

1. Edit the experiment's sweep file:
   ```bash
   nano config/shocktube_phase1/plan/sweep.yaml
   ```

2. Regenerate (old configs are automatically cleaned):
   ```bash
   python main.py shocktube_phase1 --test
   ```

3. Review and run:
   ```bash
   python main.py shocktube_phase1
   ```

### Understanding sweep.yaml

A simple parameter sweep:

```yaml
parameter_sweeps:
  - type: product
    variable: nu_shock
    values: [0.1, 0.5, 1.0]
  
  - type: product
    variable: chi_shock
    values: [1.0, 5.0]
```

This creates 3 × 2 = 6 simulations exploring all combinations.

## Next Steps

Now that you've run your first experiment:

1. **Learn Configuration**: Read the [Configuration Guide](user-guide/configuration.md)
2. **Master Parameter Sweeps**: See [Parameter Sweeps](user-guide/parameter-sweeps.md)
3. **Explore Examples**: Check out [Examples](user-guide/examples.md)
4. **Workflow Management**: Learn about [Snakemake Integration](user-guide/workflow-management.md)

## Troubleshooting Quick Issues

### "No such file or directory"

Ensure you're in the correct directory:
```bash
pwd  # Should show .../platform
```

### "Module not found"

Activate your virtual environment:
```bash
source .venv/bin/activate
```

### "Permission denied"

Make scripts executable:
```bash
chmod +x main.py
```

### Generated files look wrong

Clean and regenerate (automatic):
```bash
python main.py my_experiment --test
```

## Getting Help

- Run `python main.py --help` for command options
- Check the [Troubleshooting Guide](troubleshooting.md)
- Review [Examples](user-guide/examples.md) for common patterns

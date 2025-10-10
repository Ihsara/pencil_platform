# Troubleshooting

Common issues and their solutions when using the Pencil Code Automated Experiment Manager.

## Installation Issues

### Python Version Too Old

**Symptom:**
```
ERROR: Python 3.13 or higher is required
```

**Solution:**
Install Python 3.13 or higher:

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.13

# macOS with Homebrew
brew install python@3.13

# Verify installation
python3.13 --version
```

### Virtual Environment Not Activating

**Symptom:**
Commands like `python main.py` use system Python instead of virtual environment.

**Solution:**
```bash
# Ensure you're in the project directory
cd platform

# Recreate the virtual environment
rm -rf .venv
python3 -m venv .venv

# Activate (the prompt should change)
source .venv/bin/activate

# Verify activation
which python  # Should show path to .venv/bin/python
```

### Missing Dependencies

**Symptom:**
```
ModuleNotFoundError: No module named 'yaml'
```

**Solution:**
```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall dependencies
pip install -e .

# Verify installation
pip list
```

### h5py Installation Fails

**Symptom:**
```
ERROR: Failed building wheel for h5py
```

**Solution:**

Install system dependencies first:

```bash
# Ubuntu/Debian
sudo apt install libhdf5-dev pkg-config

# macOS
brew install hdf5

# Then retry
pip install h5py
```

## Configuration Issues

### Experiment Not Found

**Symptom:**
```
ERROR: Experiment 'my_experiment' not found
```

**Solution:**

Check experiment directory structure:

```bash
# List available experiments
ls config/

# Verify required files exist
ls config/my_experiment/plan/sweep.yaml
ls config/my_experiment/in/*.yaml
```

Required structure:
```
config/my_experiment/
├── in/
│   ├── run_in.yaml
│   └── ... (other .yaml files)
└── plan/
    └── sweep.yaml
```

### Invalid YAML Syntax

**Symptom:**
```
yaml.scanner.ScannerError: mapping values are not allowed here
```

**Solution:**

Common YAML errors:

```yaml
# Bad: Missing space after colon
parameter_sweeps:
  - type:product  # Wrong!

# Good: Space after colon
parameter_sweeps:
  - type: product  # Correct

# Bad: Inconsistent indentation
parameter_sweeps:
 - type: product
   variable: param1  # Wrong indentation!

# Good: Consistent indentation (2 spaces)
parameter_sweeps:
  - type: product
    variable: param1
```

Validate your YAML:
```bash
python -c "import yaml; yaml.safe_load(open('config/my_experiment/plan/sweep.yaml'))"
```

### Parameter Path Not Found

**Symptom:**
```
ERROR: Parameter 'wrong.path' not found in configuration
```

**Solution:**

Verify the parameter path:

```bash
# View the configuration structure
cat config/my_experiment/in/run_in.yaml

# Use correct dot notation
# If the structure is:
viscosity_run_pars:
  shock:
    nu_shock: 0.5

# Then the path is:
variable: viscosity_run_pars.shock.nu_shock
```

## Generation Issues

### No Configurations Generated

**Symptom:**
No files appear in `runs/<experiment>/generated_configs/`

**Solution:**

1. Check for errors in the log:
```bash
python main.py my_experiment 2>&1 | tee debug.log
```

2. Verify sweep.yaml is valid:
```bash
python -c "from src.read_config import read_sweep_config; print(read_sweep_config('my_experiment'))"
```

3. Check template files exist:
```bash
ls template/generic/
ls template/shocktube/  # Or your problem-specific templates
```

### Template Rendering Errors

**Symptom:**
```
jinja2.exceptions.TemplateNotFound: run.in.j2
```

**Solution:**

Verify template directory structure:

```bash
# Check templates exist
ls template/generic/*.j2
ls template/shocktube/in/*.j2

# Ensure template_dir is set correctly in sweep.yaml
grep template_dir config/my_experiment/plan/sweep.yaml
```

### Wrong Number of Runs Generated

**Symptom:**
Expected 50 runs, but only 25 were generated.

**Solution:**

Check the sweep calculation:

```bash
# The tool logs the calculation
python main.py my_experiment --test
# Look for output like:
# "3 (sweep1) × 2 (sweep2) × 5 (branches) = 30 total runs"
```

Verify sweep types:
```yaml
# Product sweep: multiplies
- type: product
  variable: param1
  values: [1, 2, 3]  # 3 values
- type: product
  variable: param2
  values: [a, b]  # 2 values
# Result: 3 × 2 = 6 runs

# Linked sweep: doesn't multiply
- type: linked
  variables: [param1, param2]
  values: [1, 2, 3]  # 3 values for both
# Result: 3 runs (not 9!)
```

## HPC/SLURM Issues

### Jobs Not Submitting

**Symptom:**
```
sbatch: error: Batch job submission failed
```

**Solution:**

1. Check SLURM account:
```bash
# Verify your account
sacctmgr list associations user=$USER

# Update in sweep.yaml
slurm:
  account: "project_XXXXXXX"  # Use correct account
```

2. Check partition availability:
```bash
# List available partitions
sinfo

# Use valid partition in sweep.yaml
slurm:
  partition: "small"  # Or "test", "large", etc.
```

3. Verify time format:
```yaml
# Correct format
slurm:
  time: "00:30:00"  # HH:MM:SS

# Wrong formats
time: "30"  # Missing format
time: "30 minutes"  # Not SLURM format
```

### Permission Denied on HPC

**Symptom:**
```
bash: /scratch/project_XXX/my_run: Permission denied
```

**Solution:**

Check directory permissions:

```bash
# On the HPC cluster
ls -ld /scratch/project_XXX/

# Create directory if needed
mkdir -p /scratch/project_XXX/my_experiment

# Check you can write
touch /scratch/project_XXX/test && rm /scratch/project_XXX/test
```

### Out of Memory Errors

**Symptom:**
Jobs fail with OOM (Out of Memory) errors.

**Solution:**

Increase memory allocation in sweep.yaml:

```yaml
slurm:
  mem: "4G"  # Increase from default
  # Or specify per-cpu
  mem_per_cpu: "2G"
```

For large resolutions, calculate required memory:
- Typical: ~100 MB per million grid points
- High-order: ~200 MB per million grid points

### Jobs Timeout

**Symptom:**
```
SLURM Job_XXX TIME LIMIT
```

**Solution:**

Increase time limit in sweep.yaml:

```yaml
slurm:
  time: "01:00:00"  # Increase as needed
  partition: "large"  # Use partition with longer time limits
```

Estimate time needed:
```bash
# Check completed job times
sacct -j JOBID --format=JobID,Elapsed,TotalCPU
```

## Snakemake Issues

### Profile Not Found

**Symptom:**
```
ProfileNotFoundError: Profile 'slurm' not found
```

**Solution:**

Create the profile:

```bash
mkdir -p .config/snakemake/slurm

cat > .config/snakemake/slurm/config.yaml << 'EOF'
cluster: "sbatch --account={resources.account} --partition={resources.partition} --time={resources.time} --nodes={resources.nodes} --ntasks={resources.ntasks}"
jobs: 100
default-resources:
  - account="project_2008296"
  - partition="small"
  - time="00:15:00"
  - ntasks=1
  - nodes=1
EOF
```

### Snakemake Not Installed

**Symptom:**
```
command not found: snakemake
```

**Solution:**

```bash
# Activate environment
source .venv/bin/activate

# Install Snakemake
pip install snakemake

# Verify
snakemake --version
```

### Workflow Execution Fails

**Symptom:**
Snakemake reports rule failures.

**Solution:**

1. Run dry run first:
```bash
snakemake --profile .config/slurm --config experiment_name=my_experiment -n
```

2. Check for errors:
```bash
# View Snakemake logs
ls .snakemake/log/

# Check most recent log
tail -n 50 .snakemake/log/*.log
```

3. Force rerun:
```bash
snakemake --profile .config/slurm --config experiment_name=my_experiment --forceall
```

## Runtime Issues

### Import Errors

**Symptom:**
```
ModuleNotFoundError: No module named 'src'
```

**Solution:**

Ensure you're running from the project root:

```bash
# Check current directory
pwd  # Should show .../platform

# If not, cd to project root
cd /path/to/platform

# Run command
python main.py my_experiment
```

### File Not Found Errors

**Symptom:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'config/...'
```

**Solution:**

```bash
# Verify files exist
ls config/my_experiment/plan/sweep.yaml

# Check you're in the right directory
pwd  # Should show project root

# If paths are wrong, check sweep.yaml
base_experiment: "shocktube_base"  # Should match directory name
```

### Permission Errors

**Symptom:**
```
PermissionError: [Errno 13] Permission denied: 'runs/my_experiment'
```

**Solution:**

```bash
# Check permissions
ls -ld runs/

# Fix permissions
chmod -R u+w runs/

# Or remove and regenerate
rm -rf runs/my_experiment
python main.py my_experiment
```

## Data Analysis Issues

### No Output Data

**Symptom:**
Analysis fails because simulation data doesn't exist.

**Solution:**

1. Verify simulations completed:
```bash
# Check SLURM job status
squeue -u $USER

# Check output directories
ls /scratch/project_XXX/my_experiment/*/data/
```

2. Wait for simulations to complete before analysis:
```bash
# Don't run analysis immediately
python main.py my_experiment  # Submit jobs

# Wait, then analyze
python main.py my_experiment --analyze
```

### Plot Generation Fails

**Symptom:**
```
RuntimeError: Could not create figure
```

**Solution:**

Ensure matplotlib backend is set:

```python
# Add to analysis scripts
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
```

## Getting More Help

### Enable Debug Logging

```bash
# Set log level to DEBUG
export LOG_LEVEL=DEBUG
python main.py my_experiment 2>&1 | tee debug.log
```

### Check System Information

```bash
# Python version
python --version

# Installed packages
pip list

# System info
uname -a

# Disk space
df -h runs/
```

### Report an Issue

When reporting issues, include:

1. Command that failed:
```bash
python main.py my_experiment --test 2
```

2. Full error message

3. Configuration files (sanitized):
```bash
cat config/my_experiment/plan/sweep.yaml
```

4. System information:
```bash
python --version
pip list | grep -E "pyyaml|jinja2"
```

5. Generated log:
```bash
python main.py my_experiment 2>&1 | tee error.log
```

## Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `ModuleNotFoundError` | Missing dependency | `pip install -e .` |
| `FileNotFoundError` | Wrong directory | `cd` to project root |
| `PermissionError` | No write access | Check permissions |
| `yaml.scanner.ScannerError` | Invalid YAML | Check syntax |
| `KeyError` | Missing config key | Verify configuration |
| `TemplateNotFound` | Missing template | Check template directory |
| `SLURM error` | Invalid SLURM config | Verify account/partition |

## Preventive Measures

### Always Test First

```bash
# ALWAYS use --test before full run
python main.py my_experiment --test 2
```

### Validate Configuration

```bash
# Check YAML syntax
python -c "import yaml; yaml.safe_load(open('config/my_experiment/plan/sweep.yaml'))"
```

### Use Version Control

```bash
# Track changes to configs
git add config/
git commit -m "Update parameter sweep"
```

### Monitor Disk Space

```bash
# Check before large runs
df -h /scratch/project_XXX/
```

### Keep Dependencies Updated

```bash
# Update dependencies periodically
pip install -e . --upgrade
```

## See Also

- [Installation Guide](installation.md)
- [Quick Start](quickstart.md)
- [CLI Reference](cli-reference.md)
- [User Guide](user-guide/index.md)

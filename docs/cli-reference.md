# CLI Reference

Complete reference for the command-line interface of the Pencil Code Automated Experiment Manager.

## Main Command

```bash
python main.py [EXPERIMENT] [OPTIONS]
```

## Arguments

### Positional Arguments

#### `EXPERIMENT` (optional)

The name of the experiment to run. If not provided, the tool enters interactive mode.

**Examples:**
```bash
# Direct specification
python main.py shocktube_phase1

# Interactive mode (will prompt for selection)
python main.py
```

**Available Experiments:**

Experiments are discovered from the `config/` directory. Each subdirectory with a `plan/sweep.yaml` file is recognized as an experiment.

To list available experiments:
```bash
python main.py
```

## Options

### `--test [N]`

Generate only the first N configurations for testing. If N is not specified, defaults to 2.

**Usage:**
```bash
# Generate first 2 configurations
python main.py shocktube_phase1 --test

# Generate first 5 configurations
python main.py shocktube_phase1 --test 5

# Generate just 1 configuration
python main.py shocktube_phase1 --test 1
```

**When to use:**
- Before generating a full suite
- Testing configuration changes
- Debugging template issues
- Quick verification of sweep logic

### `--rebuild`

Force rebuild of Pencil Code executables in all run directories.

**Usage:**
```bash
python main.py shocktube_phase1 --rebuild
```

**When to use:**
- After changing `cparam.local` parameters (nxgrid, ncpus, etc.)
- After modifying `Makefile.local` settings
- When executables may be out of sync with configurations

**Note:** The system automatically detects when rebuilds are needed for:
- Changes to grid resolution (nxgrid, nygrid, nzgrid)
- Changes to processor layout (ncpus, nprocx, nprocy, nprocz)
- Modifications to compilation files

### `--analyze`

Run video-only analysis: creates individual error evolution videos and overlay comparisons.

**Usage:**
```bash
python main.py shocktube_phase1 --analyze
```

**What it does:**
- Loads all VAR files from all simulation runs
- Calculates spatial errors between numerical and analytical solutions
- Creates individual error evolution videos for each run
- Generates overlay comparison videos for branches
- Creates top 3 performers overlay video
- Calculates L1/L2/L∞ error norms with combined scoring
- Generates comprehensive visualizations and summary reports

**Output location:** `analysis/<experiment_name>/`

**Folder structure:**
```
analysis/<experiment_name>/
├── var/
│   ├── evolution/      # Individual VAR evolution videos
│   └── frames/         # Video frames
├── error/
│   ├── evolution/      # Individual error evolution videos
│   ├── frames/         # Video frames
│   └── best/           # Best performers' videos and plots
└── error_norms/        # L1/L2 error norm analysis results
    ├── plots/          # Comparison plots
    ├── *_summary.json  # JSON summary
    └── *_summary.md    # Markdown report
```

**Requirements:**
- Simulation data must exist and be complete
- Sufficient memory for loading all VAR files
- FFmpeg installed for video generation

**See:** [Analysis and Visualization Guide](analysis-and-visualization.md) for detailed information

### `--error-norms`

Run L1/L2 error norm analysis: calculates L1, L2, L∞ metrics with combined scoring.

**Usage:**
```bash
python main.py shocktube_phase1 --error-norms
```

**What it does:**
- Loads all VAR files from all simulation runs
- Calculates L1, L2, and L∞ error norms for all variables
- Computes combined scores averaging all metrics
- Identifies best performers overall and per branch
- Generates comparison plots and detailed visualizations
- Creates comprehensive summary reports

**Output location:** `analysis/<experiment_name>/error_norms/`

**What's included:**
- Combined scores comparison plot (all runs)
- Per-metric comparison plots (L1, L2, L∞)
- Top 5 performers detailed view
- Branch comparison analysis
- Error evolution over time (top 3)
- JSON and Markdown summary reports

**Metrics calculated:**
- **L1 norm**: Mean absolute error
- **L2 norm**: Root mean square error
- **L∞ norm**: Maximum absolute error

**Note:** This analysis focuses on error norms only, without video generation. Results are saved to a dedicated `error_norms/` subfolder for easy organization.

### `--viz [RUNS...]`

**DEPRECATED:** This flag is deprecated and redirects to `--analyze`.

**Usage:**
```bash
# Use --analyze instead
python main.py shocktube_phase1 --analyze
```

**What it does:**
- Redirects to video-only analysis (`--analyze`)
- Will be removed in a future version

**Migration:** Replace all `--viz` usage with `--analyze` for the same functionality.

### `--var SELECTION`

Select which VAR file to use for visualization (used with `--viz`).

**Usage:**
```bash
# Use middle VAR file (default)
python main.py shocktube_phase1 --viz --var middle

# Use random VAR file
python main.py shocktube_phase1 --viz --var random

# Use last VAR file
python main.py shocktube_phase1 --viz --var last

# Use specific VAR file
python main.py shocktube_phase1 --viz --var VAR5
```

**Options:**
- `middle` (default): Selects VAR file in the middle of the sequence
- `random`: Randomly selects a VAR file
- `last`: Uses the final VAR file
- `first`: Uses the first VAR file
- `VAR<N>`: Specific VAR file (e.g., `VAR5`, `VAR10`)

### `--check`

Check the status of submitted jobs on the HPC cluster.

**Usage:**
```bash
python main.py shocktube_phase1 --check
```

**What it does:**
- Queries SLURM for job status
- Reports running, pending, and completed jobs
- Shows any failed jobs
- Displays estimated completion time

**Output example:**
```
Job Status for shocktube_phase1:
  Running: 15
  Pending: 5
  Completed: 30
  Failed: 0
  Total: 50
```

### `--wait`

Wait for job completion before proceeding. Useful for automated workflows.

**Usage:**
```bash
# Wait for jobs to complete
python main.py shocktube_phase1 --wait

# Wait then auto-run analysis
python main.py shocktube_phase1 --wait --analyze
```

**What it does:**
- Monitors job status on the HPC cluster
- Polls SLURM at regular intervals
- Waits until all jobs are completed
- Optionally runs analysis after completion (if `--analyze` is specified)

**Common use cases:**
```bash
# Submit, wait, and analyze automatically
python main.py my_experiment --wait --analyze

# Just wait for completion
python main.py my_experiment --wait
```

**Requirements:**
- Jobs must be submitted first (automatically done in normal mode)
- SLURM must be accessible

### `--help`, `-h`

Display help message with all available options.

**Usage:**
```bash
python main.py --help
python main.py -h
```

## Combining Options

Multiple options can be combined in a single command:

```bash
# Generate 3 test runs and force rebuild
python main.py shocktube_phase1 --test 3 --rebuild

# Generate full suite and immediately check status
python main.py shocktube_phase1 --check

# Test mode with analysis
python main.py shocktube_phase1 --test 2 --analyze
```

## Return Codes

The tool uses standard Unix return codes:

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Configuration error |
| 3 | File I/O error |
| 4 | Template error |

**Example usage in scripts:**
```bash
if python main.py shocktube_phase1 --test; then
    echo "Test successful"
    python main.py shocktube_phase1
else
    echo "Test failed"
    exit 1
fi
```

## Environment Variables

### `PENCIL_HOME`

Path to the Pencil Code installation.

**Usage:**
```bash
export PENCIL_HOME=/path/to/pencil-code
python main.py shocktube_phase1
```

### `SLURM_ACCOUNT`

Override the default SLURM account specified in sweep.yaml.

**Usage:**
```bash
export SLURM_ACCOUNT=project_1234567
python main.py shocktube_phase1
```

## Configuration Files

### Experiment Location

Experiments are discovered from:
```
config/<experiment_name>/
```

Required structure:
```
config/<experiment_name>/
├── in/
│   ├── run_in.yaml
│   ├── start_in.yaml
│   └── ...
└── plan/
    └── sweep.yaml
```

### Output Location

Generated configurations are written to:
```
runs/<experiment_name>/generated_configs/
```

SLURM scripts are written to:
```
runs/<experiment_name>/submit_jobs.sh
```

## Snakemake Integration

When using Snakemake, the command structure is different:

### Basic Snakemake Commands

```bash
# Dry run
snakemake --profile .config/slurm --config experiment_name=EXPERIMENT -n

# Execute
snakemake --profile .config/slurm --config experiment_name=EXPERIMENT

# Limit runs
snakemake --profile .config/slurm --config experiment_name=EXPERIMENT limit=N
```

### Snakemake Options

#### `experiment_name`

Specifies which experiment to run (required).

```bash
snakemake --profile .config/slurm --config experiment_name=shocktube_phase1
```

#### `limit`

Limit the number of simulation runs generated.

```bash
snakemake --profile .config/slurm --config experiment_name=shocktube_phase1 limit=5
```

#### `-n`, `--dry-run`

Preview what Snakemake will do without executing.

```bash
snakemake --profile .config/slurm --config experiment_name=shocktube_phase1 -n
```

#### `-j`, `--jobs`

Maximum number of concurrent jobs (default from profile).

```bash
snakemake --profile .config/slurm --config experiment_name=shocktube_phase1 -j 50
```

#### `--forceall`

Force re-run of all steps.

```bash
snakemake --profile .config/slurm --config experiment_name=shocktube_phase1 --forceall
```

## Examples

### Example 1: Standard Workflow

```bash
# 1. Test with 2 runs
python main.py shocktube_phase1 --test 2

# 2. Review generated configs
ls runs/shocktube_phase1/generated_configs/

# 3. Generate full suite
python main.py shocktube_phase1

# 4. Check status (after submission)
python main.py shocktube_phase1 --check
```

### Example 2: Development Workflow

```bash
# Quick iteration cycle
while true; do
    python main.py my_experiment --test 1
    cat runs/my_experiment/generated_configs/run_001/run.in
    echo "Press Enter to regenerate or Ctrl+C to exit"
    read
done
```

### Example 3: Debugging

```bash
# Generate single run with verbose output
python main.py shocktube_phase1 --test 1 2>&1 | tee debug.log

# Check what was generated
find runs/shocktube_phase1/ -type f -name "*.in"
```

### Example 4: Batch Testing Multiple Experiments

```bash
# Test all experiments
for exp in shocktube_phase1 shocktube_phase2; do
    echo "Testing $exp"
    python main.py $exp --test 1 || echo "$exp failed"
done
```

### Example 5: Snakemake Production Run

```bash
# Full production workflow with Snakemake
# 1. Dry run to verify
snakemake --profile .config/slurm \
    --config experiment_name=shocktube_phase1 \
    -n

# 2. Execute if satisfied
snakemake --profile .config/slurm \
    --config experiment_name=shocktube_phase1 \
    --jobs 100
```

## Troubleshooting Commands

### Check Installation

```bash
python -c "import main; print('OK')"
```

### Verify Dependencies

```bash
pip list | grep -E "pyyaml|jinja2|loguru"
```

### Check Experiment Discovery

```bash
python -c "import main; main.list_experiments()"
```

### Validate Configuration

```bash
python -c "from src.read_config import read_sweep_config; print(read_sweep_config('shocktube_phase1'))"
```

### Test Template Rendering

```bash
python -c "from jinja2 import Template; print('Jinja2 OK')"
```

## Advanced Usage

### Programmatic Use

You can import and use the tool programmatically:

```python
from src.suite_generator import SuiteGenerator

# Create generator
generator = SuiteGenerator('shocktube_phase1')

# Generate configs
generator.generate_all_configs()

# Or generate limited set
generator.generate_configs(limit=5)
```

### Custom Templates

To use custom templates, set the template directory:

```python
from src.suite_generator import SuiteGenerator

generator = SuiteGenerator(
    'my_experiment',
    template_dir='path/to/custom/templates'
)
generator.generate_all_configs()
```

### Custom Output Directory

To specify a custom output directory:

```bash
# Via environment variable
export OUTPUT_DIR=/custom/path
python main.py shocktube_phase1

# Or modify sweep.yaml
output_base_dir: "/custom/path"
```

## See Also

- [Quick Start](quickstart.md) - Getting started tutorial
- [User Guide](user-guide/index.md) - Comprehensive usage guide
- [Troubleshooting](troubleshooting.md) - Common issues and solutions
- [Examples](user-guide/examples.md) - Real-world usage examples

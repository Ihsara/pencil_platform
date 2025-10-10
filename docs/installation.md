# Installation

This guide covers different methods for installing and setting up the Pencil Code Automated Experiment Manager.

## Prerequisites

- **Python**: Version 3.13 or higher
- **Operating System**: Linux or macOS (Windows with WSL)
- **HPC Access**: (Optional) For running on HPC clusters like Mahti

## Installation Methods

### Method 1: Classical Python Virtual Environment (Recommended)

This is the standard, transparent method that gives you full control.

#### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd platform
```

#### Step 2: Create Virtual Environment

```bash
# Create a virtual environment named '.venv'
python3 -m venv .venv

# Activate the environment
source .venv/bin/activate  # On Linux/macOS
# or
.venv\Scripts\activate  # On Windows
```

#### Step 3: Install Dependencies

The project uses modern Python packaging with `pyproject.toml`:

```bash
pip install -e .
```

This installs the package in editable mode along with all dependencies.

**Note**: Your shell prompt will change to show `(.venv)` when the environment is active.

To deactivate the environment later:
```bash
deactivate
```

### Method 2: Using `uv` (Faster Alternative)

`uv` is a modern, extremely fast tool that combines the functionality of `pip` and `venv`.

#### Step 1: Install `uv`

```bash
pip install uv
```

#### Step 2: Clone and Setup

```bash
git clone <repository-url>
cd platform

# Create and activate virtual environment
uv venv
source .venv/bin/activate  # On Linux/macOS

# Install dependencies
uv pip install -e .
```

The `uv` approach is significantly faster than traditional pip for dependency resolution and installation.

### Method 3: Development Installation

For contributors and developers who want to modify the code:

```bash
# Clone the repository
git clone <repository-url>
cd platform

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode with development dependencies
pip install -e ".[dev]"
```

## Verifying Installation

After installation, verify that everything is working:

```bash
# Check Python version
python --version  # Should be 3.13 or higher

# Verify main script can be imported
python -c "import main; print('Installation successful!')"

# Test the CLI
python main.py --help
```

You should see the help message with available commands and options.

## Dependencies

The project requires the following Python packages (automatically installed):

- **f90nml** (>=1.4.5): Fortran namelist parser
- **flatdict** (>=4.0.1): Dictionary flattening utilities
- **h5py** (>=3.14.0): HDF5 file handling
- **jinja2** (>=3.1.6): Template engine for configuration generation
- **loguru** (>=0.7.3): Advanced logging
- **matplotlib** (>=3.10.6): Plotting and visualization
- **numpy** (>=2.3.2): Numerical computing
- **pandas** (>=2.3.2): Data analysis and manipulation
- **pexpect** (>=4.9.0): Process interaction
- **pyyaml** (>=6.0.2): YAML file parsing
- **scipy** (>=1.16.1): Scientific computing
- **tabulate** (>=0.9.0): Table formatting

## HPC-Specific Setup

### Snakemake Profile Configuration

If you plan to use Snakemake for workflow management on an HPC cluster:

#### Step 1: Create Profile Directory

```bash
mkdir -p .config/snakemake/slurm
```

#### Step 2: Configure SLURM Profile

Create `.config/snakemake/slurm/config.yaml`:

```yaml
cluster: "sbatch --account={resources.account} --partition={resources.partition} --time={resources.time} --nodes={resources.nodes} --ntasks={resources.ntasks} --cpus-per-task={resources.cpus_per_task}"
jobs: 100
default-resources:
  - account="project_2008296"  # Replace with your project account
  - partition="small"
  - time="00:15:00"
  - ntasks=1
  - cpus_per_task=1
  - nodes=1
```

**Important**: Update the `account` field with your actual HPC project account.

#### Step 3: Verify Snakemake Installation

```bash
snakemake --version
```

If Snakemake is not installed:
```bash
pip install snakemake
```

## Troubleshooting

### Python Version Issues

If `python3 --version` shows a version older than 3.13:

```bash
# On Ubuntu/Debian
sudo apt update
sudo apt install python3.13

# On macOS with Homebrew
brew install python@3.13
```

### Virtual Environment Not Activating

If `source .venv/bin/activate` doesn't work:

```bash
# Try the full path
source /path/to/platform/.venv/bin/activate

# Or use Python's module syntax
python3 -m venv .venv --clear  # Recreate the environment
```

### Import Errors

If you get import errors after installation:

```bash
# Ensure you're in the activated environment
which python  # Should point to .venv/bin/python

# Reinstall in editable mode
pip install -e . --force-reinstall
```

### HDF5 Installation Issues

On some systems, `h5py` may fail to install. Install system dependencies:

```bash
# Ubuntu/Debian
sudo apt install libhdf5-dev

# macOS
brew install hdf5

# Then retry installation
pip install h5py
```

## Next Steps

After successful installation:

1. Read the [Quick Start Guide](quickstart.md)
2. Explore [Configuration](user-guide/configuration.md)
3. Review [Examples](user-guide/examples.md)

## Updating

To update to the latest version:

```bash
# Pull latest changes
git pull origin main

# Reinstall dependencies
pip install -e . --upgrade

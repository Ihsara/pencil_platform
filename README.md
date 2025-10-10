# Pencil Code Automated Experiment Manager

> A robust framework for managing and generating large suites of simulations for the Pencil Code

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

The Pencil Code Automated Experiment Manager automates the tedious and error-prone task of creating hundreds of unique run directories for parameter sweeps in a reproducible manner. Instead of manually editing configuration files, you define your entire experiment in human-readable YAML files, and the tool generates all necessary `.in`, `.local`, and HPC submission scripts.

### Key Features

- **Declarative Configuration**: Define experiments using YAML files
- **Parameter Sweep Automation**: Generate hundreds of configurations from simple specifications
- **HPC Integration**: Automatic SLURM job submission and management
- **Workflow Management**: Integration with Snakemake for full pipeline automation
- **Reproducibility**: Version-controlled experiment definitions
- **Flexible Branching**: Run entire parameter sweeps under different configuration branches

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd platform

# Create virtual environment and install
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Basic Usage

```bash
# Run in interactive mode
python main.py

# Or specify experiment directly
python main.py shocktube_phase1

# Test with limited runs first
python main.py shocktube_phase1 --test 2
```

### Example: Define a Parameter Sweep

Create `config/my_experiment/plan/sweep.yaml`:

```yaml
base_experiment: shocktube_base
output_base_dir: "/scratch/project/my_experiment"

parameter_sweeps:
  - type: product
    variable: viscosity_run_pars.shock.nu_shock
    values: [0.1, 0.5, 1.0]
  
  - type: product
    variable: nxgrid
    values: [400, 800, 1600]

slurm:
  account: "project_2008296"
  partition: "small"
  time: "00:30:00"
```

This generates 3 × 3 = 9 simulation configurations automatically.

## Documentation

Comprehensive documentation is available in the `docs/` folder:

- **[Installation Guide](docs/installation.md)** - Detailed setup instructions
- **[Quick Start Tutorial](docs/quickstart.md)** - Get started in minutes
- **[User Guide](docs/user-guide/index.md)** - Complete usage documentation
  - [Configuration](docs/user-guide/configuration.md)
  - [Parameter Sweeps](docs/user-guide/parameter-sweeps.md)
  - [Branches](docs/user-guide/branches.md)
  - [Workflow Management](docs/user-guide/workflow-management.md)
  - [Examples](docs/user-guide/examples.md)
- **[CLI Reference](docs/cli-reference.md)** - Command-line interface documentation
- **[Troubleshooting](docs/troubleshooting.md)** - Common issues and solutions
- **[API Reference](docs/api/index.md)** - Python API documentation

## Features in Detail

### Parameter Sweeps

Define complex parameter spaces with two sweep types:

**Product Sweep**: Explore all combinations
```yaml
parameter_sweeps:
  - type: product
    variable: reynolds_number
    values: [100, 1000, 10000]
  - type: product
    variable: resolution
    values: [256, 512, 1024]
# Generates: 3 × 3 = 9 configurations
```

**Linked Sweep**: Vary parameters together
```yaml
parameter_sweeps:
  - type: linked
    variables: [nu_shock, chi_shock]
    values: [0.1, 0.5, 1.0]
# Generates: 3 configurations (not 9)
```

### Branches

Run entire parameter sweeps under different conditions:

```yaml
branches:
  - name: "with_fix"
    description: "Run with mass diffusion fix enabled"
    settings:
      run_in.yaml:
        density_run_pars:
          lmassdiff_fix: true
  
  - name: "without_fix"
    settings:
      run_in.yaml:
        density_run_pars:
          lmassdiff_fix: false
```

### HPC Integration

Seamless SLURM integration:

```bash
# Generate configs and submit to HPC
python main.py my_experiment

# Or use Snakemake for full automation
snakemake --profile .config/slurm --config experiment_name=my_experiment
```

## Requirements

- Python 3.13 or higher
- Required packages (automatically installed):
  - pyyaml >= 6.0.2
  - jinja2 >= 3.1.6
  - loguru >= 0.7.3
  - numpy >= 2.3.2
  - pandas >= 2.3.2
  - matplotlib >= 3.10.6
  - h5py >= 3.14.0
  - scipy >= 1.16.1
  - And more (see `pyproject.toml`)

## Project Structure

```
platform/
├── config/              # Experiment configurations
│   └── <experiment>/
│       ├── in/         # Base configuration files
│       └── plan/       # Parameter sweep definitions
├── docs/               # Documentation
├── src/                # Python source code
├── template/           # Jinja2 templates
├── runs/               # Generated output (not in git)
├── main.py            # CLI entry point
└── pyproject.toml     # Project metadata
```

## Command-Line Interface

```bash
python main.py [EXPERIMENT] [OPTIONS]

Options:
  --test [N]     Generate first N configurations for testing (default: 2)
  --rebuild      Force rebuild of executables
  --analyze      Run post-processing analysis
  --check        Check HPC job status
  --help         Show help message
```

See [CLI Reference](docs/cli-reference.md) for complete documentation.

## Examples

### Example 1: Shock Tube Study

```bash
# Test configuration
python main.py shocktube_phase1 --test 2

# Review generated files
ls runs/shocktube_phase1/generated_configs/

# Generate full suite
python main.py shocktube_phase1
```

### Example 2: Convergence Study

```yaml
parameter_sweeps:
  - type: product
    variable: nxgrid
    values: [128, 256, 512, 1024, 2048]
  - type: product
    variable: hyper_C
    values: [0.2, 1.0, 5.0]
# Result: 5 × 3 = 15 simulations
```

### Example 3: Snakemake Workflow

```bash
# Preview all planned jobs
snakemake --profile .config/slurm --config experiment_name=shocktube_phase2 -n

# Execute full workflow
snakemake --profile .config/slurm --config experiment_name=shocktube_phase2
```

More examples in the [User Guide](docs/user-guide/examples.md).

## Contributing

Contributions are welcome! Please see [Contributing Guide](docs/contributing.md) for details.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Citation

If you use this tool in your research, please cite:

```bibtex
@software{pencil_platform,
  title = {Pencil Code Automated Experiment Manager},
  author = {Long Chau Tran},
  year = {2025},
  url = {https://github.com/yourusername/pencil_platform}
}
```

## Support

- **Documentation**: [docs/](docs/)
- **Issues**: Report bugs and feature requests via the issue tracker
- **Discussions**: Ask questions and share ideas

## Acknowledgments

This tool is designed for use with the [Pencil Code](https://github.com/pencil-code/pencil-code), a high-order finite-difference code for compressible hydrodynamic flows with magnetic fields and particles.

---

**Getting Started**: Read the [Quick Start Tutorial](docs/quickstart.md) to begin using the platform.

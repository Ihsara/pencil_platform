# User Guide

Welcome to the comprehensive user guide for the Pencil Code Automated Experiment Manager.

## Overview

This guide covers everything you need to know to effectively use the platform for managing parameter sweep experiments. Whether you're running a simple test or managing hundreds of simulations on an HPC cluster, this guide has you covered.

## Guide Structure

### Getting Started
- **[Configuration](configuration.md)**: Learn how to set up and configure experiments
- **[Parameter Sweeps](parameter-sweeps.md)**: Master the art of defining parameter combinations
- **[Branches](branches.md)**: Use branches to run sweeps under different conditions

### Advanced Topics
- **[Workflow Management](workflow-management.md)**: Integrate with Snakemake for full automation
- **[Examples](examples.md)**: Real-world examples and common patterns

## Key Concepts

### Separation of Configuration and Logic

The platform's core philosophy is to separate **what you want to run** (configuration) from **how it gets executed** (logic):

- **Configuration**: Defined in YAML files in the `config/` directory
- **Logic**: Implemented in Python modules in the `src/` directory
- **Templates**: Jinja2 templates in the `template/` directory

This separation ensures:
- Reproducible experiments through version control
- Easy modification of experiment parameters
- No manual file editing for parameter sweeps

### Directory Structure

Understanding the project layout:

```
platform/
├── config/                    # Experiment configurations
│   ├── <experiment_name>/
│   │   ├── in/               # Base configuration files
│   │   │   ├── run_in.yaml
│   │   │   ├── start_in.yaml
│   │   │   ├── print_in.yaml
│   │   │   └── ...
│   │   └── plan/             # Experiment plan
│   │       └── sweep.yaml    # Parameter sweep definition
│   └── ...
├── template/                  # Jinja2 templates
│   ├── generic/              # Generic templates
│   └── shocktube/            # Problem-specific templates
├── src/                       # Python modules
│   ├── suite_generator.py    # Main generator logic
│   ├── read_config.py        # Configuration parser
│   └── ...
├── runs/                      # Generated output (not in git)
│   └── <experiment_name>/
│       ├── generated_configs/ # Generated configuration files
│       └── submit_jobs.sh     # SLURM submission script
└── main.py                    # Entry point
```

### Experiment Workflow

A typical experiment follows this flow:

1. **Define Base Configuration**: Set up base parameters in `config/<experiment>/in/`
2. **Plan Parameter Sweep**: Define sweeps in `config/<experiment>/plan/sweep.yaml`
3. **Generate Configurations**: Run `python main.py <experiment>`
4. **Review Output**: Check generated files in `runs/<experiment>/`
5. **Submit Jobs**: Use the generated SLURM script or Snakemake
6. **Analyze Results**: Use built-in analysis tools or custom scripts

### Configuration Files

Each experiment consists of several YAML configuration files:

- **run_in.yaml**: Runtime parameters (physics, numerics)
- **start_in.yaml**: Initial conditions
- **print_in.yaml**: Output/diagnostic settings
- **video_in.yaml**: Visualization settings
- **cparam_local.yaml**: Compilation parameters
- **Makefile_local.yaml**: Build configuration

These files map directly to Pencil Code's input files:
- `run_in.yaml` → `run.in`
- `start_in.yaml` → `start.in`
- etc.

## Three Execution Methods

The platform supports three methods of execution, from simple to advanced:

### 1. Classical Python Approach

Direct execution using Python:

```bash
python main.py shocktube_phase1
```

**Best for**:
- Quick tests and development
- Learning the system
- Simple parameter sweeps

### 2. Using `uv`

Faster setup and execution:

```bash
uv run main.py shocktube_phase1
```

**Best for**:
- Faster dependency management
- Modern Python workflows
- Development environments

### 3. Snakemake Workflow

Full workflow automation:

```bash
snakemake --profile .config/slurm --config experiment_name=shocktube_phase1
```

**Best for**:
- HPC cluster execution
- Large-scale experiments
- Automatic job management
- Reproducible pipelines

## Common Tasks

### Testing Before Full Run

Always test with a subset:

```bash
python main.py my_experiment --test 2
```

### Modifying Parameters

1. Edit the sweep file: `config/my_experiment/plan/sweep.yaml`
2. Regenerate: `python main.py my_experiment --test`
3. Review and run full suite

### Forcing Rebuilds

When changing compilation parameters:

```bash
python main.py my_experiment --rebuild
```

### Checking Status

Monitor job progress:

```bash
python main.py my_experiment --check
```

## Best Practices

### 1. Always Test First

Use `--test` mode before generating full suites:
```bash
python main.py experiment --test 2
```

### 2. Version Control Your Configs

Keep `config/` under version control:
```bash
git add config/my_experiment/
git commit -m "Add new parameter sweep"
```

### 3. Don't Commit Generated Files

The `runs/` directory should be in `.gitignore`. Only commit:
- Configuration files
- Templates
- Source code

### 4. Use Descriptive Names

Name experiments and branches descriptively:
- ✓ `shocktube_resolution_study`
- ✓ `with_mass_diffusion_fix`
- ✗ `test1`
- ✗ `experiment_v2`

### 5. Document Your Experiments

Add descriptions to your sweep files:
```yaml
branches:
  - name: "high_viscosity"
    description: "Tests behavior with increased viscosity coefficients"
```

## Navigation

Choose a topic to dive deeper:

- **[Configuration](configuration.md)**: Detailed guide to configuration files
- **[Parameter Sweeps](parameter-sweeps.md)**: Master sweep definitions
- **[Branches](branches.md)**: Use branches effectively
- **[Workflow Management](workflow-management.md)**: Snakemake integration
- **[Examples](examples.md)**: Real-world use cases

## Getting Help

If you're stuck:

1. Check the [Troubleshooting Guide](../troubleshooting.md)
2. Review [Examples](examples.md) for similar use cases
3. Consult the [CLI Reference](../cli-reference.md)
4. Check the source code documentation

## Next Steps

- New users: Start with [Configuration](configuration.md)
- Experienced users: Jump to [Workflow Management](workflow-management.md)
- Looking for examples: See [Examples](examples.md)

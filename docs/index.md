# Pencil Code Automated Experiment Manager

Welcome to the documentation for the Pencil Code Automated Experiment Manager.

## Overview

This project provides a robust framework for managing and generating large suites of simulations for the Pencil Code. It automates the tedious and error-prone task of creating hundreds of unique run directories for parameter sweeps in a reproducible manner.

The core concept is to separate **configuration** (what you want to run) from **logic** (how the files are generated). You define your entire experiment in human-readable YAML files, and this tool generates all the necessary `.in`, `.local`, and HPC submission scripts.

## Key Features

- **Declarative Configuration**: Define experiments using YAML files
- **Parameter Sweep Automation**: Generate hundreds of simulation configurations from simple specifications
- **HPC Integration**: Automatic SLURM job submission and management
- **Workflow Management**: Integration with Snakemake for full pipeline automation
- **Reproducibility**: Version-controlled experiment definitions ensure reproducible research
- **Flexible Branching**: Run entire parameter sweeps under different configuration branches

## Quick Links

- [Installation Guide](installation.md)
- [Quick Start Tutorial](quickstart.md)
- [User Guide](user-guide/index.md)
- [API Reference](api/index.md)
- [Contributing Guidelines](contributing.md)

## Documentation Contents

```{toctree}
:maxdepth: 2
:caption: Getting Started

installation
quickstart
```

```{toctree}
:maxdepth: 2
:caption: User Guide

user-guide/index
user-guide/configuration
user-guide/parameter-sweeps
user-guide/branches
user-guide/workflow-management
user-guide/examples
```

```{toctree}
:maxdepth: 2
:caption: Reference

api/index
cli-reference
troubleshooting
```

```{toctree}
:maxdepth: 1
:caption: Development

contributing
changelog
license
```

## Getting Help

- Check the [Troubleshooting Guide](troubleshooting.md)
- Review [Examples](user-guide/examples.md)
- Report issues on the project's issue tracker

## License

This project is licensed under the MIT License - see the [LICENSE](license.md) file for details.

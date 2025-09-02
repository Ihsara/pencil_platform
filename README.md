# Pencil Code Configuration Manager

A Python-based tool for managing and generating input files for the Pencil Code.

This script automates the creation of Fortran input files (`start.in`, `run.in`, `cparam.local`, etc.) from human-readable YAML configurations and powerful Jinja2 templates. It promotes a modular, repeatable, and error-free workflow for running simulations.

## Key Features

-   **Human-Readable Configuration**: Uses simple YAML files to define all simulation parameters.
-   **Powerful Templating**: Leverages Jinja2 to generate consistently formatted Fortran input files.
-   **Experiment-Oriented**: Organizes all configurations and templates by `experiment_name` for clean, modular project management.
-   **Automated Generation**: A single command processes all input files for a given experiment.
-   **Informative Logging**: Uses `loguru` for clear, colored, and timestamped feedback on the generation process.
-   **Extensible**: Easily add new experiments or new types of input files without changing the core Python code.

## Quick Start Guide

### 1. Prerequisites

-   Python 3.8+
-   A Python package manager like `pip` or `uv`.

### 2. Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd pencil_code_runner
    ```

2.  **Install dependencies:**
    Create a `requirements.txt` file with the following content:
    ```    pyyaml
    jinja2
    loguru
    ```
    Then install using your package manager:
    ```bash
    # Using uv (recommended)
    uv pip install -r requirements.txt

    # Or using pip
    pip install -r requirements.txt
    ```

### 3. Project Structure

The project is organized by experiment name. To add a new experiment, you must create corresponding directories in `config/`.

```
pencil_code_runner/
├── config/
│   └── <experiment_name>/
│       └── in/
│           ├── cparam_local.yaml
│           ├── run_in.yaml
│           └── start_in.yaml
│
├── template/
│   └── generic/
│       ├── cparam.j2
│       ├── list.j2
│       └── namelist.j2
│
└── main.py
```

### 4. How to Run

Execute the `main.py` script from the project root, providing the name of the experiment you want to process.

```bash
python main.py shocktube
```

The script will:
1.  Find the configuration files in `config/shocktube/in/`.
2.  Select the appropriate template from `template/generic/`.
3.  Generate the final Fortran input files in a new directory at `runs/shocktube/`.

## Further Information

For a detailed explanation of the workflow, file formats, and how to extend the system, please see the [Detailed Documentation](docs/documentation.md).


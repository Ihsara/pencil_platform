# Pencil Code Automated Experiment Manager

This project provides a robust framework for managing and generating large suites of simulations for the Pencil Code. It automates the tedious and error-prone task of creating hundreds of unique run directories for parameter sweeps in a reproducible manner.

The core concept is to separate **configuration** (what you want to run) from **logic** (how the files are generated). You define your entire experiment in human-readable YAML files, and this tool generates all the necessary `.in`, `.local`, and HPC submission scripts.

---

## 1. The Classical Approach: A Step-by-Step Guide

This is the standard, manual way to run the generator using basic Python tools that will be familiar to any Linux user. It is the most transparent method and gives you full control.

### Step 1: Set Up a Python Virtual Environment

First, it is highly recommended to create an isolated environment. This ensures that the required Python packages for this tool do not interfere with your system's global Python installation.

```bash
# Navigate to the project directory
cd /path/to/pencil_platform

# Create a virtual environment named '.venv'
python3 -m venv .venv

# Activate the environment. Your shell prompt will change.
source .venv/bin/activate
```
*(To leave the environment later, simply type `deactivate`)*

### Step 2: Install Required Packages

The tool depends on a few standard Python libraries. Create a file named `requirements.txt` with the following content:

**File: `requirements.txt`**
```
pyyaml
jinja2
loguru
```

Now, install these packages using `pip`:
```bash
pip install -r requirements.txt
```

### Step 3: Configure Your Experiment

All experiment configurations are located in the `config/` directory. The most important file is the `plan/sweep.yaml` inside your experiment's folder.

For example, to configure the `shocktube_phase1` experiment, you would edit:
`config/shocktube_phase1/plan/sweep.yaml`

This file defines:
-   The base directories on the HPC.
-   The SBATCH parameters for the submission script.
-   The parameters you want to sweep over.

You can also edit the base configuration files in `config/shocktube_base/in/` to change parameters that are common to all runs in the suite.

### Step 4: Generate the Simulation Suite

With your environment activated and your plan configured, run the main Python script.

**Option A: Interactive Mode**

If you run the script without arguments, it will find all available experiments and ask you to choose one.
```bash
python main.py
```
**Output:**
```
Available experiments:
  1: shocktube_phase1
Please choose an experiment number: 1
```

**Option B: Direct Mode**

Provide the name of the experiment directly as a command-line argument.
```bash
python main.py shocktube_phase1
```

**Option C: Test Mode**

To do a quick test, you can generate just the first few runs of the suite using the `--test` flag. This is highly recommended before generating a full suite.
```bash
# Generate the first 2 runs (default)
python main.py shocktube_phase1 --test

# Generate only the first run
python main.py shocktube_phase1 --test 1
```

### Step 5: Transfer and Submit on the HPC

The script will generate a new directory inside `runs/`. For example: `runs/shocktube_phase1/`. This directory is a self-contained package.

1.  **Copy the directory to the HPC** (e.g., Mahti):
    ```bash
    # Run this from your local machine
    rsync -avz --progress runs/shocktube_phase1/ your_user@mahti.csc.fi:/scratch/project_XXXX/chau/runs/
    ```

2.  **Submit the job on the HPC:**
    ```bash
    # Log in to Mahti
    ssh your_user@mahti.csc.fi

    # Navigate to the directory you just copied
    cd /scratch/project_XXXX/chau/runs/shocktube_phase1

    # Submit the master script to the SLURM scheduler
    sbatch submit_suite.sh
    ```
This single command will launch the entire array of simulations.

---

## 2. The `uv` Approach (A Faster Alternative)

`uv` is a modern, extremely fast tool that combines the functionality of `pip` and `venv`. If you have it installed (`pip install uv`), it can simplify the setup steps.

**The process is the same as the classical approach, but steps 1 and 2 are replaced by:**

### Step 1 & 2 (Combined): Setup and Installation with `uv`

```bash
# Navigate to the project directory
cd /path/to/pencil_platform

# Create and activate the virtual environment in one step
uv venv

# Install dependencies (uv reads requirements.txt automatically)
uv pip install -r requirements.txt
```
From here, proceed with **Step 3: Configure Your Experiment** and onward from the classical guide. The workflow is identical, but the setup is faster.

---

## 3. The Snakemake Approach (For Full HPC Automation)

This is the most powerful and recommended method for running large-scale experiments on an HPC cluster like Mahti. Snakemake transitions from being a simple file generator to a complete **workflow manager**.

### Why Use Snakemake for This?

-   **Full Automation:** Instead of you manually submitting a script, you submit Snakemake. Snakemake then submits all 192 jobs to SLURM on your behalf.
-   **Intelligent Execution:** It automatically determines which simulations need to be run. If some runs have already completed successfully, it will skip them.
-   **Robust Error Handling:** If a single simulation job fails, Snakemake stops and reports the exact failure. You can fix the issue and resume the workflow, and it will only restart the failed and downstream jobs.
-   **End-to-End Pipelines:** This setup is the foundation for a full scientific pipeline. You can easily add new rules that depend on the simulation output to perform automated post-processing, data analysis, and plotting.

### Step 1: One-Time Profile Setup

To allow Snakemake to communicate with the SLURM scheduler, you need a "SLURM profile". This is a one-time setup.

1.  **Create the profile directory:**
    ```bash
    mkdir -p .config/snakemake/slurm
    ```

2.  **Create the profile's configuration file:**
    **File: `.config/snakemake/slurm/config.yaml`**
    ```yaml
    # This file tells Snakemake how to construct sbatch commands.
    # It sets default resources that can be overridden by rules in the Snakefile.
    cluster: "sbatch --account={resources.account} --partition={resources.partition} --time={resources.time} --nodes={resources.nodes} --ntasks={resources.ntasks} --cpus-per-task={resources.cpus_per_task}"
    jobs: 100 # Maximum number of jobs to have submitted to the queue at one time.
    default-resources:
      - account="project_2008296" # YOUR default account
      - partition="small"
      - time="00:15:00"
      - ntasks=1
      - cpus_per_task=1
      - nodes=1
    ```

### Step 2: How to Run the Entire Suite with Snakemake

The `Snakefile` is now the main entry point. It reads your experiment plan just like `main.py`.

1.  **Activate your environment** with Snakemake installed (see classical guide).

2.  **Perform a Dry Run (CRUCIAL FIRST STEP):**
    This command is extremely powerful. It will show you all 192 simulation jobs that Snakemake plans to run and the order of operations, without actually submitting anything.
    ```bash
    # For the shocktube_phase1 experiment
    snakemake --profile .config/slurm --config experiment_name=shocktube_phase1 -n
    ```

3.  **Execute the Full Workflow on Mahti:**
    This single command submits a "master" Snakemake job to the cluster. This master job will then manage submitting all 192 simulation jobs to SLURM.
    ```bash
    snakemake --profile .config/slurm --config experiment_name=shocktube_phase1
    ```
    You can log out, and Snakemake will continue to manage your workflow on the cluster.

4.  **Run a Small Test:**
    To test the full end-to-end process with just 2 runs, you can pass the `limit` config:
    ```bash
    snakemake --profile .config/slurm --config experiment_name=shocktube_phase1 limit=2
    ```

This is the modern, reproducible, and scalable way to manage computational campaigns.
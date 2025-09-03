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





# Planning Experiments with `plan.yaml`

The `plan.yaml` file is the heart of the automation system. It provides a powerful and flexible way to define large, complex suites of simulations from a single, human-readable file. This guide explains the key concepts of **Parameter Sweeps** and **Branches**.

## The Core Idea

The generator works by starting with a **`base_experiment`** configuration and programmatically applying a series of modifications to it to generate each unique run. This process is defined by two main sections in the `plan.yaml`:
1.  `parameter_sweeps`: Defines the combinations of numerical parameter values to test.
2.  `branches`: Defines a set of distinct, fundamental configurations under which the entire parameter sweep will be run.

The total number of simulations generated is **(number of sweep combinations) x (number of branches)**.

---

## 1. Defining Parameter Sweeps

The `parameter_sweeps` section is a list of "sweep operations". The results of all operations are combined to create the final set of unique parameter combinations.

### Sweep Type 1: Product Sweep

This is the most common type of sweep, used for exploring a grid of independent parameters. The system will generate a run for every possible combination of the values.

**Concept:** For each value of `param_A`, run it against every value of `param_B`.

**Example:**
To test two different `nu_shock` values and two `chi_shock` values, you would define two `product` sweeps.

```yaml
parameter_sweeps:
  - type: product
    variable: nu_shock
    values: [0.1, 0.5]
  - type: product
    variable: chi_shock
    values: [1.0, 5.0]
```

**Result:** This will produce `2 * 2 = 4` unique parameter combinations, which will be reflected in the generated directory names:
-   `..._nu0.1_chi1.0`
-   `..._nu0.1_chi5.0`
-   `..._nu0.5_chi1.0`
-   `..._nu0.5_chi5.0`

### Sweep Type 2: Linked Sweep

This is a more specialized sweep used when you want multiple parameters to vary together, taking on the same value for each run.

**Concept:** For each value in the list, set `param_A`, `param_B`, and `param_C` to that same value.

**Example:**
To run simulations where `nu_shock`, `chi_shock`, and `diffrho_shock` are always equal, you use a single `linked` sweep.

```yaml
parameter_sweeps:
  - type: linked
    variables: [nu_shock, chi_shock, diffrho_shock]
    values: [0.1, 0.5, 1.0, 5.0]
```

**Result:** This will produce **4** unique parameter combinations:
-   `..._nu0.1_chi0.1_diffrho0.1`
-   `..._nu0.5_chi0.5_diffrho0.5`
-   `..._nu1.0_chi1.0_diffrho1.0`
-   `..._nu5.0_chi5.0_diffrho5.0`

### Combining Sweep Types

You can combine different sweep types. The system will first calculate the results of each sweep block independently and then create the Cartesian product of those results.

**Example:** Combine the linked sweep from above with a product sweep for a different parameter.

```yaml
parameter_sweeps:
  # This block results in 4 parameter sets for the shock values.
  - type: linked
    variables: [nu_shock, chi_shock, diffrho_shock]
    values: [0.1, 0.5, 1.0, 5.0]

  # This block results in 2 parameter sets for the 'nt' value.
  - type: product
    variable: nt
    values: [1000, 2000]
```

**Result:** This will produce `4 * 2 = 8` unique parameter combinations. For example, the first linked set (`nu=0.1`, `chi=0.1`, `diff=0.1`) will be combined with each value of `nt`:
-   `..._nu0.1_chi0.1_diffrho0.1_nt1000`
-   `..._nu0.1_chi0.1_diffrho0.1_nt2000`
-   And so on for the other linked sets.

---

## 2. Defining Branches

The `branches` section is for defining fundamentally different simulation setups. The entire parameter sweep (as defined above) will be run for each branch. This is perfect for comparing major configuration changes, like the effect of a physical flag (`lmassdiff_fix`) or a completely different `Makefile.local` setup.

**Concept:** Run the entire suite of experiments under `Condition_A`, and then run the *entire suite again* under `Condition_B`.

**Example:**
To run the full linked sweep with `lmassdiff_fix` both enabled and disabled.

```yaml
branches:
  - name: "massfix"
    description: "Runs with the mass diffusion fix enabled."
    settings:
      # This section defines which file to modify and what to change.
      run_in.yaml:
        density_run_pars:
          lmassdiff_fix: true

  - name: "nomassfix"
    description: "Runs with the mass diffusion fix disabled."
    settings:
      run_in.yaml:
        density_run_pars:
          lmassdiff_fix: false
```

**Result:**
The `name` of each branch is prepended to the run directory name. If you use this with the linked sweep example, you will get `4 (sweep) * 2 (branch) = 8` total runs:
-   `..._massfix_nu0.1_chi0.1_diffrho0.1`
-   `..._nomassfix_nu0.1_chi0.1_diffrho0.1`
-   `..._massfix_nu0.5_chi0.5_diffrho0.5`
-   `..._nomassfix_nu0.5_chi0.5_diffrho0.5`
-   ...and so on.

By combining sweeps and branches, you can define very complex and comprehensive simulation campaigns in a structured and highly readable way.

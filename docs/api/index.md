# API Reference

Python API documentation for the Pencil Code Automated Experiment Manager.

## Overview

This reference documents the Python modules and classes that make up the platform. These can be imported and used programmatically if you need more control than the CLI provides.

## Core Modules

### suite_generator

The main module for generating simulation suites.

```python
from src.suite_generator import SuiteGenerator

# Create a generator instance
generator = SuiteGenerator('shocktube_phase1')

# Generate configurations
generator.generate_all_configs()

# Or generate limited set
generator.generate_configs(limit=5)
```

**Key Classes:**
- `SuiteGenerator`: Main class for configuration generation

**Key Methods:**
- `generate_all_configs()`: Generate all configurations
- `generate_configs(limit)`: Generate limited number of configurations
- `process_sweep_type_product()`: Process product sweeps
- `process_sweep_type_linked()`: Process linked sweeps

### read_config

Configuration file parsing utilities.

```python
from src.read_config import read_sweep_config, read_base_config

# Read sweep configuration
sweep_config = read_sweep_config('shocktube_phase1')

# Read base experiment configuration
base_config = read_base_config('shocktube_base')
```

**Key Functions:**
- `read_sweep_config(experiment_name)`: Read sweep.yaml
- `read_base_config(experiment_name)`: Read base configuration
- `validate_config(config)`: Validate configuration structure

### job_manager

HPC job submission and management.

```python
from src.job_manager import JobManager

# Create job manager
manager = JobManager('shocktube_phase1')

# Submit jobs
manager.submit_jobs()

# Check status
status = manager.check_job_status()
```

**Key Classes:**
- `JobManager`: Manages HPC job submission

**Key Methods:**
- `submit_jobs()`: Submit jobs to SLURM
- `check_job_status()`: Query job status
- `generate_sbatch_script()`: Create SLURM script

### analysis

Post-processing and data analysis.

```python
from src.analysis import analyze_results, compare_runs

# Analyze experiment results
results = analyze_results('shocktube_phase1')

# Compare different runs
comparison = compare_runs(['run_001', 'run_002'])
```

**Key Functions:**
- `analyze_results(experiment)`: Analyze simulation output
- `compare_runs(run_list)`: Compare multiple runs
- `extract_timeseries(run_dir)`: Extract time series data

### visualization

Plotting and visualization tools.

```python
from src.visualization import plot_comparison, generate_report

# Create comparison plot
plot_comparison(results, output='comparison.png')

# Generate analysis report
generate_report(experiment_name, output_dir='reports/')
```

**Key Functions:**
- `plot_comparison()`: Create comparison plots
- `generate_report()`: Generate analysis report
- `plot_timeseries()`: Plot time series data

## Usage Examples

### Example 1: Programmatic Configuration Generation

```python
from src.suite_generator import SuiteGenerator
from src.read_config import read_sweep_config

# Read configuration
config = read_sweep_config('my_experiment')

# Create generator
generator = SuiteGenerator('my_experiment')

# Generate specific number of configs
generator.generate_configs(limit=10)

# Access generated configurations
configs = generator.get_generated_configs()
for config in configs:
    print(f"Generated: {config['run_dir']}")
```

### Example 2: Custom Analysis Pipeline

```python
from src.analysis import analyze_results
from src.visualization import plot_comparison
import pandas as pd

# Analyze results
results = analyze_results('shocktube_phase1')

# Convert to DataFrame
df = pd.DataFrame(results)

# Custom analysis
df['ratio'] = df['energy_final'] / df['energy_initial']

# Visualize
plot_comparison(df, x='nu_shock', y='ratio', output='energy_ratio.png')
```

### Example 3: Automated Job Management

```python
from src.job_manager import JobManager
import time

# Create job manager
manager = JobManager('shocktube_phase1')

# Submit jobs
job_ids = manager.submit_jobs()

# Monitor progress
while not manager.all_jobs_complete():
    status = manager.check_job_status()
    print(f"Running: {status['running']}, Complete: {status['complete']}")
    time.sleep(60)  # Check every minute

print("All jobs complete!")
```

## Configuration Classes

### SweepConfig

Represents a parameter sweep configuration.

**Attributes:**
- `type`: Sweep type ('product' or 'linked')
- `variable(s)`: Parameter name(s) to sweep
- `values`: List of values to use

**Methods:**
- `validate()`: Validate sweep configuration
- `get_combinations()`: Get all parameter combinations

### BranchConfig

Represents a branch configuration.

**Attributes:**
- `name`: Branch name
- `description`: Branch description
- `settings`: Dictionary of settings to apply

**Methods:**
- `apply_to_config()`: Apply branch settings to configuration

## Utilities

### Path Utilities

```python
from src.constants import get_config_dir, get_output_dir

# Get configuration directory
config_dir = get_config_dir('shocktube_phase1')

# Get output directory
output_dir = get_output_dir('shocktube_phase1')
```

### Template Utilities

```python
from src.suite_generator import render_template

# Render a template
rendered = render_template('run.in.j2', context={'nu_shock': 0.5})
```

## Error Handling

The API raises specific exceptions for different error conditions:

```python
from src.suite_generator import SuiteGenerator, ConfigurationError

try:
    generator = SuiteGenerator('nonexistent_experiment')
    generator.generate_all_configs()
except ConfigurationError as e:
    print(f"Configuration error: {e}")
except IOError as e:
    print(f"File error: {e}")
```

**Common Exceptions:**
- `ConfigurationError`: Invalid configuration
- `TemplateError`: Template rendering error
- `SweepError`: Parameter sweep error

## Type Hints

All modules use type hints for better IDE support:

```python
from typing import Dict, List, Optional
from src.suite_generator import SuiteGenerator

def my_function(experiment: str, limit: Optional[int] = None) -> List[Dict]:
    """Function with type hints."""
    generator = SuiteGenerator(experiment)
    return generator.generate_configs(limit=limit)
```

## Advanced Topics

### Custom Sweep Types

You can extend the system with custom sweep types:

```python
from src.suite_generator import SuiteGenerator

class CustomSweepGenerator(SuiteGenerator):
    def process_sweep_type_custom(self, sweep_config):
        """Implement custom sweep logic."""
        # Your implementation here
        pass
```

### Custom Templates

Use custom template directories:

```python
generator = SuiteGenerator(
    'my_experiment',
    template_dir='/path/to/custom/templates'
)
```

### Custom Output Formatting

Override output formatting:

```python
class CustomGenerator(SuiteGenerator):
    def format_value_for_dirname(self, value):
        """Custom value formatting."""
        # Your custom formatting
        return str(value).replace('.', 'p')
```

## See Also

- [CLI Reference](../cli-reference.md) - Command-line interface
- [User Guide](../user-guide/index.md) - Usage documentation
- [Examples](../user-guide/examples.md) - Real-world examples

## Contributing

To contribute to the API:

1. Follow the coding standards in [Contributing Guide](../contributing.md)
2. Add type hints to all functions
3. Write docstrings for all public APIs
4. Add tests for new functionality
5. Update this documentation

## API Stability

- **Stable API**: Core functions in `suite_generator`, `read_config`
- **Experimental API**: Analysis and visualization modules may change
- **Internal API**: Functions with `_` prefix are internal and may change

## Documentation Generation

This API documentation can be automatically generated using tools like Sphinx:

```bash
# Install Sphinx
pip install sphinx sphinx-rtd-theme

# Generate documentation
cd docs/
sphinx-apidoc -o api/ ../src/
make html
```

---

**Note**: This is a high-level overview. For detailed function signatures and implementation details, refer to the source code or generate full API documentation with Sphinx.

# Contributing

Thank you for your interest in contributing to the Pencil Code Automated Experiment Manager!

## Getting Started

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:

```bash
git clone https://github.com/yourusername/pencil_platform.git
cd pencil_platform
```

3. Add the upstream repository:

```bash
git remote add upstream https://github.com/originalowner/pencil_platform.git
```

### Development Setup

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks (if available)
pre-commit install
```

## Development Workflow

### Creating a Branch

```bash
# Update your main branch
git checkout main
git pull upstream main

# Create a feature branch
git checkout -b feature/your-feature-name
```

### Making Changes

1. Make your changes in the appropriate files
2. Write or update tests
3. Update documentation if needed
4. Ensure code follows project style

### Testing Your Changes

```bash
# Run tests (if test suite exists)
pytest

# Test specific experiments
python main.py shocktube_phase1 --test 1

# Check linting
flake8 src/
pylint src/
```

### Committing Changes

Write clear, descriptive commit messages:

```bash
git add .
git commit -m "Add feature: description of your changes"
```

**Commit message guidelines:**
- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit first line to 72 characters
- Reference issues and pull requests where appropriate

### Submitting a Pull Request

1. Push your changes to your fork:

```bash
git push origin feature/your-feature-name
```

2. Go to GitHub and create a Pull Request
3. Fill out the PR template with:
   - Description of changes
   - Related issues
   - Testing performed
   - Screenshots (if UI changes)

## Code Style

### Python Style Guide

This project follows PEP 8 with some modifications:

- **Line length**: 100 characters (not 79)
- **Indentation**: 4 spaces
- **Quotes**: Double quotes preferred for strings
- **Imports**: Grouped and sorted
  ```python
  # Standard library
  import os
  import sys
  
  # Third-party
  import numpy as np
  import yaml
  
  # Local
  from src.suite_generator import SuiteGenerator
  ```

### Documentation Style

- Use Google-style docstrings:

```python
def generate_configs(experiment_name: str, limit: int = None) -> None:
    """Generate configuration files for an experiment.
    
    Args:
        experiment_name: Name of the experiment to generate
        limit: Maximum number of configurations to generate
        
    Returns:
        None
        
    Raises:
        ValueError: If experiment_name is not found
        IOError: If configuration files cannot be written
    """
    pass
```

- Use Markdown for documentation files
- Include code examples where helpful
- Keep language clear and concise

### YAML Style

- Use 2-space indentation
- Consistent quoting (prefer no quotes unless necessary)
- Comments where helpful

```yaml
# Good
parameter_sweeps:
  - type: product
    variable: nu_shock
    values: [0.1, 0.5, 1.0]
```

## Areas for Contribution

### High Priority

- Additional sweep types
- Improved error messages
- More comprehensive test coverage
- Performance optimizations
- Additional analysis tools

### Medium Priority

- Support for additional HPC schedulers
- Enhanced visualization tools
- Web-based configuration interface
- Integration with additional simulation codes

### Documentation

- Tutorials for specific use cases
- Video walkthroughs
- Additional examples
- Translation to other languages

## Project Structure

Understanding the codebase:

```
platform/
├── src/                    # Core source code
│   ├── suite_generator.py  # Main generation logic
│   ├── read_config.py      # Configuration parsing
│   ├── job_manager.py      # HPC job management
│   ├── analysis.py         # Post-processing
│   └── ...
├── config/                 # Example configurations
├── template/               # Jinja2 templates
│   ├── generic/           # Generic templates
│   └── shocktube/         # Problem-specific
├── docs/                   # Documentation
├── tests/                  # Test suite (if exists)
└── main.py                # CLI entry point
```

### Key Modules

- **suite_generator.py**: Core logic for generating simulation suites
- **read_config.py**: Parses YAML configuration files
- **job_manager.py**: Handles HPC job submission and monitoring
- **analysis.py**: Post-processing and data analysis
- **visualization.py**: Plotting and visualization tools

## Adding Features

### Adding a New Sweep Type

1. Update `src/suite_generator.py`:

```python
def process_sweep_type_newsweep(self, sweep_config):
    """Process a new type of parameter sweep.
    
    Args:
        sweep_config: Dictionary with sweep configuration
        
    Returns:
        List of parameter combinations
    """
    # Implementation here
    pass
```

2. Add tests
3. Update documentation in `docs/user-guide/parameter-sweeps.md`
4. Add example in configuration

### Adding a New Template

1. Create template file in `template/generic/` or problem-specific directory
2. Use Jinja2 syntax with clear variable names
3. Add documentation comments in template
4. Test with example configurations

### Adding Analysis Tools

1. Add module to `src/analysis.py` or create new file
2. Ensure it works with HDF5 data format
3. Add CLI option in `main.py`
4. Document in user guide

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_suite_generator.py

# Run with coverage
pytest --cov=src tests/
```

### Writing Tests

```python
import pytest
from src.suite_generator import SuiteGenerator

def test_product_sweep():
    """Test product sweep generation."""
    generator = SuiteGenerator('test_experiment')
    sweep = {
        'type': 'product',
        'variable': 'param',
        'values': [1, 2, 3]
    }
    result = generator.process_sweep_type_product(sweep)
    assert len(result) == 3
```

## Documentation

### Building Documentation

If using Sphinx:

```bash
cd docs/
make html
```

### Documentation Guidelines

- Keep explanations clear and beginner-friendly
- Include code examples
- Use consistent terminology
- Add screenshots for visual features
- Link between related pages

## Review Process

### What to Expect

1. **Automated checks**: CI/CD will run tests and linters
2. **Code review**: Maintainers will review your code
3. **Discussion**: Be open to feedback and suggestions
4. **Iteration**: You may need to make changes
5. **Merge**: Once approved, your PR will be merged

### Review Checklist

Before submitting, ensure:

- [ ] Code follows project style
- [ ] Tests pass
- [ ] Documentation is updated
- [ ] Commit messages are clear
- [ ] No unnecessary files included
- [ ] Branch is up to date with main

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors.

### Expected Behavior

- Be respectful and considerate
- Welcome newcomers
- Focus on constructive criticism
- Accept responsibility for mistakes

### Unacceptable Behavior

- Harassment or discrimination
- Trolling or inflammatory comments
- Public or private harassment
- Publishing others' private information

## Getting Help

### Communication Channels

- **Issues**: For bug reports and feature requests
- **Discussions**: For questions and general discussion
- **Pull Requests**: For code contributions

### Questions?

Don't hesitate to ask! You can:

1. Open an issue with the "question" label
2. Start a discussion on GitHub
3. Reach out to maintainers

## Recognition

Contributors will be:

- Listed in the project's contributors
- Acknowledged in release notes
- Credited in relevant documentation

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT License).

## Additional Resources

- [PEP 8 Style Guide](https://www.python.org/dev/peps/pep-0008/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Git Workflow](https://guides.github.com/introduction/flow/)
- [Writing Good Commit Messages](https://chris.beams.io/posts/git-commit/)

Thank you for contributing to make this project better!

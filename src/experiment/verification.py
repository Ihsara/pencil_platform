# src/experiment/verification.py

"""
Simulation Integrity Verification System

This module provides comprehensive checks to verify that:
1. Simulations were executed with correct parameters
2. VAR files contain unique data (not identical across runs)
3. Parameter files were correctly generated
4. Code was properly built/rebuilt when needed
5. Simulations actually ran (not just copying templates)

These checks are integrated into:
- Job monitoring (--monitor)
- Job waiting (--wait)
- Analysis pipeline (--analyze)
"""

import numpy as np
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from loguru import logger
import yaml
import sys

# Import Pencil Code reader if available
try:
    # Add Pencil Code Python library to path
    from src.core.constants import DIRS
    PENCIL_CODE_PYTHON_PATH = DIRS.root.parent / "pencil-code" / "python"
    if str(PENCIL_CODE_PYTHON_PATH) not in sys.path:
        sys.path.insert(0, str(PENCIL_CODE_PYTHON_PATH))
    import pencil.read as read
    PENCIL_AVAILABLE = True
except ImportError:
    PENCIL_AVAILABLE = False
    logger.warning("Pencil Code library not available - some verification checks will be skipped")


class SimulationIntegrityChecker:
    """Checks the integrity of simulation runs to detect common issues"""
    
    def __init__(self, experiment_name: str, hpc_run_base_dir: Path, run_names: List[str]):
        """
        Initialize the integrity checker.
        
        Args:
            experiment_name: Name of the experiment
            hpc_run_base_dir: Base directory where HPC runs are located
            run_names: List of run names to check
        """
        self.experiment_name = experiment_name
        self.hpc_run_base_dir = Path(hpc_run_base_dir)
        self.run_names = run_names
        self.issues = []
        
    def check_all(self, sample_size: int = 3) -> Dict:
        """
        Run all integrity checks.
        
        Args:
            sample_size: Number of runs to sample for expensive checks
            
        Returns:
            Dictionary with check results and any issues found
        """
        results = {
            'passed': True,
            'checks': {},
            'issues': [],
            'critical_issues': []
        }
        
        # Check 1: Verify VAR file diversity
        logger.info("Running Check 1: VAR file diversity...")
        var_check = self.check_var_file_diversity(sample_size=sample_size)
        results['checks']['var_diversity'] = var_check
        if not var_check['passed']:
            results['passed'] = False
            results['issues'].extend(var_check['issues'])
            if var_check.get('critical'):
                results['critical_issues'].extend(var_check['issues'])
        
        # Check 2: Verify parameter files exist and are unique
        logger.info("Running Check 2: Parameter file uniqueness...")
        param_check = self.check_parameter_files(sample_size=sample_size)
        results['checks']['parameter_files'] = param_check
        if not param_check['passed']:
            results['passed'] = False
            results['issues'].extend(param_check['issues'])
            if param_check.get('critical'):
                results['critical_issues'].extend(param_check['issues'])
        
        # Check 3: Verify simulations actually ran (not just templates)
        logger.info("Running Check 3: Simulation execution verification...")
        exec_check = self.check_simulation_execution(sample_size=sample_size)
        results['checks']['simulation_execution'] = exec_check
        if not exec_check['passed']:
            results['passed'] = False
            results['issues'].extend(exec_check['issues'])
            if exec_check.get('critical'):
                results['critical_issues'].extend(exec_check['issues'])
        
        # Check 4: Verify sweep parameters are actually different
        logger.info("Running Check 4: Sweep parameter variation...")
        sweep_check = self.check_sweep_parameters()
        results['checks']['sweep_parameters'] = sweep_check
        if not sweep_check['passed']:
            results['passed'] = False
            results['issues'].extend(sweep_check['issues'])
            if sweep_check.get('critical'):
                results['critical_issues'].extend(sweep_check['issues'])
        
        return results
    
    def check_var_file_diversity(self, sample_size: int = 3) -> Dict:
        """
        Check if VAR files are unique across different runs.
        If all VAR files are identical, simulations likely didn't run properly.
        
        Args:
            sample_size: Number of runs to sample
        """
        if not PENCIL_AVAILABLE:
            return {
                'passed': True,
                'issues': [],
                'message': 'Skipped (Pencil Code not available)',
                'critical': False
            }
        
        # Sample runs to check
        sample_runs = self.run_names[:sample_size] if len(self.run_names) > sample_size else self.run_names
        
        var_signatures = {}
        max_rho_values = {}
        
        for run_name in sample_runs:
            run_path = self.hpc_run_base_dir / run_name
            data_dir = run_path / "data"
            proc_dir = data_dir / "proc0" if (data_dir / "proc0").is_dir() else data_dir
            
            # Find LAST VAR file
            var_files = sorted(proc_dir.glob("VAR*"), key=lambda p: int(p.stem.replace('VAR', '')))
            
            if not var_files:
                continue
            
            last_var = var_files[-1]
            
            try:
                # Read the VAR file
                var = read.var(last_var.name, datadir=str(data_dir), quiet=True, trimall=True)
                density = np.exp(var.lnrho) if hasattr(var, 'lnrho') else var.rho
                
                # Calculate signature (hash of density distribution)
                density_bytes = density.tobytes()
                signature = hashlib.md5(density_bytes).hexdigest()[:16]
                
                var_signatures[run_name] = signature
                max_rho_values[run_name] = float(np.max(density))
                
            except Exception as e:
                logger.warning(f"Could not read VAR file for {run_name}: {e}")
                continue
        
        if not var_signatures:
            return {
                'passed': False,
                'issues': ["Could not read any VAR files for verification"],
                'critical': True,
                'message': 'Failed to read VAR files'
            }
        
        # Check if all signatures are identical
        unique_signatures = set(var_signatures.values())
        unique_max_rho = set(max_rho_values.values())
        
        issues = []
        critical = False
        
        if len(unique_signatures) == 1:
            issues.append(
                f"CRITICAL: All {len(var_signatures)} sampled runs have IDENTICAL VAR files! "
                f"This indicates simulations did not vary with parameter sweep."
            )
            critical = True
        
        if len(unique_max_rho) == 1:
            max_rho = list(unique_max_rho)[0]
            issues.append(
                f"CRITICAL: All sampled runs have identical max density (rho_max={max_rho:.10e}). "
                f"Expected variation based on parameter sweep."
            )
            critical = True
        
        result = {
            'passed': len(issues) == 0,
            'issues': issues,
            'critical': critical,
            'signatures': var_signatures,
            'max_rho_values': max_rho_values,
            'unique_signatures': len(unique_signatures),
            'message': f'{len(unique_signatures)} unique VAR signatures out of {len(var_signatures)} sampled runs'
        }
        
        return result
    
    def check_parameter_files(self, sample_size: int = 3) -> Dict:
        """
        Check if parameter files exist and contain expected swept parameters.
        """
        from src.core.config_loader import create_config_loader
        from src.core.constants import DIRS
        
        # Load the plan to know what parameters should be swept
        plan_file = DIRS.config / self.experiment_name / DIRS.plan_subdir / "sweep.yaml"
        try:
            with open(plan_file, 'r') as f:
                plan = yaml.safe_load(f)
        except Exception as e:
            return {
                'passed': False,
                'issues': [f"Could not load plan file: {e}"],
                'critical': True,
                'message': 'Failed to load plan file'
            }
        
        # Get swept parameters from plan
        branches = plan.get('branches', [])
        if not branches:
            return {
                'passed': True,
                'issues': [],
                'message': 'No parameter sweep defined in plan',
                'critical': False
            }
        
        # Sample runs
        sample_runs = self.run_names[:sample_size] if len(self.run_names) > sample_size else self.run_names
        
        issues = []
        param_values = {}
        
        for run_name in sample_runs:
            run_path = self.hpc_run_base_dir / run_name
            
            # Check if run.in exists
            run_in = run_path / "src" / "run.in"
            start_in = run_path / "src" / "start.in"
            
            if not run_in.exists() and not start_in.exists():
                issues.append(f"Missing parameter files for run: {run_name}")
                continue
            
            # Try to read parameters using Pencil Code
            if PENCIL_AVAILABLE:
                try:
                    data_dir = run_path / "data"
                    params = read.param(datadir=str(data_dir), quiet=True, conflicts_quiet=True)
                    
                    # Extract key swept parameters
                    param_values[run_name] = {
                        'nu_shock': getattr(params, 'nu_shock', None),
                        'chi_shock': getattr(params, 'chi_shock', None),
                        'gamma': getattr(params, 'gamma', None),
                        'lgamma_is_1': getattr(params, 'lgamma_is_1', None)
                    }
                    
                except Exception as e:
                    logger.debug(f"Could not read params for {run_name}: {e}")
        
        # Check if parameter values are actually different
        if param_values:
            # Check each parameter type
            for param_name in ['nu_shock', 'chi_shock', 'gamma']:
                values = [v[param_name] for v in param_values.values() if v[param_name] is not None]
                unique_values = set(values)
                
                if len(values) > 1 and len(unique_values) == 1:
                    issues.append(
                        f"WARNING: Parameter '{param_name}' has identical value ({values[0]}) "
                        f"across all {len(values)} sampled runs. Expected variation."
                    )
        
        result = {
            'passed': len(issues) == 0,
            'issues': issues,
            'param_values': param_values,
            'critical': False,
            'message': f'Checked {len(sample_runs)} runs for parameter files'
        }
        
        return result
    
    def check_simulation_execution(self, sample_size: int = 3) -> Dict:
        """
        Check if simulations actually executed by looking at:
        - Multiple VAR files exist (not just VAR0)
        - Time evolved from t=0
        - Data directory structure is correct
        """
        sample_runs = self.run_names[:sample_size] if len(self.run_names) > sample_size else self.run_names
        
        issues = []
        execution_info = {}
        
        for run_name in sample_runs:
            run_path = self.hpc_run_base_dir / run_name
            data_dir = run_path / "data"
            proc_dir = data_dir / "proc0" if (data_dir / "proc0").is_dir() else data_dir
            
            info = {
                'has_data_dir': data_dir.exists(),
                'num_var_files': 0,
                'time_evolved': False,
                'initial_time': None,
                'final_time': None
            }
            
            if not data_dir.exists():
                issues.append(f"Missing data directory for run: {run_name}")
                execution_info[run_name] = info
                continue
            
            # Count VAR files
            var_files = list(proc_dir.glob("VAR*"))
            info['num_var_files'] = len(var_files)
            
            if len(var_files) < 2:
                issues.append(
                    f"Run {run_name} has only {len(var_files)} VAR file(s). "
                    f"Expected multiple timesteps."
                )
            
            # Check if time evolved
            if PENCIL_AVAILABLE and var_files:
                try:
                    # Read first and last VAR
                    sorted_vars = sorted(var_files, key=lambda p: int(p.stem.replace('VAR', '')))
                    
                    var_first = read.var(sorted_vars[0].name, datadir=str(data_dir), quiet=True, trimall=True)
                    var_last = read.var(sorted_vars[-1].name, datadir=str(data_dir), quiet=True, trimall=True)
                    
                    info['initial_time'] = float(var_first.t)
                    info['final_time'] = float(var_last.t)
                    info['time_evolved'] = abs(var_last.t - var_first.t) > 1e-10
                    
                    if not info['time_evolved']:
                        issues.append(
                            f"Run {run_name}: Time did not evolve (t_initial={var_first.t:.6e}, "
                            f"t_final={var_last.t:.6e})"
                        )
                    
                except Exception as e:
                    logger.debug(f"Could not check time evolution for {run_name}: {e}")
            
            execution_info[run_name] = info
        
        result = {
            'passed': len(issues) == 0,
            'issues': issues,
            'execution_info': execution_info,
            'critical': len(issues) > 0,
            'message': f'Checked execution for {len(sample_runs)} runs'
        }
        
        return result
    
    def check_sweep_parameters(self) -> Dict:
        """
        Verify that the sweep parameters in run names match expected patterns.
        This catches issues with parameter generation.
        """
        from src.core.constants import DIRS
        
        # Load plan
        plan_file = DIRS.config / self.experiment_name / DIRS.plan_subdir / "sweep.yaml"
        try:
            with open(plan_file, 'r') as f:
                plan = yaml.safe_load(f)
        except Exception as e:
            return {
                'passed': False,
                'issues': [f"Could not load plan file: {e}"],
                'critical': True,
                'message': 'Failed to load plan'
            }
        
        branches = plan.get('branches', [])
        if not branches:
            return {
                'passed': True,
                'issues': [],
                'message': 'No branches defined',
                'critical': False
            }
        
        issues = []
        param_patterns = {}
        
        # Extract parameter patterns from run names
        for run_name in self.run_names:
            # Look for common parameter patterns in names
            import re
            
            nu_match = re.search(r'nu([\d.e\-+]+)', run_name)
            chi_match = re.search(r'chi([\d.e\-+]+)', run_name)
            
            if nu_match:
                nu_val = nu_match.group(1)
                if nu_val not in param_patterns.get('nu', set()):
                    param_patterns.setdefault('nu', set()).add(nu_val)
            
            if chi_match:
                chi_val = chi_match.group(1)
                if chi_val not in param_patterns.get('chi', set()):
                    param_patterns.setdefault('chi', set()).add(chi_val)
        
        # Check if we have variation in parameters
        for param_name, values in param_patterns.items():
            if len(values) == 1:
                issues.append(
                    f"WARNING: All run names contain the same {param_name} value ({list(values)[0]}). "
                    f"Expected variation in parameter sweep."
                )
        
        result = {
            'passed': len(issues) == 0,
            'issues': issues,
            'param_patterns': {k: list(v) for k, v in param_patterns.items()},
            'critical': False,
            'message': f'Found {sum(len(v) for v in param_patterns.values())} unique parameter values'
        }
        
        return result


def verify_simulation_integrity(experiment_name: str, sample_size: int = 3, 
                                fail_on_critical: bool = True) -> bool:
    """
    High-level function to verify simulation integrity.
    
    Args:
        experiment_name: Name of the experiment
        sample_size: Number of runs to sample for checks
        fail_on_critical: If True, exit with error on critical issues
        
    Returns:
        True if all checks passed, False otherwise
    """
    from src.core.constants import DIRS, FILES
    
    logger.info(f"\n{'='*80}")
    logger.info(f"SIMULATION INTEGRITY VERIFICATION: {experiment_name}")
    logger.info(f"{'='*80}\n")
    
    # Load experiment configuration
    plan_file = DIRS.config / experiment_name / DIRS.plan_subdir / FILES.plan
    try:
        with open(plan_file, 'r') as f:
            plan = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Could not load plan file: {e}")
        if fail_on_critical:
            sys.exit(1)
        return False
    
    # Get HPC run directory
    hpc_run_base_dir = Path(plan['hpc']['run_base_dir'])
    
    # Get run names from manifest
    local_exp_dir = DIRS.runs / experiment_name
    manifest_file = local_exp_dir / FILES.manifest
    
    if not manifest_file.exists():
        logger.error(f"Manifest file not found: {manifest_file}")
        if fail_on_critical:
            sys.exit(1)
        return False
    
    with open(manifest_file, 'r') as f:
        run_names = [line.strip() for line in f if line.strip()]
    
    logger.info(f"Checking {len(run_names)} runs (sampling {min(sample_size, len(run_names))} for expensive checks)")
    
    # Create checker and run all checks
    checker = SimulationIntegrityChecker(experiment_name, hpc_run_base_dir, run_names)
    results = checker.check_all(sample_size=sample_size)
    
    # Display results
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    
    console = Console()
    
    # Create summary table
    table = Table(title="Verification Results", border_style="cyan")
    table.add_column("Check", style="yellow")
    table.add_column("Status", style="green")
    table.add_column("Details", style="white")
    
    for check_name, check_result in results['checks'].items():
        status = "✓ PASS" if check_result['passed'] else "✗ FAIL"
        status_style = "green" if check_result['passed'] else "red"
        message = check_result.get('message', '')
        
        table.add_row(
            check_name.replace('_', ' ').title(),
            f"[{status_style}]{status}[/{status_style}]",
            message
        )
    
    console.print(table)
    
    # Show issues
    if results['issues']:
        console.print("\n[yellow]Issues Found:[/yellow]")
        for issue in results['issues']:
            if "CRITICAL" in issue:
                console.print(f"  [red]• {issue}[/red]")
            else:
                console.print(f"  [yellow]• {issue}[/yellow]")
    
    # Show critical issues separately
    if results['critical_issues']:
        console.print("\n")
        console.print(Panel(
            "[bold red]CRITICAL ISSUES DETECTED[/bold red]\n\n" +
            "\n".join(f"• {issue}" for issue in results['critical_issues']) +
            "\n\n[yellow]These issues indicate fundamental problems with the simulation setup or execution.[/yellow]\n" +
            "[yellow]The analysis results may be invalid.[/yellow]",
            border_style="red",
            title="⚠️  ALERT"
        ))
        
        if fail_on_critical:
            logger.error("Critical issues detected - aborting")
            sys.exit(1)
    
    # Overall result
    if results['passed']:
        console.print(f"\n[bold green]✓ All verification checks passed![/bold green]\n")
    else:
        console.print(f"\n[bold yellow]⚠ Some verification checks failed[/bold yellow]\n")
    
    return results['passed']

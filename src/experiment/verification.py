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
from rich.console import Console, Group
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich import box
import time

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
        self.console = Console()
        
        # Experiment-level check status
        self.experiment_checks = {
            'build': 'pending',
            'sweep_params': 'pending'
        }
        self.experiment_details = {
            'build': 'Checking...',
            'sweep_params': 'Checking...'
        }
        
        # Run-level check status
        self.run_status = {run: {
            'var_diversity': 'pending',
            'param_files': 'pending',
            'execution': 'pending'
        } for run in run_names}
        
    def _create_experiment_table(self) -> Table:
        """Create experiment-level status table"""
        table = Table(
            title=f"[bold cyan]Experiment Status[/bold cyan] - {self.experiment_name}",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta"
        )
        
        table.add_column("Check", style="yellow", width=30)
        table.add_column("Status", justify="center", width=10)
        table.add_column("Details", style="white", width=50)
        
        # Module compatibility check
        compat_status = self.experiment_checks.get('module_compat', 'pending')
        compat_details = self.experiment_details.get('module_compat', 'Checking...')
        table.add_row(
            "Module/Method Compatibility",
            self._format_status(compat_status),
            compat_details
        )
        
        # Build check
        build_status = self.experiment_checks.get('build', 'pending')
        build_details = self.experiment_details.get('build', 'Checking...')
        table.add_row(
            "Code Build (pc_build)",
            self._format_status(build_status),
            build_details
        )
        
        # Sweep parameters check
        sweep_status = self.experiment_checks.get('sweep_params', 'pending')
        sweep_details = self.experiment_details.get('sweep_params', 'Checking...')
        table.add_row(
            "Parameter Sweep Config",
            self._format_status(sweep_status),
            sweep_details
        )
        
        return table
    
    def _create_run_status_table(self) -> Table:
        """Create run-level status table"""
        table = Table(
            title=f"[bold cyan]Per-Run Verification[/bold cyan]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta"
        )
        
        table.add_column("Run Name", style="cyan", no_wrap=False, width=40)
        table.add_column("VAR Diversity", justify="center", width=14)
        table.add_column("Param Files", justify="center", width=12)
        table.add_column("Execution", justify="center", width=10)
        
        for run_name in self.run_names:
            # Truncate long run names intelligently
            display_name = self._truncate_run_name(run_name)
            status = self.run_status[run_name]
            
            table.add_row(
                display_name,
                self._format_status(status['var_diversity']),
                self._format_status(status['param_files']),
                self._format_status(status['execution'])
            )
        
        return table
    
    def _create_combined_view(self) -> Group:
        """Create combined view with both tables"""
        return Group(
            self._create_experiment_table(),
            Text(""),  # Spacer
            self._create_run_status_table()
        )
    
    def _truncate_run_name(self, name: str, max_len: int = 38) -> str:
        """Intelligently extract distinguishing parts of run names"""
        if len(name) <= max_len:
            return name
        
        # Extract the SWEPT PARAMETERS which distinguish runs
        import re
        
        # Extract key swept parameters
        extracted_parts = []
        
        # Extract nu values (e.g., nu9e-15)
        nu_match = re.search(r'nu(\d+e-\d+)', name)
        if nu_match:
            extracted_parts.append(f"nu{nu_match.group(1)}")
        
        # Extract chi values (e.g., chi9e-15)
        chi_match = re.search(r'chi(\d+e-\d+)', name)
        if chi_match:
            extracted_parts.append(f"chi{chi_match.group(1)}")
        
        # Extract rank if present
        rank_match = re.search(r'rank(\d+)', name)
        if rank_match:
            extracted_parts.append(f"r{rank_match.group(1)}")
        
        # Extract gamma variant
        if 'gamma_is_1' in name:
            extracted_parts.append('γ=1')
        elif 'default_gamma' in name:
            extracted_parts.append('γ≈1.67')
        
        # Build display name
        if extracted_parts:
            display_name = '_'.join(extracted_parts)
            if len(display_name) <= max_len:
                return display_name
        
        # Fallback: show first part and swept params
        parts = name.split('_')
        if len(parts) > 3:
            # Get resolution/setup + swept params
            swept = [p for p in parts if any(x in p for x in ['nu', 'chi', 'rank', 'gamma'])]
            if swept:
                display_name = '_'.join(swept[:4])
                if len(display_name) <= max_len:
                    return display_name
        
        # Last resort: default truncation
        return name[:max_len-3] + "..."
    
    def _format_status(self, status: str) -> str:
        """Format status with colors and symbols"""
        if status == 'pending':
            return "[dim white]○[/dim white]"
        elif status == 'pass':
            return "[bold green]✓[/bold green]"
        elif status == 'fail':
            return "[bold red]✗[/bold red]"
        elif status == 'skip':
            return "[dim yellow]-[/dim yellow]"
        return status
    
    def check_all(self, sample_size: int = 3) -> Dict:
        """
        Run all integrity checks with live table updates.
        
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
        
        # Create live display with combined view
        with Live(self._create_combined_view(), console=self.console, refresh_per_second=4) as live:
            
            # Check 0: Verify module/method compatibility (EXPERIMENT-LEVEL)
            logger.info("Running Check 0: Module/method compatibility...")
            compat_check = self.check_module_method_compatibility()
            results['checks']['module_method_compatibility'] = compat_check
            if not compat_check['passed']:
                results['passed'] = False
                results['issues'].extend(compat_check['issues'])
                if compat_check.get('critical'):
                    results['critical_issues'].extend(compat_check['issues'])
            live.update(self._create_combined_view())
            time.sleep(0.5)
            
            # Check 1: Verify code was built (EXPERIMENT-LEVEL)
            logger.info("Running Check 1: Build verification...")
            build_check = self.check_build_status()
            results['checks']['build'] = build_check
            if not build_check['passed']:
                results['passed'] = False
                results['issues'].extend(build_check['issues'])
                if build_check.get('critical'):
                    results['critical_issues'].extend(build_check['issues'])
            live.update(self._create_combined_view())
            time.sleep(0.5)
            
            # Check 2: Verify sweep parameters are different (EXPERIMENT-LEVEL)
            logger.info("Running Check 2: Sweep parameter variation...")
            sweep_check = self.check_sweep_parameters()
            results['checks']['sweep_parameters'] = sweep_check
            if not sweep_check['passed']:
                results['passed'] = False
                results['issues'].extend(sweep_check['issues'])
                if sweep_check.get('critical'):
                    results['critical_issues'].extend(sweep_check['issues'])
            live.update(self._create_combined_view())
            time.sleep(0.5)
            
            # Check 3: Verify VAR file diversity (RUN-LEVEL)
            logger.info("Running Check 3: VAR file diversity...")
            var_check = self.check_var_file_diversity(sample_size=sample_size)
            results['checks']['var_diversity'] = var_check
            if not var_check['passed']:
                results['passed'] = False
                results['issues'].extend(var_check['issues'])
                if var_check.get('critical'):
                    results['critical_issues'].extend(var_check['issues'])
            live.update(self._create_combined_view())
            time.sleep(0.5)
            
            # Check 4: Verify parameter files exist and are unique (RUN-LEVEL)
            logger.info("Running Check 4: Parameter file uniqueness...")
            param_check = self.check_parameter_files(sample_size=sample_size)
            results['checks']['parameter_files'] = param_check
            if not param_check['passed']:
                results['passed'] = False
                results['issues'].extend(param_check['issues'])
                if param_check.get('critical'):
                    results['critical_issues'].extend(param_check['issues'])
            live.update(self._create_combined_view())
            time.sleep(0.5)
            
            # Check 5: Verify simulations actually ran (RUN-LEVEL)
            logger.info("Running Check 5: Simulation execution verification...")
            exec_check = self.check_simulation_execution(sample_size=sample_size)
            results['checks']['simulation_execution'] = exec_check
            if not exec_check['passed']:
                results['passed'] = False
                results['issues'].extend(exec_check['issues'])
                if exec_check.get('critical'):
                    results['critical_issues'].extend(exec_check['issues'])
            live.update(self._create_combined_view())
        
        return results
    
    def check_module_method_compatibility(self) -> Dict:
        """
        Check if Makefile modules match the methods specified in run_in.yaml.
        This is EXPERIMENT-AGNOSTIC - it derives requirements from config files.
        
        Maps common Pencil Code methods to required modules:
        - 'hyper3' in iheatcond/ivisc -> requires VISCOSITY module
        - 'hyper3-nu-const' in ivisc -> requires VISCOSITY module  
        - 'shock' methods -> requires SHOCK module
        - etc.
        
        This is an EXPERIMENT-LEVEL check - configuration consistency.
        """
        from src.core.constants import DIRS
        
        # Method-to-module mapping (experiment-agnostic)
        METHOD_MODULE_MAP = {
            'hyper3': 'VISCOSITY',
            'hyper3-nu-const': 'VISCOSITY',
            'hyper3-csmesh': 'VISCOSITY',
            'shock': 'SHOCK',
            'shock_highorder': 'SHOCK',
        }
        
        issues = []
        required_modules = set()
        configured_modules = set()
        methods_found = {}
        
        # Load run_in.yaml to extract methods
        run_in_file = DIRS.config / self.experiment_name / DIRS.in_subdir / "run_in.yaml"
        try:
            with open(run_in_file, 'r') as f:
                run_in_config = yaml.safe_load(f)
        except Exception as e:
            self.experiment_checks['module_compat'] = 'fail'
            self.experiment_details['module_compat'] = 'Failed to load run_in.yaml'
            return {
                'passed': False,
                'issues': [f"CRITICAL: Could not load run_in.yaml: {e}"],
                'critical': True,
                'message': 'Failed to load configuration'
            }
        
        # Load Makefile_local.yaml to extract configured modules
        makefile_file = DIRS.config / self.experiment_name / DIRS.in_subdir / "Makefile_local.yaml"
        try:
            with open(makefile_file, 'r') as f:
                makefile_config = yaml.safe_load(f)
        except Exception as e:
            self.experiment_checks['module_compat'] = 'fail'
            self.experiment_details['module_compat'] = 'Failed to load Makefile_local.yaml'
            return {
                'passed': False,
                'issues': [f"CRITICAL: Could not load Makefile_local.yaml: {e}"],
                'critical': True,
                'message': 'Failed to load Makefile'
            }
        
        # Extract methods from run_in.yaml (agnostic approach)
        data = run_in_config.get('data', {})
        
        # Check all *_run_pars sections for method specifications
        for section_name, section_data in data.items():
            if not isinstance(section_data, dict):
                continue
                
            # Look for common method specification keys
            method_keys = ['ivisc', 'iheatcond', 'idiff', 'iforcing']
            
            for method_key in method_keys:
                if method_key in section_data:
                    method_value = section_data[method_key]
                    
                    # Handle both single strings and lists
                    if isinstance(method_value, str):
                        methods = [method_value]
                    elif isinstance(method_value, list):
                        methods = method_value
                    else:
                        continue
                    
                    # Track methods found
                    if section_name not in methods_found:
                        methods_found[section_name] = {}
                    methods_found[section_name][method_key] = methods
                    
                    # Map methods to required modules
                    for method in methods:
                        if method in METHOD_MODULE_MAP:
                            required_modules.add(METHOD_MODULE_MAP[method])
        
        # Extract configured modules from Makefile
        makefile_data = makefile_config.get('data', {})
        for module_key, module_value in makefile_data.items():
            # Skip if module is explicitly disabled (e.g., 'noviscosity')
            if not module_value.startswith('no'):
                configured_modules.add(module_key)
        
        # Check for mismatches
        missing_modules = required_modules - configured_modules
        
        if missing_modules:
            for module in missing_modules:
                # Find which methods require this module
                requiring_methods = [
                    method for method, req_mod in METHOD_MODULE_MAP.items()
                    if req_mod == module
                ]
                
                # Find where these methods are used
                locations = []
                for section, method_dict in methods_found.items():
                    for key, methods in method_dict.items():
                        for method in methods:
                            if method in requiring_methods:
                                locations.append(f"{section}.{key}={methods}")
                
                issues.append(
                    f"CRITICAL: Module '{module}' required but not in Makefile! "
                    f"Needed for methods: {requiring_methods}. "
                    f"Used in: {', '.join(locations)}"
                )
        
        # Update experiment-level status
        if len(issues) == 0:
            self.experiment_checks['module_compat'] = 'pass'
            self.experiment_details['module_compat'] = 'All required modules present'
        else:
            self.experiment_checks['module_compat'] = 'fail'
            self.experiment_details['module_compat'] = f'{len(missing_modules)} missing module(s)'
        
        result = {
            'passed': len(issues) == 0,
            'issues': issues,
            'required_modules': list(required_modules),
            'configured_modules': list(configured_modules),
            'missing_modules': list(missing_modules),
            'methods_found': methods_found,
            'critical': len(missing_modules) > 0,
            'message': f'Modules: {len(configured_modules)} configured, {len(required_modules)} required, {len(missing_modules)} missing'
        }
        
        return result
    
    def check_build_status(self) -> Dict:
        """
        Check if pc_build was executed and completed successfully for the experiment.
        This is an EXPERIMENT-LEVEL check - build happens once for all runs.
        """
        issues = []
        build_info = {}
        
        for run_name in self.run_names:
            run_path = self.hpc_run_base_dir / run_name
            src_dir = run_path / "src"
            
            info = {
                'has_src': src_dir.exists(),
                'has_executable': False,
                'has_makefile': False,
                'build_success': False
            }
            
            if src_dir.exists():
                # Check for compiled executable
                start_exe = src_dir / "start.x"
                run_exe = src_dir / "run.x"
                info['has_executable'] = start_exe.exists() or run_exe.exists()
                
                # Check for Makefile (indicates build was attempted)
                makefile = src_dir / "Makefile"
                info['has_makefile'] = makefile.exists()
                
                # Check for .build-history or .build-config (Pencil Code build artifacts)
                build_history = src_dir / ".build-history"
                build_config = src_dir / ".buildinfo"
                info['build_success'] = info['has_executable'] and (build_history.exists() or build_config.exists())
            
            build_info[run_name] = info
        
        # Check if any runs were built
        built_runs = sum(1 for info in build_info.values() if info['build_success'])
        
        if built_runs == 0:
            self.experiment_checks['build'] = 'fail'
            self.experiment_details['build'] = '0 runs built - pc_build may not have run'
            issues.append("CRITICAL: No runs appear to have been built successfully!")
        elif built_runs < len(self.run_names):
            self.experiment_checks['build'] = 'fail'
            self.experiment_details['build'] = f'Only {built_runs}/{len(self.run_names)} runs built'
            issues.append(f"Partial build failure: {built_runs}/{len(self.run_names)} runs built")
        else:
            self.experiment_checks['build'] = 'pass'
            self.experiment_details['build'] = f'All {built_runs} runs built successfully'
        
        result = {
            'passed': len(issues) == 0,
            'issues': issues,
            'build_info': build_info,
            'built_runs': built_runs,
            'total_runs': len(self.run_names),
            'critical': built_runs == 0,
            'message': f'{built_runs}/{len(self.run_names)} runs built successfully'
        }
        
        return result
    
    def check_sweep_parameters(self) -> Dict:
        """
        Verify that the sweep parameters in run names match expected patterns.
        This is an EXPERIMENT-LEVEL check - validates sweep configuration.
        """
        from src.core.constants import DIRS
        
        # Load plan
        plan_file = DIRS.config / self.experiment_name / DIRS.plan_subdir / "sweep.yaml"
        try:
            with open(plan_file, 'r') as f:
                plan = yaml.safe_load(f)
        except Exception as e:
            self.experiment_checks['sweep_params'] = 'fail'
            self.experiment_details['sweep_params'] = 'Failed to load plan file'
            return {
                'passed': False,
                'issues': [f"Could not load plan file: {e}"],
                'critical': True,
                'message': 'Failed to load plan'
            }
        
        branches = plan.get('branches', [])
        if not branches:
            self.experiment_checks['sweep_params'] = 'pass'
            self.experiment_details['sweep_params'] = 'No parameter sweep defined'
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
        total_unique = sum(len(v) for v in param_patterns.values())
        
        for param_name, values in param_patterns.items():
            if len(values) == 1:
                issues.append(
                    f"WARNING: All run names contain the same {param_name} value ({list(values)[0]}). "
                    f"Expected variation in parameter sweep."
                )
        
        # Update experiment-level status
        if len(issues) == 0:
            self.experiment_checks['sweep_params'] = 'pass'
            self.experiment_details['sweep_params'] = f'{total_unique} unique parameter values found'
        else:
            self.experiment_checks['sweep_params'] = 'fail'
            self.experiment_details['sweep_params'] = 'No parameter variation detected'
        
        result = {
            'passed': len(issues) == 0,
            'issues': issues,
            'param_patterns': {k: list(v) for k, v in param_patterns.items()},
            'critical': False,
            'message': f'Found {total_unique} unique parameter values'
        }
        
        return result
    
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
            # Mark all sampled runs as failed
            for run_name in sample_runs:
                self.run_status[run_name]['var_diversity'] = 'fail'
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
        
        # Update status for all runs
        if len(unique_signatures) == 1:
            # All sampled runs failed
            for run_name in sample_runs:
                self.run_status[run_name]['var_diversity'] = 'fail'
            # Mark non-sampled as skipped
            for run_name in self.run_names:
                if run_name not in sample_runs:
                    self.run_status[run_name]['var_diversity'] = 'skip'
        else:
            # Sampled runs passed
            for run_name in sample_runs:
                self.run_status[run_name]['var_diversity'] = 'pass'
            # Mark non-sampled as skipped
            for run_name in self.run_names:
                if run_name not in sample_runs:
                    self.run_status[run_name]['var_diversity'] = 'skip'
        
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
            
            # Check if run.in exists (runtime parameter files are in run directory root, not src/)
            run_in = run_path / "run.in"
            start_in = run_path / "start.in"
            
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
                        'nu_hyper3': getattr(params, 'nu_hyper3', None),
                        'chi_hyper3': getattr(params, 'chi_hyper3', None),
                        'diffrho_shock': getattr(params, 'diffrho_shock', None),
                        'gamma': getattr(params, 'gamma', None),
                        'lgamma_is_1': getattr(params, 'lgamma_is_1', None)
                    }
                    
                except Exception as e:
                    logger.warning(f"Could not read params for {run_name}: {e}")
        
        # Update status
        for run_name in sample_runs:
            if run_name in param_values:
                self.run_status[run_name]['param_files'] = 'pass'
            else:
                self.run_status[run_name]['param_files'] = 'fail'
        
        # Mark non-sampled as skipped
        for run_name in self.run_names:
            if run_name not in sample_runs:
                self.run_status[run_name]['param_files'] = 'skip'
        
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
        
        # Update status
        for run_name in sample_runs:
            if run_name in execution_info:
                info = execution_info[run_name]
                if info.get('time_evolved', False) or info.get('num_var_files', 0) > 1:
                    self.run_status[run_name]['execution'] = 'pass'
                else:
                    self.run_status[run_name]['execution'] = 'fail'
            else:
                self.run_status[run_name]['execution'] = 'fail'
        
        # Mark non-sampled as skipped
        for run_name in self.run_names:
            if run_name not in sample_runs:
                self.run_status[run_name]['execution'] = 'skip'
        
        result = {
            'passed': len(issues) == 0,
            'issues': issues,
            'execution_info': execution_info,
            'critical': len(issues) > 0,
            'message': f'Checked execution for {len(sample_runs)} runs'
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
    
    # Display results summary
    console = Console()
    
    # Create summary table
    table = Table(title="Verification Summary", border_style="cyan", box=box.ROUNDED)
    table.add_column("Check", style="yellow", width=30)
    table.add_column("Status", style="green", justify="center", width=10)
    table.add_column("Details", style="white", width=50)
    
    for check_name, check_result in results['checks'].items():
        status = "✓ PASS" if check_result['passed'] else "✗ FAIL"
        status_style = "green" if check_result['passed'] else "red"
        message = check_result.get('message', '')
        
        table.add_row(
            check_name.replace('_', ' ').title(),
            f"[{status_style}]{status}[/{status_style}]",
            message
        )
    
    console.print("\n")
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

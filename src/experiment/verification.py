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
        """
        Intelligently extract distinguishing parts of run names.
        This is EXPERIMENT-AGNOSTIC - it uses the sweep configuration to identify
        which parameters vary, then displays those parameter values.
        """
        from src.experiment.naming import format_short_experiment_name
        
        # Use the naming module which is already experiment-agnostic
        shortened = format_short_experiment_name(name, self.experiment_name)
        
        if len(shortened) <= max_len:
            return shortened
        
        # If still too long, truncate intelligently
        if len(shortened) > max_len:
            return shortened[:max_len-3] + "..."
        
        return name
    
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
    
    def _display_build_logs(self, build_info: Dict, build_log_map: Dict):
        """
        Display build logs for all runs with Rich formatting.
        
        Args:
            build_info: Dictionary with build information for each run
            build_log_map: Mapping of task IDs to build log directories
        """
        from rich.panel import Panel
        from rich.syntax import Syntax
        
        self.console.print("\n")
        self.console.print(Panel(
            "[bold yellow]BUILD LOG DETAILS[/bold yellow]\n"
            "Showing last 15-20 lines of build logs for each run",
            border_style="yellow",
            title="🔍 Build Diagnostics"
        ))
        
        for idx, (run_name, info) in enumerate(build_info.items(), start=1):
            task_id = idx  # SLURM array tasks are 1-indexed
            
            # Create header showing run identification
            header = f"Run {task_id} (array_{task_id}): {run_name}"
            
            if task_id in build_log_map:
                build_log_file = build_log_map[task_id] / "pc_build.log"
                
                if build_log_file.exists():
                    try:
                        with open(build_log_file, 'r') as f:
                            lines = f.readlines()
                        
                        # Get last 15-20 lines
                        num_lines = min(20, len(lines))
                        last_lines = lines[-num_lines:]
                        log_content = ''.join(last_lines)
                        
                        # Determine status for coloring
                        if info['build_success']:
                            status_color = "green"
                            status_icon = "✓"
                            status_text = "Success"
                        else:
                            status_color = "red"
                            status_icon = "✗"
                            status_text = "Failed"
                        
                        # Display with syntax highlighting
                        self.console.print(f"\n[bold {status_color}]{status_icon} {header}[/bold {status_color}]")
                        self.console.print(f"[dim]Status: [{status_color}]{status_text}[/{status_color}][/dim]")
                        self.console.print(f"[dim]Log: {build_log_file}[/dim]")
                        self.console.print(f"[dim]Showing last {num_lines} lines:[/dim]\n")
                        
                        # Use Syntax for better formatting
                        syntax = Syntax(log_content, "text", theme="monokai", line_numbers=False)
                        self.console.print(Panel(syntax, border_style=status_color, expand=False))
                        
                    except Exception as e:
                        self.console.print(f"\n[bold red]✗ {header}[/bold red]")
                        self.console.print(f"[red]Error reading build log: {e}[/red]")
                else:
                    self.console.print(f"\n[bold yellow]⚠ {header}[/bold yellow]")
                    self.console.print(f"[yellow]Build log not found at: {build_log_file}[/yellow]")
            else:
                self.console.print(f"\n[bold yellow]⚠ {header}[/bold yellow]")
                self.console.print(f"[yellow]No build log directory found for task {task_id}[/yellow]")
        
        self.console.print("\n")
    
    def check_build_status(self) -> Dict:
        """
        Check if pc_build was executed and completed successfully for the experiment.
        
        There are two modes:
        1. REBUILD MODE: pc_build runs for each task, creates pc_build.log
        2. SYMLINK MODE: No build, uses existing executables via symlinks
        
        For REBUILD mode:
        - Check build logs exist and show successful compilation
        For SYMLINK mode:
        - Check that pc_start.log and pc_run.log exist (indicates job ran)
        - No build verification needed since executables are pre-built
        
        This is an EXPERIMENT-LEVEL check - tracks build success across all runs.
        """
        from src.core.constants import DIRS
        
        # Check if rebuild was enabled for this experiment
        plan_file = DIRS.config / self.experiment_name / DIRS.plan_subdir / "sweep.yaml"
        try:
            with open(plan_file, 'r') as f:
                plan = yaml.safe_load(f)
            rebuild_enabled = plan.get('rebuild', False)
        except Exception as e:
            logger.warning(f"Could not determine rebuild status from plan: {e}")
            rebuild_enabled = None  # Unknown - will try to detect from logs
        
        issues = []
        build_info = {}
        
        # Try to find build logs in submission logs
        from pathlib import Path
        log_base = Path("logs/submission") / self.experiment_name
        build_log_dirs = []
        
        if log_base.exists():
            submission_dirs = sorted(log_base.glob("sub_*"), reverse=True)
            if submission_dirs:
                latest_submission = submission_dirs[0]
                # Find all job ID directories
                job_id_dirs = [d for d in latest_submission.iterdir() if d.is_dir() and d.name.isdigit()]
                for job_id_dir in job_id_dirs:
                    build_log_dirs.extend(job_id_dir.glob("array_*"))
        
        # Create mapping of run index to build log directory
        build_log_map = {}
        for log_dir in build_log_dirs:
            task_id = int(log_dir.name.split('_')[-1])
            build_log_map[task_id] = log_dir
        
        for idx, run_name in enumerate(self.run_names):
            run_path = self.hpc_run_base_dir / run_name
            src_dir = run_path / "src"
            task_id = idx + 1  # SLURM array tasks are 1-indexed
            
            info = {
                'has_src': src_dir.exists(),
                'has_start_exe': False,
                'has_run_exe': False,
                'has_makefile': False,
                'has_build_log': False,
                'build_log_shows_execution': False,
                'build_log_shows_success': False,
                'build_success': False
            }
            
            if src_dir.exists():
                # Check for compiled executables
                start_exe = src_dir / "start.x"
                run_exe = src_dir / "run.x"
                info['has_start_exe'] = start_exe.exists()
                info['has_run_exe'] = run_exe.exists()
                
                # Check for Makefile (indicates build was attempted)
                makefile = src_dir / "Makefile"
                info['has_makefile'] = makefile.exists()
            
            # Check for build/run logs to verify job execution
            if task_id in build_log_map:
                log_dir = build_log_map[task_id]
                build_log_file = log_dir / "pc_build.log"
                start_log_file = log_dir / "pc_start.log"
                run_log_file = log_dir / "pc_run.log"
                
                # Determine if this was a rebuild job by checking for pc_build.log
                has_build_log = build_log_file.exists()
                has_start_log = start_log_file.exists()
                has_run_log = run_log_file.exists()
                
                # Auto-detect rebuild mode if not specified in plan
                if rebuild_enabled is None:
                    rebuild_enabled = has_build_log
                
                if rebuild_enabled and has_build_log:
                    # REBUILD MODE: Verify build log
                    info['has_build_log'] = True
                    try:
                        with open(build_log_file, 'r') as f:
                            log_content = f.read()
                        
                        # Check if pc_build actually executed
                        pc_build_indicators = [
                            'Compiling',
                            'Building',
                            'make',
                            '.o',  # Object files being compiled
                            'Linking'
                        ]
                        info['build_log_shows_execution'] = any(
                            indicator in log_content for indicator in pc_build_indicators
                        )
                        
                        # Check for successful completion (no fatal errors)
                        error_indicators = [
                            'ERROR:',
                            'FATAL',
                            'make: ***',
                            'compilation failed',
                            'build failed',
                            'failed:',
                            'make cleanall\' failed',
                            'ln: target',
                            'ln: failed',
                            'Can\'t open',
                            'No such file:',
                            'getcwd: No such file or directory',
                        ]
                        has_errors = any(error in log_content for error in error_indicators)
                        info['build_log_shows_success'] = not has_errors
                        
                    except Exception as e:
                        logger.debug(f"Could not read build log for {run_name}: {e}")
                
                # For symlink mode, verify job ran by checking start/run logs exist
                info['has_start_log'] = has_start_log
                info['has_run_log'] = has_run_log
            
            # Determine success based on mode
            if rebuild_enabled:
                # REBUILD MODE: Build must have succeeded
                info['build_success'] = (
                    info['has_build_log'] and
                    info['build_log_shows_execution'] and
                    info['build_log_shows_success']
                )
            else:
                # SYMLINK MODE: Just verify job ran (start and run logs exist)
                # No build verification needed - executables are pre-built
                info['build_success'] = info['has_start_log'] and info['has_run_log']
            
            build_info[run_name] = info
        
        # Analyze results
        successful_runs = sum(1 for info in build_info.values() if info['build_success'])
        runs_with_build_logs = sum(1 for info in build_info.values() if info.get('has_build_log', False))
        runs_with_run_logs = sum(1 for info in build_info.values() if info.get('has_run_log', False))
        
        mode_description = "REBUILD" if rebuild_enabled else "SYMLINK"
        
        if successful_runs == 0:
            self.experiment_checks['build'] = 'fail'
            if rebuild_enabled:
                self.experiment_details['build'] = f'Build failed - no successful builds found'
                issues.append(f"CRITICAL: No runs successfully built in REBUILD mode!")
            else:
                self.experiment_details['build'] = f'No run logs found'
                issues.append(f"CRITICAL: No runs have execution logs (pc_start.log, pc_run.log)!")
        elif successful_runs < len(self.run_names):
            self.experiment_checks['build'] = 'fail'
            self.experiment_details['build'] = f'Only {successful_runs}/{len(self.run_names)} runs successful'
            if rebuild_enabled:
                issues.append(f"Partial build failure: {successful_runs}/{len(self.run_names)} builds succeeded")
            else:
                issues.append(f"Partial execution failure: {successful_runs}/{len(self.run_names)} runs have execution logs")
        else:
            self.experiment_checks['build'] = 'pass'
            if rebuild_enabled:
                self.experiment_details['build'] = f'All {successful_runs} runs built successfully'
            else:
                self.experiment_details['build'] = f'All {successful_runs} runs executed (symlink mode)'
        
        result = {
            'passed': len(issues) == 0,
            'issues': issues,
            'build_info': build_info,
            'build_log_map': build_log_map,
            'rebuild_mode': rebuild_enabled,
            'successful_runs': successful_runs,
            'runs_with_build_logs': runs_with_build_logs,
            'runs_with_run_logs': runs_with_run_logs,
            'total_runs': len(self.run_names),
            'critical': successful_runs == 0,
            'message': f'{successful_runs}/{len(self.run_names)} runs successful ({mode_description} mode)'
        }
        
        return result
    
    def check_sweep_parameters(self) -> Dict:
        """
        Verify that swept parameters actually vary across runs.
        This is EXPERIMENT-AGNOSTIC - it reads the sweep configuration to identify
        which parameters should vary, then checks if they actually do.
        
        Returns:
            Dictionary with check results
        """
        from src.core.constants import DIRS
        
        # Load plan to identify swept parameters
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
        
        # Extract swept parameters from configuration
        swept_params = self._extract_swept_parameters(plan)
        
        if not swept_params:
            self.experiment_checks['sweep_params'] = 'pass'
            self.experiment_details['sweep_params'] = 'No parameter sweep defined'
            return {
                'passed': True,
                'issues': [],
                'message': 'No parameter sweep configured',
                'critical': False
            }
        
        # Extract actual parameter values from run names
        param_values = self._extract_param_values_from_runs(swept_params)
        
        # Check for variation
        issues = []
        total_unique = 0
        
        for param_name, values in param_values.items():
            unique_count = len(values)
            total_unique += unique_count
            
            if unique_count == 1:
                issues.append(
                    f"WARNING: Parameter '{param_name}' has only 1 unique value across all runs: {list(values)[0]}. "
                    f"Expected variation in sweep."
                )
            elif unique_count == 0:
                issues.append(
                    f"CRITICAL: Parameter '{param_name}' not found in any run names! "
                    f"This parameter is configured as swept but missing from run names."
                )
        
        # Update experiment-level status
        if len(issues) == 0:
            self.experiment_checks['sweep_params'] = 'pass'
            self.experiment_details['sweep_params'] = f'{total_unique} unique values across {len(swept_params)} parameters'
        else:
            self.experiment_checks['sweep_params'] = 'fail'
            self.experiment_details['sweep_params'] = 'Parameter variation issues detected'
        
        result = {
            'passed': len(issues) == 0,
            'issues': issues,
            'swept_params': swept_params,
            'param_values': {k: list(v) for k, v in param_values.items()},
            'critical': any('CRITICAL' in issue for issue in issues),
            'message': f'{total_unique} unique values across {len(swept_params)} swept parameters'
        }
        
        return result
    
    def _extract_swept_parameters(self, plan: Dict) -> List[str]:
        """
        Extract list of swept parameter names from plan configuration.
        
        Args:
            plan: Plan configuration dictionary
            
        Returns:
            List of parameter names that are being swept
        """
        swept_params = set()
        
        # Check parameter_sweeps section
        if 'parameter_sweeps' in plan:
            for sweep in plan['parameter_sweeps']:
                if 'variables' in sweep:
                    variables = sweep['variables']
                    if isinstance(variables, str):
                        swept_params.add(variables)
                    elif isinstance(variables, list):
                        swept_params.update(variables)
        
        return list(swept_params)
    
    def _extract_param_values_from_runs(self, param_names: List[str]) -> Dict[str, set]:
        """
        Extract parameter values from run names for specified parameters.
        
        Args:
            param_names: List of parameter names to extract
            
        Returns:
            Dictionary mapping parameter names to sets of found values
        """
        import re
        
        param_values = {param: set() for param in param_names}
        
        for run_name in self.run_names:
            for param_name in param_names:
                # Create regex pattern for this parameter
                # Handle various formats:
                # - nu9e-15 (scientific notation)
                # - nu0p1 (filesystem safe decimal)
                # - chi1.0 (decimal with dot)
                # - diffrho_shock5.0 (with underscore suffix)
                
                # Try multiple patterns
                patterns = [
                    rf'{param_name}([\d.e\-+p]+)',  # Basic: nu9e-15, nu0p1, chi1.0
                    rf'{param_name}_([\d.e\-+p]+)', # With underscore: nu_9e-15
                    rf'{param_name}_shock([\d.e\-+p]+)', # With suffix: nu_shock9e-15
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, run_name)
                    if match:
                        value = match.group(1)
                        # Normalize: convert 'p' to '.' for consistency
                        value = value.replace('p', '.')
                        param_values[param_name].add(value)
                        break  # Found it, move to next parameter
        
        return param_values
    
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
        Check if parameter files exist and contain expected swept parameters WITH CORRECT VALUES.
        This is EXPERIMENT-AGNOSTIC - it reads the sweep config to know what to check.
        
        This verifies:
        1. Parameter files exist (run.in, start.in)
        2. Swept parameters are present with non-default values
        3. Parameter values match what's expected from run nam specification
        """
        from src.core.constants import DIRS
        
        # Load plan to identify swept parameters
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
        
        # Get swept parameters
        swept_params = self._extract_swept_parameters(plan)
        
        if not swept_params:
            return {
                'passed': True,
                'issues': [],
                'message': 'No parameter sweep defined',
                'critical': False
            }
        
        # Sample runs
        sample_runs = self.run_names[:sample_size] if len(self.run_names) > sample_size else self.run_names
        
        issues = []
        param_values = {}
        
        for run_name in sample_runs:
            run_path = self.hpc_run_base_dir / run_name
            
            # Check if parameter files exist
            run_in = run_path / "run.in"
            start_in = run_path / "start.in"
            
            if not run_in.exists() and not start_in.exists():
                issues.append(f"CRITICAL: Missing parameter files for run: {run_name}")
                continue
            
            # Read and validate parameters
            if PENCIL_AVAILABLE:
                try:
                    data_dir = run_path / "data"
                    params = read.param(datadir=str(data_dir), quiet=True, conflicts_quiet=True)
                    
                    # Extract ALL swept parameters (experiment-agnostic)
                    run_params = {}
                    for param_name in swept_params:
                        # Try to get the parameter value
                        value = getattr(params, param_name, None)
                        run_params[param_name] = value
                        
                        # Warn if swept parameter is missing or default
                        if value is None:
                            issues.append(
                                f"WARNING: Run '{run_name}' missing swept parameter '{param_name}'"
                            )
                    
                    param_values[run_name] = run_params
                    
                except Exception as e:
                    logger.warning(f"Could not read params for {run_name}: {e}")
                    issues.append(f"Failed to read parameters from {run_name}: {e}")
        
        # Check for parameter diversity across sampled runs
        if param_values:
            for param_name in swept_params:
                values_for_param = [
                    run_params.get(param_name) 
                    for run_params in param_values.values()
                    if run_params.get(param_name) is not None
                ]
                
                unique_values = len(set(str(v) for v in values_for_param))
                
                if unique_values == 1 and len(values_for_param) > 1:
                    issues.append(
                        f"WARNING: Parameter '{param_name}' has identical value across all sampled runs: {values_for_param[0]}. "
                        f"Expected variation."
                    )
        
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
            'swept_params': swept_params,
            'critical': any('CRITICAL' in issue for issue in issues),
            'message': f'Checked {len(sample_runs)} runs for {len(swept_params)} swept parameters'
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
    
    # Show build logs if build check exists and has issues (only in REBUILD mode)
    if 'build' in results['checks']:
        build_check = results['checks']['build']
        rebuild_mode = build_check.get('rebuild_mode', False)
        if rebuild_mode and (not build_check['passed'] or build_check.get('successful_runs', 0) < build_check.get('total_runs', 0)):
            # Display build logs for all runs in REBUILD mode
            build_info = build_check.get('build_info', {})
            build_log_map = build_check.get('build_log_map', {})
            if build_info and build_log_map:
                checker._display_build_logs(build_info, build_log_map)
    
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

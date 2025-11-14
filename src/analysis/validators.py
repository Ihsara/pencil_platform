"""
Simulation Validation System

This module provides robust validation of simulation integrity to prevent
incomplete or failed simulations from being incorrectly ranked as best performers.

Key Validations:
1. Minimum VAR file count - ensures simulation actually ran
2. Time coverage - checks if simulation reached expected end time
3. Physical evolution - verifies data changed from initial conditions
4. Numerical stability - detects blow-ups or NaN values

Architecture:
- SimulationHealth: Data class holding validation results
- SimulationValidator: Main validation engine with clear interface
- ValidationCriteria: Configuration for validation thresholds
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from enum import Enum
import numpy as np
from loguru import logger


class ValidationStatus(Enum):
    """Simulation validation status."""
    VALID = "valid"                    # Fully successful simulation
    WARNING = "warning"                # Usable but with concerns
    INCOMPLETE = "incomplete"          # Crashed unexpectedly mid-simulation
    FAILED_AS_EXPECTED = "failed"      # Failed at extreme parameters (NORMAL for sweeps)


@dataclass
class ValidationCriteria:
    """Configuration for simulation validation thresholds."""
    
    # Minimum number of VAR files for valid simulation
    min_var_files: int = 10
    
    # Minimum time coverage as fraction of expected end time (0.0 to 1.0)
    min_time_coverage: float = 0.9
    
    # Minimum evolution threshold - data must change from initial condition
    # Checks if max(|final - initial| / |initial|) > threshold
    min_evolution_threshold: float = 0.01
    
    # Maximum acceptable relative change (detects blow-ups)
    # If max(|final - initial| / |initial|) > threshold, simulation exploded
    max_evolution_threshold: float = 100.0
    
    # Whether to allow warnings to pass as valid
    allow_warnings: bool = False


@dataclass
class SimulationHealth:
    """Results of simulation validation check."""
    
    status: ValidationStatus
    
    # Raw metrics
    n_var_files: int
    time_coverage: float  # Fraction of expected end time reached (0.0 to 1.0)
    max_evolution: float  # Maximum relative change from initial condition
    has_nans: bool
    has_infs: bool
    
    # Computed flags
    sufficient_var_files: bool
    sufficient_time_coverage: bool
    has_physical_evolution: bool
    numerically_stable: bool
    
    # Issues detected
    issues: List[str]
    
    # Completeness factor for weighting (0.0 to 1.0)
    completeness_factor: float
    
    def is_valid(self) -> bool:
        """Check if simulation is considered valid."""
        return self.status == ValidationStatus.VALID
    
    def is_usable(self) -> bool:
        """Check if simulation can be used (valid or warning)."""
        return self.status in [ValidationStatus.VALID, ValidationStatus.WARNING]
    
    def summary(self) -> str:
        """Get human-readable validation summary."""
        status_symbol = {
            ValidationStatus.VALID: "✓",
            ValidationStatus.WARNING: "⚠",
            ValidationStatus.INCOMPLETE: "✗",
            ValidationStatus.FAILED_AS_EXPECTED: "○"
        }
        
        # Clear status descriptions
        status_desc = {
            ValidationStatus.VALID: "VALID (successful simulation)",
            ValidationStatus.WARNING: "WARNING (usable with penalty)",
            ValidationStatus.INCOMPLETE: "INCOMPLETE (unexpected crash)",
            ValidationStatus.FAILED_AS_EXPECTED: "FAILED AS EXPECTED (extreme parameters)"
        }
        
        lines = [
            f"{status_symbol[self.status]} Status: {status_desc[self.status]}",
            f"  VAR files: {self.n_var_files} ({'✓' if self.sufficient_var_files else '✗'})",
            f"  Time coverage: {self.time_coverage:.1%} ({'✓' if self.sufficient_time_coverage else '✗'})",
            f"  Physical evolution: {self.max_evolution:.2e} ({'✓' if self.has_physical_evolution else '✗'})",
            f"  Numerical stability: {'✓' if self.numerically_stable else '✗'}",
            f"  Completeness: {self.completeness_factor:.1%}"
        ]
        
        if self.issues:
            lines.append(f"  Issues: {'; '.join(self.issues)}")
        
        return '\n'.join(lines)


class SimulationValidator:
    """
    Validates simulation integrity and health.
    
    Prevents incomplete or failed simulations from being incorrectly
    ranked as best performers by detecting:
    - Simulations that barely ran (few VAR files)
    - Simulations that stopped early (low time coverage)
    - Simulations stuck at initial conditions (no evolution)
    - Simulations that blew up (numerical instability)
    
    Usage:
        validator = SimulationValidator(criteria)
        health = validator.validate(sim_data_list, expected_end_time)
        
        if health.is_valid():
            # Use simulation in ranking
            pass
        else:
            # Exclude or penalize simulation
            pass
    """
    
    def __init__(self, criteria: Optional[ValidationCriteria] = None):
        """
        Initialize validator with criteria.
        
        Args:
            criteria: Validation criteria. If None, uses defaults.
        """
        self.criteria = criteria or ValidationCriteria()
    
    def validate(
        self,
        sim_data_list: List[dict],
        expected_end_time: Optional[float] = None,
        variables: List[str] = ['rho', 'ux', 'pp', 'ee']
    ) -> SimulationHealth:
        """
        Perform comprehensive validation of simulation data.
        
        Args:
            sim_data_list: List of simulation data from VAR files
            expected_end_time: Expected final time (if known)
            variables: Physical variables to check for evolution
        
        Returns:
            SimulationHealth object with validation results
        """
        if not sim_data_list:
            return SimulationHealth(
                status=ValidationStatus.INVALID,
                n_var_files=0,
                time_coverage=0.0,
                max_evolution=0.0,
                has_nans=False,
                has_infs=False,
                sufficient_var_files=False,
                sufficient_time_coverage=False,
                has_physical_evolution=False,
                numerically_stable=True,
                issues=["No VAR files loaded"],
                completeness_factor=0.0
            )
        
        # Extract metrics
        n_var_files = len(sim_data_list)
        
        # Check time coverage
        final_time = sim_data_list[-1]['t']
        initial_time = sim_data_list[0]['t']
        
        if expected_end_time and expected_end_time > initial_time:
            time_coverage = (final_time - initial_time) / (expected_end_time - initial_time)
        else:
            # If no expected time, consider coverage based on VAR count
            time_coverage = min(1.0, n_var_files / self.criteria.min_var_files)
        
        # Check physical evolution
        max_evolution = self._check_evolution(sim_data_list, variables)
        
        # Check numerical stability
        has_nans, has_infs = self._check_numerical_stability(sim_data_list, variables)
        
        # Evaluate criteria
        sufficient_var_files = n_var_files >= self.criteria.min_var_files
        sufficient_time_coverage = time_coverage >= self.criteria.min_time_coverage
        has_physical_evolution = (
            max_evolution >= self.criteria.min_evolution_threshold and
            max_evolution <= self.criteria.max_evolution_threshold
        )
        numerically_stable = not (has_nans or has_infs)
        
        # Collect issues
        issues = []
        if not sufficient_var_files:
            issues.append(f"Only {n_var_files} VAR files (need ≥{self.criteria.min_var_files})")
        if not sufficient_time_coverage:
            issues.append(f"Only {time_coverage:.1%} time coverage (need ≥{self.criteria.min_time_coverage:.1%})")
        if not has_physical_evolution:
            if max_evolution < self.criteria.min_evolution_threshold:
                issues.append(f"Insufficient evolution ({max_evolution:.2e} < {self.criteria.min_evolution_threshold:.2e})")
            elif max_evolution > self.criteria.max_evolution_threshold:
                issues.append(f"Simulation blew up (evolution {max_evolution:.2e} > {self.criteria.max_evolution_threshold:.2e})")
        if not numerically_stable:
            if has_nans:
                issues.append("NaN values detected")
            if has_infs:
                issues.append("Inf values detected")
        
        # Determine overall status with clear distinction between failure types
        
        # Case 1: Immediate failure (0-1 VARs, no evolution) - EXPECTED at extreme parameters
        if n_var_files <= 1 and max_evolution < self.criteria.min_evolution_threshold:
            status = ValidationStatus.FAILED_AS_EXPECTED
            if not issues:
                issues = []
            issues.append("Simulation failed immediately at extreme parameter values (EXPECTED for parameter sweep)")
        
        # Case 2: Numerical instability (NaN/Inf) - ALWAYS INVALID
        elif not numerically_stable:
            status = ValidationStatus.INCOMPLETE
            if not issues:
                issues = []
            issues.append("Numerical instability detected")
        
        # Case 3: Incomplete run (started but didn't finish) - UNEXPECTED crash
        elif not sufficient_var_files:
            status = ValidationStatus.INCOMPLETE
            if not issues:
                issues = []
            issues.append(f"Simulation crashed unexpectedly after {n_var_files} timesteps")
        
        # Case 4: Completed but with concerns (partial time coverage or evolution issues)
        elif not sufficient_time_coverage or not has_physical_evolution:
            status = ValidationStatus.WARNING
        
        # Case 5: Fully successful
        else:
            status = ValidationStatus.VALID
        
        # Calculate completeness factor for weighting
        completeness_factor = self._calculate_completeness(
            n_var_files, time_coverage, max_evolution, numerically_stable
        )
        
        return SimulationHealth(
            status=status,
            n_var_files=n_var_files,
            time_coverage=time_coverage,
            max_evolution=max_evolution,
            has_nans=has_nans,
            has_infs=has_infs,
            sufficient_var_files=sufficient_var_files,
            sufficient_time_coverage=sufficient_time_coverage,
            has_physical_evolution=has_physical_evolution,
            numerically_stable=numerically_stable,
            issues=issues,
            completeness_factor=completeness_factor
        )
    
    def _check_evolution(self, sim_data_list: List[dict], variables: List[str]) -> float:
        """
        Check if simulation evolved from initial conditions.
        
        Returns:
            Maximum relative change across all variables
        """
        if len(sim_data_list) < 2:
            return 0.0
        
        initial_data = sim_data_list[0]
        final_data = sim_data_list[-1]
        
        max_relative_change = 0.0
        
        for var in variables:
            if var not in initial_data or var not in final_data:
                continue
            
            initial_vals = np.array(initial_data[var])
            final_vals = np.array(final_data[var])
            
            # Avoid division by zero
            initial_safe = np.where(np.abs(initial_vals) < 1e-10, 1e-10, initial_vals)
            
            relative_change = np.abs((final_vals - initial_vals) / initial_safe)
            max_change = np.max(relative_change)
            
            if np.isfinite(max_change):
                max_relative_change = max(max_relative_change, max_change)
        
        return float(max_relative_change)
    
    def _check_numerical_stability(
        self,
        sim_data_list: List[dict],
        variables: List[str]
    ) -> Tuple[bool, bool]:
        """
        Check for NaN or Inf values indicating numerical instability.
        
        Returns:
            Tuple of (has_nans, has_infs)
        """
        has_nans = False
        has_infs = False
        
        for sim_data in sim_data_list:
            for var in variables:
                if var not in sim_data:
                    continue
                
                data = np.array(sim_data[var])
                
                if np.any(np.isnan(data)):
                    has_nans = True
                if np.any(np.isinf(data)):
                    has_infs = True
                
                if has_nans and has_infs:
                    return has_nans, has_infs
        
        return has_nans, has_infs
    
    def _calculate_completeness(
        self,
        n_var_files: int,
        time_coverage: float,
        max_evolution: float,
        numerically_stable: bool
    ) -> float:
        """
        Calculate completeness factor for weighting (0.0 to 1.0).
        
        Combines multiple factors:
        - VAR file count (more is better)
        - Time coverage (closer to 1.0 is better)
        - Physical evolution (moderate is best)
        - Numerical stability (must be stable)
        """
        if not numerically_stable:
            return 0.0
        
        # VAR file factor (sigmoid curve, saturates at 2x min_var_files)
        var_factor = min(1.0, n_var_files / (2 * self.criteria.min_var_files))
        
        # Time coverage factor (linear with minimum threshold)
        time_factor = max(0.0, min(1.0, time_coverage / self.criteria.min_time_coverage))
        
        # Evolution factor (penalize both too little and too much)
        if max_evolution < self.criteria.min_evolution_threshold:
            # Too little evolution
            evo_factor = max_evolution / self.criteria.min_evolution_threshold
        elif max_evolution > self.criteria.max_evolution_threshold:
            # Too much evolution (blow-up)
            evo_factor = max(0.0, 1.0 - (max_evolution - self.criteria.max_evolution_threshold) / self.criteria.max_evolution_threshold)
        else:
            # Good evolution
            evo_factor = 1.0
        
        # Combine factors with weights
        # Prioritize: time coverage > VAR count > evolution
        completeness = (
            0.5 * time_factor +
            0.3 * var_factor +
            0.2 * evo_factor
        )
        
        return float(np.clip(completeness, 0.0, 1.0))

# src/error_metrics.py

"""
Modular error calculation system for comparing numerical and analytical solutions.

Implements various error norms including L1 (mean absolute error) and L2 (root mean square error)
as described in Gent et al. (2018) for shock tube test convergence analysis.

Reference:
    Gent, F.A. et al. (2018). "Modelling supernova driven turbulence."
    Geophysical and Astrophysical Fluid Dynamics. Equation (23) for L1 norm.
"""

import numpy as np
from typing import Callable, Dict
from loguru import logger


# ============================================================
# ERROR METRIC FUNCTIONS
# ============================================================

def l1_norm(numerical: np.ndarray, analytical: np.ndarray) -> float:
    """
    Calculate L1 error norm (mean absolute error).
    
    L1 = (1/N) * Σ|qi - q̃i|
    
    This measures the average magnitude of errors across all grid points.
    
    Args:
        numerical: Numerical solution values
        analytical: Analytical solution values
        
    Returns:
        L1 error norm (scalar)
        
    Reference:
        Gent et al. (2018), Equation (23)
    """
    analytical_copy = np.where(analytical == 0, 1, analytical)  
    
    return np.mean(np.abs((numerical - analytical)/analytical_copy))


def l2_norm(numerical: np.ndarray, analytical: np.ndarray) -> float:
    """
    Calculate L2 error norm (root mean square error).
    
    L2 = sqrt((1/N) * Σ(qi - q̃i)²)
    
    This measures the root mean square deviation, giving more weight to larger errors.
    
    Args:
        numerical: Numerical solution values
        analytical: Analytical solution values
        
    Returns:
        L2 error norm (scalar)
    """
    return np.sqrt(np.mean((numerical - analytical)**2))


def linf_norm(numerical: np.ndarray, analytical: np.ndarray) -> float:
    """
    Calculate L∞ error norm (maximum absolute error).
    
    L∞ = max|qi - q̃i|
    
    This measures the worst-case error at any single grid point.
    
    Args:
        numerical: Numerical solution values
        analytical: Analytical solution values
        
    Returns:
        L∞ error norm (scalar)
    """
    return np.max(np.abs(numerical - analytical))


def relative_l1_norm(numerical: np.ndarray, analytical: np.ndarray, 
                     epsilon: float = 1e-10) -> float:
    """
    Calculate relative L1 error norm.
    
    Relative L1 = (1/N) * Σ(|qi - q̃i| / |q̃i|)
    
    This normalizes errors by the analytical solution magnitude.
    
    Args:
        numerical: Numerical solution values
        analytical: Analytical solution values
        epsilon: Small value to avoid division by zero
        
    Returns:
        Relative L1 error norm (scalar)
    """
    analytical_safe = np.where(np.abs(analytical) < epsilon, epsilon, analytical)
    return np.mean(np.abs(numerical - analytical) / np.abs(analytical_safe))


def relative_l2_norm(numerical: np.ndarray, analytical: np.ndarray,
                     epsilon: float = 1e-10) -> float:
    """
    Calculate relative L2 error norm.
    
    Relative L2 = sqrt((1/N) * Σ((qi - q̃i) / q̃i)²)
    
    This normalizes the RMS error by the analytical solution magnitude.
    
    Args:
        numerical: Numerical solution values
        analytical: Analytical solution values
        epsilon: Small value to avoid division by zero
        
    Returns:
        Relative L2 error norm (scalar)
    """
    analytical_safe = np.where(np.abs(analytical) < epsilon, epsilon, analytical)
    return np.sqrt(np.mean(((numerical - analytical) / analytical_safe)**2))


def mean_absolute_percentage_error(numerical: np.ndarray, analytical: np.ndarray,
                                   epsilon: float = 1e-10) -> float:
    """
    Calculate Mean Absolute Percentage Error (MAPE).
    
    MAPE = (100/N) * Σ(|qi - q̃i| / |q̃i|)
    
    This expresses the error as a percentage.
    
    Args:
        numerical: Numerical solution values
        analytical: Analytical solution values
        epsilon: Small value to avoid division by zero
        
    Returns:
        MAPE in percentage (scalar)
    """
    return 100.0 * relative_l1_norm(numerical, analytical, epsilon)


# ============================================================
# ERROR METRIC REGISTRY
# ============================================================

class ErrorMetricRegistry:
    """
    Registry for error calculation metrics.
    
    This class implements a registry pattern that allows for:
    - Easy addition of new error metrics
    - Consistent interface for all metrics
    - Dynamic metric selection at runtime
    """
    
    def __init__(self):
        self._metrics: Dict[str, Callable] = {}
        self._descriptions: Dict[str, str] = {}
        
        # Register default metrics
        self._register_default_metrics()
    
    def _register_default_metrics(self):
        """Register all built-in error metrics."""
        self.register('l1', l1_norm, 
                     'L1 norm (mean absolute error)')
        
        self.register('l2', l2_norm,
                     'L2 norm (root mean square error)')
        
        self.register('linf', linf_norm,
                     'L∞ norm (maximum absolute error)')
        
        self.register('relative_l1', relative_l1_norm,
                     'Relative L1 norm')
        
        self.register('relative_l2', relative_l2_norm,
                     'Relative L2 norm')
        
        self.register('mape', mean_absolute_percentage_error,
                     'Mean Absolute Percentage Error')
    
    def register(self, name: str, metric_func: Callable, description: str = ""):
        """
        Register a new error metric.
        
        Args:
            name: Unique identifier for the metric
            metric_func: Function that takes (numerical, analytical) and returns scalar error
            description: Human-readable description of the metric
        """
        if name in self._metrics:
            logger.warning(f"Overwriting existing metric '{name}'")
        
        self._metrics[name] = metric_func
        self._descriptions[name] = description
        logger.debug(f"Registered error metric: {name}")
    
    def calculate(self, name: str, numerical: np.ndarray, 
                 analytical: np.ndarray) -> float:
        """
        Calculate error using specified metric.
        
        Args:
            name: Name of the registered metric
            numerical: Numerical solution values
            analytical: Analytical solution values
            
        Returns:
            Error value (scalar)
            
        Raises:
            KeyError: If metric name is not registered
        """
        if name not in self._metrics:
            available = ', '.join(self._metrics.keys())
            raise KeyError(f"Unknown error metric '{name}'. Available: {available}")
        
        return self._metrics[name](numerical, analytical)
    
    def calculate_all(self, numerical: np.ndarray, 
                     analytical: np.ndarray) -> Dict[str, float]:
        """
        Calculate all registered error metrics.
        
        Args:
            numerical: Numerical solution values
            analytical: Analytical solution values
            
        Returns:
            Dictionary mapping metric names to error values
        """
        results = {}
        for name in self._metrics:
            try:
                results[name] = self.calculate(name, numerical, analytical)
            except Exception as e:
                logger.warning(f"Failed to calculate metric '{name}': {e}")
                results[name] = np.nan
        
        return results
    
    def list_metrics(self) -> Dict[str, str]:
        """
        Get list of all registered metrics with descriptions.
        
        Returns:
            Dictionary mapping metric names to descriptions
        """
        return self._descriptions.copy()
    
    def get_metric_names(self) -> list:
        """Get list of registered metric names."""
        return list(self._metrics.keys())


# ============================================================
# GLOBAL REGISTRY INSTANCE
# ============================================================

# Create a global registry instance for easy access
METRIC_REGISTRY = ErrorMetricRegistry()


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def calculate_error(numerical: np.ndarray, analytical: np.ndarray,
                   metric: str = 'l1') -> float:
    """
    Convenience function to calculate a single error metric.
    
    Args:
        numerical: Numerical solution values
        analytical: Analytical solution values
        metric: Name of error metric to use (default: 'l1')
        
    Returns:
        Error value (scalar)
        
    Example:
        >>> error = calculate_error(sim_data, analytical_data, metric='l2')
    """
    return METRIC_REGISTRY.calculate(metric, numerical, analytical)


def calculate_all_errors(numerical: np.ndarray, 
                        analytical: np.ndarray) -> Dict[str, float]:
    """
    Convenience function to calculate all error metrics.
    
    Args:
        numerical: Numerical solution values
        analytical: Analytical solution values
        
    Returns:
        Dictionary mapping metric names to error values
        
    Example:
        >>> errors = calculate_all_errors(sim_data, analytical_data)
        >>> print(f"L1 error: {errors['l1']:.6e}")
        >>> print(f"L2 error: {errors['l2']:.6e}")
    """
    return METRIC_REGISTRY.calculate_all(numerical, analytical)


def register_custom_metric(name: str, metric_func: Callable, 
                          description: str = ""):
    """
    Convenience function to register a custom error metric.
    
    Args:
        name: Unique identifier for the metric
        metric_func: Function that takes (numerical, analytical) and returns scalar error
        description: Human-readable description of the metric
        
    Example:
        >>> def my_custom_error(num, ana):
        ...     return np.sum((num - ana)**4)
        >>> 
        >>> register_custom_metric('l4', my_custom_error, 'L4 norm')
    """
    METRIC_REGISTRY.register(name, metric_func, description)


# ============================================================
# HELPER FUNCTIONS FOR BATCH PROCESSING
# ============================================================

def calculate_errors_over_time(numerical_list: list, analytical_list: list,
                               metrics: list = None) -> Dict[str, list]:
    """
    Calculate error metrics across multiple timesteps.
    
    Args:
        numerical_list: List of numerical solution arrays (one per timestep)
        analytical_list: List of analytical solution arrays (one per timestep)
        metrics: List of metric names to calculate (default: ['l1', 'l2'])
        
    Returns:
        Dictionary mapping metric names to lists of error values over time
        
    Example:
        >>> errors_over_time = calculate_errors_over_time(
        ...     all_sim_data, all_analytical_data, 
        ...     metrics=['l1', 'l2', 'linf']
        ... )
        >>> plt.plot(errors_over_time['l1'], label='L1')
        >>> plt.plot(errors_over_time['l2'], label='L2')
    """
    if metrics is None:
        metrics = ['l1', 'l2']
    
    results = {metric: [] for metric in metrics}
    
    for num, ana in zip(numerical_list, analytical_list):
        for metric in metrics:
            try:
                error_val = METRIC_REGISTRY.calculate(metric, num, ana)
                results[metric].append(error_val)
            except Exception as e:
                logger.warning(f"Failed to calculate {metric} at timestep: {e}")
                results[metric].append(np.nan)
    
    return results


def calculate_convergence_rate(errors: list, resolutions: list, 
                               metric_name: str = 'l1') -> float:
    """
    Calculate convergence rate from error values at different resolutions.
    
    Convergence rate p is obtained from: error ∝ (resolution)^p
    
    Args:
        errors: List of error values at different resolutions
        resolutions: List of grid spacings (dx values)
        metric_name: Name of the metric for logging purposes
        
    Returns:
        Convergence rate (p in error ∝ dx^p)
        
    Example:
        >>> dx_values = [0.01, 0.005, 0.0025, 0.00125]
        >>> l1_errors = [1e-3, 2.5e-4, 6.25e-5, 1.56e-5]
        >>> rate = calculate_convergence_rate(l1_errors, dx_values)
        >>> print(f"Convergence rate: {rate:.2f}")
    """
    if len(errors) != len(resolutions):
        raise ValueError("errors and resolutions must have same length")
    
    if len(errors) < 2:
        raise ValueError("Need at least 2 data points to calculate convergence rate")
    
    # Use log-log fit: log(error) = p * log(dx) + c
    log_errors = np.log(errors)
    log_dx = np.log(resolutions)
    
    # Linear fit
    coeffs = np.polyfit(log_dx, log_errors, 1)
    convergence_rate = coeffs[0]
    
    logger.info(f"Convergence rate for {metric_name}: {convergence_rate:.3f}")
    logger.info(f"  (error ∝ dx^{convergence_rate:.3f})")
    
    return convergence_rate

# src/analysis.py

import numpy as np
import pandas as pd
from loguru import logger

def calculate_mse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculates the Mean Squared Error between two 1D arrays."""
    if y_true.shape != y_pred.shape:
        raise ValueError("Input arrays must have the same shape.")
    return np.mean((y_true - y_pred) ** 2)

def compare_simulation_to_analytical(sim_data: dict, analytical_data: dict) -> dict:
    """
    Compares simulation data against an analytical solution using Mean Squared Error.

    Args:
        sim_data (dict): Dictionary of processed simulation data arrays.
        analytical_data (dict): Dictionary of analytical solution arrays.

    Returns:
        dict: A dictionary of MSE values for each comparable variable.
    """
    metrics = {}
    comparable_vars = ['rho', 'ux', 'pp', 'ee']
    
    for var in comparable_vars:
        if var in sim_data and var in analytical_data:
            try:
                # Format the MSE to a reasonable number of significant figures
                metrics[f'MSE_{var}'] = f"{calculate_mse(analytical_data[var], sim_data[var]):.4e}"
            except ValueError as e:
                logger.warning(f"Could not compute MSE for '{var}': {e}")
    
    return metrics

def format_comparison_table(all_metrics: dict) -> tuple[str, str]:
    """
    Formats metrics from all runs into a single side-by-side comparison table.

    Args:
        all_metrics (dict): A dictionary where keys are run names and values are metric dictionaries.

    Returns:
        tuple[str, str]: A tuple containing the log summary string and the Markdown table string.
    """
    # Create a DataFrame where columns are run names and rows are metrics
    df = pd.DataFrame(all_metrics).T  # Transpose to get runs as rows initially
    df.index.name = "Run Name"
    df = df.T # Transpose back to have runs as columns
    
    # Format for logging
    log_summary = "Side-by-Side Analysis Metrics:\n" + df.to_string()
    
    # Format for Markdown report
    markdown_table = df.to_markdown()
    
    return log_summary, markdown_table
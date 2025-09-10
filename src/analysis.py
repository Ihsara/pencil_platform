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
                metrics[f'mse_{var}'] = calculate_mse(analytical_data[var], sim_data[var])
            except ValueError as e:
                logger.warning(f"Could not compute MSE for '{var}': {e}")
    
    return metrics

def format_report_tables(metrics: dict) -> tuple[str, str]:
    """
    Formats the analysis metrics into both a log-friendly string and a Markdown table.

    Args:
        metrics (dict): A dictionary of calculated metrics (e.g., from compare_simulation_to_analytical).

    Returns:
        tuple[str, str]: A tuple containing the log summary string and the Markdown table string.
    """
    df = pd.DataFrame.from_dict(metrics, orient='index', columns=['Value'])
    df.index.name = "Metric"
    
    # Format for logging
    log_summary = "Analysis Metrics:\n" + df.to_string()
    
    # Format for Markdown report
    markdown_table = df.to_markdown()
    
    return log_summary, markdown_table
"""
Logging utility module for file-based logging with loguru.

Provides detailed file logging while keeping terminal output clean.
Terminal display is handled separately via src.core.display module.
"""

from datetime import datetime
from pathlib import Path
import sys
from loguru import logger


def setup_file_logging(experiment_name: str, command_type: str) -> tuple[Path, Path]:
    """Setup dual file logging for a command: full detailed log + shorter summary log.
    
    This function configures loguru to write logs to TWO timestamped files:
    1. Full detailed log: Contains everything including verbose library output
    2. Shorter summary log: Contains only key progress info without verbose details
    
    Directory structure:
        logs/{command_type}/{experiment_name}/{timestamp}/{command_type}.log
        logs/{command_type}/{experiment_name}/{timestamp}/{command_type}_shorter.log
        
    Where timestamp is in format: sub_YYYYMMDDHHMM (e.g., sub_202510210025)
    
    Args:
        experiment_name: Name of the experiment (e.g., 'shocktube_phase1')
        command_type: Type of command being executed. Valid options:
            - 'analysis': For --analyze command
            - 'generation': For --generate command
            - 'submission': For --submit command
            - 'status': For --status command
    
    Returns:
        tuple[Path, Path]: Paths to (full_log_file, shorter_log_file)
        
    Example:
        >>> full_log, shorter_log = setup_file_logging('my_experiment', 'analysis')
        >>> logger.info("This message goes to console and both log files")
    """
    # Remove default console handler - terminal display handled by display.py
    logger.remove()
    
    # Add minimal console handler (only for errors/critical)
    logger.add(
        sys.stderr,
        format="<red>{level}:</red> {message}",
        level="ERROR",  # Only show errors in console
        colorize=True
    )
    
    # Create timestamp in format sub_YYYYMMDDHHMM
    timestamp = datetime.now().strftime("sub_%Y%m%d%H%M")
    
    # Create log directory structure with timestamp folder
    log_dir = Path("logs") / command_type / experiment_name / timestamp
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Create log file paths
    full_log_file = log_dir / f"{command_type}.log"
    summary_log_file = log_dir / f"{command_type}_summary.log"
    
    # Add FULL detailed log file sink (everything)
    logger.add(
        full_log_file,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",  # Log everything to full file
        backtrace=True,
        diagnose=True,
        enqueue=True,
        catch=True
    )
    
    # Add SUMMARY log file sink (key info only)
    logger.add(
        summary_log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="INFO",  # Only INFO and above
        backtrace=False,
        diagnose=False,
        enqueue=True,
        catch=True,
        filter=lambda record: not record["extra"].get("verbose", False)
    )
    
    # Log setup complete
    logger.info(f"Logging initialized for {experiment_name} - {command_type}")
    logger.info(f"Full log: {full_log_file}")
    logger.info(f"Summary log: {summary_log_file}")
    
    return full_log_file, summary_log_file


def remove_file_handlers():
    """Remove all file handlers from loguru.
    
    Useful for cleanup or when switching between different log files.
    """
    logger.remove()
    
    # Re-add minimal console handler (errors only)
    logger.add(
        sys.stderr,
        format="<red>{level}:</red> {message}",
        level="ERROR",
        colorize=True
    )


def setup_console_logging():
    """Setup console-only logging for simple operations.
    
    Use this when you don't need file logging, only terminal output.
    """
    logger.remove()
    logger.add(
        sys.stderr,
        format="<level>{level}:</level> {message}",
        level="INFO",
        colorize=True
    )

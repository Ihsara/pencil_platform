"""
Logging utility module for setting up file-based logging with loguru.

This module provides centralized logging configuration that saves all console
output to timestamped log files organized by command type and experiment name.
"""

from datetime import datetime
from pathlib import Path
from loguru import logger


def setup_file_logging(experiment_name: str, command_type: str) -> Path:
    """Setup file logging for a command.
    
    This function configures loguru to write logs to a timestamped file while
    maintaining the default console output. Each command invocation creates a
    new log file in the appropriate directory structure.
    
    Directory structure:
        logs/{command_type}/{experiment_name}/{timestamp}/{command_type}.log
        
    Where timestamp is in format: sub_YYYYMMDDHHMM (e.g., sub_202510210025)
    
    Args:
        experiment_name: Name of the experiment (e.g., 'shocktube_phase1')
        command_type: Type of command being executed. Valid options:
            - 'analysis': For --analyze command
            - 'generation': For --generate command
            - 'submission': For --submit command
            - 'status': For --status command
    
    Returns:
        Path: Path to the created log file
        
    Example:
        >>> log_file = setup_file_logging('my_experiment', 'analysis')
        >>> logger.info("This message goes to both console and file")
    """
    # Create timestamp in format sub_YYYYMMDDHHMM
    timestamp = datetime.now().strftime("sub_%Y%m%d%H%M")
    
    # Create log directory structure with timestamp folder
    log_dir = Path("logs") / command_type / experiment_name / timestamp
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Create log file path
    log_file = log_dir / f"{command_type}.log"
    
    # Add file sink to loguru (in addition to default console sink)
    # Using a detailed format for file logs with full context
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",  # Log everything to file
        backtrace=True,  # Include traceback info for errors
        diagnose=True,   # Show variable values in tracebacks
        enqueue=True,    # Thread-safe logging
        catch=True       # Catch exceptions during logging
    )
    
    # Log the setup (goes to both console and file)
    logger.info(f"📝 Logging to file: {log_file}")
    logger.debug(f"Log directory: {log_dir}")
    
    return log_file


def remove_file_handlers():
    """Remove all file handlers from loguru.
    
    This is useful for cleanup or when switching between different log files.
    Note: This only removes handlers added after the default handler (ID 0).
    """
    # Remove all handlers except the default console handler (ID 0)
    logger.remove()
    
    # Re-add default console handler
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

"""
Logging utility module for setting up file-based logging with loguru.

This module provides centralized logging configuration that saves all console
output to timestamped log files organized by command type and experiment name.
"""

from datetime import datetime
from pathlib import Path
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
    # Create timestamp in format sub_YYYYMMDDHHMM
    timestamp = datetime.now().strftime("sub_%Y%m%d%H%M")
    
    # Create log directory structure with timestamp folder
    log_dir = Path("logs") / command_type / experiment_name / timestamp
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Create log file paths
    full_log_file = log_dir / f"{command_type}.log"
    shorter_log_file = log_dir / f"{command_type}_shorter.log"
    
    # Add FULL detailed log file sink (everything)
    logger.add(
        full_log_file,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",  # Log everything to full file
        backtrace=True,
        diagnose=True,
        enqueue=True,
        catch=True,
        filter=lambda record: True  # Accept all messages
    )
    
    # Add SHORTER summary log file sink (no verbose/debug)
    # This filters out verbose library output and debug messages
    logger.add(
        shorter_log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="INFO",  # Only INFO and above (skip DEBUG/verbose)
        backtrace=False,
        diagnose=False,
        enqueue=True,
        catch=True,
        filter=lambda record: not record["extra"].get("verbose", False)  # Skip messages marked as verbose
    )
    
    # Log the setup (goes to both console and files)
    logger.info(f"📝 Logging to files:")
    logger.info(f"   ├─ Full log: {full_log_file}")
    logger.info(f"   └─ Shorter log: {shorter_log_file}")
    
    return full_log_file, shorter_log_file


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

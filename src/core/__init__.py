"""
Core module for the platform.

This module provides the unified communication interface and related utilities
for managing terminal output and logging across all platform operations.

Main Components:
--------------
- Communicator: Unified interface for task communication (terminal + logs)
- MessageLevel: Message severity levels
- TaskStatus: Task execution states

The communication interface automatically routes all output to both terminal
(via rich) and logs (via loguru), ensuring clean terminal output while
maintaining complete detailed logs.

Usage:
------
    from src.core import Communicator, MessageLevel
    
    comm = Communicator("experiment_name", "operation_type")
    comm.header("Task Title")
    
    task = comm.task_start("task_name", "Description")
    comm.message("Processing...", MessageLevel.INFO)
    comm.task_end(task, success=True)
    
    comm.summary()

Architecture:
------------
    Task/Operation → Communicator → [Terminal Display, File Logging]
                                      (terminal.py)    (logging.py)

The interface is modular, with separate components for:
- interface.py: Main Communicator class and enums
- terminal.py: Terminal display functionality (Rich)
- logging.py: File logging functionality (Loguru)
- display.py: Legacy display utilities (deprecated, use interface instead)
"""

# Main unified interface
from src.core.interface import (
    Communicator,
    MessageLevel,
    TaskStatus,
    create_communicator,
)

# Modular components (for advanced usage)
from src.core.logging import (
    setup_file_logging,
    remove_file_handlers,
    setup_console_logging,
)

from src.core.terminal import (
    create_console,
    display_header,
    display_message,
    display_validation_table,
    show_error,
    show_warning,
    show_success,
    show_info,
    TERM_WIDTH,
)

# Export main interface components
__all__ = [
    # Primary interface
    "Communicator",
    "MessageLevel",
    "TaskStatus",
    "create_communicator",
    
    # Logging utilities
    "setup_file_logging",
    "remove_file_handlers",
    "setup_console_logging",
    
    # Terminal utilities
    "create_console",
    "display_header",
    "display_message",
    "display_validation_table",
    "show_error",
    "show_warning",
    "show_success",
    "show_info",
    "TERM_WIDTH",
]

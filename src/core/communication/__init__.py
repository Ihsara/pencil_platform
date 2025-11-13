"""
Communication module - Unified interface for terminal and logging.

This module provides the core communication interface that automatically
routes all output to both terminal display and file logging.

Components:
- interface: Main Communicator class and enums
- terminal: Terminal display functions (Rich)
- logging: File logging configuration (Loguru)
"""

from src.core.communication.interface import (
    Communicator,
    MessageLevel,
    TaskStatus,
    create_communicator,
)

from src.core.communication.logging import (
    setup_file_logging,
    remove_file_handlers,
    setup_console_logging,
)

from src.core.communication.terminal import (
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

__all__ = [
    # Main interface
    "Communicator",
    "MessageLevel",
    "TaskStatus",
    "create_communicator",
    
    # Logging functions
    "setup_file_logging",
    "remove_file_handlers",
    "setup_console_logging",
    
    # Terminal functions
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

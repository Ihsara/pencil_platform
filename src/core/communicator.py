"""
DEPRECATED: This module is maintained for backward compatibility only.

Please use src.core.interface instead:
    from src.core.interface import Communicator, MessageLevel, TaskStatus
    
Or simply:
    from src.core import Communicator, MessageLevel, TaskStatus

This file now re-exports from the new modular interface for backward compatibility.
"""

# Re-export from the new interface module for backward compatibility
from src.core.interface import (
    Communicator,
    MessageLevel,
    TaskStatus,
    create_communicator,
)

# Re-export terminal width constant
from src.core.terminal import TERM_WIDTH

# Also export console for any legacy code that might use it
from src.core.terminal import create_console

console = create_console()

__all__ = [
    "Communicator",
    "MessageLevel",
    "TaskStatus",
    "create_communicator",
    "TERM_WIDTH",
    "console",
]

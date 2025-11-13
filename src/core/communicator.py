"""
DEPRECATED: This module is maintained for backward compatibility only.

Please use src.core.communication instead:
    from src.core.communication import Communicator, MessageLevel, TaskStatus
    
Or simply:
    from src.core import Communicator, MessageLevel, TaskStatus

This file now re-exports from the new communication subfolder for backward compatibility.
"""

# Re-export from the communication subfolder for backward compatibility
from src.core.communication import (
    Communicator,
    MessageLevel,
    TaskStatus,
    create_communicator,
    TERM_WIDTH,
    create_console,
)

# Also export console for any legacy code that might use it
console = create_console()

__all__ = [
    "Communicator",
    "MessageLevel",
    "TaskStatus",
    "create_communicator",
    "TERM_WIDTH",
    "console",
]

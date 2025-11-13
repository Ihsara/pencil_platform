# Core Communication Interface

This module provides the **unified communication interface** for all platform operations.

## Structure

```
src/core/
├── interface.py      # Main Communicator class (USE THIS)
├── terminal.py       # Terminal display functions (Rich)
├── logging.py        # File logging setup (Loguru)
├── communicator.py   # DEPRECATED - backward compatibility only
├── display.py        # DEPRECATED - legacy display utilities
└── __init__.py       # Module exports
```

## Quick Start

### Recommended Usage

```python
from src.core import Communicator, MessageLevel

# Create communicator for your operation
comm = Communicator("experiment_name", "operation_type")

# Display header
comm.header("Task Title", "Optional subtitle")

# Start a task
task = comm.task_start("task_id", "Task description")

# Send messages
comm.message("Processing data", MessageLevel.INFO)
comm.message("Something went wrong", MessageLevel.ERROR)

# Update progress
comm.task_progress(task, step=50, message="Halfway done")

# Complete task
comm.task_end(task, success=True)

# Show summary
comm.summary(stats={"Total": 100, "Errors": 0})
```

## Architecture

The interface automatically routes all output to **both** terminal and logs:

```
Your Code
    ↓
Communicator (interface.py)
    ├→ Terminal Display (terminal.py via Rich)
    └→ File Logging (logging.py via Loguru)
```

### Key Features

1. **Unified Interface**: Single point for all communication
2. **Automatic Routing**: Output goes to both terminal and logs
3. **Modular Design**: Separate concerns (interface, terminal, logging)
4. **Experiment-Agnostic**: Works with any experiment type
5. **Task Tracking**: Every task is registered and monitored

## Module Components

### interface.py (Primary)

Main communication interface with the `Communicator` class.

**Classes:**
- `Communicator`: Main interface class
- `MessageLevel`: Message severity levels (DEBUG, INFO, WARNING, ERROR, SUCCESS, CRITICAL)
- `TaskStatus`: Task execution states (PENDING, RUNNING, COMPLETED, FAILED, SKIPPED)

**Key Methods:**
- `header()`: Display operation header
- `message()`: Send message to terminal and/or logs
- `task_start()`: Begin a new task
- `task_progress()`: Update task progress
- `task_end()`: Complete a task
- `summary()`: Display operation summary
- `validation_table()`: Show validation results

### terminal.py (Modular)

Terminal display functionality using Rich.

**Functions:**
- `create_console()`: Create Rich console with fixed width (72 chars)
- `display_header()`: Show header with title and subtitle
- `display_message()`: Display formatted message
- `display_validation_table()`: Show validation results table
- `show_error()`, `show_warning()`, `show_success()`, `show_info()`: Quick message displays

**Constants:**
- `TERM_WIDTH = 72`: Fixed terminal width for optimal readability

### logging.py (Modular)

File logging configuration using Loguru.

**Functions:**
- `setup_file_logging()`: Configure file logging with timestamps
- `remove_file_handlers()`: Remove all file handlers
- `setup_console_logging()`: Setup console-only logging

**Log Structure:**
```
logs/
├── operation_type/
│   └── experiment_name/
│       └── sub_YYYYMMDDHHMM/
│           ├── operation_type.log         # Full detailed log
│           └── operation_type_summary.log # Key info only
```

### communicator.py (DEPRECATED)

**⚠️ This file is maintained for backward compatibility only.**

Old imports still work:
```python
from src.core.communicator import Communicator  # Still works
```

But prefer the new import:
```python
from src.core import Communicator  # Recommended
```

### display.py (DEPRECATED)

**⚠️ Legacy display utilities. Use `interface.py` instead.**

Contains old scene-based display classes. Kept for backward compatibility but not recommended for new code.

## Usage Patterns

### Pattern 1: Simple Operation

```python
from src.core import Communicator, MessageLevel

comm = Communicator("exp_name", "operation")
comm.header("Operation Title")

task = comm.task_start("task_name", "Task description")
comm.message("Starting process", MessageLevel.INFO)
# ... do work ...
comm.task_end(task, success=True)

comm.summary()
```

### Pattern 2: Progress Tracking

```python
from src.core import Communicator, MessageLevel

comm = Communicator("exp_name", "analysis")
comm.header("Analysis", "Processing runs")

task = comm.task_start("analyze", "Analyzing runs", total_steps=100)

for i in range(100):
    # Detailed logging (logs only)
    comm.message(
        f"Processing run_{i}",
        MessageLevel.DEBUG,
        detail=f"Loading VAR, computing errors",
        terminal=False  # Don't clutter terminal
    )
    
    # Progress update (terminal shows [i/100] XX%)
    comm.task_progress(task, step=i+1, message=f"run_{i:03d}")

comm.task_end(task, success=True)
comm.summary(stats={"Runs": 100})
```

### Pattern 3: Error Handling

```python
from src.core import Communicator, MessageLevel

comm = Communicator("exp_name", "operation")
comm.header("Operation with Error Handling")

task = comm.task_start("risky_task", "Processing data")

try:
    result = process_data()
    comm.message("Processing complete", MessageLevel.INFO)
    comm.task_end(task, success=True, result=result)
except Exception as e:
    comm.message(
        "Processing failed",
        MessageLevel.ERROR,
        detail=f"Exception: {type(e).__name__}: {str(e)}"
    )
    comm.task_end(task, success=False, error=str(e))

comm.summary()
```

### Pattern 4: Validation Checks

```python
from src.core import Communicator

comm = Communicator("exp_name", "validation")
comm.header("Validation")

checks = [
    ("Config file", True, "Found"),
    ("Parameters", True, "Valid"),
    ("Dependencies", False, "Missing numpy"),
]

comm.validation_table(checks)
```

## Message Levels

Use appropriate levels for different message types:

- `MessageLevel.DEBUG`: Technical details (logs only by default)
- `MessageLevel.INFO`: Important information
- `MessageLevel.WARNING`: Warnings
- `MessageLevel.ERROR`: Errors
- `MessageLevel.SUCCESS`: Success messages
- `MessageLevel.CRITICAL`: Critical failures

## Benefits

### For Developers
- ✓ Single interface for all output
- ✓ No need to manage separate logging/display calls
- ✓ Consistent across all operations
- ✓ Easy to extend with new features

### For Users
- ✓ Clean terminal output (concise, readable)
- ✓ Complete information in logs (for debugging)
- ✓ Progress tracking for long operations
- ✓ Clear status indicators

### For Debugging
- ✓ Full audit trail in log files
- ✓ Task registry for post-mortem analysis
- ✓ Detailed error information
- ✓ Timing data for performance analysis

## Migration from Legacy Code

### Old Code (Mixed Approaches)

```python
# Inconsistent output
logger.info("Processing run 1")
print("Run 1 complete")
from src.core.display import show_info
show_info("Processing run 2")
```

### New Code (Unified Interface)

```python
from src.core import Communicator, MessageLevel

comm = Communicator("exp", "analysis")
comm.header("Analysis")

task = comm.task_start("analyze", "Analyzing runs", total_steps=2)
comm.task_progress(task, step=1, message="run_1")
comm.task_progress(task, step=2, message="run_2")
comm.task_end(task, success=True)

comm.summary()
```

## Testing

```bash
# Run examples
python -m src.core.communicator_examples

# Quick test
python -c "
from src.core import Communicator, MessageLevel
comm = Communicator('test', 'test')
comm.header('Test')
task = comm.task_start('test', 'Testing', total_steps=3)
for i in range(3):
    comm.task_progress(task, step=i+1, message=f'step_{i}')
comm.task_end(task, success=True)
comm.summary()
"
```

## See Also

- [Full Documentation](../../docs/UNIFIED-COMMUNICATION-INTERFACE.md)
- [Examples](communicator_examples.py)

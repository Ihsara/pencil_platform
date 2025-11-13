"""
Unified Communication Interface for the Platform

This module provides the main communication interface that automatically routes
all output to both terminal (via rich) and logs (via loguru).

Architecture:
    Task/Operation → Interface → [Terminal Display, File Logging]

Key Components:
- Communicator: Main unified interface class
- MessageLevel: Severity levels for messages
- TaskStatus: Task execution states

Usage:
    from src.core.interface import Communicator, MessageLevel
    
    comm = Communicator("experiment_name", "operation_type")
    comm.header("Task Title")
    
    task = comm.task_start("task_name", "Description")
    comm.message("Processing...", MessageLevel.INFO)
    comm.task_end(task, success=True)
    
    comm.summary()
"""

from typing import Optional, Dict, Any
from enum import Enum
from loguru import logger
from rich.console import Console
from rich.table import Table
from rich import box
from pathlib import Path
import time

# Import modular components
from src.core.logging import setup_file_logging
from src.core.terminal import (
    create_console,
    display_header,
    display_message,
    display_validation_table,
    TERM_WIDTH
)


class MessageLevel(Enum):
    """Message severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"
    CRITICAL = "critical"


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class Communicator:
    """
    Unified communication interface for tasks.
    
    Automatically sends output to:
    1. Terminal (via rich) - Concise, user-friendly
    2. Logs (via loguru) - Detailed, technical
    
    This is the primary interface for ALL platform operations including:
    - Experiment generation
    - Job submission
    - Analysis pipelines
    - Status monitoring
    - Validation checks
    
    Usage:
        comm = Communicator("experiment_name", "operation_type")
        comm.header("Operation Title", "Subtitle")
        
        task = comm.task_start("task_id", "Task description")
        comm.message("Processing data", MessageLevel.INFO)
        comm.task_progress(task, step=50, message="Halfway")
        comm.task_end(task, success=True)
        
        comm.summary(stats={"Total": 100})
    """
    
    def __init__(self, experiment_name: str, operation_type: str):
        """
        Initialize communicator for an operation.
        
        Args:
            experiment_name: Name of experiment (e.g., 'shocktube_phase1')
            operation_type: Type of operation (e.g., 'generation', 'analysis', 'submission', 'status')
        """
        self.exp_name = experiment_name
        self.op_type = operation_type
        self.current_task: Optional[str] = None
        self.task_count = 0
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.start_time = time.time()
        self.task_registry: Dict[str, Dict[str, Any]] = {}
        
        # Initialize console
        self.console = create_console()
        
        # Initialize logging
        self._setup_logging()
        
        # Log initialization
        logger.info(f"Communicator initialized: {experiment_name} - {operation_type}")
    
    def _setup_logging(self):
        """Setup file logging with timestamped directory."""
        setup_file_logging(self.exp_name, self.op_type)
    
    def header(self, title: str, subtitle: str = ""):
        """
        Display operation header.
        
        Args:
            title: Main title
            subtitle: Optional subtitle
        """
        display_header(self.console, title, subtitle)
        
        # Log output
        header_text = f"=== {title} {'| ' + subtitle if subtitle else ''} ==="
        logger.info(header_text)
        logger.info("=" * len(header_text))
    
    def message(
        self,
        text: str,
        level: MessageLevel = MessageLevel.INFO,
        detail: str = "",
        terminal: bool = True,
        log: bool = True
    ):
        """
        Send message to both terminal and logs.
        
        Args:
            text: Main message text
            level: Message severity level
            detail: Additional detail (logs only)
            terminal: Whether to show in terminal
            log: Whether to write to log
        """
        # Route to appropriate logger level
        log_text = f"{text}{' | ' + detail if detail else ''}"
        
        if log:
            if level == MessageLevel.DEBUG:
                logger.debug(log_text)
            elif level == MessageLevel.INFO:
                logger.info(log_text)
            elif level == MessageLevel.WARNING:
                logger.warning(log_text)
            elif level == MessageLevel.ERROR:
                logger.error(log_text)
            elif level == MessageLevel.CRITICAL:
                logger.critical(log_text)
            elif level == MessageLevel.SUCCESS:
                logger.success(log_text)
        
        # Terminal output (concise)
        if terminal:
            display_message(self.console, text, level)
    
    def task_start(
        self,
        task_name: str,
        description: str = "",
        total_steps: Optional[int] = None
    ) -> str:
        """
        Register and start a new task.
        
        Args:
            task_name: Unique task identifier
            description: Human-readable description
            total_steps: Optional number of steps in task
        
        Returns:
            task_id: Task identifier for tracking
        """
        self.task_count += 1
        task_id = f"task_{self.task_count:03d}"
        
        # Register task
        self.task_registry[task_id] = {
            "name": task_name,
            "description": description,
            "status": TaskStatus.RUNNING,
            "start_time": time.time(),
            "total_steps": total_steps,
            "current_step": 0,
            "result": None
        }
        
        self.current_task = task_id
        
        # Log detailed info
        logger.info(f"Task started: {task_name}")
        logger.debug(f"Task ID: {task_id} | Description: {description} | Steps: {total_steps}")
        
        # Terminal output (concise)
        desc_short = description[:40] if len(description) > 40 else description
        self.console.print(f"[cyan]→[/cyan] {desc_short}")
        
        return task_id
    
    def task_progress(
        self,
        task_id: Optional[str] = None,
        step: Optional[int] = None,
        message: str = ""
    ):
        """
        Update task progress.
        
        Args:
            task_id: Task identifier (uses current if None)
            step: Current step number
            message: Progress message
        """
        tid = task_id or self.current_task
        if not tid or tid not in self.task_registry:
            return
        
        task = self.task_registry[tid]
        
        if step is not None:
            task["current_step"] = step
        
        # Log detailed progress
        logger.debug(f"Task {tid} progress: step {step}/{task['total_steps']} | {message}")
        
        # Terminal output (progress bar style)
        if task["total_steps"]:
            pct = (task["current_step"] / task["total_steps"]) * 100
            prog_text = f"[{task['current_step']}/{task['total_steps']}] {pct:.0f}%"
            
            # Truncate message for terminal
            msg_short = message[:TERM_WIDTH - len(prog_text) - 5] if message else ""
            self.console.print(f"  {prog_text} [dim]{msg_short}[/dim]")
    
    def task_end(
        self,
        task_id: Optional[str] = None,
        success: bool = True,
        result: Any = None,
        error: Optional[str] = None
    ):
        """
        Mark task as complete.
        
        Args:
            task_id: Task identifier (uses current if None)
            success: Whether task succeeded
            result: Task result data
            error: Error message if failed
        """
        tid = task_id or self.current_task
        if not tid or tid not in self.task_registry:
            return
        
        task = self.task_registry[tid]
        task["status"] = TaskStatus.COMPLETED if success else TaskStatus.FAILED
        task["end_time"] = time.time()
        task["duration"] = task["end_time"] - task["start_time"]
        task["result"] = result
        task["error"] = error
        
        if success:
            self.tasks_completed += 1
        else:
            self.tasks_failed += 1
        
        # Log completion
        if success:
            logger.success(f"Task completed: {task['name']} ({task['duration']:.2f}s)")
            if result:
                logger.debug(f"Task result: {result}")
        else:
            logger.error(f"Task failed: {task['name']} | Error: {error}")
        
        # Terminal output
        if success:
            self.console.print(f"[green]✓[/green] {task['description'] or task['name']}")
        else:
            err_short = error[:50] if error and len(error) > 50 else error
            self.console.print(f"[red]✗[/red] {task['description']} | {err_short}")
        
        # Clear current task
        if self.current_task == tid:
            self.current_task = None
    
    def summary(self, stats: Dict[str, Any] = None):
        """
        Display operation summary.
        
        Args:
            stats: Optional statistics dictionary
        """
        self.console.rule(f"[cyan]Summary: {self.exp_name}[/cyan]")
        
        # Task statistics
        total_time = time.time() - self.start_time
        self.console.print(f"Total tasks: {self.task_count}")
        self.console.print(f"Completed: [green]{self.tasks_completed}[/green]")
        if self.tasks_failed > 0:
            self.console.print(f"Failed: [red]{self.tasks_failed}[/red]")
        self.console.print(f"Duration: {total_time:.1f}s")
        
        # Additional statistics
        if stats:
            self.console.print()
            table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
            table.add_column("Metric", style="cyan", width=25)
            table.add_column("Value", width=40)
            
            for key, value in stats.items():
                # Format value
                if isinstance(value, float):
                    val_str = f"{value:.4f}"
                else:
                    val_str = str(value)
                
                # Truncate if needed
                if len(val_str) > 40:
                    val_str = val_str[:37] + "..."
                
                table.add_row(key, val_str)
            
            self.console.print(table)
        
        self.console.print()
        
        # Log summary
        logger.info(f"Operation summary: {self.tasks_completed}/{self.task_count} completed, {self.tasks_failed} failed, {total_time:.1f}s")
        if stats:
            logger.info(f"Statistics: {stats}")
    
    def validation_table(self, checks: list[tuple[str, bool, str]]):
        """
        Display validation results in table format.
        
        Args:
            checks: List of (check_name, passed, detail) tuples
        """
        display_validation_table(self.console, self.exp_name, checks)
        
        # Log full details
        for name, passed, detail in checks:
            logger.debug(f"Check {name}: {'PASS' if passed else 'FAIL'} | {detail}")
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get status of a specific task."""
        if task_id in self.task_registry:
            return self.task_registry[task_id]["status"]
        return None
    
    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered tasks."""
        return self.task_registry.copy()


def create_communicator(experiment_name: str, operation_type: str) -> Communicator:
    """
    Create a new communicator instance.
    
    Args:
        experiment_name: Name of experiment
        operation_type: Type of operation (generation, submission, analysis, status)
    
    Returns:
        Configured Communicator instance
    """
    return Communicator(experiment_name, operation_type)

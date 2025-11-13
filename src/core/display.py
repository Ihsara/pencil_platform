"""
Rich-based terminal display system for concise, readable output.

Separates detailed logging (loguru) from terminal display (rich).
Terminal width: 72 characters for optimal readability.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, Any
import time

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.live import Live
from rich.layout import Layout
from rich import box
from loguru import logger


# Terminal width constraint
TERM_WIDTH = 72

# Initialize console with fixed width
console = Console(width=TERM_WIDTH)


class StatusBar:
    """Manages status bar display with task progress and timing."""
    
    def __init__(self, total_tasks: int, scene_name: str):
        self.total_tasks = total_tasks
        self.current_task = 0
        self.scene_name = scene_name
        self.start_time = time.time()
        self.task_times: list[float] = []
        
    def format_elapsed(self) -> str:
        """Format elapsed time in seconds."""
        elapsed = int(time.time() - self.start_time)
        return f"{elapsed}s"
    
    def render(self, task_desc: str = "") -> str:
        """Render status bar with progress and timing."""
        # Progress dots (green)
        dots = "." * min(self.current_task, 10)
        
        # Task counter
        task_progress = f"[{self.current_task}/{self.total_tasks}]"
        
        # Time elapsed
        time_str = self.format_elapsed()
        
        # Build status bar
        if task_desc:
            status = f"{dots} {task_progress} {time_str} - {task_desc}"
        else:
            status = f"{dots} {task_progress} {time_str}"
        
        # Truncate if too long
        if len(status) > TERM_WIDTH:
            status = status[:TERM_WIDTH-3] + "..."
        
        return status
    
    def increment(self):
        """Move to next task."""
        self.current_task += 1


class ConfigScene:
    """Display scene for configuration validation."""
    
    def __init__(self, experiment_name: str):
        self.exp_name = experiment_name
        self.checks: list[tuple[str, bool, str]] = []
        
    def add_check(self, name: str, passed: bool, detail: str = ""):
        """Add validation check result."""
        self.checks.append((name, passed, detail))
        logger.debug(f"Config check: {name} = {'PASS' if passed else 'FAIL'} | {detail}")
    
    def display(self):
        """Display configuration validation results."""
        console.rule(f"[cyan]Config Validation: {self.exp_name}[/cyan]")
        
        table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
        table.add_column("Check", style="dim", width=25)
        table.add_column("Status", width=8)
        table.add_column("Detail", style="dim", width=30)
        
        for name, passed, detail in self.checks:
            status = "[green]✓[/green]" if passed else "[red]✗[/red]"
            # Truncate detail if too long
            if len(detail) > 30:
                detail = detail[:27] + "..."
            table.add_row(name, status, detail)
        
        console.print(table)
        console.print()


class SubmissionScene:
    """Display scene for job submission."""
    
    def __init__(self, experiment_name: str):
        self.exp_name = experiment_name
        self.info: dict[str, str] = {}
        
    def add_info(self, key: str, value: str):
        """Add submission information."""
        self.info[key] = value
        logger.info(f"Submission info: {key} = {value}")
    
    def display_pre_submit(self):
        """Display before submission."""
        console.rule(f"[cyan]Submission: {self.exp_name}[/cyan]")
        
        table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
        table.add_column("Item", style="cyan", width=20)
        table.add_column("Value", width=45)
        
        for key, value in self.info.items():
            # Truncate long values
            if len(value) > 45:
                value = value[:42] + "..."
            table.add_row(key, value)
        
        console.print(table)
        console.print()
    
    def display_result(self, job_id: str, success: bool):
        """Display submission result."""
        if success:
            console.print(f"[green]✓[/green] Job submitted: [cyan]{job_id}[/cyan]")
            logger.success(f"Job submitted successfully: {job_id}")
        else:
            console.print(f"[red]✗[/red] Submission failed")
            logger.error("Job submission failed")
        console.print()


class AnalysisScene:
    """Display scene for analysis operations."""
    
    def __init__(self, experiment_name: str, total_runs: int):
        self.exp_name = experiment_name
        self.total_runs = total_runs
        self.completed_runs = 0
        self.current_phase = ""
        self.stats: dict[str, Any] = {}
        
    def update_phase(self, phase: str):
        """Update current analysis phase."""
        self.current_phase = phase
        logger.info(f"Analysis phase: {phase}")
    
    def add_stat(self, key: str, value: Any):
        """Add analysis statistic."""
        self.stats[key] = value
        logger.debug(f"Analysis stat: {key} = {value}")
    
    def display_progress(self, run_name: str):
        """Display progress for current run."""
        self.completed_runs += 1
        pct = (self.completed_runs / self.total_runs) * 100
        
        # Status line
        status = f"[{self.completed_runs}/{self.total_runs}] {pct:.0f}%"
        
        # Truncate run name if needed
        display_name = run_name
        max_name_len = TERM_WIDTH - len(status) - 10
        if len(display_name) > max_name_len:
            display_name = display_name[:max_name_len-3] + "..."
        
        console.print(f"{status} [dim]{display_name}[/dim]")
        logger.debug(f"Processed run {self.completed_runs}/{self.total_runs}: {run_name}")
    
    def display_summary(self):
        """Display analysis summary."""
        console.rule(f"[cyan]Analysis Complete: {self.exp_name}[/cyan]")
        
        if self.stats:
            table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
            table.add_column("Metric", style="cyan", width=25)
            table.add_column("Value", width=40)
            
            for key, value in self.stats.items():
                # Format value
                if isinstance(value, float):
                    val_str = f"{value:.4f}"
                else:
                    val_str = str(value)
                
                # Truncate if too long
                if len(val_str) > 40:
                    val_str = val_str[:37] + "..."
                
                table.add_row(key, val_str)
            
            console.print(table)
        
        console.print(f"[green]✓[/green] Total runs analyzed: {self.total_runs}")
        console.print()


class MonitorScene:
    """Display scene for job monitoring."""
    
    def __init__(self, experiment_name: str):
        self.exp_name = experiment_name
        self.job_id = ""
        self.status = "UNKNOWN"
        self.tasks_info: dict[str, dict] = {}
        
    def update_status(self, job_id: str, status: str):
        """Update job status."""
        self.job_id = job_id
        self.status = status
        logger.debug(f"Job {job_id} status: {status}")
    
    def add_task_info(self, task_id: str, info: dict):
        """Add information about a task."""
        self.tasks_info[task_id] = info
        logger.debug(f"Task {task_id} info: {info}")
    
    def display(self):
        """Display monitoring information."""
        console.rule(f"[cyan]Monitor: {self.exp_name}[/cyan]")
        
        # Job status
        status_color = {
            "RUNNING": "yellow",
            "COMPLETED": "green",
            "FAILED": "red",
            "PENDING": "blue",
            "TIMEOUT": "red"
        }.get(self.status, "white")
        
        console.print(f"Job: [cyan]{self.job_id}[/cyan] | Status: [{status_color}]{self.status}[/{status_color}]")
        
        # Task summary (limit to most relevant)
        if self.tasks_info:
            # Show only first 5 and last 5 if more than 10
            task_ids = sorted(self.tasks_info.keys())
            if len(task_ids) > 10:
                show_ids = task_ids[:5] + ["..."] + task_ids[-5:]
            else:
                show_ids = task_ids
            
            for task_id in show_ids:
                if task_id == "...":
                    console.print("[dim]  ...[/dim]")
                    continue
                    
                info = self.tasks_info[task_id]
                stage = info.get("stage", "unknown")
                progress = info.get("progress", "")
                
                # Compact display
                line = f"  {task_id}: {stage}"
                if progress:
                    line += f" [{progress}]"
                
                # Truncate if too long
                if len(line) > TERM_WIDTH:
                    line = line[:TERM_WIDTH-3] + "..."
                
                console.print(f"[dim]{line}[/dim]")
        
        console.print()


def show_header(title: str, subtitle: str = ""):
    """Display header for operation."""
    console.clear()
    console.rule(f"[bold cyan]{title}[/bold cyan]")
    if subtitle:
        console.print(f"[dim]{subtitle}[/dim]")
    console.print()
    logger.info(f"=== {title} {'| ' + subtitle if subtitle else ''} ===")


def show_error(message: str):
    """Display error message."""
    console.print(f"[red]✗ Error:[/red] {message}")
    logger.error(message)


def show_warning(message: str):
    """Display warning message."""
    console.print(f"[yellow]⚠ Warning:[/yellow] {message}")
    logger.warning(message)


def show_success(message: str):
    """Display success message."""
    console.print(f"[green]✓[/green] {message}")
    logger.success(message)


def show_info(message: str):
    """Display informational message."""
    console.print(f"[cyan]ℹ[/cyan] {message}")
    logger.info(message)


def create_progress_bar(total: int, description: str = "Processing") -> Progress:
    """Create a rich progress bar for long operations."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(complete_style="green", finished_style="green"),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        expand=False
    )

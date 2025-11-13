"""
Terminal display functionality using Rich.

This module provides terminal-specific display functions that are used by
the unified communication interface. It handles all terminal output formatting,
keeping terminal display logic separate from the main interface.

Features:
- Fixed width terminal (72 chars) for optimal readability
- Rich formatting with colors and styles
- Modular display functions for headers, messages, tables
"""

from typing import Optional
from rich.console import Console
from rich.table import Table
from rich import box

# Terminal width constraint
TERM_WIDTH = 72


def create_console() -> Console:
    """
    Create a Rich console with fixed width.
    
    Returns:
        Configured Console instance with width=72
    """
    return Console(width=TERM_WIDTH)


def display_header(console: Console, title: str, subtitle: str = ""):
    """
    Display operation header with title and optional subtitle.
    
    Args:
        console: Rich Console instance
        title: Main title text
        subtitle: Optional subtitle text
    """
    console.clear()
    console.rule(f"[bold cyan]{title}[/bold cyan]")
    if subtitle:
        console.print(f"[dim]{subtitle}[/dim]")
    console.print()


def display_message(console: Console, text: str, level):
    """
    Display a message in the terminal with appropriate formatting.
    
    Args:
        console: Rich Console instance
        text: Message text
        level: MessageLevel enum value
    """
    from src.core.communication.interface import MessageLevel
    
    # Truncate for terminal width
    display_text = text[:TERM_WIDTH-10] if len(text) > TERM_WIDTH-10 else text
    
    if level == MessageLevel.DEBUG:
        pass  # Don't show debug in terminal
    elif level == MessageLevel.INFO:
        console.print(f"[cyan]ℹ[/cyan] {display_text}")
    elif level == MessageLevel.WARNING:
        console.print(f"[yellow]⚠ Warning:[/yellow] {display_text}")
    elif level == MessageLevel.ERROR:
        console.print(f"[red]✗ Error:[/red] {display_text}")
    elif level == MessageLevel.SUCCESS:
        console.print(f"[green]✓[/green] {display_text}")
    elif level == MessageLevel.CRITICAL:
        console.print(f"[bold red]✗ CRITICAL:[/bold red] {display_text}")


def display_validation_table(console: Console, exp_name: str, checks: list[tuple[str, bool, str]]):
    """
    Display validation results in a table format.
    
    Args:
        console: Rich Console instance
        exp_name: Experiment name
        checks: List of (check_name, passed, detail) tuples
    """
    console.rule(f"[cyan]Validation: {exp_name}[/cyan]")
    
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    table.add_column("Check", style="dim", width=25)
    table.add_column("Status", width=8)
    table.add_column("Detail", style="dim", width=30)
    
    for name, passed, detail in checks:
        status = "[green]✓[/green]" if passed else "[red]✗[/red]"
        
        # Truncate detail if too long
        detail_short = detail[:30] if len(detail) > 30 else detail
        if len(detail) > 30:
            detail_short = detail[:27] + "..."
        
        table.add_row(name, status, detail_short)
    
    console.print(table)
    console.print()


def show_error(console: Console, message: str):
    """Display error message."""
    console.print(f"[red]✗ Error:[/red] {message}")


def show_warning(console: Console, message: str):
    """Display warning message."""
    console.print(f"[yellow]⚠ Warning:[/yellow] {message}")


def show_success(console: Console, message: str):
    """Display success message."""
    console.print(f"[green]✓[/green] {message}")


def show_info(console: Console, message: str):
    """Display informational message."""
    console.print(f"[cyan]ℹ[/cyan] {message}")

"""
Console output utilities for cleaner terminal display.

Provides context managers and utilities to suppress verbose library output
while maintaining full logging to files.
"""

import sys
import os
from contextlib import contextmanager
from io import StringIO


@contextmanager
def suppress_stdout_stderr():
    """
    Context manager to suppress stdout and stderr.
    
    Use this to hide verbose library output from the console while
    still allowing logger output to work normally.
    
    Example:
        with suppress_stdout_stderr():
            # This output won't appear in console
            print("Hidden output")
            some_verbose_library_function()
    """
    # Save original stdout/stderr
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    
    try:
        # Redirect to null
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')
        yield
    finally:
        # Restore original stdout/stderr
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout = old_stdout
        sys.stderr = old_stderr


@contextmanager
def capture_output():
    """
    Context manager to capture stdout/stderr output.
    
    Returns a StringIO object containing the captured output.
    
    Example:
        with capture_output() as output:
            print("This is captured")
        captured_text = output.getvalue()
    """
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    
    output = StringIO()
    
    try:
        sys.stdout = output
        sys.stderr = output
        yield output
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr


class ProgressTracker:
    """
    Simple progress tracker for cleaner console output.
    
    Shows current progress and can collapse completed steps.
    """
    
    def __init__(self, total: int, description: str = "Processing"):
        self.total = total
        self.current = 0
        self.description = description
        self.last_line_length = 0
    
    def update(self, item_name: str = ""):
        """Update progress and display current item."""
        self.current += 1
        pct = (self.current / self.total) * 100
        
        # Clear previous line
        if self.last_line_length > 0:
            print('\r' + ' ' * self.last_line_length + '\r', end='')
        
        # Show progress
        progress_text = f"  [{self.current}/{self.total}] ({pct:.1f}%) {item_name}"
        print(progress_text, end='', flush=True)
        self.last_line_length = len(progress_text)
    
    def complete(self, summary: str = ""):
        """Mark as complete and show summary."""
        # Clear the progress line
        if self.last_line_length > 0:
            print('\r' + ' ' * self.last_line_length + '\r', end='')
        
        # Show completion
        if summary:
            print(f"  ✓ {summary}")
        self.last_line_length = 0

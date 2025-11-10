"""Visual feedback components for async operations."""

from collections.abc import Generator
from contextlib import contextmanager

from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text

console = Console()


@contextmanager
def loading_indicator(message: str = "Processing") -> Generator[None, None, None]:
    """Display a loading spinner during operations.

    Args:
        message: Message to display with spinner

    Example:
        with loading_indicator("Fetching data"):
            # Long running operation
            time.sleep(2)
    """
    spinner = Spinner("dots", text=f"[cyan]{message}...[/cyan]")
    with Live(spinner, console=console, transient=True):
        yield


def show_success(message: str) -> None:
    """Display success message with checkmark.

    Args:
        message: Success message to display
    """
    text = Text()
    text.append("✓ ", style="bold green")
    text.append(message, style="green")
    console.print(text)


def show_error(message: str) -> None:
    """Display error message with X mark.

    Args:
        message: Error message to display
    """
    text = Text()
    text.append("✗ ", style="bold red")
    text.append(message, style="red")
    console.print(text)


def show_info(message: str) -> None:
    """Display info message with icon.

    Args:
        message: Info message to display
    """
    text = Text()
    text.append("ℹ ", style="bold blue")
    text.append(message, style="blue")
    console.print(text)


def show_warning(message: str) -> None:
    """Display warning message with icon.

    Args:
        message: Warning message to display
    """
    text = Text()
    text.append("⚠ ", style="bold yellow")
    text.append(message, style="yellow")
    console.print(text)

"""Interactive prompt wrappers using InquirerPy."""

import asyncio
import re
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any

from InquirerPy import inquirer
from InquirerPy.validator import PathValidator
from rich.console import Console
from rich.panel import Panel

console = Console()


def sync_to_async(func: Callable[..., Any]) -> Callable[..., Any]:
    """Convert synchronous function to async."""

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        return await asyncio.get_event_loop().run_in_executor(None, lambda: func(*args, **kwargs))

    return wrapper


@sync_to_async
def prompt_text(
    prompt: str, default: str | None = None, multiline: bool = False, validate_pattern: str | None = None
) -> str:
    """Prompt for text input."""

    def validator(text: str) -> bool:
        if validate_pattern:
            return bool(re.match(validate_pattern, text))
        return True

    if multiline:
        console.print(
            Panel(f"[bold cyan]{prompt}[/bold cyan]\n(Press Esc+Enter to submit)", border_style="cyan")
        )
        result: str = inquirer.text(
            message="", default=default or "", multiline=True, validate=validator
        ).execute()
    else:
        result = inquirer.text(message=prompt, default=default or "", validate=validator).execute()

    return result


@sync_to_async
def prompt_select(prompt: str, choices: list[str], default: str | None = None) -> str:
    """Prompt for single selection."""
    result: str = inquirer.select(message=prompt, choices=choices, default=default).execute()
    return result


@sync_to_async
def prompt_checkbox(prompt: str, choices: list[str]) -> list[str]:
    """Prompt for multiple selections."""
    result: list[str] = inquirer.checkbox(message=prompt, choices=choices).execute()
    return result


@sync_to_async
def prompt_confirm(prompt: str, default: bool = False) -> bool:
    """Prompt for yes/no confirmation."""
    result: bool = inquirer.confirm(message=prompt, default=default).execute()
    return result


@sync_to_async
def prompt_path(
    prompt: str, path_type: str = "any", must_exist: bool = False, default: str | None = None
) -> str:
    """Prompt for file/directory path."""
    validator = None
    if must_exist:
        if path_type == "file":
            validator = PathValidator(is_file=True, message="Path must be an existing file")
        elif path_type == "directory":
            validator = PathValidator(is_dir=True, message="Path must be an existing directory")
        else:
            validator = PathValidator(message="Path must exist")

    result = inquirer.filepath(message=prompt, default=default or "", validate=validator).execute()
    return str(Path(result).expanduser().resolve())


def display_notification(title: str, message: str, notification_type: str = "info") -> None:
    """Display formatted notification panel."""
    color_map = {"success": "green", "info": "blue", "warning": "yellow", "error": "red"}
    color = color_map.get(notification_type, "blue")

    panel = Panel(message, title=f"[bold {color}]{title}[/bold {color}]", border_style=color, padding=(1, 2))
    console.print(panel)

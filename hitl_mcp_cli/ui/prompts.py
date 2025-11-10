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
from rich.text import Text

console = Console()

# Icons for different prompt types
ICONS = {
    "text": "✏️ ",
    "select": "🎯",
    "checkbox": "☑️ ",
    "confirm": "❓",
    "path": "📁",
    "success": "✅",
    "info": "ℹ️ ",
    "warning": "⚠️ ",
    "error": "❌",
}


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

    # Add icon to prompt
    formatted_prompt = f"{ICONS['text']} {prompt}"

    if multiline:
        panel_text = Text()
        panel_text.append(ICONS["text"], style="bold cyan")
        panel_text.append(prompt, style="bold cyan")
        panel_text.append("\n(Press Esc+Enter to submit)", style="dim italic")
        console.print(Panel(panel_text, border_style="cyan", padding=(1, 2)))
        result: str = inquirer.text(  # type: ignore[attr-defined]
            message="", default=default or "", multiline=True, validate=validator
        ).execute()
    else:
        result = inquirer.text(message=formatted_prompt, default=default or "", validate=validator).execute()  # type: ignore[attr-defined]

    return result


@sync_to_async
def prompt_select(prompt: str, choices: list[str], default: str | None = None) -> str:
    """Prompt for single selection."""
    formatted_prompt = f"{ICONS['select']} {prompt}"
    result: str = inquirer.select(message=formatted_prompt, choices=choices, default=default).execute()  # type: ignore[attr-defined]
    return result


@sync_to_async
def prompt_checkbox(prompt: str, choices: list[str]) -> list[str]:
    """Prompt for multiple selections."""
    formatted_prompt = f"{ICONS['checkbox']} {prompt}"
    result: list[str] = inquirer.checkbox(message=formatted_prompt, choices=choices).execute()  # type: ignore[attr-defined]
    return result


@sync_to_async
def prompt_confirm(prompt: str, default: bool = False) -> bool:
    """Prompt for yes/no confirmation."""
    formatted_prompt = f"{ICONS['confirm']} {prompt}"
    result: bool = inquirer.confirm(message=formatted_prompt, default=default).execute()  # type: ignore[attr-defined]
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

    formatted_prompt = f"{ICONS['path']} {prompt}"
    result = inquirer.filepath(message=formatted_prompt, default=default or "", validate=validator).execute()  # type: ignore[attr-defined]
    return str(Path(result).expanduser().resolve())


def display_notification(title: str, message: str, notification_type: str = "info") -> None:
    """Display formatted notification panel."""
    color_map = {"success": "green", "info": "blue", "warning": "yellow", "error": "red"}
    color = color_map.get(notification_type, "blue")
    icon = ICONS.get(notification_type, ICONS["info"])

    # Create rich text for title with icon
    title_text = Text()
    title_text.append(icon, style=f"bold {color}")
    title_text.append(title, style=f"bold {color}")

    panel = Panel(message, title=title_text, border_style=color, padding=(1, 2))
    console.print(panel)
    console.print()  # Add spacing after notification

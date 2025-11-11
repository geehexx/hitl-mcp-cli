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
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

console = Console()

# Track if we need a separator (only after output)
# WARNING: Global state is not thread-safe for concurrent tool calls.
# This is acceptable for HITL use case where prompts are sequential,
# but may cause visual inconsistencies if multiple prompts execute concurrently.
# Future: Replace with request-scoped state or context manager.
_needs_separator = False

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
    global _needs_separator

    def validator(text: str) -> bool:
        if validate_pattern:
            try:
                return bool(re.match(validate_pattern, text))
            except re.error:
                return False
        return True

    # Show separator if needed
    if _needs_separator:
        console.print(Rule(style="dim"))
        _needs_separator = False

    # Render markdown if present
    if _has_markdown(prompt):
        _render_markdown_prompt(prompt, ICONS["text"])
        formatted_prompt = ""
    else:
        formatted_prompt = f"{ICONS['text']} {prompt}"

    if multiline:
        if not _has_markdown(prompt):
            panel_text = Text()
            panel_text.append(ICONS["text"], style="bold cyan")
            panel_text.append(prompt, style="bold cyan")
            panel_text.append("\n(Press Esc+Enter to submit)", style="dim italic")
            console.print(Panel(panel_text, border_style="cyan", padding=(1, 2)))
        else:
            console.print(Text("(Press Esc+Enter to submit)", style="dim italic"))

        try:
            result: str = inquirer.text(  # type: ignore[attr-defined]
                message="",
                default=default or "",
                multiline=True,
                validate=validator,
                keybindings={"answer": [{"key": ["escape", "enter"]}]},
                raise_keyboard_interrupt=True,
            ).execute()
        except KeyboardInterrupt:
            raise
        # Print newline to prevent terminal clearing
        console.print()
    else:
        result = inquirer.text(  # type: ignore[attr-defined]
            message=formatted_prompt,
            default=default or "",
            validate=validator,
            raise_keyboard_interrupt=True,
        ).execute()

    _needs_separator = True
    return result


@sync_to_async
def prompt_select(prompt: str, choices: list[str], default: str | None = None) -> str:
    """Prompt for single selection."""
    global _needs_separator

    if _needs_separator:
        console.print(Rule(style="dim"))
        _needs_separator = False

    if _has_markdown(prompt):
        _render_markdown_prompt(prompt, ICONS["select"])
        formatted_prompt = ""
    else:
        formatted_prompt = f"{ICONS['select']} {prompt}"

    # Use fuzzy search for long lists (>15 items)
    if len(choices) > 15:
        result: str = inquirer.fuzzy(  # type: ignore[attr-defined]
            message=formatted_prompt,
            choices=choices,
            default=default or "",
            max_height="70%",
            raise_keyboard_interrupt=True,
        ).execute()
    else:
        result = inquirer.select(  # type: ignore[attr-defined]
            message=formatted_prompt,
            choices=choices,
            default=default,
            max_height="70%",
            raise_keyboard_interrupt=True,
        ).execute()
    _needs_separator = True
    return result


@sync_to_async
def prompt_checkbox(prompt: str, choices: list[str]) -> list[str]:
    """Prompt for multiple selections."""
    global _needs_separator

    if _needs_separator:
        console.print(Rule(style="dim"))
        _needs_separator = False

    if _has_markdown(prompt):
        _render_markdown_prompt(prompt, ICONS["checkbox"])
        formatted_prompt = ""
    else:
        formatted_prompt = f"{ICONS['checkbox']} {prompt}"

    result: list[str] = inquirer.checkbox(  # type: ignore[attr-defined]
        message=formatted_prompt,
        choices=choices,
        show_cursor=True,
        max_height="70%",
        instruction="(Space to select, Enter to confirm)",
        raise_keyboard_interrupt=True,
    ).execute()
    _needs_separator = True
    return result


@sync_to_async
def prompt_confirm(prompt: str, default: bool = False) -> bool:
    """Prompt for yes/no confirmation."""
    global _needs_separator

    if _needs_separator:
        console.print(Rule(style="dim"))
        _needs_separator = False

    if _has_markdown(prompt):
        _render_markdown_prompt(prompt, ICONS["confirm"])
        formatted_prompt = ""
    else:
        formatted_prompt = f"{ICONS['confirm']} {prompt}"

    result: bool = inquirer.confirm(  # type: ignore[attr-defined]
        message=formatted_prompt,
        default=default,
        raise_keyboard_interrupt=True,
    ).execute()
    _needs_separator = True
    return result


@sync_to_async
def prompt_path(
    prompt: str, path_type: str = "any", must_exist: bool = False, default: str | None = None
) -> str:
    """Prompt for file/directory path."""
    global _needs_separator

    if _needs_separator:
        console.print(Rule(style="dim"))
        _needs_separator = False

    validator = None
    if must_exist:
        if path_type == "file":
            validator = PathValidator(is_file=True, message="Path must be an existing file")
        elif path_type == "directory":
            validator = PathValidator(is_dir=True, message="Path must be an existing directory")
        else:
            validator = PathValidator(message="Path must exist")

    if _has_markdown(prompt):
        _render_markdown_prompt(prompt, ICONS["path"])
        formatted_prompt = ""
    else:
        formatted_prompt = f"{ICONS['path']} {prompt}"

    result = inquirer.filepath(  # type: ignore[attr-defined]
        message=formatted_prompt,
        default=default or "",
        validate=validator,
        raise_keyboard_interrupt=True,
    ).execute()
    _needs_separator = True
    return str(Path(result).expanduser().resolve())


def display_notification(title: str, message: str, notification_type: str = "info") -> None:
    """Display formatted notification panel."""
    global _needs_separator

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
    _needs_separator = True


def _has_markdown(text: str) -> bool:
    """Detect if text contains markdown formatting.

    Uses conservative detection to avoid false positives.
    Requires strong markdown indicators, not just backticks.
    """
    if len(text) > 10000:  # Length limit for safety
        return False
    # Require strong indicators: code blocks, headers, or bold+structure
    return any(
        [
            "```" in text,  # Code blocks
            text.lstrip().startswith("# ") or "\n# " in text,  # Headers
            ("**" in text and ("\n- " in text or "\n* " in text or "\n1. " in text)),  # Bold + lists
        ]
    )


def _render_markdown_prompt(prompt: str, icon: str) -> None:
    """Render prompt with markdown formatting.

    Note: Rich's Markdown renderer handles HTML sanitization safely.
    No pre-processing needed.
    """
    # Show icon header
    header = Text()
    header.append(icon, style="bold cyan")
    console.print(header)

    # Render markdown (Rich handles HTML sanitization)
    console.print(Markdown(prompt))
    console.print()  # Spacing

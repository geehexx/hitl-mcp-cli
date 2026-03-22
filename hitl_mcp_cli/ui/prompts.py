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
from rich.markup import escape
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

# Icons for different prompt types (no trailing spaces — formatting adds spacing)
ICONS = {
    "text": "✏️",
    "select": "🎯",
    "checkbox": "☑️",
    "confirm": "❓",
    "path": "📁",
    "success": "✅",
    "info": "ℹ️",
    "warning": "⚠️",
    "error": "❌",
}


def sync_to_async(func: Callable[..., Any]) -> Callable[..., Any]:
    """Convert synchronous function to async."""

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        return await asyncio.get_event_loop().run_in_executor(None, lambda: func(*args, **kwargs))

    return wrapper


def _expand_escapes(text: str) -> str:
    """Expand literal backslash-n sequences to real newlines."""
    return text.replace("\\n", "\n")


def _render_notes(notes: str | None) -> None:
    """Display optional notes line in dim style."""
    if notes:
        notes = _expand_escapes(notes)
        console.print(f"[dim]{escape(notes)}[/dim]")


@sync_to_async
def prompt_text(
    prompt: str,
    default: str | None = None,
    multiline: bool = False,
    validate_pattern: str | None = None,
    invalid_message: str | None = None,
    notes: str | None = None,
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

    # Pre-render question with Rich (handles emoji width correctly),
    # then use empty message for InquirerPy (avoids emoji width miscalculation)
    if _has_markdown(prompt):
        _render_markdown_prompt(prompt, ICONS["text"])
    else:
        _render_inline_prompt(prompt, ICONS["text"])

    _render_notes(notes)

    # Build default/placeholder hint for long_instruction
    long_instruction = ""
    if default and not multiline:
        long_instruction = f"(default: {default})"

    if multiline:
        if _has_markdown(prompt):
            console.print(Text("(Press Esc+Enter to submit)", style="dim italic"))
        else:
            console.print(Text("  (Press Esc+Enter to submit)", style="dim italic"))

        try:
            result: str = inquirer.text(  # type: ignore[attr-defined]
                message="",
                qmark="",
                default=default or "",
                multiline=True,
                validate=validator,
                invalid_message=invalid_message or "Invalid input",
                keybindings={"answer": [{"key": ["escape", "enter"]}]},
                raise_keyboard_interrupt=True,
            ).execute()
        except KeyboardInterrupt:
            raise
    else:
        # Placeholder behavior: show default in long_instruction, start with empty buffer.
        # If user submits empty, return the default value.
        result = inquirer.text(  # type: ignore[attr-defined]
            message="",
            qmark="",
            default="",
            long_instruction=long_instruction,
            validate=validator,
            invalid_message=invalid_message or "Invalid input",
            raise_keyboard_interrupt=True,
        ).execute()
        if not result and default:
            result = default

    _needs_separator = True
    return result


@sync_to_async
def prompt_select(
    prompt: str, choices: list[str], default: str | None = None, notes: str | None = None
) -> str:
    """Prompt for single selection."""
    global _needs_separator

    if _needs_separator:
        console.print(Rule(style="dim"))
        _needs_separator = False

    if _has_markdown(prompt):
        _render_markdown_prompt(prompt, ICONS["select"])
    else:
        _render_inline_prompt(prompt, ICONS["select"])

    _render_notes(notes)

    # Use fuzzy search for long lists (>15 items)
    if len(choices) > 15:
        result: str = inquirer.fuzzy(  # type: ignore[attr-defined]
            message="",
            qmark="",
            choices=choices,
            default=default or "",
            max_height="70%",
            raise_keyboard_interrupt=True,
        ).execute()
    else:
        result = inquirer.select(  # type: ignore[attr-defined]
            message="",
            qmark="",
            choices=choices,
            default=default,
            max_height="70%",
            raise_keyboard_interrupt=True,
        ).execute()
    _needs_separator = True
    return result


@sync_to_async
def prompt_checkbox(prompt: str, choices: list[str], notes: str | None = None) -> list[str] | dict[str, Any]:
    """Prompt for multiple selections.

    Escape hatch: if ALL or NONE selected, offers optional free-text note.
    Returns dict with 'selected' and 'note' keys when note provided,
    otherwise returns plain list.
    """
    global _needs_separator

    if _needs_separator:
        console.print(Rule(style="dim"))
        _needs_separator = False

    if _has_markdown(prompt):
        _render_markdown_prompt(prompt, ICONS["checkbox"])
    else:
        _render_inline_prompt(prompt, ICONS["checkbox"])

    _render_notes(notes)

    result: list[str] = inquirer.checkbox(  # type: ignore[attr-defined]
        message="",
        qmark="",
        choices=choices,
        show_cursor=True,
        max_height="70%",
        instruction="(Space to select, Enter to confirm)",
        raise_keyboard_interrupt=True,
    ).execute()

    # Escape hatch: all or none selected
    if len(result) == len(choices) or len(result) == 0:
        note_text: str = inquirer.text(  # type: ignore[attr-defined]
            message="Add a note? (optional, press Enter to skip)",
            qmark="",
            default="",
            raise_keyboard_interrupt=True,
        ).execute()
        if note_text.strip():
            _needs_separator = True
            return {"selected": result, "note": note_text.strip()}

    _needs_separator = True
    return result


@sync_to_async
def prompt_confirm(prompt: str, default: bool = False, notes: str | None = None) -> bool:
    """Prompt for yes/no confirmation."""
    global _needs_separator

    if _needs_separator:
        console.print(Rule(style="dim"))
        _needs_separator = False

    if _has_markdown(prompt):
        _render_markdown_prompt(prompt, ICONS["confirm"])
    else:
        _render_inline_prompt(prompt, ICONS["confirm"])

    _render_notes(notes)

    result: bool = inquirer.confirm(  # type: ignore[attr-defined]
        message="",
        qmark="",
        default=default,
        raise_keyboard_interrupt=True,
    ).execute()
    _needs_separator = True
    return result


@sync_to_async
def prompt_path(
    prompt: str,
    path_type: str = "any",
    must_exist: bool = False,
    default: str | None = None,
    notes: str | None = None,
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
    else:
        _render_inline_prompt(prompt, ICONS["path"])

    _render_notes(notes)

    result = inquirer.filepath(  # type: ignore[attr-defined]
        message="",
        qmark="",
        default=default or "",
        validate=validator,
        raise_keyboard_interrupt=True,
    ).execute()
    _needs_separator = True
    return str(Path(result).expanduser().resolve())


def display_notification(
    title: str, message: str, notification_type: str = "info", notes: str | None = None
) -> None:
    """Display formatted notification panel."""
    global _needs_separator

    color_map = {"success": "green", "info": "blue", "warning": "yellow", "error": "red"}
    color = color_map.get(notification_type, "blue")
    icon = ICONS.get(notification_type, ICONS["info"])

    title = _expand_escapes(title)
    message = _expand_escapes(message)

    # Create rich text for title with icon
    title_text = Text()
    title_text.append(icon, style=f"bold {color}")
    title_text.append(escape(title), style=f"bold {color}")

    body: Markdown | Text
    if _has_markdown(message):
        body = Markdown(message)
    else:
        body = Text(escape(message))

    panel = Panel(body, title=title_text, border_style=color, padding=(1, 2))
    _render_notes(notes)
    console.print(panel)
    console.print()  # Add spacing after notification
    _needs_separator = True


def _render_inline_prompt(prompt: str, icon: str) -> None:
    """Render a non-markdown prompt with Rich (handles emoji width correctly)."""
    prompt = _expand_escapes(prompt)
    text = Text()
    text.append(f"{icon} ", style="bold cyan")
    text.append(prompt, style="bold cyan")
    console.print(text)


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

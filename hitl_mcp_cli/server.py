"""FastMCP server for interactive user input."""

import asyncio
from typing import Any, Literal

from fastmcp import FastMCP

from .ui import display_notification, prompt_checkbox, prompt_confirm, prompt_path, prompt_select, prompt_text

mcp = FastMCP(
    name="HITL MCP Server",
    instructions=(
        "Human-in-the-Loop MCP server. Provides tools for AI agents to request human input, "
        "confirmation, and approval at critical decision points. All tools block until the user "
        "responds, ensuring human oversight of consequential actions."
    ),
)


@mcp.tool()
async def hitl_collect(
    message: str,
    input_type: Literal["text", "path", "multiline"] = "text",
    default: str | None = None,
    validation_pattern: str | None = None,
    validation_message: str | None = None,
) -> str:
    """Collect a single input value from the user. Use for text, file paths, or multiline content. Blocks until the user responds.

    Args:
        message: Clear, specific question to ask the user
        input_type: "text" for single-line, "path" for file paths with completion, "multiline" for multi-line (Esc+Enter to submit)
        default: Pre-filled value the user can accept or modify
        validation_pattern: Regex pattern to validate input (e.g., r"^[a-z0-9-]+$" for slugs)
        validation_message: Custom message shown when validation fails

    Returns:
        The user's input string
    """
    try:
        if input_type == "path":
            result: str = await prompt_path(message, "any", False, default)
        elif input_type == "multiline":
            result = await prompt_text(message, default, True, validation_pattern)
        else:
            result = await prompt_text(message, default, False, validation_pattern)
        return result
    except KeyboardInterrupt:
        raise Exception("User cancelled input (Ctrl+C)") from None
    except Exception as e:
        raise Exception(f"Input collection failed: {str(e)}") from e


@mcp.tool()
async def hitl_choose(
    message: str,
    choices: list[str] | None = None,
    options: list[dict[str, str]] | None = None,
    multiple: bool = False,
    default: str | None = None,
    fuzzy_search: bool | None = None,
) -> str | list[str]:
    """Present a list of options for the user to select from. Supports single or multiple selection, fuzzy search for long lists, and rich option descriptions.

    Args:
        message: Clear question explaining what to choose
        choices: Simple list of option strings (e.g., ["Option A", "Option B"])
        options: Rich options with value/label/description dicts (e.g., [{"value": "a", "label": "Option A", "description": "Fast"}])
        multiple: Enable checkbox mode for selecting multiple items
        default: Pre-selected option value
        fuzzy_search: Force fuzzy search on/off (auto-enabled for >15 items)

    Returns:
        Selected value (string) or values (list) if multiple=True
    """
    if not choices and not options:
        raise Exception("At least one of 'choices' or 'options' must be provided")

    # Build display_to_value mapping when options format used
    display_to_value: dict[str, str] | None = None
    if options and not choices:
        display_to_value = {}
        choices = []
        for opt in options:
            label = opt.get("label", opt.get("value", ""))
            desc = opt.get("description", "")
            display = f"{label}: {desc}" if desc else label
            choices.append(display)
            display_to_value[display] = opt.get("value", label)

    assert choices is not None  # guaranteed by validation above

    try:
        if multiple:
            result: list[str] = await prompt_checkbox(message, choices)
            return result
        result_str: str = await prompt_select(message, choices, default)
        if display_to_value is not None:
            return display_to_value.get(result_str, result_str)
        return result_str
    except KeyboardInterrupt:
        raise Exception("User cancelled selection (Ctrl+C)") from None
    except Exception as e:
        raise Exception(f"Selection failed: {str(e)}") from e


@mcp.tool()
async def hitl_confirm(
    message: str,
    default: bool = False,
    severity: Literal["low", "medium", "high"] = "medium",
) -> dict[str, str]:
    """Ask the user to confirm or reject an action. Use severity='high' for destructive or irreversible operations.

    Args:
        message: Clear yes/no question explaining the action
        default: Default answer - use False for destructive operations
        severity: "low" (default yes), "medium" (standard), "high" (red warning, requires typed "yes")

    Returns:
        Dict with 'action': 'accept' (confirmed), 'decline' (rejected), or 'cancel' (Ctrl+C)
    """
    try:
        if severity == "low":
            result: bool = await prompt_confirm(message, default=True)
        elif severity == "high":
            result = await prompt_confirm_high(message)
        else:
            result = await prompt_confirm(message, default)
        return {"action": "accept" if result else "decline"}
    except KeyboardInterrupt:
        return {"action": "cancel"}
    except Exception as e:
        raise Exception(f"Confirmation failed: {str(e)}") from e


@mcp.tool()
async def hitl_notify(
    message: str,
    level: Literal["success", "info", "warning", "error"] = "info",
    title: str | None = None,
) -> dict[str, bool]:
    """Display a styled notification to the user. Non-blocking — does not wait for user input. Use for progress updates, completion notices, and status changes.

    Args:
        message: Detailed message (supports multi-line with newlines)
        level: "success" (green), "info" (blue), "warning" (yellow), "error" (red)
        title: Optional short title for the notification

    Returns:
        Dict with 'acknowledged' key (always True)
    """
    try:
        display_notification(title or level.capitalize(), message, level)
        return {"acknowledged": True}
    except Exception as e:
        raise Exception(f"Notification display failed: {str(e)}") from e


@mcp.tool()
async def hitl_approve_workflow(
    message: str,
    context: str | None = None,
    options: list[str] | None = None,
    timeout_seconds: int = 300,
    severity: Literal["low", "medium", "high"] = "high",
) -> dict[str, Any]:
    """Request explicit human approval before proceeding with a significant workflow step. Blocks until approved, rejected, or timed out. Use for deploying to production, deleting data, sending external communications, or any irreversible action.

    Args:
        message: What needs approval
        context: Additional details to display
        options: Choices (default: ["Approve", "Reject"])
        timeout_seconds: Seconds to wait (0 = infinite, default 300)
        severity: Visual severity level

    Returns:
        Dict with 'approved' (bool), 'choice' (str), 'timed_out' (bool)
    """
    effective_options = options or ["Approve", "Reject"]

    try:
        # Display context if provided
        if context:
            display_notification("Approval Required", f"{message}\n\n{context}", "warning")
        else:
            display_notification("Approval Required", message, "warning")

        # Use select for the approval choice, with optional timeout
        if timeout_seconds > 0:
            try:
                choice: str = await asyncio.wait_for(
                    prompt_select(message, effective_options, None),
                    timeout=timeout_seconds,
                )
            except TimeoutError:
                return {"approved": False, "choice": "", "timed_out": True}
        else:
            choice = await prompt_select(message, effective_options, None)

        approved = choice == effective_options[0]
        return {"approved": approved, "choice": choice, "timed_out": False}
    except KeyboardInterrupt:
        raise Exception("User cancelled approval (Ctrl+C)") from None
    except Exception as e:
        raise Exception(f"Approval workflow failed: {str(e)}") from e


async def prompt_confirm_high(message: str) -> bool:
    """High-severity confirmation requiring typed 'yes'."""
    display_notification("⚠️  HIGH SEVERITY", message, "error")
    result: str = await prompt_text(
        'Type "yes" to confirm this action:',
        default=None,
        multiline=False,
        validate_pattern=None,
    )
    return result.strip().lower() == "yes"

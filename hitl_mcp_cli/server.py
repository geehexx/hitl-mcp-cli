"""FastMCP server for interactive user input."""

from typing import Literal

from fastmcp import FastMCP

from .ui import display_notification, prompt_checkbox, prompt_confirm, prompt_path, prompt_select, prompt_text

mcp = FastMCP(
    name="Interactive Input Server",
    instructions="""
# Interactive User Input Server

This server provides tools for requesting user input and feedback during agent execution.

## When to Use These Tools

**Use these tools when you need to:**
- Ask clarifying questions before making significant decisions
- Request user approval for destructive operations
- Gather specific information that's not available in context
- Present options and let the user choose the approach
- Confirm important assumptions or interpretations

**Best Practices:**
- Always provide clear, specific prompts
- Use `request_selection` with meaningful choices when options are limited
- Use `request_confirmation` for yes/no decisions
- Batch related questions when possible to minimize interruptions
- Use `notify_completion` to inform user of major milestone completions

## Tool Usage Patterns

### Clarification Pattern
When requirements are ambiguous:
1. Use `request_text_input` or `request_selection` to ask specific questions
2. Proceed only after receiving clear answers

### Approval Pattern
Before performing significant actions:
1. Explain what you plan to do
2. Use `request_confirmation` to get explicit approval
3. Proceed only if confirmed

### Choice Pattern
When multiple valid approaches exist:
1. Use `request_selection` with `choices` listing the approaches
2. Provide brief descriptions in each choice string
3. Implement the chosen approach

### Information Gathering Pattern
For collecting structured data:
1. Use multiple `request_text_input` calls with validation
2. Use `request_path_input` for file/directory paths
3. Use `request_selection` when valid values are constrained

## Important Notes

- These tools will pause agent execution until user responds
- Always provide context in your prompts - users may not remember previous messages
- Default values and clear choices improve user experience
- Use validation to prevent invalid input when possible
""",
)


@mcp.tool()
async def request_text_input(
    prompt: str, default: str | None = None, multiline: bool = False, validate_pattern: str | None = None
) -> str:
    """Request text input from the user.

    Args:
        prompt: The question/prompt to display to the user
        default: Optional default value
        multiline: If True, allow multi-line input (text editor style)
        validate_pattern: Optional regex pattern for validation

    Returns:
        The user's text input
    """
    try:
        result: str = await prompt_text(prompt, default, multiline, validate_pattern)
        return result
    except KeyboardInterrupt:
        raise Exception("User cancelled input (Ctrl+C)") from None
    except Exception as e:
        raise Exception(f"Input collection failed: {str(e)}") from e


@mcp.tool()
async def request_selection(
    prompt: str, choices: list[str], default: str | None = None, allow_multiple: bool = False
) -> str | list[str]:
    """Request user to select from a list of options.

    Args:
        prompt: The question to display
        choices: List of options to choose from
        default: Default selection (if applicable)
        allow_multiple: If True, allow multiple selections (checkbox), else single (radio)

    Returns:
        Selected choice(s) - string for single, list for multiple
    """
    try:
        if allow_multiple:
            result: list[str] = await prompt_checkbox(prompt, choices)
            return result
        result_str: str = await prompt_select(prompt, choices, default)
        return result_str
    except KeyboardInterrupt:
        raise Exception("User cancelled selection (Ctrl+C)") from None
    except Exception as e:
        raise Exception(f"Selection failed: {str(e)}") from e


@mcp.tool()
async def request_confirmation(prompt: str, default: bool = False) -> bool:
    """Request yes/no confirmation from the user.

    Args:
        prompt: The yes/no question
        default: Default answer if user just presses enter

    Returns:
        Boolean confirmation result
    """
    try:
        result: bool = await prompt_confirm(prompt, default)
        return result
    except KeyboardInterrupt:
        raise Exception("User cancelled confirmation (Ctrl+C)") from None
    except Exception as e:
        raise Exception(f"Confirmation failed: {str(e)}") from e


@mcp.tool()
async def request_path_input(
    prompt: str,
    path_type: Literal["file", "directory", "any"] = "any",
    must_exist: bool = False,
    default: str | None = None,
) -> str:
    """Request file/directory path from user with validation.

    Args:
        prompt: The prompt message
        path_type: Type of path expected
        must_exist: Whether path must exist
        default: Default path

    Returns:
        Validated path string
    """
    try:
        result: str = await prompt_path(prompt, path_type, must_exist, default)
        return result
    except KeyboardInterrupt:
        raise Exception("User cancelled path input (Ctrl+C)") from None
    except Exception as e:
        raise Exception(f"Path input failed: {str(e)}") from e


@mcp.tool()
async def notify_completion(
    title: str, message: str, notification_type: Literal["success", "info", "warning", "error"] = "info"
) -> dict[str, bool]:
    """Display a completion notification to the user.

    Args:
        title: Notification title
        message: Notification message
        notification_type: Visual style of notification

    Returns:
        Dict with 'acknowledged' key
    """
    try:
        display_notification(title, message, notification_type)
        return {"acknowledged": True}
    except Exception as e:
        raise Exception(f"Notification display failed: {str(e)}") from e

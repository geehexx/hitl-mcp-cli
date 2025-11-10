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

    Use this when you need free-form text input like names, descriptions, or configuration values.
    Perfect for collecting information that doesn't fit predefined choices.

    Args:
        prompt: Clear, specific question to ask the user
        default: Pre-filled value the user can accept or modify
        multiline: Enable for longer text like descriptions or code snippets
        validate_pattern: Regex pattern to ensure input format (e.g., r"^[a-z0-9-]+$" for slugs)
                         Keep patterns simple to avoid performance issues. Avoid nested quantifiers.

    Returns:
        The user's text input

    Example:
        name = await request_text_input(
            prompt="What should we name this project?",
            default="my-project",
            validate_pattern=r"^[a-z0-9-]+$"
        )
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
    """Request user to select from predefined options.

    Use this when presenting multiple approaches, configurations, or options where the user
    should choose. Much better UX than free-form text when options are known.

    Args:
        prompt: Clear question explaining what to choose
        choices: List of options (be descriptive, e.g., "Option A: Fast but risky")
        default: Pre-selected option for convenience
        allow_multiple: Enable checkbox mode for selecting multiple items

    Returns:
        Selected choice (string) or choices (list) if allow_multiple=True

    Example:
        env = await request_selection(
            prompt="Which environment should I deploy to?",
            choices=["Development", "Staging", "Production"],
            default="Staging"
        )
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

    Use this before destructive operations, expensive API calls, or whenever you need
    explicit approval. Always explain what will happen if they confirm.

    Args:
        prompt: Clear yes/no question explaining the action (e.g., "Delete 50 files?")
        default: Default answer - use False for destructive operations

    Returns:
        True if user confirms, False otherwise

    Example:
        confirmed = await request_confirmation(
            prompt="I will delete 50 unused dependencies. Proceed?",
            default=False
        )
        if confirmed:
            # Proceed with operation
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

    Use this for selecting config files, output directories, or any filesystem paths.
    Provides path completion and validation for better UX.

    Args:
        prompt: Clear question about what path is needed
        path_type: "file" for files, "directory" for folders, "any" for either
        must_exist: Validate that path exists (use False if you'll create it)
        default: Pre-filled path for convenience

    Returns:
        Absolute, resolved path string

    Example:
        config = await request_path_input(
            prompt="Select configuration file:",
            path_type="file",
            must_exist=True,
            default="./config.yaml"
        )
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
    """Display a styled notification to the user.

    Use this to confirm successful operations, report errors, or highlight important
    information. Great for providing feedback after completing tasks.

    Args:
        title: Short, clear title (e.g., "Deployment Complete")
        message: Detailed message (supports multi-line with \n)
        notification_type: "success" (green), "info" (blue), "warning" (yellow), "error" (red)

    Returns:
        Dict with 'acknowledged' key (always True)

    Example:
        await notify_completion(
            title="Deployment Complete",
            message="Successfully deployed v2.1.0 to production\n\nURL: https://app.example.com",
            notification_type="success"
        )
    """
    try:
        display_notification(title, message, notification_type)
        return {"acknowledged": True}
    except Exception as e:
        raise Exception(f"Notification display failed: {str(e)}") from e

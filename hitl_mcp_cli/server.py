"""FastMCP server for interactive user input."""

import os
from typing import Literal

from fastmcp import FastMCP

from .ui import display_notification, prompt_checkbox, prompt_confirm, prompt_path, prompt_select, prompt_text

# Optional: Multi-agent coordination support
ENABLE_COORDINATION = os.getenv("HITL_ENABLE_COORDINATION", "").lower() in ("1", "true", "yes")

mcp = FastMCP(
    name="Interactive Input Server",
    instructions="""
# Interactive User Input Server

This server provides tools for requesting user input and feedback during agent execution.

## Core Principle

Tools enable real-time user input during execution, eliminating assumptions. Use liberally for ANY uncertainty.

## When to Invoke (Timing Triggers)

- **Immediately** when encountering uncertainty (don't batch, don't defer)
- **Before beginning large work** (allow plan review, prevent wasted effort)
- **Before ending session** (check for additional work, prevent premature termination)
- **At inflection points** (milestone completion, approach changes, scope shifts)

## What Constitutes Uncertainty (Usage Categories)

- **Ambiguous requirements** (multiple interpretations, unclear scope, undefined success criteria)
- **Missing information** (parameters, target files, configuration values)
- **Decision points** (multiple valid approaches, trade-offs, naming, file organization)
- **Confirmations** (destructive operations, expensive operations, breaking changes)
- **Preferences** (code style, implementation patterns, testing strategies, documentation format)

## Which Tool to Use (Selection Logic)

- `request_text_input`: Free-form input (names, descriptions, paths, multi-line content)
- `request_selection`: Enumerable options (≤10 choices with trade-offs)
- `request_confirmation`: Binary decisions (yes/no, proceed/cancel)
- `request_path_input`: File/directory paths with validation
- `notify_completion`: Status updates (success, info, warning, error)

## Session Continuity Benefits

- Prevents premature termination (user can queue multiple tasks)
- Reduces token waste (avoids context reload in new sessions)
- Enables continuous work flow (chain tasks without interruption)
- Early course correction (fix approach before wasting implementation effort)

## Best Practices

- Always provide clear, specific prompts with context
- Use `request_selection` with meaningful choices when options are limited
- Use `request_confirmation` for yes/no decisions
- Use `notify_completion` to inform user of major milestone completions
- When calling tools, explain your reasoning to help users understand your thought process

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

- These tools will pause agent execution until user responds (infinite timeout configured)
- Always provide context in your prompts - users may not remember previous messages
- Default values and clear choices improve user experience
- Use validation to prevent invalid input when possible
- If you're uncertain about anything, ASK - that's what these tools are for

## Meta-Development Note

This HITL MCP server is also used during its own development. When working on this project:
- Use these tools to clarify requirements and get user feedback
- The "user" in development context is the project maintainer
- Don't confuse the development usage with the production usage examples
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


# Multi-Agent Coordination (Optional)
# These are module-level so they can be accessed from cli.py for lifecycle management
coordination_channel_store = None
coordination_lock_manager = None

if ENABLE_COORDINATION:
    from .coordination.channels import ChannelStore
    from .coordination.locks import LockManager
    from .coordination.resources import register_coordination_resources
    from .coordination.tools import register_coordination_tools

    # Initialize coordination backends
    coordination_channel_store = ChannelStore()
    coordination_lock_manager = LockManager()

    # Register MCP resources and tools
    register_coordination_resources(mcp, coordination_channel_store)
    register_coordination_tools(mcp, coordination_channel_store, coordination_lock_manager)

    # Update server instructions
    mcp.instructions += """

## Multi-Agent Coordination (Enabled)

This server also provides multi-agent coordination capabilities:

### Coordination Tools
- `join_coordination_channel`: Join a channel to communicate with other agents
- `send_coordination_message`: Send structured messages to channel
- `poll_coordination_channel`: Check for new messages (non-blocking)
- `acquire_coordination_lock`: Acquire distributed lock for exclusive access
- `release_coordination_lock`: Release a held lock
- `leave_coordination_channel`: Leave a channel

### Coordination Resources
- `coordination://channels` - List all channels
- `coordination://{channel}` - Read all messages in channel
- `coordination://{channel}/{message_id}` - Read specific message
- `coordination://{channel}/type/{type}` - Filter messages by type
- `coordination://stats` - System statistics

### Message Types
Structured protocol for agent coordination:
- Discovery: `init`, `acknowledgment`
- Synchronization: `sync`, `capabilities`, `ownership`
- Operational: `question`, `response`, `task_assign`, `task_complete`, `progress`
- Control: `ready`, `standby`, `stop`, `done`
- Conflict: `conflict_detected`, `conflict_resolved`

### Example Workflow
```python
# Agent A (Primary)
await join_coordination_channel("project", "agent-a", role="primary")
await send_coordination_message("project", "agent-a", "init", "Hello")

# Agent B (Subordinate)
await join_coordination_channel("project", "agent-b", role="subordinate")
msgs = await poll_coordination_channel("project", filter_type="init")
await send_coordination_message("project", "agent-b", "acknowledgment", "Ready")
```

See documentation for full coordination protocol and patterns.
"""

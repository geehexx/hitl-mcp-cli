"""``hitl_collect`` / ``hitl_ask`` / ``hitl_choose`` tool primitives.

Both block until the user responds. ``hitl_ask`` is an alias for
``hitl_collect`` kept for back-compat — agents pick whichever name reads
more naturally.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Literal, cast

from .._server_core import (
    Context,
    get_client_name,
    get_session_id,
    tui_enqueue,
)
from .._server_core import mcp as _mcp
from ..interaction_log import ResultType, log_interaction


async def _collect_impl(
    tool: str,
    *,
    message: str,
    input_type: Literal["text", "path", "multiline"],
    default: str | None,
    validation_pattern: str | None,
    validation_message: str | None,
    notes: str | None,
    context: str | None,
    strip_whitespace: bool,
    required: bool,
    path_type: Literal["file", "dir", "any"] | None,
    agent_name: str | None,
    project_id: str | None,
    step: int | None,
    total_steps: int | None,
    ctx: Context | None,
) -> str | dict[str, str]:
    """Shared implementation for ``hitl_collect`` and ``hitl_ask``."""
    t0 = time.monotonic()
    client_name = get_client_name(ctx, agent_name)
    session_id = get_session_id(ctx)
    result = await tui_enqueue(
        "hitl_collect",
        {
            "message": message,
            "input_type": input_type,
            "default": default,
            "validation_pattern": validation_pattern,
            "validation_message": validation_message,
            "notes": notes,
            "context": context,
            "strip_whitespace": strip_whitespace,
            "required": required,
            "path_type": path_type,
            "project_id": project_id,
            "step": step,
            "total_steps": total_steps,
        },
        client_name=client_name,
        session_id=session_id,
    )
    if isinstance(result, str):
        if strip_whitespace:
            result = result.strip()
        if required and not result:
            result = {"action": "cancel", "reason": "required field was empty"}
        elif input_type == "path" and isinstance(result, str) and result:
            resolved = Path(result).expanduser().resolve()
            if path_type == "file" and not resolved.is_file():
                result = {"action": "cancel", "reason": f"not a file: {resolved}"}
            elif path_type == "dir" and not resolved.is_dir():
                result = {"action": "cancel", "reason": f"not a directory: {resolved}"}
            else:
                result = str(resolved)
    ms = int((time.monotonic() - t0) * 1000)
    rt: ResultType = "cancel" if isinstance(result, dict) else "value"
    log_interaction(tool, ms, rt, message=message, result=str(result)[:80], notes=notes)
    return cast("str | dict[str, str]", result)


@_mcp.tool()
async def hitl_collect(
    message: str,
    input_type: Literal["text", "path", "multiline"] = "text",
    default: str | None = None,
    validation_pattern: str | None = None,
    validation_message: str | None = None,
    notes: str | None = None,
    context: str | None = None,
    strip_whitespace: bool = False,
    required: bool = False,
    path_type: Literal["file", "dir", "any"] | None = None,
    agent_name: str | None = None,
    project_id: str | None = None,
    step: int | None = None,
    total_steps: int | None = None,
    ctx: Context | None = None,
) -> str | dict[str, str]:
    """Collect a single input value from the user. Blocks until the user responds.

    Args:
        message: Clear, specific question to ask the user.
        input_type: ``"text"`` for single-line, ``"path"`` for filesystem paths, ``"multiline"`` for multi-line (Esc+Enter to submit).
        default: Pre-filled value the user can accept or modify.
        validation_pattern: Regex pattern to validate input.
        validation_message: Custom message shown when validation fails.
        notes: Freeform context displayed as a dimmed line below the prompt.
        context: Additional context shown above the prompt.
        strip_whitespace: Auto-strip leading/trailing whitespace from the result.
        required: Reject empty input with a validation message.
        path_type: Validate path type when ``input_type="path"``.
        agent_name: Calling agent identifier; shown in the Sessions panel.
        project_id: Project identifier; groups sessions in the TUI.
        step: Current step number when the agent is in a multi-step workflow.
        total_steps: Total steps in the workflow.

    Returns:
        The user's input string, or ``{"action": "cancel", "reason": ...}`` when cancelled / validation failed.
    """
    return await _collect_impl(
        "hitl_collect",
        message=message,
        input_type=input_type,
        default=default,
        validation_pattern=validation_pattern,
        validation_message=validation_message,
        notes=notes,
        context=context,
        strip_whitespace=strip_whitespace,
        required=required,
        path_type=path_type,
        agent_name=agent_name,
        project_id=project_id,
        step=step,
        total_steps=total_steps,
        ctx=ctx,
    )


@_mcp.tool()
async def hitl_ask(
    message: str,
    input_type: Literal["text", "path", "multiline"] = "text",
    default: str | None = None,
    validation_pattern: str | None = None,
    validation_message: str | None = None,
    notes: str | None = None,
    context: str | None = None,
    strip_whitespace: bool = False,
    required: bool = False,
    path_type: Literal["file", "dir", "any"] | None = None,
    agent_name: str | None = None,
    project_id: str | None = None,
    step: int | None = None,
    total_steps: int | None = None,
    ctx: Context | None = None,
) -> str | dict[str, str]:
    """Alias for :func:`hitl_collect`. Use whichever name reads more naturally."""
    return await _collect_impl(
        "hitl_ask",
        message=message,
        input_type=input_type,
        default=default,
        validation_pattern=validation_pattern,
        validation_message=validation_message,
        notes=notes,
        context=context,
        strip_whitespace=strip_whitespace,
        required=required,
        path_type=path_type,
        agent_name=agent_name,
        project_id=project_id,
        step=step,
        total_steps=total_steps,
        ctx=ctx,
    )


@_mcp.tool()
async def hitl_choose(
    message: str,
    choices: list[str] | None = None,
    options: list[dict[str, str]] | None = None,
    multiple: bool = False,
    default: str | None = None,
    fuzzy_search: bool | None = None,
    notes: str | None = None,
    context: str | None = None,
    agent_name: str | None = None,
    project_id: str | None = None,
    step: int | None = None,
    total_steps: int | None = None,
    ctx: Context | None = None,
) -> str | list[str] | dict[str, str] | dict[str, Any]:
    """Present a list of options for the user to select from.

    Args:
        message: Clear question explaining what to choose.
        choices: Simple list of option strings.
        options: Rich options with ``value`` / ``label`` / ``description`` keys.
        multiple: Enable checkbox mode for selecting multiple items.
        default: Pre-selected option value.
        fuzzy_search: Force fuzzy search on/off (auto-enabled for >15 items).
        notes: Freeform context.
        context: Additional context shown above the prompt.
        agent_name: Calling agent identifier.
        project_id: Project identifier for session grouping.
        step: Current step number.
        total_steps: Total steps in workflow.

    Returns:
        Selected value (string) or list of values when ``multiple=True``.
    """
    if not choices and not options:
        raise ValueError("At least one of 'choices' or 'options' must be provided")

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

    assert choices is not None

    t0 = time.monotonic()
    client_name = get_client_name(ctx, agent_name)
    session_id = get_session_id(ctx)

    result = await tui_enqueue(
        "hitl_choose",
        {
            "message": message,
            "choices": choices,
            "multiple": multiple,
            "default": default,
            "fuzzy_search": fuzzy_search,
            "notes": notes,
            "context": context,
            "project_id": project_id,
            "step": step,
            "total_steps": total_steps,
        },
        client_name=client_name,
        session_id=session_id,
    )
    ms = int((time.monotonic() - t0) * 1000)
    log_interaction("hitl_choose", ms, "value", message=message, result=str(result)[:80], notes=notes)
    if display_to_value and isinstance(result, str):
        return display_to_value.get(result, result)
    if display_to_value and isinstance(result, list):
        return [display_to_value.get(str(r), str(r)) for r in result]
    return cast("str | list[str] | dict[str, str] | dict[str, Any]", result)


__all__ = ["hitl_ask", "hitl_choose", "hitl_collect"]

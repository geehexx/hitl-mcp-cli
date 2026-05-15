"""``hitl_collect`` / ``hitl_ask`` / ``hitl_choose`` tool primitives.

Both block until the user responds. ``hitl_ask`` is an alias for
``hitl_collect`` kept for back-compat — agents pick whichever name reads
more naturally.

Morning-batch protocol: when ``urgency`` is ``"soon"`` or ``"fyi"`` and the
TUI queue is unavailable (user away), the question is appended to
``~/.local/state/hitl-deferred-questions.jsonl`` and the call returns
immediately with ``{"action": "deferred", "urgency": urgency}``.
``urgency="blocking"`` always blocks regardless of TUI availability.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Literal, cast

from .._server_core import (
    Context,
    get_client_name,
    get_session_id,
    get_tui_queue,
    tui_enqueue,
)
from .._server_core import mcp as _mcp
from ..interaction_log import ResultType, log_interaction

_DEFERRED_QUESTIONS_LOG = Path.home() / ".local" / "state" / "hitl-deferred-questions.jsonl"


def _defer_question(
    *,
    message: str,
    urgency: Literal["blocking", "soon", "fyi"],
    notes: str | None,
    context: str | None,
    agent_name: str | None,
    project_id: str | None,
) -> dict[str, str]:
    """Append a deferred question to the morning-batch JSONL and return a deferred sentinel."""
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "category": "hitl-collect",
        "urgency": urgency,
        "context": (context or message)[:200],
        "proposed": None,
        "source": agent_name or "unknown",
        "project_id": project_id,
        "notes": notes,
    }
    _DEFERRED_QUESTIONS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with _DEFERRED_QUESTIONS_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return {"action": "deferred", "urgency": urgency}


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
    urgency: Literal["blocking", "soon", "fyi"],
    ctx: Context | None,
) -> str | dict[str, str]:
    """Shared implementation for ``hitl_collect`` and ``hitl_ask``."""
    # Morning-batch: defer non-blocking questions when TUI is unavailable
    if urgency in ("soon", "fyi") and get_tui_queue() is None:
        result = _defer_question(
            message=message,
            urgency=urgency,
            notes=notes,
            context=context,
            agent_name=agent_name,
            project_id=project_id,
        )
        log_interaction(tool, 0, "cancel", message=message, result=str(result)[:80], notes=notes)
        return result

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
    out: str | dict[str, str] = result
    if isinstance(result, str):
        s = result.strip() if strip_whitespace else result
        if required and not s:
            out = {"action": "cancel", "reason": "required field was empty"}
        elif input_type == "path" and s:
            resolved = Path(s).expanduser().resolve()
            if path_type == "file" and not resolved.is_file():
                out = {"action": "cancel", "reason": f"not a file: {resolved}"}
            elif path_type == "dir" and not resolved.is_dir():
                out = {"action": "cancel", "reason": f"not a directory: {resolved}"}
            else:
                out = str(resolved)
        else:
            out = s
    ms = int((time.monotonic() - t0) * 1000)
    rt: ResultType = "cancel" if isinstance(out, dict) else "value"
    log_interaction(tool, ms, rt, message=message, result=str(out)[:80], notes=notes)
    return out


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
    urgency: Literal["blocking", "soon", "fyi"] = "blocking",
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
        urgency: ``"blocking"`` always waits for user; ``"soon"``/``"fyi"`` defer to
            morning-batch JSONL when TUI is unavailable (user away).

    Returns:
        The user's input string, ``{"action": "cancel", "reason": ...}`` when cancelled /
        validation failed, or ``{"action": "deferred", "urgency": ...}`` when deferred to
        morning-batch.
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
        urgency=urgency,
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
    urgency: Literal["blocking", "soon", "fyi"] = "blocking",
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
        urgency=urgency,
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
    urgency: Literal["blocking", "soon", "fyi"] = "blocking",
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
        urgency: ``"blocking"`` always waits; ``"soon"``/``"fyi"`` defer to morning-batch
            when TUI is unavailable.

    Returns:
        Selected value (string) or list of values when ``multiple=True``.
    """
    if not choices and not options:
        raise ValueError("At least one of 'choices' or 'options' must be provided")

    # Morning-batch: defer non-blocking choices when TUI is unavailable
    if urgency in ("soon", "fyi") and get_tui_queue() is None:
        result = _defer_question(
            message=message,
            urgency=urgency,
            notes=notes,
            context=context,
            agent_name=agent_name,
            project_id=project_id,
        )
        log_interaction("hitl_choose", 0, "cancel", message=message, result=str(result)[:80], notes=notes)
        return result

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

    auto_fuzzy = fuzzy_search if fuzzy_search is not None else (len(choices) > 15)
    result = await tui_enqueue(
        "hitl_choose",
        {
            "message": message,
            "choices": choices,
            "multiple": multiple,
            "fuzzy_search": auto_fuzzy,
            "default": default,
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

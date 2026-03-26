"""FastMCP server for interactive user input."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any, Literal, cast

from fastmcp import Context, FastMCP

from .interaction_log import ResultType, log_interaction

if TYPE_CHECKING:
    from .tui.app import HITLApp
    from .tui.queue import HITLQueue

logger = logging.getLogger(__name__)


def _get_client_name(ctx: Context | None, agent_name: str | None = None) -> str | None:
    """Extract client name from agent_name param first, then FastMCP Context."""
    if agent_name:
        return agent_name
    if ctx is None:
        return None
    try:
        session = ctx.session
        params = session.client_params
        if params and params.clientInfo:
            return params.clientInfo.name
    except Exception:
        pass
    return None


def _get_session_id(ctx: Context | None) -> str:
    """Get MCP session ID from context, falling back to thread ID."""
    import threading

    if ctx is not None:
        try:
            return ctx.session_id
        except (RuntimeError, AttributeError):
            pass
    return f"thread-{threading.current_thread().ident}"


_tui_queue: HITLQueue | None = None
_tui_app: HITLApp | None = None


def configure_tui_mode(queue: HITLQueue, app: HITLApp) -> None:
    """Configure server to route HITL requests through the TUI queue."""
    global _tui_queue, _tui_app
    _tui_queue, _tui_app = queue, app


def _require_tui_queue() -> HITLQueue:
    """Return the TUI queue or raise if not configured."""
    if _tui_queue is None:
        raise RuntimeError("HITL server requires TUI mode. Run with hitl-mcp command.")
    return _tui_queue


async def _tui_enqueue(
    tool: str,
    params: dict[str, Any],
    client_name: str | None = None,
    session_id: str | None = None,
) -> Any:
    """Enqueue a request on the TUI queue and await the user's response."""
    import threading

    from .tui.queue import HITLRequest

    queue = _require_tui_queue()
    loop = asyncio.get_running_loop()
    if queue._caller_loop is None:
        queue.set_caller_loop(loop)
    future: asyncio.Future[Any] = loop.create_future()

    sid = session_id or f"thread-{threading.current_thread().ident}"
    params = {**params, "_session_id": sid, "_client_name": client_name or "unknown"}

    request = HITLRequest(tool=tool, params=params, future=future)
    queue.put_threadsafe(request)

    if _tui_app is not None:
        project_id = params.get("project_id")
        _tui_app.call_from_thread(_tui_app.record_session_activity, sid, tool, project_id, client_name)

    result = await future

    if _tui_app is not None:
        _tui_app.call_from_thread(_tui_app.record_session_resolved, sid)

    return result


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
    """Collect a single input value from the user. Use for text, file paths, or multiline content. Blocks until the user responds.

    Args:
        message: Clear, specific question to ask the user
        input_type: "text" for single-line, "path" for file paths with completion, "multiline" for multi-line (Esc+Enter to submit)
        default: Pre-filled value the user can accept or modify
        validation_pattern: Regex pattern to validate input (e.g., r"^[a-z0-9-]+$" for slugs)
        validation_message: Custom message shown when validation fails
        notes: Optional freeform context displayed as a dimmed line below the message
        context: Additional context shown above the prompt
        strip_whitespace: Auto-strip leading/trailing whitespace from result
        required: Reject empty input with validation message
        path_type: Validate path type when input_type="path" ("file", "dir", "any")
        agent_name: Agent/client name for session display
        project_id: Project identifier for session grouping
        step: Current step number (e.g. 2)
        total_steps: Total steps (e.g. 5)

    Returns:
        The user's input string
    """
    from pathlib import Path

    t0 = time.monotonic()
    client_name = _get_client_name(ctx, agent_name)
    session_id = _get_session_id(ctx)
    result = await _tui_enqueue(
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
    log_interaction("hitl_collect", ms, rt, message=message, result=str(result)[:80], notes=notes)
    return cast("str | dict[str, str]", result)


@mcp.tool()
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
    """Alias for hitl_collect. Collect a single input value from the user."""
    from pathlib import Path

    t0 = time.monotonic()
    client_name = _get_client_name(ctx, agent_name)
    session_id = _get_session_id(ctx)
    result = await _tui_enqueue(
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
    log_interaction("hitl_ask", ms, rt, message=message, result=str(result)[:80], notes=notes)
    return cast("str | dict[str, str]", result)


@mcp.tool()
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
    """Present a list of options for the user to select from. Supports single or multiple selection, fuzzy search for long lists, and rich option descriptions.

    Args:
        message: Clear question explaining what to choose
        choices: Simple list of option strings (e.g., ["Option A", "Option B"])
        options: Rich options with value/label/description dicts (e.g., [{"value": "a", "label": "Option A", "description": "Fast"}])
        multiple: Enable checkbox mode for selecting multiple items
        default: Pre-selected option value
        fuzzy_search: Force fuzzy search on/off (auto-enabled for >15 items)
        notes: Optional freeform context displayed as a dimmed line below the message
        context: Additional context shown above the prompt
        agent_name: Agent/client name for session display
        project_id: Project identifier for session grouping
        step: Current step number (e.g. 2)
        total_steps: Total steps (e.g. 5)

    Returns:
        Selected value (string), values (list) if multiple=True, or dict with 'selected' and 'note' keys if escape hatch triggered
    """
    if not choices and not options:
        raise Exception("At least one of 'choices' or 'options' must be provided")

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
    client_name = _get_client_name(ctx, agent_name)
    session_id = _get_session_id(ctx)

    result = await _tui_enqueue(
        "hitl_choose",
        {
            "message": message,
            "choices": choices,
            "multiple": multiple,
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


@mcp.tool()
async def hitl_confirm(
    message: str,
    default: bool = False,
    severity: Literal["low", "medium", "high"] = "medium",
    context: str | None = None,
    timeout_seconds: int = 0,
    notes: str | None = None,
    agent_name: str | None = None,
    project_id: str | None = None,
    step: int | None = None,
    total_steps: int | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Ask the user to confirm or reject an action. Use severity='high' for destructive or irreversible operations.

    Args:
        message: Clear yes/no question explaining the action
        default: Default answer - use False for destructive operations
        severity: "low" (default yes), "medium" (standard), "high" (red warning, requires typed "yes")
        context: Additional context displayed in a panel above the confirm prompt
        timeout_seconds: Seconds to wait (0 = infinite, >0 = timed confirmation)
        notes: Optional freeform context displayed as a dimmed line below the message
        agent_name: Agent/client name for session display
        project_id: Project identifier for session grouping
        step: Current step number (e.g. 2)
        total_steps: Total steps (e.g. 5)

    Returns:
        Dict with 'action': 'accept' (confirmed), 'decline' (rejected), or 'cancel' (Ctrl+C).
        Always includes 'timed_out' (bool) — True only when timeout_seconds > 0 and the timeout expired.
    """
    t0 = time.monotonic()
    client_name = _get_client_name(ctx, agent_name)
    session_id = _get_session_id(ctx)

    tui_params: dict[str, Any] = {
        "message": message,
        "severity": severity,
        "context": context,
        "notes": notes,
        "project_id": project_id,
        "step": step,
        "total_steps": total_steps,
    }
    try:
        if timeout_seconds > 0:
            tui_result: dict[str, Any] = await asyncio.wait_for(
                _tui_enqueue("hitl_confirm", tui_params, client_name=client_name, session_id=session_id),
                timeout=timeout_seconds,
            )
            ms = int((time.monotonic() - t0) * 1000)
            log_interaction("hitl_confirm", ms, "value", message=message, result=str(tui_result), notes=notes)
            tui_result["timed_out"] = False
            return tui_result
        tui_result = await _tui_enqueue(
            "hitl_confirm", tui_params, client_name=client_name, session_id=session_id
        )
        ms = int((time.monotonic() - t0) * 1000)
        log_interaction("hitl_confirm", ms, "value", message=message, result=str(tui_result), notes=notes)
        tui_result.setdefault("timed_out", False)
        return tui_result
    except TimeoutError:
        if _tui_app is not None:
            _tui_app.call_from_thread(_tui_app.record_session_resolved, session_id)
        ms = int((time.monotonic() - t0) * 1000)
        log_interaction("hitl_confirm", ms, "timeout", message=message, notes=notes)
        return {"action": "decline", "timed_out": True}


@mcp.tool()
async def hitl_notify(
    message: str,
    level: Literal["success", "info", "warning", "error"] = "info",
    title: str | None = None,
    notes: str | None = None,
    agent_name: str | None = None,
    project_id: str | None = None,
    step: int | None = None,
    total_steps: int | None = None,
    ctx: Context | None = None,
) -> dict[str, bool]:
    """Display a styled notification to the user. Non-blocking — does not wait for user input. Use for progress updates, completion notices, and status changes.

    Args:
        message: Detailed message (supports multi-line with newlines)
        level: "success" (green), "info" (blue), "warning" (yellow), "error" (red)
        title: Optional short title for the notification
        notes: Optional freeform context displayed as a dimmed line below the notification
        agent_name: Agent/client name for session display
        project_id: Project identifier for session grouping
        step: Current step number (e.g. 2)
        total_steps: Total steps (e.g. 5)

    Returns:
        Dict with 'acknowledged' key (always True)
    """
    t0 = time.monotonic()
    client_name = _get_client_name(ctx, agent_name)
    session_id = _get_session_id(ctx)

    queue = _require_tui_queue()
    if _tui_app is not None:
        _tui_app.call_from_thread(_tui_app.stream_output, title or "agent", message, level)
        _tui_app.call_from_thread(
            _tui_app.record_session_activity, session_id, "hitl_notify", project_id, client_name
        )
        short_msg = message[:40] + "..." if len(message) > 40 else message
        _tui_app.call_from_thread(
            _tui_app.stream_output,
            "queue",
            f"▶ [bold]hitl_notify[/bold] \\[{client_name or 'unknown'}] — {short_msg}",
            "info",
        )
    # Suppress unused variable warning — queue is checked via _require_tui_queue
    _ = queue
    ms = int((time.monotonic() - t0) * 1000)
    log_interaction("hitl_notify", ms, "value", message=message, notes=notes)
    return {"acknowledged": True}

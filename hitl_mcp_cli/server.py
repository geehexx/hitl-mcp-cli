"""FastMCP server for interactive user input."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any, Literal, cast

from fastmcp import Context, FastMCP

from .interaction_log import ResultType, log_interaction
from .ui import display_notification, prompt_checkbox, prompt_confirm, prompt_path, prompt_select, prompt_text

if TYPE_CHECKING:
    from .tui.app import HITLApp
    from .tui.queue import HITLQueue

logger = logging.getLogger(__name__)


def _get_client_name(ctx: Context | None) -> str | None:
    """Extract client name from FastMCP Context, if available."""
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


_tui_queue: HITLQueue | None = None
_tui_app: HITLApp | None = None


def configure_tui_mode(queue: HITLQueue, app: HITLApp) -> None:
    """Configure server to route HITL requests through the TUI queue."""
    global _tui_queue, _tui_app
    _tui_queue, _tui_app = queue, app


async def _tui_enqueue(tool: str, params: dict[str, Any], client_name: str | None = None) -> Any:
    """Enqueue a request on the TUI queue and await the user's response.

    The queue's asyncio.PriorityQueue lives on the Textual event loop, so
    we use put_threadsafe() to schedule the enqueue on the correct loop
    (HTTP/uvicorn thread → Textual loop direction).  The future is created
    on the uvicorn loop and resolved back via call_soon_threadsafe
    (Textual → uvicorn direction) in HITLQueue.resolve().
    """
    import threading

    from .tui.queue import HITLRequest

    assert _tui_queue is not None
    loop = asyncio.get_running_loop()
    if _tui_queue._caller_loop is None:
        _tui_queue.set_caller_loop(loop)
    future: asyncio.Future[Any] = loop.create_future()

    # Inject session metadata so the queue worker can display it
    session_id = f"thread-{threading.current_thread().ident}"
    params = {**params, "_session_id": session_id, "_client_name": client_name or "unknown"}

    request = HITLRequest(tool=tool, params=params, future=future)

    # Enqueue on the Textual event loop (owns the asyncio.PriorityQueue)
    _tui_queue.put_threadsafe(request)

    if _tui_app is not None:
        project_id = params.get("project_id")
        _tui_app.call_from_thread(_tui_app.record_session_activity, session_id, tool, project_id, client_name)

    result = await future

    if _tui_app is not None:
        _tui_app.call_from_thread(_tui_app.record_session_resolved, session_id)

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

    Returns:
        The user's input string
    """
    t0 = time.monotonic()
    if _tui_queue is not None:
        result = await _tui_enqueue(
            "hitl_collect",
            {
                "message": message,
                "input_type": input_type,
                "default": default,
                "validation_pattern": validation_pattern,
                "validation_message": validation_message,
                "notes": notes,
            },
            client_name=_get_client_name(ctx),
        )
    else:
        result = await _collect_input(
            message, input_type, default, validation_pattern, validation_message, notes
        )
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
    ctx: Context | None = None,
) -> str | dict[str, str]:
    """Alias for hitl_collect. Collect a single input value from the user."""
    t0 = time.monotonic()
    if _tui_queue is not None:
        result = await _tui_enqueue(
            "hitl_collect",
            {
                "message": message,
                "input_type": input_type,
                "default": default,
                "validation_pattern": validation_pattern,
                "validation_message": validation_message,
                "notes": notes,
            },
            client_name=_get_client_name(ctx),
        )
    else:
        result = await _collect_input(
            message, input_type, default, validation_pattern, validation_message, notes
        )
    ms = int((time.monotonic() - t0) * 1000)
    rt: ResultType = "cancel" if isinstance(result, dict) else "value"
    log_interaction("hitl_ask", ms, rt, message=message, result=str(result)[:80], notes=notes)
    return cast("str | dict[str, str]", result)


async def _collect_input(
    message: str,
    input_type: Literal["text", "path", "multiline"] = "text",
    default: str | None = None,
    validation_pattern: str | None = None,
    validation_message: str | None = None,
    notes: str | None = None,
) -> str | dict[str, str]:
    """Shared implementation for hitl_collect and hitl_ask."""
    try:
        if input_type == "path":
            result: str = await prompt_path(message, "any", False, default, notes)
        elif input_type == "multiline":
            result = await prompt_text(message, default, True, validation_pattern, validation_message, notes)
        else:
            result = await prompt_text(message, default, False, validation_pattern, validation_message, notes)
        return result
    except KeyboardInterrupt:
        return {"action": "cancel"}
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
    notes: str | None = None,
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

    Returns:
        Selected value (string), values (list) if multiple=True, or dict with 'selected' and 'note' keys if escape hatch triggered
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

    t0 = time.monotonic()

    if _tui_queue is not None:
        result = await _tui_enqueue(
            "hitl_choose",
            {
                "message": message,
                "choices": choices,
                "multiple": multiple,
                "notes": notes,
            },
            client_name=_get_client_name(ctx),
        )
        ms = int((time.monotonic() - t0) * 1000)
        log_interaction("hitl_choose", ms, "value", message=message, result=str(result)[:80], notes=notes)
        if display_to_value and isinstance(result, str):
            return display_to_value.get(result, result)
        if display_to_value and isinstance(result, list):
            return [display_to_value.get(str(r), str(r)) for r in result]
        return cast("str | list[str] | dict[str, str] | dict[str, Any]", result)

    try:
        if multiple:
            raw: Any = await prompt_checkbox(message, choices, notes)
            ms = int((time.monotonic() - t0) * 1000)
            log_interaction("hitl_choose", ms, "value", message=message, result=str(raw)[:80], notes=notes)
            if isinstance(raw, dict):
                # Escape hatch returned dict with note
                if display_to_value:
                    raw["selected"] = [display_to_value.get(r, r) for r in raw["selected"]]
                return raw
            if display_to_value:
                return [display_to_value.get(r, r) for r in raw]
            return list(raw) if raw else []
        result_str: str = await prompt_select(message, choices, default, notes)
        ms = int((time.monotonic() - t0) * 1000)
        log_interaction("hitl_choose", ms, "value", message=message, result=result_str[:80], notes=notes)
        if display_to_value is not None:
            return display_to_value.get(result_str, result_str)
        return result_str
    except KeyboardInterrupt:
        ms = int((time.monotonic() - t0) * 1000)
        log_interaction("hitl_choose", ms, "cancel", message=message, notes=notes)
        return {"action": "cancel"}
    except Exception as e:
        raise Exception(f"Selection failed: {str(e)}") from e


@mcp.tool()
async def hitl_confirm(
    message: str,
    default: bool = False,
    severity: Literal["low", "medium", "high"] = "medium",
    context: str | None = None,
    timeout_seconds: int = 0,
    notes: str | None = None,
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

    Returns:
        Dict with 'action': 'accept' (confirmed), 'decline' (rejected), or 'cancel' (Ctrl+C).
        Always includes 'timed_out' (bool) — True only when timeout_seconds > 0 and the timeout expired.
    """
    t0 = time.monotonic()

    if _tui_queue is not None:
        tui_params: dict[str, Any] = {
            "message": message,
            "severity": severity,
            "context": context,
            "notes": notes,
        }
        try:
            if timeout_seconds > 0:
                tui_result: dict[str, Any] = await asyncio.wait_for(
                    _tui_enqueue("hitl_confirm", tui_params, client_name=_get_client_name(ctx)),
                    timeout=timeout_seconds,
                )
                ms = int((time.monotonic() - t0) * 1000)
                log_interaction(
                    "hitl_confirm", ms, "value", message=message, result=str(tui_result), notes=notes
                )
                tui_result["timed_out"] = False
                return tui_result
            tui_result = await _tui_enqueue("hitl_confirm", tui_params, client_name=_get_client_name(ctx))
            ms = int((time.monotonic() - t0) * 1000)
            log_interaction("hitl_confirm", ms, "value", message=message, result=str(tui_result), notes=notes)
            tui_result.setdefault("timed_out", False)
            return tui_result
        except TimeoutError:
            if _tui_app is not None:
                import threading

                session_id = f"thread-{threading.current_thread().ident}"
                _tui_app.call_from_thread(_tui_app.record_session_resolved, session_id)
            ms = int((time.monotonic() - t0) * 1000)
            log_interaction("hitl_confirm", ms, "timeout", message=message, notes=notes)
            return {"action": "decline", "timed_out": True}

    try:
        if context:
            display_notification("Context", context, "info")

        async def _do_confirm() -> bool:
            if severity == "low":
                result = await prompt_confirm(message, default=True, notes=notes)
                return bool(result)
            elif severity == "high":
                result = await prompt_confirm_high(message)
                return bool(result)
            else:
                result = await prompt_confirm(message, default, notes=notes)
                return bool(result)

        if timeout_seconds > 0:
            try:
                confirmed = await asyncio.wait_for(_do_confirm(), timeout=timeout_seconds)
                ms = int((time.monotonic() - t0) * 1000)
                log_interaction(
                    "hitl_confirm", ms, "value", message=message, result=str(confirmed), notes=notes
                )
                return {"action": "accept" if confirmed else "decline", "timed_out": False}
            except TimeoutError:
                ms = int((time.monotonic() - t0) * 1000)
                log_interaction("hitl_confirm", ms, "timeout", message=message, notes=notes)
                return {"action": "decline", "timed_out": True}

        confirmed = await _do_confirm()
        ms = int((time.monotonic() - t0) * 1000)
        log_interaction("hitl_confirm", ms, "value", message=message, result=str(confirmed), notes=notes)
        return {"action": "accept" if confirmed else "decline", "timed_out": False}
    except KeyboardInterrupt:
        ms = int((time.monotonic() - t0) * 1000)
        log_interaction("hitl_confirm", ms, "cancel", message=message, notes=notes)
        return {"action": "cancel", "timed_out": False}
    except Exception as e:
        raise Exception(f"Confirmation failed: {str(e)}") from e


@mcp.tool()
async def hitl_notify(
    message: str,
    level: Literal["success", "info", "warning", "error"] = "info",
    title: str | None = None,
    notes: str | None = None,
    ctx: Context | None = None,
) -> dict[str, bool]:
    """Display a styled notification to the user. Non-blocking — does not wait for user input. Use for progress updates, completion notices, and status changes.

    Args:
        message: Detailed message (supports multi-line with newlines)
        level: "success" (green), "info" (blue), "warning" (yellow), "error" (red)
        title: Optional short title for the notification
        notes: Optional freeform context displayed as a dimmed line below the notification

    Returns:
        Dict with 'acknowledged' key (always True)
    """
    t0 = time.monotonic()

    if _tui_queue is not None and _tui_app is not None:
        client_name = _get_client_name(ctx)
        _tui_app.call_from_thread(_tui_app.stream_output, title or "agent", message, level)
        import threading

        session_id = f"thread-{threading.current_thread().ident}"
        _tui_app.call_from_thread(
            _tui_app.record_session_activity, session_id, "hitl_notify", None, client_name
        )
        # Log notify with params in activity log
        short_msg = message[:40] + "..." if len(message) > 40 else message
        _tui_app.call_from_thread(
            _tui_app.stream_output,
            "queue",
            f"▶ [bold]hitl_notify[/bold] \\[{client_name or 'unknown'}] — {short_msg}",
            "info",
        )
        ms = int((time.monotonic() - t0) * 1000)
        log_interaction("hitl_notify", ms, "value", message=message, notes=notes)
        return {"acknowledged": True}

    try:
        display_notification(title or level.capitalize(), message, level, notes)
        ms = int((time.monotonic() - t0) * 1000)
        log_interaction("hitl_notify", ms, "value", message=message, notes=notes)
        return {"acknowledged": True}
    except Exception as e:
        raise Exception(f"Notification display failed: {str(e)}") from e


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

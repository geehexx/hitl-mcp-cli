"""Comprehensive Textual Pilot tests for hitl-mcp-cli v0.9.0.

Screens must be pushed onto an App — Screen.run_test() does not exist.
Pattern: push_screen(screen, callback=results.append), then interact.
"""

from __future__ import annotations

import asyncio
from typing import Any, ClassVar

import pytest
from textual.widgets import Collapsible, DataTable, Input

from hitl_mcp_cli.tui.app import HITLApp
from hitl_mcp_cli.tui.queue import HITLQueue, HITLRequest
from hitl_mcp_cli.tui.screens import (
    _MINIMIZED,
    ChooseScreen,
    CollectScreen,
    ConfirmScreen,
    NotifyScreen,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _req(
    tool: str = "hitl_confirm",
    params: dict[str, Any] | None = None,
) -> HITLRequest:
    loop = asyncio.get_running_loop()
    return HITLRequest(tool=tool, params=params or {}, future=loop.create_future())


class _TestApp(HITLApp):
    """HITLApp that skips the queue worker and server thread for testing."""

    CSS_PATH: ClassVar[list[str]] = []  # type: ignore[assignment]

    def start_queue_worker(self) -> None:
        pass


@pytest.fixture
async def hitl_app():  # type: ignore[return]
    """Fixture: running HITLApp with queue and pilot."""
    queue = HITLQueue()
    app = _TestApp(hitl_queue=queue, host="127.0.0.1", port=15555, mcp_app=None)
    async with app.run_test(size=(120, 40)) as pilot:
        yield app, queue, pilot


# ---------------------------------------------------------------------------
# ConfirmScreen
# ---------------------------------------------------------------------------


async def test_confirm_screen_yes_button() -> None:
    app = _TestApp(hitl_queue=HITLQueue())
    results: list[Any] = []
    async with app.run_test(size=(120, 40)) as pilot:
        req = _req("hitl_confirm", {"message": "Are you sure?", "severity": "medium"})
        app.push_screen(ConfirmScreen(req), callback=results.append)
        await pilot.pause()
        await pilot.click("#yes")
        await pilot.pause()
    assert results == [{"action": "accept"}]


async def test_confirm_screen_no_button() -> None:
    app = _TestApp(hitl_queue=HITLQueue())
    results: list[Any] = []
    async with app.run_test(size=(120, 40)) as pilot:
        req = _req("hitl_confirm", {"message": "Delete?", "severity": "medium"})
        app.push_screen(ConfirmScreen(req), callback=results.append)
        await pilot.pause()
        await pilot.click("#no")
        await pilot.pause()
    assert results == [{"action": "decline"}]


async def test_confirm_screen_escape_minimizes() -> None:
    app = _TestApp(hitl_queue=HITLQueue())
    results: list[Any] = []
    async with app.run_test(size=(120, 40)) as pilot:
        req = _req("hitl_confirm", {"message": "Minimize me?", "severity": "medium"})
        app.push_screen(ConfirmScreen(req), callback=results.append)
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
    assert results == [_MINIMIZED]


async def test_confirm_screen_high_severity_requires_yes() -> None:
    app = _TestApp(hitl_queue=HITLQueue())
    results: list[Any] = []
    async with app.run_test(size=(120, 40)) as pilot:
        req = _req("hitl_confirm", {"message": "Irreversible!", "severity": "high"})
        app.push_screen(ConfirmScreen(req), callback=results.append)
        await pilot.pause()
        # High severity shows Input widget, not buttons — query from the pushed screen
        screen = app.screen
        inp = screen.query_one("#high-input", Input)
        assert inp is not None
        await pilot.click("#high-input")
        await pilot.press("y", "e", "s")
        await pilot.press("enter")
        await pilot.pause()
    assert results == [{"action": "accept"}]


async def test_confirm_screen_high_severity_wrong_input_declines() -> None:
    app = _TestApp(hitl_queue=HITLQueue())
    results: list[Any] = []
    async with app.run_test(size=(120, 40)) as pilot:
        req = _req("hitl_confirm", {"message": "Irreversible!", "severity": "high"})
        app.push_screen(ConfirmScreen(req), callback=results.append)
        await pilot.pause()
        await pilot.click("#high-input")
        await pilot.press("n", "o")
        await pilot.press("enter")
        await pilot.pause()
    assert results == [{"action": "decline"}]


# ---------------------------------------------------------------------------
# CollectScreen
# ---------------------------------------------------------------------------


async def test_collect_screen_text_input() -> None:
    app = _TestApp(hitl_queue=HITLQueue())
    results: list[Any] = []
    async with app.run_test(size=(120, 40)) as pilot:
        req = _req("hitl_collect", {"message": "Enter name:", "input_type": "text"})
        app.push_screen(CollectScreen(req), callback=results.append)
        await pilot.pause()
        await pilot.click("#collect-input")
        await pilot.press("A", "l", "i", "c", "e")
        await pilot.press("enter")
        await pilot.pause()
    assert results == ["Alice"]


async def test_collect_screen_submit_button() -> None:
    app = _TestApp(hitl_queue=HITLQueue())
    results: list[Any] = []
    async with app.run_test(size=(120, 40)) as pilot:
        req = _req("hitl_collect", {"message": "Enter value:", "input_type": "text"})
        app.push_screen(CollectScreen(req), callback=results.append)
        await pilot.pause()
        await pilot.click("#collect-input")
        await pilot.press("h", "e", "l", "l", "o")
        await pilot.click("#submit")
        await pilot.pause()
    assert results == ["hello"]


async def test_collect_screen_cancel_button() -> None:
    app = _TestApp(hitl_queue=HITLQueue())
    results: list[Any] = []
    async with app.run_test(size=(120, 40)) as pilot:
        req = _req("hitl_collect", {"message": "Enter value:", "input_type": "text"})
        app.push_screen(CollectScreen(req), callback=results.append)
        await pilot.pause()
        await pilot.click("#cancel")
        await pilot.pause()
    assert results == [{"action": "cancel"}]


async def test_collect_screen_multiline() -> None:
    app = _TestApp(hitl_queue=HITLQueue())
    results: list[Any] = []
    async with app.run_test(size=(120, 40)) as pilot:
        req = _req("hitl_collect", {"message": "Enter text:", "input_type": "multiline"})
        app.push_screen(CollectScreen(req), callback=results.append)
        await pilot.pause()
        await pilot.click("#collect-input")
        await pilot.press("h", "i")
        # ctrl+j triggers action_submit
        await pilot.press("ctrl+j")
        await pilot.pause()
    assert len(results) == 1
    assert "hi" in results[0]


# ---------------------------------------------------------------------------
# ChooseScreen
# ---------------------------------------------------------------------------


async def test_choose_screen_single_selection() -> None:
    app = _TestApp(hitl_queue=HITLQueue())
    results: list[Any] = []
    async with app.run_test(size=(120, 40)) as pilot:
        req = _req("hitl_choose", {"message": "Pick one:", "choices": ["Alpha", "Beta", "Gamma"]})
        app.push_screen(ChooseScreen(req), callback=results.append)
        await pilot.pause()
        # First option is highlighted by default; press enter to select
        await pilot.press("enter")
        await pilot.pause()
    assert results == ["Alpha"]


async def test_choose_screen_navigate_and_select() -> None:
    app = _TestApp(hitl_queue=HITLQueue())
    results: list[Any] = []
    async with app.run_test(size=(120, 40)) as pilot:
        req = _req("hitl_choose", {"message": "Pick one:", "choices": ["Alpha", "Beta", "Gamma"]})
        app.push_screen(ChooseScreen(req), callback=results.append)
        await pilot.pause()
        await pilot.press("down")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
    assert results == ["Beta"]


async def test_choose_screen_multiple_selection() -> None:
    app = _TestApp(hitl_queue=HITLQueue())
    results: list[Any] = []
    async with app.run_test(size=(120, 40)) as pilot:
        req = _req(
            "hitl_choose",
            {"message": "Pick many:", "choices": ["A", "B", "C"], "multiple": True},
        )
        app.push_screen(ChooseScreen(req), callback=results.append)
        await pilot.pause()
        await pilot.click("#choice-0")
        await pilot.pause()
        await pilot.click("#choice-2")
        await pilot.pause()
        await pilot.click("#done")
        await pilot.pause()
    assert len(results) == 1
    assert sorted(results[0]) == ["A", "C"]


async def test_choose_screen_cancel() -> None:
    app = _TestApp(hitl_queue=HITLQueue())
    results: list[Any] = []
    async with app.run_test(size=(120, 40)) as pilot:
        req = _req("hitl_choose", {"message": "Pick one:", "choices": ["X", "Y"]})
        app.push_screen(ChooseScreen(req), callback=results.append)
        await pilot.pause()
        await pilot.click("#cancel")
        await pilot.pause()
    assert results == [{"action": "cancel"}]


# ---------------------------------------------------------------------------
# NotifyScreen
# ---------------------------------------------------------------------------


async def test_notify_screen_dismiss_button() -> None:
    app = _TestApp(hitl_queue=HITLQueue())
    results: list[Any] = []
    async with app.run_test(size=(120, 40)) as pilot:
        req = _req("hitl_notify", {"message": "Done!", "level": "success"})
        app.push_screen(NotifyScreen(req), callback=results.append)
        await pilot.pause()
        await pilot.click("#dismiss")
        await pilot.pause()
    assert results == [True]


async def test_notify_screen_auto_dismisses() -> None:
    """NotifyScreen auto-dismisses after AUTO_DISMISS_SECONDS."""
    app = _TestApp(hitl_queue=HITLQueue())
    results: list[Any] = []

    class FastNotifyScreen(NotifyScreen):
        AUTO_DISMISS_SECONDS: float = 0.1

    async with app.run_test(size=(120, 40)) as pilot:
        req = _req("hitl_notify", {"message": "Auto-dismiss me", "level": "info"})
        app.push_screen(FastNotifyScreen(req), callback=results.append)
        await pilot.pause()
        await pilot.pause(delay=0.4)

    assert results == [True]


# ---------------------------------------------------------------------------
# HITLApp queue table
# ---------------------------------------------------------------------------


async def test_queue_row_added(hitl_app: Any) -> None:
    app, _queue, pilot = hitl_app
    req = _req("hitl_confirm", {"message": "Test queue row"})
    app.add_queue_row(req.request_id, req.tool, req.params.get("message", ""), request=req)
    await pilot.pause()
    table = app.query_one("#queue-table", DataTable)
    assert table.row_count == 1


async def test_queue_row_stays_after_remove(hitl_app: Any) -> None:
    """remove_queue_row should update status, not remove the row."""
    app, queue, pilot = hitl_app
    req = _req("hitl_confirm", {"message": "Persist me"})
    app.add_queue_row(req.request_id, req.tool, req.params.get("message", ""), request=req)
    await pilot.pause()
    # Mark answered so remove_queue_row picks up the status
    queue.mark_answered(req.request_id, "accepted")
    app.remove_queue_row(req.request_id)
    await pilot.pause()
    table = app.query_one("#queue-table", DataTable)
    # Row count stays at 1 — row is NOT removed
    assert table.row_count == 1


async def test_session_table_shows_agent_name(hitl_app: Any) -> None:
    app, _queue, pilot = hitl_app
    app.record_session_activity("sess-1", "hitl_confirm", project_id="proj-x", client_name="my-agent")
    await pilot.pause()
    table = app.query_one("#sessions-table", DataTable)
    assert table.row_count == 1


async def test_session_coloring_active(hitl_app: Any) -> None:
    """Active sessions (recent) should appear in the sessions table."""
    app, _queue, pilot = hitl_app
    app.record_session_activity("sess-active", "hitl_confirm", client_name="active-agent")
    await pilot.pause()
    table = app.query_one("#sessions-table", DataTable)
    assert table.row_count >= 1


# ---------------------------------------------------------------------------
# Collapsible message widget
# ---------------------------------------------------------------------------


async def test_collapsible_message_long() -> None:
    """Messages > 200 chars should render a Collapsible widget."""
    app = _TestApp(hitl_queue=HITLQueue())
    async with app.run_test(size=(120, 40)) as pilot:
        long_msg = "x" * 250
        req = _req("hitl_confirm", {"message": long_msg, "severity": "medium"})
        app.push_screen(ConfirmScreen(req))
        await pilot.pause()
        # Query from the current screen (the pushed ConfirmScreen)
        collapsibles = app.screen.query(Collapsible)
        assert len(collapsibles) > 0


async def test_collapsible_message_short() -> None:
    """Messages <= 200 chars should NOT render a Collapsible widget."""
    app = _TestApp(hitl_queue=HITLQueue())
    async with app.run_test(size=(120, 40)) as pilot:
        req = _req("hitl_confirm", {"message": "Short message", "severity": "medium"})
        app.push_screen(ConfirmScreen(req))
        await pilot.pause()
        collapsibles = app.screen.query(Collapsible)
        assert len(collapsibles) == 0


# ---------------------------------------------------------------------------
# Step indicator
# ---------------------------------------------------------------------------


async def test_step_indicator_shown() -> None:
    app = _TestApp(hitl_queue=HITLQueue())
    async with app.run_test(size=(120, 40)) as pilot:
        req = _req(
            "hitl_confirm",
            {"message": "Step test", "severity": "medium", "step": 2, "total_steps": 5},
        )
        app.push_screen(ConfirmScreen(req))
        await pilot.pause()
        # _step_widget returns Static with classes="step-indicator"
        step_widgets = app.screen.query(".step-indicator")
        assert len(step_widgets) > 0


# ---------------------------------------------------------------------------
# Expand/Collapse All (ctrl+e)
# ---------------------------------------------------------------------------


async def test_ctrl_e_toggles_queue_expanded(hitl_app: Any) -> None:
    """ctrl+e should toggle _queue_expanded reactive."""
    app, _queue, pilot = hitl_app
    assert app._queue_expanded is False
    await pilot.press("ctrl+e")
    await pilot.pause()
    assert app._queue_expanded is True
    await pilot.press("ctrl+e")
    await pilot.pause()
    assert app._queue_expanded is False

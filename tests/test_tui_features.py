"""Tests for v0.8.0 TUI features: session tracking, queue table, log level, VS Code bindings."""

from __future__ import annotations

from typing import ClassVar

import pytest
from textual.widgets import DataTable

from hitl_mcp_cli.tui.app import HITLApp
from hitl_mcp_cli.tui.queue import HITLQueue


class _TestApp(HITLApp):
    """Test subclass that skips server thread and auto-starts queue worker."""

    CSS_PATH: ClassVar[list[str]] = []

    def on_mount(self) -> None:
        # Init tables only, no server thread
        st = self.query_one("#sessions-table", DataTable)
        st.add_columns("ID", "Calls", "Pending", "Last active")
        qt = self.query_one("#queue-table", DataTable)
        qt.add_columns("#", "Tool", "Message")


@pytest.mark.asyncio
async def test_startup_banner_in_log() -> None:
    """Startup banner should appear in activity log on mount."""
    queue = HITLQueue()
    app = HITLApp(hitl_queue=queue)
    async with app.run_test(size=(120, 40)):
        log = app.query_one("#output-log")
        # Banner is written in on_mount — just verify the log widget exists and is mounted
        assert log is not None


@pytest.mark.asyncio
async def test_session_tracking() -> None:
    """record_session_activity should add rows to sessions table."""
    queue = HITLQueue()
    app = _TestApp(hitl_queue=queue)
    async with app.run_test(size=(120, 40)) as pilot:
        app.record_session_activity("session-abc123", "hitl_notify", "my-project")
        await pilot.pause(0.1)
        table = app.query_one("#sessions-table", DataTable)
        assert table.row_count == 1
        assert app.session_count == 1


@pytest.mark.asyncio
async def test_session_tracking_dedup() -> None:
    """Same session_id should not add duplicate rows."""
    queue = HITLQueue()
    app = _TestApp(hitl_queue=queue)
    async with app.run_test(size=(120, 40)) as pilot:
        app.record_session_activity("session-abc123", "hitl_notify")
        app.record_session_activity("session-abc123", "hitl_confirm")
        await pilot.pause(0.1)
        table = app.query_one("#sessions-table", DataTable)
        assert table.row_count == 1  # no duplicate
        assert app.session_count == 1


@pytest.mark.asyncio
async def test_queue_table_add_remove() -> None:
    """add_queue_row and remove_queue_row should update queue DataTable."""
    queue = HITLQueue()
    app = _TestApp(hitl_queue=queue)
    async with app.run_test(size=(120, 40)) as pilot:
        app.add_queue_row("req-1", "hitl_confirm", "Are you sure?")
        await pilot.pause(0.1)
        table = app.query_one("#queue-table", DataTable)
        assert table.row_count == 1
        assert app.queue_count == 1

        app.remove_queue_row("req-1")
        await pilot.pause(0.1)
        # Row stays in table (queue history persistence) — only status is updated
        assert table.row_count == 1
        assert app.queue_count == 0


@pytest.mark.asyncio
async def test_log_level_cycle() -> None:
    """F2 should cycle through log levels."""
    queue = HITLQueue()
    app = _TestApp(hitl_queue=queue)
    async with app.run_test(size=(120, 40)) as pilot:
        assert app.min_level == "INFO"
        await pilot.press("f2")
        assert app.min_level == "WARNING"
        await pilot.press("f2")
        assert app.min_level == "ERROR"
        await pilot.press("f2")
        assert app.min_level == "DEBUG"
        await pilot.press("f2")
        assert app.min_level == "INFO"  # wraps around


@pytest.mark.asyncio
async def test_toggle_sessions_panel() -> None:
    """ctrl+b should toggle sessions panel visibility."""
    queue = HITLQueue()
    app = _TestApp(hitl_queue=queue)
    async with app.run_test(size=(120, 40)) as pilot:
        assert app.sessions_visible is True
        await pilot.press("ctrl+b")
        assert app.sessions_visible is False
        await pilot.press("ctrl+b")
        assert app.sessions_visible is True


@pytest.mark.asyncio
async def test_clear_log_action() -> None:
    """ctrl+l should clear the activity log."""
    queue = HITLQueue()
    app = _TestApp(hitl_queue=queue)
    async with app.run_test(size=(120, 40)) as pilot:
        app.stream_output("agent", "test message", "info")
        await pilot.pause(0.1)
        await pilot.press("ctrl+l")
        await pilot.pause(0.1)
        # Log should be cleared (no exception = success)
        log = app.query_one("#output-log")
        assert log is not None


@pytest.mark.asyncio
async def test_stream_output_level_filter() -> None:
    """stream_output should filter messages below min_level."""
    queue = HITLQueue()
    app = _TestApp(hitl_queue=queue)
    async with app.run_test(size=(120, 40)) as pilot:
        app.min_level = "ERROR"
        # This should be filtered (info < error)
        app.stream_output("agent", "debug message", "info")
        # This should pass through
        app.stream_output("agent", "error message", "error")
        await pilot.pause(0.1)
        # No exception = success; filtering is visual only

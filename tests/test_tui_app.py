"""Tests for HITLApp and TUI screens using Textual's Pilot."""

from __future__ import annotations

import asyncio
import time
from typing import Any, ClassVar

import pytest
from textual.widgets import Button, DataTable, Input, Label, OptionList, RichLog, TextArea

from hitl_mcp_cli.tui.app import HITLApp, _queue_status_text, _session_style
from hitl_mcp_cli.tui.queue import HITLQueue, HITLRequest
from hitl_mcp_cli.tui.screens import ChooseScreen, CollectScreen, ConfirmScreen, NotifyScreen, screen_for


def _make_request(
    tool: str = "confirm",
    params: dict[str, Any] | None = None,
    priority: int = 5,
    loop: asyncio.AbstractEventLoop | None = None,
) -> HITLRequest:
    if loop is None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
    return HITLRequest(
        tool=tool,
        params=params or {},
        future=loop.create_future(),
        priority=priority,
    )


class _TestApp(HITLApp):
    """HITLApp subclass that skips queue worker for testing."""

    CSS_PATH: ClassVar[list[str]] = []  # type: ignore[assignment]  # Override to avoid CSS file resolution in tests

    def start_queue_worker(self) -> None:
        pass  # Don't start the blocking queue worker in tests


# --- HITLApp ---


class TestHITLApp:
    @pytest.mark.asyncio
    async def test_app_mounts(self) -> None:
        queue = HITLQueue()
        app = _TestApp(hitl_queue=queue)
        async with app.run_test() as _:
            assert app.query_one("#output-log", RichLog) is not None
            assert app.query_one("#status-bar", Label) is not None

    @pytest.mark.asyncio
    async def test_stream_output(self) -> None:
        queue = HITLQueue()
        app = _TestApp(hitl_queue=queue)
        async with app.run_test() as _:
            app.stream_output("test-agent", "hello world", "info")
            log = app.query_one("#output-log", RichLog)
            assert log is not None

    @pytest.mark.asyncio
    async def test_stream_output_levels(self) -> None:
        queue = HITLQueue()
        app = _TestApp(hitl_queue=queue)
        async with app.run_test() as _:
            for level in ("success", "error", "warning", "info"):
                app.stream_output("agent", f"msg-{level}", level)

    @pytest.mark.asyncio
    async def test_update_queue_status(self) -> None:
        queue = HITLQueue()
        app = _TestApp(hitl_queue=queue)
        async with app.run_test() as pilot:
            app.update_queue_status()
            label = app.query_one("#status-bar", Label)
            await pilot.pause()
            assert label is not None

    @pytest.mark.asyncio
    async def test_no_server_thread_without_mcp_app(self) -> None:
        queue = HITLQueue()
        app = _TestApp(hitl_queue=queue)
        async with app.run_test() as _:
            assert app._server_thread is None


# --- screen_for factory ---


class TestScreenFactory:
    def test_confirm_screen(self) -> None:
        req = _make_request("hitl_confirm", {"message": "ok?"})
        assert isinstance(screen_for(req), ConfirmScreen)

    def test_collect_screen(self) -> None:
        req = _make_request("hitl_collect", {"message": "name?"})
        assert isinstance(screen_for(req), CollectScreen)

    def test_ask_screen(self) -> None:
        req = _make_request("hitl_ask", {"message": "name?"})
        assert isinstance(screen_for(req), CollectScreen)

    def test_choose_screen(self) -> None:
        req = _make_request("hitl_choose", {"message": "pick", "choices": ["a", "b"]})
        assert isinstance(screen_for(req), ChooseScreen)

    def test_notify_screen(self) -> None:
        req = _make_request("hitl_notify", {"message": "done"})
        assert isinstance(screen_for(req), NotifyScreen)

    def test_unknown_tool_defaults_to_notify(self) -> None:
        req = _make_request("unknown_tool", {"message": "?"})
        assert isinstance(screen_for(req), NotifyScreen)

    def test_short_tool_names(self) -> None:
        assert isinstance(screen_for(_make_request("confirm")), ConfirmScreen)
        assert isinstance(screen_for(_make_request("collect")), CollectScreen)
        assert isinstance(screen_for(_make_request("choose")), ChooseScreen)
        assert isinstance(screen_for(_make_request("notify")), NotifyScreen)


# --- ConfirmScreen ---


class TestConfirmScreen:
    @pytest.mark.asyncio
    async def test_confirm_yes(self) -> None:
        app = _TestApp(hitl_queue=HITLQueue())
        results: list[Any] = []

        async with app.run_test() as pilot:
            req = _make_request("confirm", {"message": "Proceed?", "severity": "medium"})
            app.push_screen(ConfirmScreen(req), callback=results.append)
            await pilot.pause()
            await pilot.click("#yes")
            await pilot.pause()

        assert results == [{"action": "accept"}]

    @pytest.mark.asyncio
    async def test_confirm_no(self) -> None:
        app = _TestApp(hitl_queue=HITLQueue())
        results: list[Any] = []

        async with app.run_test() as pilot:
            req = _make_request("confirm", {"message": "Proceed?", "severity": "low"})
            app.push_screen(ConfirmScreen(req), callback=results.append)
            await pilot.pause()
            await pilot.click("#no")
            await pilot.pause()

        assert results == [{"action": "decline"}]

    @pytest.mark.asyncio
    async def test_confirm_high_severity_shows_input(self) -> None:
        app = _TestApp(hitl_queue=HITLQueue())

        async with app.run_test() as pilot:
            req = _make_request("confirm", {"message": "Delete?", "severity": "high"})
            screen = ConfirmScreen(req)
            app.push_screen(screen)
            await pilot.pause()
            inp = screen.query_one("#high-input", Input)
            assert inp is not None

    @pytest.mark.asyncio
    async def test_confirm_with_context(self) -> None:
        app = _TestApp(hitl_queue=HITLQueue())

        async with app.run_test() as pilot:
            req = _make_request(
                "confirm",
                {
                    "message": "Deploy?",
                    "severity": "medium",
                    "context": "This will affect production",
                },
            )
            screen = ConfirmScreen(req)
            app.push_screen(screen)
            await pilot.pause()
            assert len(screen.query(".context")) > 0


# --- CollectScreen ---


class TestCollectScreen:
    @pytest.mark.asyncio
    async def test_collect_text_input(self) -> None:
        app = _TestApp(hitl_queue=HITLQueue())

        async with app.run_test() as pilot:
            req = _make_request("collect", {"message": "Name?", "input_type": "text"})
            screen = CollectScreen(req)
            app.push_screen(screen)
            await pilot.pause()
            assert screen.query_one("#collect-input", Input) is not None

    @pytest.mark.asyncio
    async def test_collect_with_default(self) -> None:
        app = _TestApp(hitl_queue=HITLQueue())

        async with app.run_test() as pilot:
            req = _make_request(
                "collect",
                {
                    "message": "Name?",
                    "input_type": "text",
                    "default": "John",
                },
            )
            screen = CollectScreen(req)
            app.push_screen(screen)
            await pilot.pause()
            inp = screen.query_one("#collect-input", Input)
            assert inp.value == "John"

    @pytest.mark.asyncio
    async def test_collect_cancel(self) -> None:
        app = _TestApp(hitl_queue=HITLQueue())
        results: list[Any] = []

        async with app.run_test() as pilot:
            req = _make_request("collect", {"message": "Name?"})
            app.push_screen(CollectScreen(req), callback=results.append)
            await pilot.pause()
            await pilot.click("#cancel")
            await pilot.pause()

        assert results == [{"action": "cancel"}]


# --- ChooseScreen ---


class TestChooseScreen:
    @pytest.mark.asyncio
    async def test_choose_single_select(self) -> None:
        app = _TestApp(hitl_queue=HITLQueue())

        async with app.run_test() as pilot:
            req = _make_request(
                "choose",
                {
                    "message": "Pick one",
                    "choices": ["alpha", "beta", "gamma"],
                },
            )
            screen = ChooseScreen(req)
            app.push_screen(screen)
            await pilot.pause()
            assert screen.query_one("#choose-list", OptionList) is not None

    @pytest.mark.asyncio
    async def test_choose_multiple_shows_buttons(self) -> None:
        app = _TestApp(hitl_queue=HITLQueue())

        async with app.run_test() as pilot:
            req = _make_request(
                "choose",
                {
                    "message": "Pick many",
                    "choices": ["a", "b", "c"],
                    "multiple": True,
                },
            )
            screen = ChooseScreen(req)
            app.push_screen(screen)
            await pilot.pause()
            assert len(screen.query(".choice-btn")) == 3

    @pytest.mark.asyncio
    async def test_choose_cancel(self) -> None:
        app = _TestApp(hitl_queue=HITLQueue())
        results: list[Any] = []

        async with app.run_test() as pilot:
            req = _make_request(
                "choose",
                {
                    "message": "Pick",
                    "choices": ["a", "b"],
                },
            )
            app.push_screen(ChooseScreen(req), callback=results.append)
            await pilot.pause()
            await pilot.click("#cancel")
            await pilot.pause()

        assert results == [{"action": "cancel"}]


# --- NotifyScreen ---


class TestNotifyScreen:
    @pytest.mark.asyncio
    async def test_notify_renders(self) -> None:
        app = _TestApp(hitl_queue=HITLQueue())

        async with app.run_test() as pilot:
            req = _make_request(
                "notify",
                {
                    "message": "All done!",
                    "level": "success",
                    "title": "Complete",
                },
            )
            screen = NotifyScreen(req)
            app.push_screen(screen)
            await pilot.pause()
            assert screen.query_one("#dismiss", Button) is not None

    @pytest.mark.asyncio
    async def test_notify_manual_dismiss(self) -> None:
        app = _TestApp(hitl_queue=HITLQueue())
        results: list[Any] = []

        async with app.run_test() as pilot:
            req = _make_request("notify", {"message": "Info"})
            app.push_screen(NotifyScreen(req), callback=results.append)
            await pilot.pause()
            await pilot.click("#dismiss")
            await pilot.pause()

        assert results == [True]


# --- Additional coverage tests ---


class TestConfirmScreenHighSeverity:
    @pytest.mark.asyncio
    async def test_high_severity_accept(self) -> None:
        app = _TestApp(hitl_queue=HITLQueue())
        results: list[Any] = []

        async with app.run_test(size=(80, 24)) as pilot:
            req = _make_request("confirm", {"message": "Delete all?", "severity": "high"})
            screen = ConfirmScreen(req)
            app.push_screen(screen, callback=results.append)
            await pilot.pause()
            inp = screen.query_one("#high-input", Input)
            inp.value = "yes"
            await pilot.press("enter")
            await pilot.pause()

        assert results == [{"action": "accept"}]

    @pytest.mark.asyncio
    async def test_high_severity_decline(self) -> None:
        app = _TestApp(hitl_queue=HITLQueue())
        results: list[Any] = []

        async with app.run_test(size=(80, 24)) as pilot:
            req = _make_request("confirm", {"message": "Delete all?", "severity": "high"})
            screen = ConfirmScreen(req)
            app.push_screen(screen, callback=results.append)
            await pilot.pause()
            inp = screen.query_one("#high-input", Input)
            inp.value = "no"
            await pilot.press("enter")
            await pilot.pause()

        assert results == [{"action": "decline"}]


class TestCollectScreenValidation:
    @pytest.mark.asyncio
    async def test_collect_submit_valid(self) -> None:
        app = _TestApp(hitl_queue=HITLQueue())
        results: list[Any] = []

        async with app.run_test(size=(80, 24)) as pilot:
            req = _make_request("collect", {"message": "Slug?", "validation_pattern": r"^[a-z-]+$"})
            screen = CollectScreen(req)
            app.push_screen(screen, callback=results.append)
            await pilot.pause()
            inp = screen.query_one("#collect-input", Input)
            inp.value = "my-slug"
            await pilot.click("#submit")
            await pilot.pause()

        assert results == ["my-slug"]

    @pytest.mark.asyncio
    async def test_collect_submit_invalid_shows_error(self) -> None:
        app = _TestApp(hitl_queue=HITLQueue())
        results: list[Any] = []

        async with app.run_test(size=(80, 24)) as pilot:
            req = _make_request(
                "collect",
                {
                    "message": "Slug?",
                    "validation_pattern": r"^[a-z-]+$",
                    "validation_message": "Only lowercase and dashes",
                },
            )
            screen = CollectScreen(req)
            app.push_screen(screen, callback=results.append)
            await pilot.pause()
            inp = screen.query_one("#collect-input", Input)
            inp.value = "INVALID!"
            await pilot.click("#submit")
            await pilot.pause()
            # Should NOT have dismissed — validation failed
            assert results == []
            # Error message should be visible
            err = screen.query_one("#validation-msg")
            assert "visible" in err.classes

    @pytest.mark.asyncio
    async def test_collect_multiline(self) -> None:
        app = _TestApp(hitl_queue=HITLQueue())

        async with app.run_test(size=(80, 24)) as pilot:
            req = _make_request("collect", {"message": "Description?", "input_type": "multiline"})
            screen = CollectScreen(req)
            app.push_screen(screen)
            await pilot.pause()
            ta = screen.query_one("#collect-input", TextArea)
            assert ta is not None

    @pytest.mark.asyncio
    async def test_collect_submit_via_ctrl_enter(self) -> None:
        app = _TestApp(hitl_queue=HITLQueue())
        results: list[Any] = []

        async with app.run_test(size=(80, 24)) as pilot:
            req = _make_request("collect", {"message": "Name?"})
            screen = CollectScreen(req)
            app.push_screen(screen, callback=results.append)
            await pilot.pause()
            inp = screen.query_one("#collect-input", Input)
            inp.value = "test-value"
            inp.focus()
            await pilot.press("ctrl+j")
            await pilot.pause()

        assert results == ["test-value"]


class TestChooseScreenInteraction:
    @pytest.mark.asyncio
    async def test_choose_ok_single(self) -> None:
        app = _TestApp(hitl_queue=HITLQueue())
        results: list[Any] = []

        async with app.run_test(size=(80, 24)) as pilot:
            req = _make_request(
                "choose",
                {
                    "message": "Pick",
                    "choices": ["alpha", "beta"],
                },
            )
            screen = ChooseScreen(req)
            app.push_screen(screen, callback=results.append)
            await pilot.pause()
            # OptionList: highlight first item and press enter to select
            option_list = screen.query_one("#choose-list", OptionList)
            option_list.focus()
            await pilot.press("enter")
            await pilot.pause()

        assert len(results) == 1
        assert results[0] in ("alpha", "beta")

    @pytest.mark.asyncio
    async def test_choose_multiple_done(self) -> None:
        app = _TestApp(hitl_queue=HITLQueue())
        results: list[Any] = []

        async with app.run_test(size=(80, 24)) as pilot:
            req = _make_request(
                "choose",
                {
                    "message": "Pick many",
                    "choices": ["a", "b", "c"],
                    "multiple": True,
                },
            )
            screen = ChooseScreen(req)
            app.push_screen(screen, callback=results.append)
            await pilot.pause()
            # Click done without selecting anything
            await pilot.click("#done")
            await pilot.pause()

        assert results == [[]]


# --- Newline expansion and Markdown rendering (TUI) ---


class TestNotifyScreenNewlineAndMarkdown:
    @pytest.mark.asyncio
    async def test_notify_expands_literal_newlines(self) -> None:
        """Test that literal \\n in message is expanded to real newlines."""
        app = _TestApp(hitl_queue=HITLQueue())

        async with app.run_test() as pilot:
            req = _make_request(
                "notify",
                {"message": "line1\\nline2", "level": "info"},
            )
            screen = NotifyScreen(req)
            app.push_screen(screen)
            await pilot.pause()
            # The internal message should have real newlines
            assert screen._message == "line1\nline2"

    @pytest.mark.asyncio
    async def test_notify_renders_markdown_widget(self) -> None:
        """Test that markdown content uses Markdown widget instead of Static."""
        from textual.widgets import Markdown as TextualMarkdown

        app = _TestApp(hitl_queue=HITLQueue())

        async with app.run_test() as pilot:
            req = _make_request(
                "notify",
                {
                    "message": "# Header\n\n- item1\n- item2\n\n**bold text**",
                    "level": "info",
                },
            )
            screen = NotifyScreen(req)
            app.push_screen(screen)
            await pilot.pause()
            md_widgets = screen.query(TextualMarkdown)
            assert len(md_widgets) > 0

    @pytest.mark.asyncio
    async def test_notify_plain_text_uses_static(self) -> None:
        """Test that plain text uses Static widget, not Markdown."""
        from textual.widgets import Markdown as TextualMarkdown

        app = _TestApp(hitl_queue=HITLQueue())

        async with app.run_test() as pilot:
            req = _make_request(
                "notify",
                {"message": "Just plain text", "level": "info"},
            )
            screen = NotifyScreen(req)
            app.push_screen(screen)
            await pilot.pause()
            md_widgets = screen.query(TextualMarkdown)
            assert len(md_widgets) == 0

    @pytest.mark.asyncio
    async def test_notify_title_expands_newlines(self) -> None:
        """Test that literal \\n in title is expanded."""
        app = _TestApp(hitl_queue=HITLQueue())

        async with app.run_test() as pilot:
            req = _make_request(
                "notify",
                {"message": "msg", "title": "Title\\nSubtitle", "level": "info"},
            )
            screen = NotifyScreen(req)
            app.push_screen(screen)
            await pilot.pause()
            assert screen._title_text == "Title\nSubtitle"


# ---------------------------------------------------------------------------
# Pure unit tests for module-level helpers (lines 44-59)
# ---------------------------------------------------------------------------


class TestSessionStyle:
    def test_active_session(self) -> None:
        ts = time.monotonic()  # just now → age < 600s
        assert _session_style(ts) == "bold bright_white"

    def test_idle_session(self) -> None:
        ts = time.monotonic() - 1200  # 20 min ago → 600 < age < 3600
        assert _session_style(ts) == "white"

    def test_old_session(self) -> None:
        ts = time.monotonic() - 7200  # 2 hours ago → age > 3600
        assert _session_style(ts) == "dim"


class TestQueueStatusText:
    def test_pending(self) -> None:
        t = _queue_status_text("pending")
        assert "PENDING" in t.plain

    def test_answered(self) -> None:
        t = _queue_status_text("answered")
        assert "DONE" in t.plain

    def test_cancelled(self) -> None:
        t = _queue_status_text("cancelled")
        assert "CANCEL" in t.plain

    def test_minimized(self) -> None:
        t = _queue_status_text("minimized")
        assert "PAUSED" in t.plain

    def test_unknown_status(self) -> None:
        t = _queue_status_text("foobar")
        assert t.plain == "foobar"


# ---------------------------------------------------------------------------
# _update_queue_row_status with answer_preview (lines 528-533)
# ---------------------------------------------------------------------------


class TestUpdateQueueRowStatus:
    @pytest.mark.asyncio
    async def test_status_update_with_answer_preview(self) -> None:
        app = _TestApp(hitl_queue=HITLQueue())
        async with app.run_test(size=(120, 40)) as pilot:
            req = _make_request("hitl_confirm", {"message": "ok?"})
            app.add_queue_row(req.request_id, req.tool, "ok?", request=req)
            await pilot.pause()
            # Call with answer_preview — covers the answer_preview branch
            app._update_queue_row_status(req.request_id, "answered", "accepted")
            await pilot.pause()
            table = app.query_one("#queue-table", DataTable)
            assert table.row_count == 1

    @pytest.mark.asyncio
    async def test_status_update_unknown_row_is_silent(self) -> None:
        """Updating a non-existent row should not raise (exception pass)."""
        app = _TestApp(hitl_queue=HITLQueue())
        async with app.run_test(size=(120, 40)) as _pilot:
            # No row added — should silently pass
            app._update_queue_row_status("nonexistent-id", "cancelled", "")


# ---------------------------------------------------------------------------
# record_session_resolved (lines 325-333)
# ---------------------------------------------------------------------------


class TestRecordSessionResolved:
    @pytest.mark.asyncio
    async def test_resolved_unknown_session_is_noop(self) -> None:
        app = _TestApp(hitl_queue=HITLQueue())
        async with app.run_test(size=(120, 40)) as _pilot:
            # Should return early without error
            app.record_session_resolved("nonexistent-session")

    @pytest.mark.asyncio
    async def test_resolved_decrements_pending(self) -> None:
        app = _TestApp(hitl_queue=HITLQueue())
        async with app.run_test(size=(120, 40)) as pilot:
            app.record_session_activity("sess-1", "hitl_confirm", client_name="agent")
            await pilot.pause()
            assert app._sessions["sess-1"]["pending"] == 1
            app.record_session_resolved("sess-1")
            await pilot.pause()
            assert app._sessions["sess-1"]["pending"] == 0
            assert app._sessions["sess-1"]["completed"] == 1

    @pytest.mark.asyncio
    async def test_resolved_pending_floor_is_zero(self) -> None:
        """Calling resolved twice should not go below 0."""
        app = _TestApp(hitl_queue=HITLQueue())
        async with app.run_test(size=(120, 40)) as pilot:
            app.record_session_activity("sess-2", "hitl_confirm")
            await pilot.pause()
            app.record_session_resolved("sess-2")
            app.record_session_resolved("sess-2")
            await pilot.pause()
            assert app._sessions["sess-2"]["pending"] == 0


# ---------------------------------------------------------------------------
# _update_elapsed (lines 277-282)
# ---------------------------------------------------------------------------


class TestUpdateElapsed:
    @pytest.mark.asyncio
    async def test_update_elapsed_updates_cell(self) -> None:
        app = _TestApp(hitl_queue=HITLQueue())
        async with app.run_test(size=(120, 40)) as pilot:
            req = _make_request("hitl_confirm", {"message": "timer test"})
            app.add_queue_row(req.request_id, req.tool, "timer test", request=req)
            await pilot.pause()
            # Call directly — covers the loop body
            app._update_elapsed()
            await pilot.pause()
            table = app.query_one("#queue-table", DataTable)
            assert table.row_count == 1

    @pytest.mark.asyncio
    async def test_update_elapsed_empty_map_is_noop(self) -> None:
        app = _TestApp(hitl_queue=HITLQueue())
        async with app.run_test(size=(120, 40)) as _pilot:
            # No rows — should not raise
            app._update_elapsed()


# ---------------------------------------------------------------------------
# _rebuild_sessions_table with multiple sessions (lines 305-320)
# ---------------------------------------------------------------------------


class TestRebuildSessionsTable:
    @pytest.mark.asyncio
    async def test_multiple_sessions_sorted_by_recency(self) -> None:
        app = _TestApp(hitl_queue=HITLQueue())
        async with app.run_test(size=(120, 40)) as pilot:
            app.record_session_activity("sess-a", "hitl_confirm", client_name="agent-a")
            await pilot.pause()
            app.record_session_activity("sess-b", "hitl_confirm", client_name="agent-b")
            await pilot.pause()
            table = app.query_one("#sessions-table", DataTable)
            assert table.row_count == 2

    @pytest.mark.asyncio
    async def test_existing_session_updates_calls(self) -> None:
        app = _TestApp(hitl_queue=HITLQueue())
        async with app.run_test(size=(120, 40)) as pilot:
            app.record_session_activity("sess-x", "hitl_confirm", client_name="agent-x")
            await pilot.pause()
            # Second call to same session — covers the else branch (lines 378-385)
            app.record_session_activity(
                "sess-x", "hitl_collect", project_id="proj-y", client_name="agent-x-v2"
            )
            await pilot.pause()
            assert app._sessions["sess-x"]["calls"] == 2
            assert app._sessions["sess-x"]["project_id"] == "proj-y"
            assert app._sessions["sess-x"]["client_name"] == "agent-x-v2"


# ---------------------------------------------------------------------------
# _on_queue_row_selected — all status branches (lines 236-268)
# ---------------------------------------------------------------------------


class TestOnQueueRowSelected:
    @pytest.mark.asyncio
    async def test_row_selected_no_request_no_pending_screen(self) -> None:
        """Row with no request map entry and no pending screen → notify."""
        app = _TestApp(hitl_queue=HITLQueue())
        async with app.run_test(size=(120, 40)) as pilot:
            req = _make_request("hitl_confirm", {"message": "test"})
            app.add_queue_row(req.request_id, req.tool, "test", request=req)
            await pilot.pause()
            table = app.query_one("#queue-table", DataTable)
            # Remove from map so handler hits the "no request" branch
            del app._queue_request_map[req.request_id]
            row_key = table._row_locations.get_key(0)
            event = DataTable.RowSelected(table, 0, row_key)
            app._on_queue_row_selected(event)
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_row_selected_answered_status(self) -> None:
        """Clicking an answered row shows answer preview notification."""
        app = _TestApp(hitl_queue=HITLQueue())
        async with app.run_test(size=(120, 40)) as pilot:
            req = _make_request("hitl_confirm", {"message": "done"})
            app.add_queue_row(req.request_id, req.tool, "done", request=req)
            await pilot.pause()
            app._hitl_queue.mark_answered(req.request_id, "accepted")
            table = app.query_one("#queue-table", DataTable)
            row_key = table._row_locations.get_key(0)
            event = DataTable.RowSelected(table, 0, row_key)
            app._on_queue_row_selected(event)
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_row_selected_cancelled_status(self) -> None:
        """Clicking a cancelled row shows cancelled notification."""
        app = _TestApp(hitl_queue=HITLQueue())
        async with app.run_test(size=(120, 40)) as pilot:
            req = _make_request("hitl_confirm", {"message": "gone"})
            app.add_queue_row(req.request_id, req.tool, "gone", request=req)
            await pilot.pause()
            app._hitl_queue.mark_cancelled(req.request_id)
            table = app.query_one("#queue-table", DataTable)
            row_key = table._row_locations.get_key(0)
            event = DataTable.RowSelected(table, 0, row_key)
            app._on_queue_row_selected(event)
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_row_selected_pending_no_pending_screen(self) -> None:
        """Clicking a pending row with no pending screen → 'already active' notify."""
        app = _TestApp(hitl_queue=HITLQueue())
        async with app.run_test(size=(120, 40)) as pilot:
            req = _make_request("hitl_confirm", {"message": "active"})
            app.add_queue_row(req.request_id, req.tool, "active", request=req)
            await pilot.pause()
            table = app.query_one("#queue-table", DataTable)
            row_key = table._row_locations.get_key(0)
            event = DataTable.RowSelected(table, 0, row_key)
            app._on_queue_row_selected(event)
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_row_selected_minimized_no_pending_screen(self) -> None:
        """Clicking a minimized row with no pending screen → 'not minimized' notify."""
        app = _TestApp(hitl_queue=HITLQueue())
        async with app.run_test(size=(120, 40)) as pilot:
            req = _make_request("hitl_confirm", {"message": "paused"})
            app.add_queue_row(req.request_id, req.tool, "paused", request=req)
            await pilot.pause()
            app._hitl_queue.mark_minimized(req.request_id)
            table = app.query_one("#queue-table", DataTable)
            row_key = table._row_locations.get_key(0)
            event = DataTable.RowSelected(table, 0, row_key)
            app._on_queue_row_selected(event)
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_row_selected_answered_no_preview(self) -> None:
        """Answered row with no answer_preview shows '(no preview)'."""
        app = _TestApp(hitl_queue=HITLQueue())
        async with app.run_test(size=(120, 40)) as pilot:
            req = _make_request("hitl_confirm", {"message": "done"})
            app.add_queue_row(req.request_id, req.tool, "done", request=req)
            await pilot.pause()
            app._hitl_queue.mark_answered(req.request_id, "")
            table = app.query_one("#queue-table", DataTable)
            row_key = table._row_locations.get_key(0)
            event = DataTable.RowSelected(table, 0, row_key)
            app._on_queue_row_selected(event)
            await pilot.pause()


# ---------------------------------------------------------------------------
# action_restore_prompt with pending screen set (lines 220-222)
# ---------------------------------------------------------------------------


class TestActionRestorePrompt:
    @pytest.mark.asyncio
    async def test_restore_prompt_with_pending_screen(self) -> None:
        """action_restore_prompt clears _pending_screen and sets event."""
        from unittest.mock import MagicMock

        app = _TestApp(hitl_queue=HITLQueue())
        async with app.run_test(size=(120, 40)) as pilot:
            mock_screen = MagicMock()
            app._pending_screen = mock_screen
            app._restore_event = asyncio.Event()
            app.action_restore_prompt()
            await pilot.pause()
            assert app._pending_screen is None
            assert app._restore_event.is_set()

    @pytest.mark.asyncio
    async def test_restore_prompt_without_pending_screen(self) -> None:
        """action_restore_prompt with no pending screen is a no-op."""
        app = _TestApp(hitl_queue=HITLQueue())
        async with app.run_test(size=(120, 40)) as pilot:
            assert app._pending_screen is None
            app.action_restore_prompt()
            await pilot.pause()
            assert app._pending_screen is None


# ---------------------------------------------------------------------------
# stream_output level filtering (line 370)
# ---------------------------------------------------------------------------


class TestStreamOutputFiltering:
    @pytest.mark.asyncio
    async def test_debug_filtered_at_info_level(self) -> None:
        """DEBUG messages should be filtered when min_level is INFO."""
        app = _TestApp(hitl_queue=HITLQueue())
        async with app.run_test(size=(120, 40)) as pilot:
            app.min_level = "INFO"
            log = app.query_one("#output-log", RichLog)
            line_count_before = len(log.lines)
            app.stream_output("agent", "debug message", "debug")
            await pilot.pause()
            # Line count should not increase (filtered out)
            assert len(log.lines) == line_count_before

    @pytest.mark.asyncio
    async def test_warning_passes_at_info_level(self) -> None:
        """WARNING messages should pass through when min_level is INFO."""
        app = _TestApp(hitl_queue=HITLQueue())
        async with app.run_test(size=(120, 40)) as pilot:
            app.min_level = "INFO"
            log = app.query_one("#output-log", RichLog)
            line_count_before = len(log.lines)
            app.stream_output("agent", "warning message", "warning")
            await pilot.pause()
            assert len(log.lines) > line_count_before

    @pytest.mark.asyncio
    async def test_stream_output_markdown_path(self) -> None:
        """Messages with markdown syntax should use RichMarkdown renderer (line 372)."""
        app = _TestApp(hitl_queue=HITLQueue())
        async with app.run_test(size=(120, 40)) as pilot:
            app.min_level = "DEBUG"
            log = app.query_one("#output-log", RichLog)
            line_count_before = len(log.lines)
            # Markdown-like content triggers _has_markdown
            app.stream_output("agent", "# Header\n\n- item1\n- item2", "info")
            await pilot.pause()
            assert len(log.lines) > line_count_before

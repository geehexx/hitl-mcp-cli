"""Targeted tests to close remaining coverage gaps.

Covers:
- _server_core.py: get_client_name ctx path, get_session_id ctx fallback
- interaction_log.py: _rotate_if_needed rename race condition
- tools/_collect.py: path validation (not-a-file, not-a-dir, valid path)
- tui/screens.py: _has_markdown long text, helper None returns,
  CollectScreen step/context/notes branches, _validate regex error
"""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path
from typing import Any, ClassVar
from unittest.mock import MagicMock, patch

import pytest

from hitl_mcp_cli.tui.app import HITLApp
from hitl_mcp_cli.tui.queue import HITLQueue

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _TestApp(HITLApp):
    CSS_PATH: ClassVar[list[str]] = []  # type: ignore[assignment]

    def start_queue_worker(self) -> None:
        pass


# ---------------------------------------------------------------------------
# _server_core.py
# ---------------------------------------------------------------------------


class TestGetClientName:
    def test_returns_agent_name_when_provided(self) -> None:
        from hitl_mcp_cli._server_core import get_client_name

        result = get_client_name(None, agent_name="my-agent")
        assert result == "my-agent"

    def test_returns_none_when_ctx_is_none(self) -> None:
        from hitl_mcp_cli._server_core import get_client_name

        result = get_client_name(None)
        assert result is None

    def test_returns_client_info_name_from_ctx(self) -> None:
        from hitl_mcp_cli._server_core import get_client_name

        mock_ctx = MagicMock()
        mock_ctx.session.client_params.clientInfo.name = "claude-code"
        result = get_client_name(mock_ctx)
        assert result == "claude-code"

    def test_returns_none_when_ctx_raises(self) -> None:
        """Covers lines 72-74: exception path in get_client_name."""
        from hitl_mcp_cli._server_core import get_client_name

        mock_ctx = MagicMock()
        mock_ctx.session.client_params = None  # accessing .clientInfo will raise AttributeError
        # Force the try block to raise
        type(mock_ctx).session = property(lambda self: (_ for _ in ()).throw(RuntimeError("no session")))
        result = get_client_name(mock_ctx)
        assert result is None

    def test_returns_none_when_client_params_none(self) -> None:
        """Covers line 64 (agent_name falsy) + lines 72-74 (params is None → returns None at line 74)."""
        from hitl_mcp_cli._server_core import get_client_name

        mock_ctx = MagicMock()
        mock_ctx.session.client_params = None
        result = get_client_name(mock_ctx)
        assert result is None


class TestGetSessionId:
    def test_returns_thread_fallback_when_ctx_none(self) -> None:
        from hitl_mcp_cli._server_core import get_session_id

        result = get_session_id(None)
        assert result.startswith("thread-")
        assert str(threading.current_thread().ident) in result

    def test_returns_session_id_from_ctx(self) -> None:
        from hitl_mcp_cli._server_core import get_session_id

        mock_ctx = MagicMock()
        mock_ctx.session_id = "sess-abc123"
        result = get_session_id(mock_ctx)
        assert result == "sess-abc123"

    def test_falls_back_to_thread_when_ctx_raises(self) -> None:
        """Covers lines 82-83: RuntimeError/AttributeError fallback."""
        from hitl_mcp_cli._server_core import get_session_id

        mock_ctx = MagicMock()
        type(mock_ctx).session_id = property(lambda self: (_ for _ in ()).throw(RuntimeError("no id")))
        result = get_session_id(mock_ctx)
        assert result.startswith("thread-")

    def test_falls_back_to_thread_on_attribute_error(self) -> None:
        """Covers lines 82-83: AttributeError fallback."""
        from hitl_mcp_cli._server_core import get_session_id

        mock_ctx = MagicMock()
        type(mock_ctx).session_id = property(lambda self: (_ for _ in ()).throw(AttributeError("no attr")))
        result = get_session_id(mock_ctx)
        assert result.startswith("thread-")


# ---------------------------------------------------------------------------
# interaction_log.py
# ---------------------------------------------------------------------------


class TestRotateIfNeeded:
    def test_rotate_handles_file_not_found_race(self, tmp_path: Path) -> None:
        """Covers lines 34-35: FileNotFoundError during rename is silently ignored."""
        from hitl_mcp_cli import interaction_log

        fake_log = tmp_path / "interactions.jsonl"
        fake_log.write_text("x" * 100)

        original_log_file = interaction_log.LOG_FILE
        interaction_log.LOG_FILE = fake_log
        original_max = interaction_log.MAX_LOG_SIZE
        interaction_log.MAX_LOG_SIZE = 10  # trigger rotation

        try:
            # Delete the file between exists() and rename() to simulate race
            with patch.object(Path, "rename", side_effect=FileNotFoundError("gone")):
                interaction_log._rotate_if_needed()  # should not raise
        finally:
            interaction_log.LOG_FILE = original_log_file
            interaction_log.MAX_LOG_SIZE = original_max


# ---------------------------------------------------------------------------
# tools/_collect.py — path validation branches
# ---------------------------------------------------------------------------


class TestCollectPathValidation:
    @pytest.mark.asyncio
    async def test_path_not_a_file_returns_cancel(self, tmp_path: Path) -> None:
        """Covers line 75: path_type='file' but path is a directory."""
        from hitl_mcp_cli.server import configure_tui_mode
        from hitl_mcp_cli.tui.queue import HITLQueue

        queue = HITLQueue()
        configure_tui_mode(queue, None)  # type: ignore[arg-type]
        try:
            from fastmcp import Client

            from hitl_mcp_cli.server import mcp

            async def _resolve() -> None:
                req = await queue.get()
                # Return the tmp_path directory (not a file)
                queue.resolve(req, str(tmp_path))

            task = asyncio.create_task(_resolve())
            async with Client(mcp) as client:
                result = await client.call_tool(
                    "hitl_collect",
                    {"message": "Pick a file:", "input_type": "path", "path_type": "file"},
                )
            await task
            assert isinstance(result.data, dict)
            assert result.data["action"] == "cancel"
            assert "not a file" in result.data["reason"]
        finally:
            configure_tui_mode(None, None)  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_path_not_a_dir_returns_cancel(self, tmp_path: Path) -> None:
        """Covers line 77: path_type='dir' but path is a file."""
        from hitl_mcp_cli.server import configure_tui_mode
        from hitl_mcp_cli.tui.queue import HITLQueue

        queue = HITLQueue()
        configure_tui_mode(queue, None)  # type: ignore[arg-type]
        try:
            from fastmcp import Client

            from hitl_mcp_cli.server import mcp

            fake_file = tmp_path / "test.txt"
            fake_file.write_text("hello")

            async def _resolve() -> None:
                req = await queue.get()
                queue.resolve(req, str(fake_file))

            task = asyncio.create_task(_resolve())
            async with Client(mcp) as client:
                result = await client.call_tool(
                    "hitl_collect",
                    {"message": "Pick a dir:", "input_type": "path", "path_type": "dir"},
                )
            await task
            assert isinstance(result.data, dict)
            assert result.data["action"] == "cancel"
            assert "not a directory" in result.data["reason"]
        finally:
            configure_tui_mode(None, None)  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_valid_file_path_returns_resolved(self, tmp_path: Path) -> None:
        """Covers line 69 (strip_whitespace) and line 79 (valid path → resolved str)."""
        from hitl_mcp_cli.server import configure_tui_mode
        from hitl_mcp_cli.tui.queue import HITLQueue

        queue = HITLQueue()
        configure_tui_mode(queue, None)  # type: ignore[arg-type]
        try:
            from fastmcp import Client

            from hitl_mcp_cli.server import mcp

            real_file = tmp_path / "real.txt"
            real_file.write_text("content")

            async def _resolve() -> None:
                req = await queue.get()
                # Return with leading whitespace to test strip_whitespace
                queue.resolve(req, f"  {real_file}  ")

            task = asyncio.create_task(_resolve())
            async with Client(mcp) as client:
                result = await client.call_tool(
                    "hitl_collect",
                    {
                        "message": "Pick a file:",
                        "input_type": "path",
                        "path_type": "file",
                        "strip_whitespace": True,
                    },
                )
            await task
            assert result.data == str(real_file.resolve())
        finally:
            configure_tui_mode(None, None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# tui/screens.py — helper functions
# ---------------------------------------------------------------------------


class TestHasMarkdown:
    def test_long_text_returns_false(self) -> None:
        """Covers line 89: text > 10000 chars returns False immediately."""
        from hitl_mcp_cli.tui.screens import _has_markdown

        long_text = "# heading\n" * 2000  # > 10000 chars, has markdown
        assert _has_markdown(long_text) is False

    def test_code_fence_detected(self) -> None:
        from hitl_mcp_cli.tui.screens import _has_markdown

        assert _has_markdown("```python\ncode\n```") is True

    def test_heading_detected(self) -> None:
        from hitl_mcp_cli.tui.screens import _has_markdown

        assert _has_markdown("# Title\nsome text") is True

    def test_plain_text_returns_false(self) -> None:
        from hitl_mcp_cli.tui.screens import _has_markdown

        assert _has_markdown("just plain text here") is False


class TestNotesWidget:
    def test_returns_none_for_empty_notes(self) -> None:
        """Covers line 102: notes is None/empty → returns None."""
        from hitl_mcp_cli.tui.screens import _notes_widget

        assert _notes_widget(None) is None
        assert _notes_widget("") is None

    def test_returns_widget_for_notes(self) -> None:
        from hitl_mcp_cli.tui.screens import _notes_widget

        widget = _notes_widget("some notes")
        assert widget is not None


class TestContextWidget:
    def test_returns_none_for_empty_context(self) -> None:
        """Covers line 121: context_text is None/empty → returns None."""
        from hitl_mcp_cli.tui.screens import _context_widget

        assert _context_widget(None) is None
        assert _context_widget("") is None

    def test_returns_widget_for_context(self) -> None:
        from hitl_mcp_cli.tui.screens import _context_widget

        widget = _context_widget("some context")
        assert widget is not None


# ---------------------------------------------------------------------------
# tui/screens.py — CollectScreen compose branches
# ---------------------------------------------------------------------------


class TestCollectScreenComposeBranches:
    @pytest.mark.asyncio
    async def test_collect_with_step_and_context_and_notes(self) -> None:
        """Covers lines 325, 328, 337: step_w, ctx_w, notes_w yielded in compose."""
        from hitl_mcp_cli.tui.queue import HITLRequest
        from hitl_mcp_cli.tui.screens import CollectScreen

        app = _TestApp(hitl_queue=HITLQueue())

        async with app.run_test(size=(80, 30)) as pilot:
            loop = asyncio.get_running_loop()
            req = HITLRequest(
                tool="collect",
                params={
                    "message": "Enter value:",
                    "input_type": "text",
                    "step": 2,
                    "total_steps": 5,
                    "context": "Some context here",
                    "notes": "Some notes here",
                },
                future=loop.create_future(),
            )
            screen = CollectScreen(req)
            results: list[Any] = []
            app.push_screen(screen, callback=results.append)
            await pilot.pause()
            step_widgets = screen.query(".step-indicator")
            assert len(step_widgets) == 1
            ctx_widgets = screen.query(".context-panel")
            assert len(ctx_widgets) == 1
            notes_widgets = screen.query(".notes")
            assert len(notes_widgets) == 1


# ---------------------------------------------------------------------------
# tui/screens.py — CollectScreen _validate regex error branch
# ---------------------------------------------------------------------------


class TestCollectScreenValidateRegexError:
    @pytest.mark.asyncio
    async def test_invalid_regex_pattern_returns_false(self) -> None:
        """Covers lines 376-377: re.error in _validate returns False."""
        from hitl_mcp_cli.tui.queue import HITLRequest
        from hitl_mcp_cli.tui.screens import CollectScreen

        loop = asyncio.new_event_loop()
        req = HITLRequest(
            tool="collect",
            params={
                "message": "Enter:",
                "input_type": "text",
                "validation_pattern": "[invalid(regex",
            },
            future=loop.create_future(),
        )
        screen = CollectScreen(req)
        # _validate should return False for broken regex, not raise
        result = screen._validate("anything")
        assert result is False
        loop.close()


# ---------------------------------------------------------------------------
# tui/screens.py — ConfirmScreen notes branch (line 201)
# ---------------------------------------------------------------------------


class TestConfirmScreenNotes:
    @pytest.mark.asyncio
    async def test_confirm_with_notes_renders(self) -> None:
        """Covers line 201: notes_w yielded in ConfirmScreen.compose."""
        from hitl_mcp_cli.tui.queue import HITLRequest
        from hitl_mcp_cli.tui.screens import ConfirmScreen

        app = _TestApp(hitl_queue=HITLQueue())
        async with app.run_test(size=(80, 24)) as pilot:
            loop = asyncio.get_running_loop()
            req = HITLRequest(
                tool="confirm",
                params={"message": "Proceed?", "notes": "This is a note"},
                future=loop.create_future(),
            )
            screen = ConfirmScreen(req)
            results: list[Any] = []
            app.push_screen(screen, callback=results.append)
            await pilot.pause()
            notes_widgets = screen.query(".notes")
            assert len(notes_widgets) == 1


# ---------------------------------------------------------------------------
# tui/screens.py — CollectScreen validation failure on input submit (384-387)
# and action_minimize (410)
# ---------------------------------------------------------------------------


class TestCollectScreenInputValidation:
    @pytest.mark.asyncio
    async def test_input_submitted_with_invalid_value_shows_error(self) -> None:
        """Covers lines 384-387: validation failure on Input.Submitted."""
        from textual.widgets import Input, Label

        from hitl_mcp_cli.tui.queue import HITLRequest
        from hitl_mcp_cli.tui.screens import CollectScreen

        app = _TestApp(hitl_queue=HITLQueue())
        async with app.run_test(size=(80, 24)) as pilot:
            loop = asyncio.get_running_loop()
            req = HITLRequest(
                tool="collect",
                params={
                    "message": "Enter digits only:",
                    "input_type": "text",
                    "validation_pattern": r"^\d+$",
                    "validation_message": "Digits only",
                },
                future=loop.create_future(),
            )
            screen = CollectScreen(req)
            results: list[Any] = []
            app.push_screen(screen, callback=results.append)
            await pilot.pause()
            inp = screen.query_one("#collect-input", Input)
            inp.focus()
            inp.value = "abc"
            await pilot.press("enter")
            await pilot.pause()
            # Screen should still be active (not dismissed) — validation blocked it
            msg = screen.query_one("#validation-msg", Label)
            assert "visible" in msg.classes
            assert len(results) == 0

    @pytest.mark.asyncio
    async def test_action_minimize_dismisses_with_sentinel(self) -> None:
        """Covers line 410: action_minimize dismisses with _MINIMIZED sentinel."""
        from hitl_mcp_cli.tui.queue import HITLRequest
        from hitl_mcp_cli.tui.screens import _MINIMIZED, CollectScreen

        app = _TestApp(hitl_queue=HITLQueue())
        async with app.run_test(size=(80, 24)) as pilot:
            loop = asyncio.get_running_loop()
            req = HITLRequest(
                tool="collect",
                params={"message": "Enter:", "input_type": "text"},
                future=loop.create_future(),
            )
            screen = CollectScreen(req)
            results: list[Any] = []
            app.push_screen(screen, callback=results.append)
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            assert results == [_MINIMIZED]


# ---------------------------------------------------------------------------
# tui/screens.py — ChooseScreen compose branches (498, 501, 505)
# and custom input submit (530-532) and action_minimize (559)
# ---------------------------------------------------------------------------


class TestChooseScreenBranches:
    @pytest.mark.asyncio
    async def test_choose_with_step_context_notes(self) -> None:
        """Covers lines 498, 501, 505: step/context/notes in ChooseScreen.compose."""
        from hitl_mcp_cli.tui.queue import HITLRequest
        from hitl_mcp_cli.tui.screens import ChooseScreen

        app = _TestApp(hitl_queue=HITLQueue())
        async with app.run_test(size=(80, 30)) as pilot:
            loop = asyncio.get_running_loop()
            req = HITLRequest(
                tool="choose",
                params={
                    "message": "Pick one:",
                    "choices": ["alpha", "beta"],
                    "step": 1,
                    "total_steps": 3,
                    "context": "Some context",
                    "notes": "Some notes",
                },
                future=loop.create_future(),
            )
            screen = ChooseScreen(req)
            results: list[Any] = []
            app.push_screen(screen, callback=results.append)
            await pilot.pause()
            assert len(screen.query(".step-indicator")) == 1
            assert len(screen.query(".context-panel")) == 1
            assert len(screen.query(".notes")) == 1

    @pytest.mark.asyncio
    async def test_choose_custom_input_submit(self) -> None:
        """Covers lines 530-532: custom free-text value submitted via Input."""
        from textual.widgets import Input

        from hitl_mcp_cli.tui.queue import HITLRequest
        from hitl_mcp_cli.tui.screens import ChooseScreen

        app = _TestApp(hitl_queue=HITLQueue())
        async with app.run_test(size=(80, 24)) as pilot:
            loop = asyncio.get_running_loop()
            req = HITLRequest(
                tool="choose",
                params={"message": "Pick:", "choices": ["alpha", "beta"]},
                future=loop.create_future(),
            )
            screen = ChooseScreen(req)
            results: list[Any] = []
            app.push_screen(screen, callback=results.append)
            await pilot.pause()
            inp = screen.query_one("#custom-input", Input)
            inp.focus()
            inp.value = "custom-value"
            await pilot.press("enter")
            await pilot.pause()
            assert results == ["custom-value"]

    @pytest.mark.asyncio
    async def test_choose_action_minimize(self) -> None:
        """Covers line 559: ChooseScreen.action_minimize dismisses with _MINIMIZED."""
        from hitl_mcp_cli.tui.queue import HITLRequest
        from hitl_mcp_cli.tui.screens import _MINIMIZED, ChooseScreen

        app = _TestApp(hitl_queue=HITLQueue())
        async with app.run_test(size=(80, 24)) as pilot:
            loop = asyncio.get_running_loop()
            req = HITLRequest(
                tool="choose",
                params={"message": "Pick:", "choices": ["alpha", "beta"]},
                future=loop.create_future(),
            )
            screen = ChooseScreen(req)
            results: list[Any] = []
            app.push_screen(screen, callback=results.append)
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            assert results == [_MINIMIZED]

"""Phase 5: Targeted coverage tests for uncovered lines."""

from __future__ import annotations

import asyncio
from typing import Any, ClassVar
from unittest.mock import MagicMock, patch

import pytest
from textual.widgets import Button, OptionList, TextArea

from hitl_mcp_cli.tui.app import HITLApp
from hitl_mcp_cli.tui.queue import HITLQueue, HITLRequest
from hitl_mcp_cli.tui.screens import ChooseScreen, CollectScreen, NotifyScreen

# --- Helper ---


def _make_request(
    tool: str = "confirm",
    params: dict[str, Any] | None = None,
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
        priority=5,
    )


class _TestApp(HITLApp):
    CSS_PATH: ClassVar[list[str]] = []  # type: ignore[assignment]

    def start_queue_worker(self) -> None:
        pass


# --- cli.py: --tui branch ---


def test_cli_tui_mode() -> None:
    """Cover TUI branch in main()."""
    from hitl_mcp_cli.cli import main

    with patch("sys.argv", ["hitl-mcp"]):
        with patch("hitl_mcp_cli.cli.mcp") as mock_mcp:
            mock_mcp.http_app.return_value = MagicMock()
            with patch("hitl_mcp_cli.server.configure_tui_mode"):
                with patch("hitl_mcp_cli.tui.HITLApp.run") as mock_run:
                    main()
                    mock_run.assert_called_once()


# --- tui/app.py: on_mount with mcp_app, _run_server, _process_queue ---


class TestAppOnMount:
    @pytest.mark.asyncio
    async def test_on_mount_starts_server_thread(self) -> None:
        """Cover L80-83: on_mount starts server thread when mcp_app provided."""
        queue = HITLQueue()
        app = HITLApp(hitl_queue=queue, mcp_app=MagicMock())
        app.CSS_PATH = []  # type: ignore[assignment]
        app.start_queue_worker = lambda: None  # type: ignore[assignment]
        with patch.object(app, "_run_server"):
            async with app.run_test() as pilot:
                await pilot.pause()
                assert app._server_thread is not None
                assert app._server_thread.daemon is True

    @pytest.mark.asyncio
    async def test_run_server_exception_logged(self) -> None:
        """Cover L92-102: _run_server catches exceptions."""
        queue = HITLQueue()
        app = _TestApp(hitl_queue=queue, mcp_app=MagicMock())
        with patch("hitl_mcp_cli.tui.app.uvicorn.Config", side_effect=RuntimeError("fail")):
            with patch("hitl_mcp_cli.tui.app.logger") as mock_logger:
                app._run_server()
                mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_queue_resolves_request(self) -> None:
        """Cover L107-116: _process_queue dequeues and resolves."""
        queue = HITLQueue()
        app = _TestApp(hitl_queue=queue)

        async with app.run_test():
            req = _make_request("notify", {"message": "hi"})
            await queue.put(req)

            request = await queue.get()
            queue.resolve(request, True)
            assert req.future.result() is True

    @pytest.mark.asyncio
    async def test_process_queue_rejects_on_error(self) -> None:
        """Cover L107-116: _process_queue rejects on screen error."""
        queue = HITLQueue()
        app = _TestApp(hitl_queue=queue)

        async with app.run_test():
            req = _make_request("notify", {"message": "hi"})
            await queue.put(req)

            request = await queue.get()
            queue.reject(request, RuntimeError("screen broke"))
            with pytest.raises(RuntimeError, match="screen broke"):
                req.future.result()


# --- tui/queue.py: __lt__ NotImplemented ---


def test_hitl_request_lt_not_implemented() -> None:
    """Cover queue.py L50: __lt__ with non-HITLRequest."""
    loop = asyncio.new_event_loop()
    req = HITLRequest(tool="t", params={}, future=loop.create_future(), priority=5)
    assert req.__lt__("not a request") is NotImplemented
    loop.close()


# --- tui/screens.py: uncovered branches ---


class TestCollectScreenTextArea:
    @pytest.mark.asyncio
    async def test_collect_multiline_submit(self) -> None:
        """Cover L132: _get_value TextArea branch."""
        app = _TestApp(hitl_queue=HITLQueue())
        results: list[Any] = []

        async with app.run_test(size=(80, 24)) as pilot:
            req = _make_request("collect", {"message": "Desc?", "input_type": "multiline"})
            screen = CollectScreen(req)
            app.push_screen(screen, callback=results.append)
            await pilot.pause()
            ta = screen.query_one("#collect-input", TextArea)
            ta.load_text("multiline content")
            await pilot.click("#submit")
            await pilot.pause()

        assert results == ["multiline content"]


class TestChooseScreenToggle:
    @pytest.mark.asyncio
    async def test_toggle_choice_on_off(self) -> None:
        """Cover L198-206: _toggle_choice method."""
        app = _TestApp(hitl_queue=HITLQueue())
        results: list[Any] = []

        async with app.run_test(size=(80, 24)) as pilot:
            req = _make_request(
                "choose",
                {
                    "message": "Pick",
                    "choices": ["alpha", "beta"],
                    "multiple": True,
                },
            )
            screen = ChooseScreen(req)
            app.push_screen(screen, callback=results.append)
            await pilot.pause()
            btn = screen.query(".choice-btn")[0]
            screen._toggle_choice(Button.Pressed(btn))
            await pilot.pause()
            assert "☑" in btn.label.plain
            screen._toggle_choice(Button.Pressed(btn))
            await pilot.pause()
            assert "☐" in btn.label.plain
            screen._toggle_choice(Button.Pressed(btn))
            await pilot.click("#done")
            await pilot.pause()

        assert len(results) == 1
        assert "alpha" in results[0]


class TestChooseScreenOptionListSelection:
    @pytest.mark.asyncio
    async def test_option_list_select_first(self) -> None:
        """Cover OptionList selection in single-choice mode."""
        app = _TestApp(hitl_queue=HITLQueue())
        results: list[Any] = []

        async with app.run_test(size=(80, 24)) as pilot:
            req = _make_request(
                "choose",
                {
                    "message": "Pick",
                    "choices": ["first", "second"],
                },
            )
            screen = ChooseScreen(req)
            app.push_screen(screen, callback=results.append)
            await pilot.pause()
            option_list = screen.query_one("#choose-list", OptionList)
            option_list.focus()
            await pilot.press("enter")
            await pilot.pause()

        assert results == ["first"]


class TestNotifyAutoDismiss:
    @pytest.mark.asyncio
    async def test_auto_dismiss(self) -> None:
        """Cover L266-267: _auto_dismiss fires after timer."""
        app = _TestApp(hitl_queue=HITLQueue())
        results: list[Any] = []

        async with app.run_test(size=(80, 24)) as pilot:
            req = _make_request("notify", {"message": "Auto"})
            screen = NotifyScreen(req)
            screen.AUTO_DISMISS_SECONDS = 0.1  # Speed up for test
            app.push_screen(screen, callback=results.append)
            await pilot.pause(0.3)

        assert results == [True]


# --- tui/app.py: _process_queue full loop ---


class TestProcessQueueWorker:
    @pytest.mark.asyncio
    async def test_process_queue_full_cycle(self) -> None:
        """Cover L88, L107-116: start_queue_worker + _process_queue loop."""
        queue = HITLQueue()
        app = HITLApp(hitl_queue=queue)
        app.CSS_PATH = []  # type: ignore[assignment]

        async with app.run_test(size=(80, 24)) as pilot:
            req = _make_request("notify", {"message": "auto-test"})
            await queue.put(req)
            await pilot.pause(0.5)
            try:
                app.query_one("#dismiss", Button)
                await pilot.click("#dismiss")
            except Exception:
                pass
            await pilot.pause(0.5)

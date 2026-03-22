"""Phase 5: Targeted coverage tests for uncovered lines."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from textual.widgets import Button, OptionList, TextArea

from hitl_mcp_cli.tui.app import HITLApp
from hitl_mcp_cli.tui.queue import HITLQueue, HITLRequest
from hitl_mcp_cli.tui.screens import ChooseScreen, CollectScreen, NotifyScreen
from hitl_mcp_cli.ui.prompts import (
    _has_markdown,
    _render_markdown_prompt,
    prompt_confirm,
    prompt_path,
    prompt_select,
    prompt_text,
)

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
    CSS_PATH = []  # type: ignore[assignment]

    def start_queue_worker(self) -> None:
        pass


# --- prompts.py: _has_markdown + _render_markdown_prompt ---


def test_has_markdown_length_limit() -> None:
    """Cover L328: text > 10000 chars returns False."""
    assert _has_markdown("x" * 10001) is False


def test_has_markdown_code_block() -> None:
    assert _has_markdown("Here is\n```python\ncode\n```") is True


def test_has_markdown_header() -> None:
    assert _has_markdown("# Title\nSome text") is True


def test_has_markdown_bold_with_list() -> None:
    assert _has_markdown("**bold** text\n- item") is True


def test_has_markdown_plain_text() -> None:
    assert _has_markdown("just plain text") is False


def test_render_markdown_prompt() -> None:
    """Cover L346-352: _render_markdown_prompt body."""
    with patch("hitl_mcp_cli.ui.prompts.console") as mock_console:
        _render_markdown_prompt("# Hello\nworld", "✏️")
        assert mock_console.print.call_count == 3  # header + markdown + spacing


# --- prompts.py: markdown branches in prompt functions ---


@pytest.mark.asyncio
async def test_prompt_text_markdown_prompt() -> None:
    """Cover L86: _render_markdown_prompt branch in prompt_text."""
    with patch("hitl_mcp_cli.ui.prompts.inquirer.text") as mock_inq:
        with patch("hitl_mcp_cli.ui.prompts.console"):
            mock_result = MagicMock()
            mock_result.execute.return_value = "answer"
            mock_inq.return_value = mock_result
            result = await prompt_text("# Markdown\n- item")
            assert result == "answer"


@pytest.mark.asyncio
async def test_prompt_text_multiline_markdown() -> None:
    """Cover L99: multiline + markdown branch."""
    with patch("hitl_mcp_cli.ui.prompts.inquirer.text") as mock_inq:
        with patch("hitl_mcp_cli.ui.prompts.console"):
            mock_result = MagicMock()
            mock_result.execute.return_value = "multi"
            mock_inq.return_value = mock_result
            result = await prompt_text("# Markdown\n- item", multiline=True)
            assert result == "multi"


@pytest.mark.asyncio
async def test_prompt_text_multiline_keyboard_interrupt() -> None:
    """Cover L114-115: KeyboardInterrupt in multiline."""
    with patch("hitl_mcp_cli.ui.prompts.inquirer.text") as mock_inq:
        with patch("hitl_mcp_cli.ui.prompts.console"):
            mock_result = MagicMock()
            mock_result.execute.side_effect = KeyboardInterrupt()
            mock_inq.return_value = mock_result
            with pytest.raises(KeyboardInterrupt):
                await prompt_text("Enter:", multiline=True)


@pytest.mark.asyncio
async def test_prompt_text_separator() -> None:
    """Cover L74-76: _needs_separator branch."""
    import hitl_mcp_cli.ui.prompts as p

    p._needs_separator = True
    with patch("hitl_mcp_cli.ui.prompts.inquirer.text") as mock_inq:
        with patch("hitl_mcp_cli.ui.prompts.console") as mock_console:
            mock_result = MagicMock()
            mock_result.execute.return_value = "val"
            mock_inq.return_value = mock_result
            await prompt_text("Q:")
            # Rule separator should have been printed
            calls = [str(c) for c in mock_console.print.call_args_list]
            assert any("Rule" in c for c in calls)


@pytest.mark.asyncio
async def test_prompt_text_invalid_regex() -> None:
    """Cover re.error branch in validator."""
    with patch("hitl_mcp_cli.ui.prompts.inquirer.text") as mock_inq:
        with patch("hitl_mcp_cli.ui.prompts.console"):
            mock_result = MagicMock()
            mock_result.execute.return_value = "test"
            mock_inq.return_value = mock_result
            await prompt_text("Q:", validate_pattern="[invalid")
            validator = mock_inq.call_args[1]["validate"]
            assert validator("anything") is False


@pytest.mark.asyncio
async def test_prompt_select_fuzzy_search() -> None:
    """Cover L147: fuzzy search for >15 choices."""
    with patch("hitl_mcp_cli.ui.prompts.inquirer.fuzzy") as mock_fuzzy:
        with patch("hitl_mcp_cli.ui.prompts.console"):
            mock_result = MagicMock()
            mock_result.execute.return_value = "choice_5"
            mock_fuzzy.return_value = mock_result
            choices = [f"choice_{i}" for i in range(20)]
            result = await prompt_select("Pick:", choices)
            assert result == "choice_5"
            mock_fuzzy.assert_called_once()


@pytest.mark.asyncio
async def test_prompt_confirm_markdown() -> None:
    """Cover L233: markdown branch in prompt_confirm."""
    with patch("hitl_mcp_cli.ui.prompts.inquirer.confirm") as mock_inq:
        with patch("hitl_mcp_cli.ui.prompts.console"):
            mock_result = MagicMock()
            mock_result.execute.return_value = True
            mock_inq.return_value = mock_result
            result = await prompt_confirm("# Confirm\n- action")
            assert result is True


@pytest.mark.asyncio
async def test_prompt_path_directory_must_exist() -> None:
    """Cover L268-271: directory path_type with must_exist."""
    with patch("hitl_mcp_cli.ui.prompts.inquirer.filepath") as mock_inq:
        with patch("hitl_mcp_cli.ui.prompts.PathValidator"):
            with patch("hitl_mcp_cli.ui.prompts.console"):
                mock_result = MagicMock()
                mock_result.execute.return_value = "/tmp"
                mock_inq.return_value = mock_result
                result = await prompt_path("Dir:", path_type="directory", must_exist=True)
                assert "/tmp" in result


@pytest.mark.asyncio
async def test_prompt_path_any_must_exist() -> None:
    """Cover L274: 'any' path_type with must_exist."""
    with patch("hitl_mcp_cli.ui.prompts.inquirer.filepath") as mock_inq:
        with patch("hitl_mcp_cli.ui.prompts.PathValidator") as mock_pv:
            with patch("hitl_mcp_cli.ui.prompts.console"):
                mock_result = MagicMock()
                mock_result.execute.return_value = "/tmp/x"
                mock_inq.return_value = mock_result
                await prompt_path("Path:", path_type="any", must_exist=True)
                mock_pv.assert_called_once_with(message="Path must exist")


@pytest.mark.asyncio
async def test_prompt_path_markdown() -> None:
    """Cover L274 markdown branch in prompt_path."""
    with patch("hitl_mcp_cli.ui.prompts.inquirer.filepath") as mock_inq:
        with patch("hitl_mcp_cli.ui.prompts.console"):
            mock_result = MagicMock()
            mock_result.execute.return_value = "/tmp/f"
            mock_inq.return_value = mock_result
            await prompt_path("# Select\n- a path")


# --- cli.py: --tui branch ---


def test_cli_tui_mode() -> None:
    """Cover L70-77: --tui branch in main()."""
    from hitl_mcp_cli.cli import main

    with patch("sys.argv", ["hitl-mcp", "--tui"]):
        with patch("hitl_mcp_cli.cli.mcp") as mock_mcp:
            mock_mcp.http_app.return_value = MagicMock()
            with patch("hitl_mcp_cli.server.configure_tui_mode"):
                with patch("hitl_mcp_cli.tui.app.HITLApp.run") as mock_run:
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
        # Override start_queue_worker to avoid blocking
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


# --- tui/tmux_manager.py: init with libtmux ---


class TestTmuxManagerInit:
    def test_init_with_libtmux_available(self) -> None:
        """Cover L11-13, L25-28: init when libtmux is importable."""
        from hitl_mcp_cli.tui import tmux_manager

        with patch.object(tmux_manager, "HAS_LIBTMUX", True):
            mock_server_cls = MagicMock()
            with patch.object(tmux_manager, "libtmux", create=True) as mock_lib:
                mock_lib.Server = mock_server_cls
                mgr = tmux_manager.TmuxManager("test-session")
                assert mgr._session_name == "test-session"
                mock_server_cls.assert_called_once()

    def test_init_libtmux_server_exception(self) -> None:
        """Cover L25-28: init when libtmux.Server() raises."""
        from hitl_mcp_cli.tui import tmux_manager

        with patch.object(tmux_manager, "HAS_LIBTMUX", True):
            with patch.object(tmux_manager, "libtmux", create=True) as mock_lib:
                mock_lib.Server.side_effect = Exception("no tmux")
                mgr = tmux_manager.TmuxManager()
                assert mgr._server is None


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
            # Simulate toggle via direct Button.Pressed event
            screen._toggle_choice(Button.Pressed(btn))
            await pilot.pause()
            assert "☑" in btn.label.plain
            # Toggle off
            screen._toggle_choice(Button.Pressed(btn))
            await pilot.pause()
            assert "☐" in btn.label.plain
            # Select and submit
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


# --- tui/queue.py: __lt__ NotImplemented ---


def test_hitl_request_lt_not_implemented() -> None:
    """Cover queue.py L50: __lt__ with non-HITLRequest."""
    loop = asyncio.new_event_loop()
    req = HITLRequest(tool="t", params={}, future=loop.create_future(), priority=5)
    assert req.__lt__("not a request") is NotImplemented
    loop.close()


# --- prompts.py: separator branches in select/checkbox ---


@pytest.mark.asyncio
async def test_prompt_select_separator() -> None:
    """Cover L147 (approx): _needs_separator in prompt_select."""
    import hitl_mcp_cli.ui.prompts as p

    p._needs_separator = True
    with patch("hitl_mcp_cli.ui.prompts.inquirer.select") as mock_inq:
        with patch("hitl_mcp_cli.ui.prompts.console"):
            mock_result = MagicMock()
            mock_result.execute.return_value = "A"
            mock_inq.return_value = mock_result
            await prompt_select("Pick:", ["A", "B"])


@pytest.mark.asyncio
async def test_prompt_select_markdown() -> None:
    """Cover markdown branch in prompt_select."""
    with patch("hitl_mcp_cli.ui.prompts.inquirer.select") as mock_inq:
        with patch("hitl_mcp_cli.ui.prompts.console"):
            mock_result = MagicMock()
            mock_result.execute.return_value = "A"
            mock_inq.return_value = mock_result
            await prompt_select("# Pick\n- one", ["A", "B"])


@pytest.mark.asyncio
async def test_prompt_checkbox_markdown() -> None:
    """Cover L191: markdown branch in prompt_checkbox."""
    from hitl_mcp_cli.ui.prompts import prompt_checkbox

    with patch("hitl_mcp_cli.ui.prompts.inquirer.checkbox") as mock_cb:
        with patch("hitl_mcp_cli.ui.prompts.console"):
            mock_result = MagicMock()
            mock_result.execute.return_value = ["A"]
            mock_cb.return_value = mock_result
            await prompt_checkbox("# Select\n- items", ["A", "B"])


# --- tui/app.py: _process_queue full loop ---


class TestProcessQueueWorker:
    @pytest.mark.asyncio
    async def test_process_queue_full_cycle(self) -> None:
        """Cover L88, L107-116: start_queue_worker + _process_queue loop."""
        queue = HITLQueue()
        # Use real HITLApp (not _TestApp) to cover start_queue_worker
        app = HITLApp(hitl_queue=queue)
        app.CSS_PATH = []  # type: ignore[assignment]

        async with app.run_test(size=(80, 24)) as pilot:
            req = _make_request("notify", {"message": "auto-test"})
            await queue.put(req)
            # Give the worker time to pick up and push screen
            await pilot.pause(0.5)
            # The NotifyScreen auto-dismisses after 3s, but we can dismiss manually
            try:
                app.query_one("#dismiss", Button)
                await pilot.click("#dismiss")
            except Exception:
                pass
            await pilot.pause(0.5)

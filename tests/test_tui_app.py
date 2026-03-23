"""Tests for HITLApp and TUI screens using Textual's Pilot."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from textual.widgets import Button, Input, Label, OptionList, RichLog, TextArea

from hitl_mcp_cli.tui.app import HITLApp
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

    CSS_PATH = []  # type: ignore[assignment]  # Override to avoid CSS file resolution in tests

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

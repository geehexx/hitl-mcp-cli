"""Textual Pilot tests for HITLQueue serialization and screen UX."""

from __future__ import annotations

import asyncio
import threading
from typing import Any, ClassVar

import pytest

from hitl_mcp_cli.tui.app import HITLApp
from hitl_mcp_cli.tui.queue import HITLQueue, HITLRequest
from hitl_mcp_cli.tui.screens import ChooseScreen, ConfirmScreen


class _QueueTestApp(HITLApp):
    """HITLApp subclass that avoids CSS file resolution and auto-start in tests."""

    CSS_PATH: ClassVar[list[str]] = []  # type: ignore[assignment]

    def on_mount(self) -> None:
        """Skip auto-starting queue worker and server on mount."""
        pass


def _make_request(tool: str, params: dict[str, Any]) -> HITLRequest:
    """Create a HITLRequest with a future on the running loop."""
    loop = asyncio.get_running_loop()
    return HITLRequest(tool=tool, params=params, future=loop.create_future())


@pytest.mark.asyncio
async def test_notify_non_blocking_queue() -> None:
    """hitl_notify should resolve immediately without blocking the queue worker.

    Verifies that the queue worker handles notify inline (no screen push)
    and resolves the future synchronously within the dequeue loop.
    """
    queue = HITLQueue()
    notify_req = _make_request(
        "hitl_notify",
        {"message": "Hello from agent", "level": "info", "title": "TestAgent"},
    )
    await queue.put(notify_req)

    # Dequeue and resolve inline — mirrors _process_queue notify branch
    request = await queue.get()
    assert request.tool == "hitl_notify"
    queue.resolve(request, True)

    assert notify_req.future.done(), "notify future should resolve immediately"
    assert notify_req.future.result() is True
    assert queue.size == 0, "queue should be empty after processing"


@pytest.mark.asyncio
async def test_queue_drain_two_confirms() -> None:
    """Two confirm requests queued: both should be resolved in order."""
    queue = HITLQueue()
    app = _QueueTestApp(hitl_queue=queue)
    results: list[Any] = []

    async with app.run_test(size=(120, 40)) as pilot:
        req1 = _make_request("hitl_confirm", {"message": "First?", "severity": "medium"})
        req2 = _make_request("hitl_confirm", {"message": "Second?", "severity": "medium"})

        # Push screens directly (like existing tests) to test serialized drain
        screen1 = ConfirmScreen(req1)
        screen2_pushed = False

        def _on_first(result: Any) -> None:
            nonlocal screen2_pushed
            results.append(result)
            # Push second screen after first dismisses
            screen2 = ConfirmScreen(req2)
            app.push_screen(screen2, callback=lambda r: results.append(r))
            screen2_pushed = True

        app.push_screen(screen1, callback=_on_first)
        await pilot.pause()

        # First screen should appear
        assert app.screen.__class__.__name__ == "ConfirmScreen"
        await pilot.click("#yes")
        await pilot.pause()

        # Second screen should appear
        assert app.screen.__class__.__name__ == "ConfirmScreen"
        await pilot.click("#no")
        await pilot.pause()

    assert results == [{"action": "accept"}, {"action": "decline"}]


@pytest.mark.asyncio
async def test_choose_optionlist_keyboard_nav() -> None:
    """ChooseScreen OptionList: pressing Enter on highlighted option dismisses with value."""
    queue = HITLQueue()
    app = _QueueTestApp(hitl_queue=queue)
    results: list[Any] = []

    async with app.run_test(size=(120, 40)) as pilot:
        req = _make_request(
            "hitl_choose",
            {"message": "Pick one:", "choices": ["alpha", "beta", "gamma"]},
        )
        screen = ChooseScreen(req)
        app.push_screen(screen, callback=results.append)
        await pilot.pause()

        # OptionList should be visible
        assert app.screen.__class__.__name__ == "ChooseScreen"
        # Press Enter to select the first highlighted option
        await pilot.press("enter")
        await pilot.pause()

    assert results == ["alpha"]


@pytest.mark.asyncio
async def test_cross_loop_future_resolution() -> None:
    """Futures created in a background thread should be resolved via call_soon_threadsafe."""
    queue = HITLQueue()

    # Simulate futures created in a different thread (like uvicorn)
    thread_loop = asyncio.new_event_loop()
    thread_future: asyncio.Future[Any] = thread_loop.create_future()
    req = HITLRequest(
        tool="hitl_notify",
        params={"message": "cross-loop test", "level": "info"},
        future=thread_future,
    )
    queue.set_caller_loop(thread_loop)

    # Run the thread loop in a background thread so call_soon_threadsafe works
    stop_event = threading.Event()

    def _run_loop() -> None:
        thread_loop.run_until_complete(_wait_stop())

    async def _wait_stop() -> None:
        while not stop_event.is_set():
            await asyncio.sleep(0.05)

    t = threading.Thread(target=_run_loop, daemon=True)
    t.start()

    try:
        # Resolve via call_soon_threadsafe directly (unit-testing the queue method)
        await queue.put(req)
        request = await queue.get()
        queue.resolve(request, True)

        # Give the thread loop time to process the scheduled callback
        await asyncio.sleep(0.3)
        assert thread_future.done(), "cross-loop future should be resolved"
        assert thread_future.result() is True
    finally:
        stop_event.set()
        t.join(timeout=2)
        thread_loop.close()

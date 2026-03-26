"""Snapshot tests for hitl-mcp-cli TUI using pytest-textual-snapshot.

Run with --snapshot-update to create/update baselines.
Subsequent runs compare against stored SVG baselines.

Uses run_before callbacks to push screens before snapshotting.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from hitl_mcp_cli.tui.queue import HITLRequest
from hitl_mcp_cli.tui.screens import ChooseScreen, CollectScreen, ConfirmScreen, NotifyScreen

_SNAP_APP_PATH = Path(__file__).parent / "snap_app.py"


def _req(tool: str = "hitl_confirm", params: dict[str, Any] | None = None) -> HITLRequest:
    loop = asyncio.get_event_loop()
    return HITLRequest(tool=tool, params=params or {}, future=loop.create_future())


def test_confirm_screen_medium(snap_compare: Any) -> None:
    """Snapshot: ConfirmScreen with medium severity."""

    async def setup(pilot: Any) -> None:
        req = _req("hitl_confirm", {"message": "Are you sure you want to proceed?", "severity": "medium"})
        pilot.app.push_screen(ConfirmScreen(req))
        await pilot.pause()

    assert snap_compare(_SNAP_APP_PATH, run_before=setup, terminal_size=(120, 40))


def test_confirm_screen_high(snap_compare: Any) -> None:
    """Snapshot: ConfirmScreen with high severity (red border)."""

    async def setup(pilot: Any) -> None:
        req = _req("hitl_confirm", {"message": "This action is irreversible!", "severity": "high"})
        pilot.app.push_screen(ConfirmScreen(req))
        await pilot.pause()

    assert snap_compare(_SNAP_APP_PATH, run_before=setup, terminal_size=(120, 40))


def test_collect_screen_text(snap_compare: Any) -> None:
    """Snapshot: CollectScreen with text input."""

    async def setup(pilot: Any) -> None:
        req = _req("hitl_collect", {"message": "Enter your name:", "input_type": "text"})
        pilot.app.push_screen(CollectScreen(req))
        await pilot.pause()

    assert snap_compare(_SNAP_APP_PATH, run_before=setup, terminal_size=(120, 40))


def test_choose_screen_single(snap_compare: Any) -> None:
    """Snapshot: ChooseScreen with single selection."""

    async def setup(pilot: Any) -> None:
        req = _req(
            "hitl_choose",
            {"message": "Select an option:", "choices": ["Option A", "Option B", "Option C"]},
        )
        pilot.app.push_screen(ChooseScreen(req))
        await pilot.pause()

    assert snap_compare(_SNAP_APP_PATH, run_before=setup, terminal_size=(120, 40))


def test_notify_screen_success(snap_compare: Any) -> None:
    """Snapshot: NotifyScreen with success level."""

    async def setup(pilot: Any) -> None:
        req = _req("hitl_notify", {"message": "Operation completed successfully!", "level": "success"})
        pilot.app.push_screen(NotifyScreen(req))
        await pilot.pause()

    assert snap_compare(_SNAP_APP_PATH, run_before=setup, terminal_size=(120, 40))


def test_long_message_collapsible(snap_compare: Any) -> None:
    """Snapshot: ConfirmScreen with long message showing Collapsible widget."""

    async def setup(pilot: Any) -> None:
        long_msg = (
            "This is a very long message that exceeds the 200 character threshold and should therefore "
            "be rendered inside a Collapsible widget to keep the UI clean and readable. "
            "The user can expand it to see the full content."
        )
        req = _req("hitl_confirm", {"message": long_msg, "severity": "medium"})
        pilot.app.push_screen(ConfirmScreen(req))
        await pilot.pause()

    assert snap_compare(_SNAP_APP_PATH, run_before=setup, terminal_size=(120, 40))


def test_confirm_screen_with_step(snap_compare: Any) -> None:
    """Snapshot: ConfirmScreen with step indicator."""

    async def setup(pilot: Any) -> None:
        req = _req(
            "hitl_confirm",
            {"message": "Step confirmation", "severity": "medium", "step": 2, "total_steps": 5},
        )
        pilot.app.push_screen(ConfirmScreen(req))
        await pilot.pause()

    assert snap_compare(_SNAP_APP_PATH, run_before=setup, terminal_size=(120, 40))

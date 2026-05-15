"""Standalone app for snapshot testing.

This module defines an `app` variable that pytest-textual-snapshot
imports via import_app() when snap_compare() is called with a path.

The clock is disabled to ensure deterministic SVG output.
"""

from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Label, RichLog

from hitl_mcp_cli.tui.app import HITLApp
from hitl_mcp_cli.tui.queue import HITLQueue


class _SnapApp(HITLApp):
    """Minimal HITLApp for snapshot testing — no clock, no server, no queue worker."""

    CSS_PATH: ClassVar[list[str]] = []  # type: ignore[assignment]

    def __init__(self) -> None:
        super().__init__(hitl_queue=HITLQueue(), host="127.0.0.1", port=15555, mcp_app=None)

    def compose(self) -> ComposeResult:
        # Override to use Header without clock for deterministic snapshots
        yield Header(show_clock=False)
        with Horizontal(id="main-pane"):
            with Vertical(id="sessions-pane"):
                yield Label("Sessions", classes="pane-title")
                yield DataTable(id="sessions-table", show_cursor=True, zebra_stripes=True)
                yield Label(
                    "No active sessions.",
                    id="sessions-placeholder",
                    classes="placeholder-text",
                )
            with Vertical(id="activity-pane"):
                yield Label("Activity", classes="pane-title")
                yield RichLog(id="output-log", highlight=True, auto_scroll=True, markup=True, wrap=True)
            with Vertical(id="queue-pane"):
                yield Label("Queue  [[+] Expand All]", id="queue-title", classes="pane-title")
                yield DataTable(id="queue-table", show_cursor=True, zebra_stripes=True, cursor_type="row")
        yield Label("[blue]INFO[/blue]  Sessions: 0  Queue: 0", id="status-bar")
        yield Footer()

    def start_queue_worker(self) -> None:
        pass


app = _SnapApp()

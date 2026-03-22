"""Textual App with split-pane layout for HITL interactions."""

from __future__ import annotations

import asyncio
import logging
import threading
from pathlib import Path
from typing import Any

import uvicorn
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Footer, Label, RichLog

from .queue import HITLQueue
from .screens import screen_for

logger = logging.getLogger(__name__)

_CSS_DIR = Path(__file__).parent


class HITLApp(App[None]):
    """Unified TUI for human-in-the-loop MCP interactions.

    Top 2/3: RichLog output pane (agent streaming via hitl_notify).
    Bottom 1/3: Queue status + active prompt area.
    """

    CSS_PATH = _CSS_DIR / "hitl.tcss"
    BINDINGS = [("q", "quit", "Quit")]

    def __init__(
        self,
        hitl_queue: HITLQueue,
        host: str = "127.0.0.1",
        port: int = 5555,
        mcp_app: Any | None = None,
    ) -> None:
        super().__init__()
        self._hitl_queue = hitl_queue
        self._host = host
        self._port = port
        self._mcp_app = mcp_app
        self._server_thread: threading.Thread | None = None

    def compose(self) -> ComposeResult:
        yield Vertical(
            RichLog(id="output-log", highlight=True, auto_scroll=True, markup=True),
            id="output-pane",
        )
        yield Vertical(
            Label("Queue: 0 pending", id="queue-status"),
            id="queue-pane",
        )
        yield Footer()

    def stream_output(self, agent: str, message: str, level: str = "info") -> None:
        """Append to RichLog. Call via call_from_thread from server thread."""
        from rich.markdown import Markdown as RichMarkdown

        from .screens import _expand_escapes, _has_markdown

        level_styles = {
            "success": "[green]",
            "error": "[red]",
            "warning": "[yellow]",
            "info": "[blue]",
        }
        prefix = level_styles.get(level, "[blue]")
        log = self.query_one("#output-log", RichLog)
        message = _expand_escapes(message)
        log.write(f"{prefix}{agent}:[/]")
        if _has_markdown(message):
            log.write(RichMarkdown(message))
        else:
            log.write(message)

    def update_queue_status(self) -> None:
        """Refresh the queue status label."""
        count = self._hitl_queue.size
        label = self.query_one("#queue-status", Label)
        label.update(f"Queue: {count} pending")

    async def on_mount(self) -> None:
        """Start background uvicorn thread + queue worker."""
        if self._mcp_app is not None:
            self._server_thread = threading.Thread(
                target=self._run_server, daemon=True, name="fastmcp-server"
            )
            self._server_thread.start()
        self.start_queue_worker()

    def start_queue_worker(self) -> None:
        """Start the queue processing worker. Separate method for testability."""
        self._process_queue()

    def _run_server(self) -> None:
        """Run FastMCP HTTP server in background thread."""
        try:
            assert self._mcp_app is not None
            config = uvicorn.Config(
                self._mcp_app,
                host=self._host,
                port=self._port,
                log_level="warning",
            )
            server = uvicorn.Server(config)
            server.run()
        except Exception as e:
            logger.error(f"Server thread error: {e}", exc_info=True)

    @work(exclusive=True)
    async def _process_queue(self) -> None:
        """Background worker: dequeue HITLRequests and push screens."""
        try:
            while True:
                request = await self._hitl_queue.get()
                self.update_queue_status()
                try:
                    result = await self.push_screen_wait(screen_for(request))
                    self._hitl_queue.resolve(request, result)
                except Exception as e:
                    logger.error(f"Screen error for {request.tool}: {e}", exc_info=True)
                    self._hitl_queue.reject(request, e)
                self.update_queue_status()
        except asyncio.CancelledError:
            while not self._hitl_queue._queue.empty():
                try:
                    _, _, req = self._hitl_queue._queue.get_nowait()
                    if not req.future.done():
                        req.future.set_exception(RuntimeError("TUI exited"))
                except asyncio.QueueEmpty:
                    break
            raise

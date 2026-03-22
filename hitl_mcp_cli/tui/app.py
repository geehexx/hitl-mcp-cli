"""Textual App with three-pane layout for HITL interactions."""

from __future__ import annotations

import asyncio
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

import uvicorn
from rich.markup import escape
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import DataTable, Footer, Header, Label, RichLog

from .queue import HITLQueue
from .screens import _expand_escapes, _has_markdown, screen_for

logger = logging.getLogger(__name__)

_CSS_DIR = Path(__file__).parent

LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"]
LEVEL_STYLES = {"DEBUG": "dim", "INFO": "blue", "WARNING": "yellow", "ERROR": "red"}


class HITLApp(App[None]):
    """Three-pane TUI for HITL MCP interactions.

    Left: Sessions DataTable. Center: RichLog activity. Right: Queue DataTable.
    """

    CSS_PATH = _CSS_DIR / "hitl.tcss"
    TITLE = "HITL MCP"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("ctrl+l", "clear_log", "Clear log"),
        Binding("ctrl+b", "toggle_sessions", "Sessions"),
        Binding("f2", "cycle_log_level", "Log level"),
        Binding("f3", "toggle_sessions", "Sessions", show=False),  # VS Code-safe alternative
        Binding("ctrl+backslash", "command_palette", "Commands", show=True),
    ]

    # Reactive state
    min_level: reactive[str] = reactive("INFO")
    session_count: reactive[int] = reactive(0)
    queue_count: reactive[int] = reactive(0)
    sessions_visible: reactive[bool] = reactive(True)

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
        self._sessions: dict[str, dict[str, Any]] = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main-pane"):
            with Vertical(id="sessions-pane"):
                yield Label("Sessions", classes="pane-title")
                yield DataTable(id="sessions-table", show_cursor=True, zebra_stripes=True)
            with Vertical(id="activity-pane"):
                yield Label("Activity", classes="pane-title")
                yield RichLog(id="output-log", highlight=True, auto_scroll=True, markup=True)
            with Vertical(id="queue-pane"):
                yield Label("Queue", classes="pane-title")
                yield DataTable(id="queue-table", show_cursor=False, zebra_stripes=True)
        yield Label("[blue]INFO[/blue]  Sessions: 0  Queue: 0", id="status-bar")
        yield Footer()

    def _status_text(self) -> str:
        level = self.min_level
        style = LEVEL_STYLES.get(level, "blue")
        return f"[{style}]{level}[/{style}]  Sessions: {self.session_count}  Queue: {self.queue_count}"

    def on_mount(self) -> None:
        """Initialize tables, start server + queue worker."""
        st = self.query_one("#sessions-table", DataTable)
        st.add_columns("ID", "Project", "Calls", "Last seen")

        qt = self.query_one("#queue-table", DataTable)
        qt.add_columns("#", "Tool", "Message")

        log = self.query_one("#output-log", RichLog)
        log.write("[bold cyan]HITL MCP Server[/bold cyan] [dim]v0.8.0[/dim]")
        log.write(f"[dim]Listening on http://{self._host}:{self._port}[/dim]")
        log.write("[dim]Press [bold]ctrl+\\[/bold] for commands, [bold]q[/bold] to quit[/dim]")
        log.write("")

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

    # --- Reactive watchers ---

    def _update_status_bar(self) -> None:
        try:
            self.query_one("#status-bar", Label).update(self._status_text())
        except Exception:
            pass  # Not yet composed

    def watch_min_level(self, level: str) -> None:
        self._update_status_bar()

    def watch_session_count(self, count: int) -> None:
        self._update_status_bar()

    def watch_queue_count(self, count: int) -> None:
        self._update_status_bar()

    def watch_sessions_visible(self, visible: bool) -> None:
        try:
            self.query_one("#sessions-pane").display = visible
        except Exception:
            pass

    # --- Actions ---

    def action_clear_log(self) -> None:
        self.query_one("#output-log", RichLog).clear()

    def action_toggle_sessions(self) -> None:
        self.sessions_visible = not self.sessions_visible

    def action_cycle_log_level(self) -> None:
        idx = LOG_LEVELS.index(self.min_level)
        self.min_level = LOG_LEVELS[(idx + 1) % len(LOG_LEVELS)]
        self.notify(f"Log level: {self.min_level}", timeout=2)

    # --- Public API (called from server thread) ---

    def stream_output(self, agent: str, message: str, level: str = "info") -> None:
        """Append to RichLog. Call via call_from_thread from server thread."""
        from rich.markdown import Markdown as RichMarkdown

        level_order = {"debug": 0, "info": 1, "warning": 2, "error": 3, "success": 1}
        min_order = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3}.get(self.min_level, 1)
        if level_order.get(level.lower(), 1) < min_order:
            return

        level_styles = {"success": "green", "error": "red", "warning": "yellow", "info": "blue"}
        style = level_styles.get(level, "blue")
        log = self.query_one("#output-log", RichLog)
        message = _expand_escapes(message)
        log.write(f"[{style}]{agent}:[/{style}]")
        if _has_markdown(message):
            log.write(RichMarkdown(message))
        else:
            log.write(message)

    def record_session_activity(self, session_id: str, tool: str, project_id: str | None = None) -> None:
        """Record a tool call from a session. Call via call_from_thread."""
        short_id = session_id[:8] if len(session_id) > 8 else session_id
        now = datetime.now().strftime("%H:%M:%S")
        table = self.query_one("#sessions-table", DataTable)

        if session_id not in self._sessions:
            self._sessions[session_id] = {"project": project_id or "", "calls": 1, "last_seen": now}
            table.add_row(short_id, project_id or "", "1", now, key=session_id)
            self.session_count = len(self._sessions)
            self.stream_output(
                "server",
                f"New session: [bold]{short_id}[/bold]"
                + (f" project=[cyan]{escape(project_id)}[/cyan]" if project_id else ""),
                "info",
            )
        else:
            self._sessions[session_id]["calls"] += 1
            self._sessions[session_id]["last_seen"] = now
            calls = self._sessions[session_id]["calls"]
            try:
                table.update_cell(session_id, "Calls", str(calls))
                table.update_cell(session_id, "Last seen", now)
            except Exception:
                pass

    def add_queue_row(self, request_id: str, tool: str, message: str) -> None:
        """Add a row to the queue table. Call via call_from_thread."""
        table = self.query_one("#queue-table", DataTable)
        short_msg = message[:30] + "..." if len(message) > 30 else message
        row_count = table.row_count + 1
        table.add_row(str(row_count), tool, short_msg, key=request_id)
        self.queue_count = table.row_count

    def remove_queue_row(self, request_id: str) -> None:
        """Remove a row from the queue table. Call via call_from_thread."""
        table = self.query_one("#queue-table", DataTable)
        try:
            table.remove_row(request_id)
        except Exception:
            pass
        self.queue_count = table.row_count

    def update_queue_status(self) -> None:
        """Refresh queue count from actual queue size."""
        self.queue_count = self._hitl_queue.size

    @work(exclusive=True)
    async def _process_queue(self) -> None:
        """Background worker: dequeue HITLRequests and push screens."""
        try:
            while True:
                request = await self._hitl_queue.get()
                self.update_queue_status()
                try:
                    if request.tool in ("hitl_notify", "notify"):
                        params = request.params
                        agent = params.get("title") or "agent"
                        message = params.get("message", "")
                        level = params.get("level", "info")
                        self.stream_output(agent, message, level)
                        self._hitl_queue.resolve(request, True)
                    else:
                        msg = request.params.get("message", "")
                        self.add_queue_row(request.request_id, request.tool, msg)
                        result = await self.push_screen_wait(screen_for(request))
                        self.remove_queue_row(request.request_id)
                        self._hitl_queue.resolve(request, result)
                except Exception as e:
                    logger.error(f"Screen error for {request.tool}: {e}", exc_info=True)
                    self.remove_queue_row(request.request_id)
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

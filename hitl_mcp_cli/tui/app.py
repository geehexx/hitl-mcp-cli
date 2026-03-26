"""Textual App with three-pane layout for HITL interactions."""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar

import uvicorn
from rich.markup import escape
from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Label, RichLog

from .queue import HITLQueue
from .screens import _MINIMIZED, _expand_escapes, _has_markdown, screen_for

logger = logging.getLogger(__name__)

_CSS_DIR = Path(__file__).parent

LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"]
LEVEL_STYLES = {"DEBUG": "dim", "INFO": "blue", "WARNING": "yellow", "ERROR": "red"}

# Session recency thresholds (seconds)
_SESSION_ACTIVE_SECS = 600  # 10 min
_SESSION_IDLE_SECS = 3600  # 60 min


def _session_style(last_active_ts: float) -> str:
    """Return Rich style string based on session recency."""
    age = time.monotonic() - last_active_ts
    if age < _SESSION_ACTIVE_SECS:
        return "bold bright_white"
    if age < _SESSION_IDLE_SECS:
        return "white"
    return "dim"


def _queue_status_text(status: str) -> Text:
    """Return a Rich Text for queue row status."""
    if status == "pending":
        return Text("⏳ PENDING", style="bold yellow")
    if status == "answered":
        return Text("✓ DONE", style="bold green")
    if status == "cancelled":
        return Text("✗ CANCEL", style="dim")
    if status == "minimized":
        return Text("⏸ PAUSED", style="bold blue")
    return Text(status, style="dim")


class HITLApp(App[None]):
    """Three-pane TUI for HITL MCP interactions.

    Left: Sessions DataTable. Center: RichLog activity. Right: Queue DataTable.
    """

    CSS_PATH: ClassVar[list[Any]] = [_CSS_DIR / "hitl.tcss"]
    TITLE = "HITL MCP"
    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("q", "quit", "Quit"),
        Binding("ctrl+l", "clear_log", "Clear log"),
        Binding("ctrl+b", "toggle_sessions", "Sessions"),
        Binding("f2", "cycle_log_level", "Log level"),
        Binding("f3", "toggle_sessions", "Sessions", show=False),  # VS Code-safe alternative
        Binding("escape", "restore_prompt", "Restore prompt", show=False),
        Binding("ctrl+e", "toggle_expand_all", "Expand/Collapse All", show=True),
    ]

    # Reactive state
    min_level: reactive[str] = reactive("INFO")
    session_count: reactive[int] = reactive(0)
    queue_count: reactive[int] = reactive(0)
    sessions_visible: reactive[bool] = reactive(True)
    _queue_expanded: reactive[bool] = reactive(False)

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
        # FIX 2: Store minimized prompt screen so Escape can pop/restore it.
        self._pending_screen: Screen[Any] | None = None
        self._restore_event = asyncio.Event()
        # Map request_id → HITLRequest for queue row click handling
        self._queue_request_map: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main-pane"):
            with Vertical(id="sessions-pane"):
                yield Label("Sessions", classes="pane-title")
                yield DataTable(id="sessions-table", show_cursor=True, zebra_stripes=True)
                yield Label(
                    "No active sessions. Waiting for tool calls...",
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

    def _status_text(self) -> str:
        level = self.min_level
        style = LEVEL_STYLES.get(level, "blue")
        return f"[{style}]{level}[/{style}]  Sessions: {self.session_count}  Queue: {self.queue_count}"

    def on_mount(self) -> None:
        """Initialize tables, start server + queue worker."""
        # Register the Textual event loop so the queue can accept
        # cross-thread put_threadsafe() calls from the uvicorn thread.
        self._hitl_queue.set_textual_loop(asyncio.get_running_loop())

        st = self.query_one("#sessions-table", DataTable)
        st.add_columns("Client", "Project", "Calls", "Pending", "Last active")

        qt = self.query_one("#queue-table", DataTable)
        qt.add_columns(
            ("#", "num"),
            ("Tool", "tool"),
            ("Message", "msg"),
            ("Status", "status"),
            ("Answer", "answer"),
            ("Elapsed", "elapsed"),
        )

        log = self.query_one("#output-log", RichLog)
        log.write("[bold cyan]HITL MCP Server[/bold cyan] [dim]v0.9.0[/dim]")
        log.write(f"[dim]Listening on http://{self._host}:{self._port}[/dim]")
        log.write(
            "[dim]Press [bold]q[/bold] to quit, [bold]f2[/bold] log level, [bold]ctrl+l[/bold] clear, "
            "[bold]ctrl+e[/bold] expand/collapse queue[/dim]"
        )
        log.write("")

        if self._mcp_app is not None:
            self._server_thread = threading.Thread(
                target=self._run_server, daemon=True, name="fastmcp-server"
            )
            self._server_thread.start()

        self.start_queue_worker()
        # Update elapsed times every second
        self.set_interval(1.0, self._update_elapsed)

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

    def action_restore_prompt(self) -> None:
        """Signal the queue worker to re-push the minimized prompt screen."""
        if self._pending_screen is not None:
            self._pending_screen = None
            self._restore_event.set()

    def action_toggle_expand_all(self) -> None:
        """Toggle expand/collapse all queue rows."""
        self._queue_expanded = not self._queue_expanded
        label = "Queue  [[-] Collapse All]" if self._queue_expanded else "Queue  [[+] Expand All]"
        try:
            self.query_one("#queue-title", Label).update(label)
        except Exception:
            pass

    @on(DataTable.RowSelected, "#queue-table")
    def _on_queue_row_selected(self, event: DataTable.RowSelected) -> None:
        """Click a queue row to interact based on its status."""
        row_key = str(event.row_key.value) if event.row_key.value is not None else ""
        request = self._queue_request_map.get(row_key)
        if request is None:
            # Legacy: restore minimized if pending_screen set
            if self._pending_screen is not None:
                self._pending_screen = None
                self._restore_event.set()
            else:
                self.notify("No request found for this row", timeout=2)
            return

        status = request.status
        if status == "pending":
            # Push the corresponding screen
            if self._pending_screen is not None:
                self._pending_screen = None
                self._restore_event.set()
            else:
                self.notify("This prompt is already active", timeout=2)
        elif status == "minimized":
            # Restore it
            if self._pending_screen is not None:
                self._pending_screen = None
                self._restore_event.set()
            else:
                self.notify("Prompt is not currently minimized", timeout=2)
        elif status == "answered":
            # Show answer preview
            preview = request.answer_preview or "(no preview)"
            self.notify(f"Answer: {preview}", timeout=4)
        else:
            # cancelled — do nothing
            self.notify("This request was cancelled", timeout=2)

    # --- Elapsed time updater ---

    def _update_elapsed(self) -> None:
        """Update elapsed time column for all queue rows."""
        qt = self.query_one("#queue-table", DataTable)
        now = time.monotonic()
        for request_id, request in self._queue_request_map.items():
            elapsed = int(now - request.created_at)
            elapsed_text = Text(f"{elapsed}s", style="dim", justify="right")
            try:
                qt.update_cell(request_id, "elapsed", elapsed_text, update_width=False)
            except Exception:
                pass

    # --- Sessions table rebuild ---

    def _rebuild_sessions_table(self) -> None:
        """Rebuild sessions table sorted by last_active descending."""
        table = self.query_one("#sessions-table", DataTable)
        table.clear()
        sorted_sessions = sorted(
            self._sessions.items(),
            key=lambda kv: kv[1].get("last_active_ts", 0.0),
            reverse=True,
        )
        for session_id, s in sorted_sessions:
            style = _session_style(s.get("last_active_ts", 0.0))
            client = s.get("client_name", "unknown")
            project = s.get("project_id", "")
            calls = str(s["calls"])
            pending = str(s["pending"])
            last = s["last_active"]
            table.add_row(
                Text(client, style=style),
                Text(project or "", style=style),
                Text(calls, style=style),
                Text(pending, style=style),
                Text(last, style=style),
                key=session_id,
            )

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

    def record_session_activity(
        self, session_id: str, tool: str, project_id: str | None = None, client_name: str | None = None
    ) -> None:
        """Record a tool call from a session. Call via call_from_thread."""
        now = datetime.now().strftime("%H:%M:%S")
        now_ts = time.monotonic()
        display_name = client_name or "unknown"

        # Hide placeholder on first real session
        try:
            self.query_one("#sessions-placeholder").display = False
        except Exception:
            pass

        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "calls": 1,
                "pending": 1,
                "completed": 0,
                "last_active": now,
                "last_active_ts": now_ts,
                "client_name": display_name,
                "project_id": project_id or "",
            }
            self.session_count = len(self._sessions)
            self.stream_output(
                "server",
                f"New session: [bold cyan]{escape(display_name)}[/bold cyan]"
                + (f" project=[cyan]{escape(project_id)}[/cyan]" if project_id else ""),
                "info",
            )
        else:
            s = self._sessions[session_id]
            s["calls"] += 1
            s["pending"] += 1
            s["last_active"] = now
            s["last_active_ts"] = now_ts
            if project_id:
                s["project_id"] = project_id
            if client_name:
                s["client_name"] = display_name

        self._rebuild_sessions_table()

    def record_session_resolved(self, session_id: str) -> None:
        """Record that a request from this session was resolved."""
        if session_id not in self._sessions:
            return
        s = self._sessions[session_id]
        s["pending"] = max(0, s["pending"] - 1)
        s["completed"] += 1
        s["last_active"] = datetime.now().strftime("%H:%M:%S")
        s["last_active_ts"] = time.monotonic()
        self._rebuild_sessions_table()

    def add_queue_row(self, request_id: str, tool: str, message: str, request: Any = None) -> None:
        """Add a row to the queue table. Call via call_from_thread."""
        table = self.query_one("#queue-table", DataTable)
        short_msg = message[:30] + "..." if len(message) > 30 else message
        row_count = table.row_count + 1
        elapsed_text = Text("0s", style="dim", justify="right")
        table.add_row(
            str(row_count),
            tool,
            short_msg,
            _queue_status_text("pending"),
            Text("", style="dim"),
            elapsed_text,
            key=request_id,
        )
        if request is not None:
            self._queue_request_map[request_id] = request
        self.queue_count = table.row_count

    def remove_queue_row(self, request_id: str) -> None:
        """Keep the row but mark it with its final status. Call via call_from_thread.

        Rows are never removed — queue history is preserved for inspection.
        The status cell is updated to reflect the final state.
        """
        req = self._queue_request_map.get(request_id)
        if req is not None:
            self._update_queue_row_status(request_id, req.status, req.answer_preview)
        # Update queue count based on pending items only
        self.queue_count = self._hitl_queue.size

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
                _start = asyncio.get_event_loop().time()
                try:
                    if request.tool in ("hitl_notify", "notify"):
                        params = request.params
                        agent = params.get("title") or "agent"
                        message = params.get("message", "")
                        level = params.get("level", "info")
                        self.stream_output(agent, message, level)
                        self._hitl_queue.resolve(request, True)
                        sid = request.params.get("_session_id", "")
                        if sid:
                            self.record_session_resolved(sid)
                    else:
                        msg = request.params.get("message", "")
                        client_name = request.params.get("_client_name", "unknown")
                        severity = request.params.get("severity", "")
                        timeout_s = request.params.get("timeout_seconds", 0)
                        short_msg = msg[:40] + "..." if len(msg) > 40 else msg
                        detail_parts: list[str] = [short_msg] if short_msg else []
                        if severity:
                            detail_parts.append(f"severity={severity}")
                        if timeout_s:
                            detail_parts.append(f"timeout={timeout_s}s")
                        detail_suffix = f" — {', '.join(detail_parts)}" if detail_parts else ""
                        self.stream_output(
                            "queue",
                            f"▶ [bold]{request.tool}[/bold] \\[{client_name}]{detail_suffix}",
                            "info",
                        )
                        self.add_queue_row(request.request_id, request.tool, msg, request=request)
                        # FIX 2: Loop handles Escape-to-minimize. When the user
                        # presses Escape, the screen dismisses with _MINIMIZED
                        # sentinel. We store it and wait for restore, then re-push.
                        screen = screen_for(request)
                        result = _MINIMIZED
                        while result == _MINIMIZED:
                            result = await self.push_screen_wait(screen)
                            if result == _MINIMIZED:
                                self._restore_event = asyncio.Event()
                                self._pending_screen = screen
                                # Mark as minimized in queue
                                self._hitl_queue.mark_minimized(request.request_id)
                                self._update_queue_row_status(request.request_id, "minimized")
                                self.notify(
                                    "Prompt minimized — press Escape or click row to restore",
                                    timeout=3,
                                )
                                # Wait until action_restore_prompt signals via Event
                                await self._restore_event.wait()
                                self._restore_event.clear()
                                # Mark back to pending while re-pushing
                                self._hitl_queue._by_id.get(request.request_id)
                                self._update_queue_row_status(request.request_id, "pending")
                                # Screen was re-pushed by action_restore_prompt;
                                # create a fresh instance to avoid compose errors.
                                screen = screen_for(request)
                        self.remove_queue_row(request.request_id)
                        elapsed = asyncio.get_event_loop().time() - _start
                        # Determine resolution type for richer log
                        client_name = request.params.get("_client_name", "unknown")
                        if isinstance(result, dict) and result.get("action") == "cancel":
                            self._hitl_queue.mark_cancelled(request.request_id)
                            self._update_queue_row_status(request.request_id, "cancelled")
                            self.stream_output(
                                "queue",
                                f"✕ [bold]{request.tool}[/bold] \\[{client_name}] — cancelled (elapsed: {elapsed:.1f}s)",
                                "warning",
                            )
                        else:
                            action = result.get("action", "value") if isinstance(result, dict) else "value"
                            preview = str(result)[:60] if not isinstance(result, dict) else action
                            self._hitl_queue.mark_answered(request.request_id, preview)
                            self._update_queue_row_status(request.request_id, "answered", preview)
                            self.stream_output(
                                "queue",
                                f"✓ [bold]{request.tool}[/bold] \\[{client_name}] — {action} (elapsed: {elapsed:.1f}s)",
                                "success",
                            )
                        self._hitl_queue.resolve(request, result)
                        sid = request.params.get("_session_id", "")
                        if sid:
                            self.record_session_resolved(sid)
                except Exception as e:
                    logger.error(f"Screen error for {request.tool}: {e}", exc_info=True)
                    elapsed = asyncio.get_event_loop().time() - _start
                    client_name = request.params.get("_client_name", "unknown")
                    timeout_s = request.params.get("timeout_seconds", 0)
                    if "TimeoutError" in type(e).__name__ or "timeout" in str(e).lower():
                        self.stream_output(
                            "queue",
                            f"⏱ [bold]{request.tool}[/bold] \\[{client_name}] — timed out after {timeout_s}s",
                            "error",
                        )
                    else:
                        self.stream_output(
                            "queue",
                            f"⏱ [bold]{request.tool}[/bold] \\[{client_name}] — failed after {elapsed:.1f}s",
                            "error",
                        )
                    self._hitl_queue.mark_cancelled(request.request_id)
                    self._update_queue_row_status(request.request_id, "cancelled")
                    self._hitl_queue.reject(request, e)
                    sid = request.params.get("_session_id", "")
                    if sid:
                        self.record_session_resolved(sid)
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

    def _update_queue_row_status(self, request_id: str, status: str, answer_preview: str = "") -> None:
        """Update status and answer cells for a queue row."""
        table = self.query_one("#queue-table", DataTable)
        try:
            table.update_cell(request_id, "status", _queue_status_text(status), update_width=False)
            if answer_preview:
                table.update_cell(
                    request_id,
                    "answer",
                    Text(answer_preview[:30], style="dim"),
                    update_width=False,
                )
        except Exception:
            pass

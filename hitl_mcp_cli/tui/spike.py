"""Phase 1 Spike: Textual + FastMCP/uvicorn in background threading.Thread.

Validates:
1. Textual App.run() owns the asyncio event loop on the main thread
2. uvicorn.run() works in a daemon threading.Thread (its own event loop)
3. call_from_thread bridges tool calls back to the TUI safely
4. Clean shutdown: Textual exit kills the daemon thread

Run: cd ~/projects/hitl-mcp-cli && timeout 15 uv run python -m hitl_mcp_cli.tui.spike 2>&1 | head -50
"""

from __future__ import annotations

import logging
import threading

import uvicorn
from fastmcp import FastMCP
from textual.app import App, ComposeResult
from textual.widgets import Label, RichLog

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# --- FastMCP server (will run in background thread) ---

spike_mcp = FastMCP("spike-server")

# Will be set by the Textual app before the server thread starts
_app_ref: SpikeApp | None = None


@spike_mcp.tool()
async def spike_ping(message: str = "hello from tool") -> dict[str, str]:
    """Test tool that bridges a message to the TUI via call_from_thread."""
    if _app_ref is not None:
        _app_ref.call_from_thread(_app_ref.write_to_log, f"[green]✓ TOOL CALL:[/] {message}")
    return {"status": "ok", "message": message}


# --- Textual App ---


class SpikeApp(App[None]):
    """Minimal Textual app to validate thread bridge with FastMCP."""

    CSS = """
    #log { height: 1fr; }
    #status { height: 3; background: $panel; padding: 1; }
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8199) -> None:
        super().__init__()
        self._host = host
        self._port = port
        self._server_thread: threading.Thread | None = None

    def compose(self) -> ComposeResult:
        yield RichLog(id="log", highlight=True, auto_scroll=True)
        yield Label("Spike: starting...", id="status")

    def write_to_log(self, text: str) -> None:
        """Thread-safe: called via call_from_thread from the server thread."""
        self.query_one("#log", RichLog).write(text)
        # Also print for headless verification
        print(f"[LOG] {text}")

    def update_status(self, text: str) -> None:
        """Thread-safe: called via call_from_thread."""
        self.query_one("#status", Label).update(text)
        print(f"[STATUS] {text}")

    async def on_mount(self) -> None:
        global _app_ref
        _app_ref = self

        self.write_to_log("[bold]Spike started[/bold]")
        self.write_to_log(f"Starting FastMCP server on {self._host}:{self._port}...")

        # Start FastMCP/uvicorn in a daemon thread
        self._server_thread = threading.Thread(target=self._run_server, daemon=True, name="fastmcp-server")
        self._server_thread.start()

        # Schedule a self-test: call the tool via HTTP after server is up
        self.set_timer(2.0, self._run_self_test)

        # Auto-exit after 5 seconds
        self.set_timer(5.0, self._auto_exit)

    def _run_server(self) -> None:
        """Run FastMCP HTTP server in background thread (own event loop)."""
        try:
            asgi_app = spike_mcp.http_app(stateless_http=True)
            config = uvicorn.Config(
                asgi_app,
                host=self._host,
                port=self._port,
                log_level="warning",
            )
            server = uvicorn.Server(config)
            server.run()
        except Exception as e:
            logger.error(f"Server thread error: {e}")
            if _app_ref:
                _app_ref.call_from_thread(_app_ref.write_to_log, f"[red]SERVER ERROR:[/] {e}")

    async def _run_self_test(self) -> None:
        """Call the spike_ping tool via HTTP to validate the bridge."""
        import httpx

        self.write_to_log("Sending self-test MCP call...")
        url = f"http://{self._host}:{self._port}/mcp"
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                # Initialize MCP session
                init_resp = await client.post(
                    url,
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2025-03-26",
                            "capabilities": {},
                            "clientInfo": {"name": "spike-test", "version": "0.1"},
                        },
                    },
                    headers=headers,
                )
                self.write_to_log(f"Init response: {init_resp.status_code}")

                # Call the tool
                tool_resp = await client.post(
                    url,
                    json={
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {
                            "name": "spike_ping",
                            "arguments": {"message": "hello from self-test"},
                        },
                    },
                    headers=headers,
                )
                self.write_to_log(f"Tool response: {tool_resp.status_code}")
                self.write_to_log(f"Body: {tool_resp.text[:300]}")

                passed = tool_resp.status_code == 200
                if passed:
                    self.update_status("✓ Spike PASSED — thread bridge + MCP tool call works")
                else:
                    self.update_status(f"✗ Spike PARTIAL — HTTP {tool_resp.status_code}")
        except Exception as e:
            self.write_to_log(f"[red]Self-test error:[/] {e}")
            self.update_status(f"✗ Spike FAILED — {e}")

    async def _auto_exit(self) -> None:
        """Exit cleanly after the test window."""
        self.write_to_log("[bold]Auto-exit (5s timer)[/bold]")
        self.exit()


def main() -> None:
    """Entry point for the spike."""
    print("=== Phase 1 Spike: Textual + FastMCP/uvicorn coexistence ===")
    print("Running for 5 seconds...")
    app = SpikeApp()
    app.run(headless=True)
    print("=== Spike complete ===")


if __name__ == "__main__":
    main()

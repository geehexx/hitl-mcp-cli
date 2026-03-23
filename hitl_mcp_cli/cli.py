"""CLI entry point for interactive MCP server."""

import argparse
import logging
import os

import anyio
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

from .server import mcp
from .ui import display_banner

# Configure logging level from environment
log_level = os.getenv("HITL_LOG_LEVEL", "ERROR").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.ERROR),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class _SuppressClosedResource(logging.Filter):
    """Suppress expected ClosedResourceError noise from FastMCP stateless HTTP cleanup."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return not any(
            x in msg
            for x in (
                "ClosedResourceError",
                "ClientDisconnect",
                "Error in message router",
                "Received exception from stream",
            )
        )


def main() -> None:
    """Run the interactive MCP server."""
    # Get defaults from environment variables
    default_host = os.getenv("HITL_HOST", "127.0.0.1")
    default_port = int(os.getenv("HITL_PORT", "5555"))
    default_no_banner = os.getenv("HITL_NO_BANNER", "").lower() in ("1", "true", "yes")

    parser = argparse.ArgumentParser(
        description="Interactive MCP Server for User Input",
        epilog="Environment variables: HITL_HOST, HITL_PORT, HITL_LOG_LEVEL, HITL_NO_BANNER",
    )
    parser.add_argument(
        "--port", type=int, default=default_port, help=f"Port to listen on (default: {default_port})"
    )
    parser.add_argument(
        "--host", type=str, default=default_host, help=f"Host to bind to (default: {default_host})"
    )
    parser.add_argument(
        "--no-banner", action="store_true", default=default_no_banner, help="Disable startup banner"
    )

    # TUI mode (default: on)
    default_no_tui = os.getenv("HITL_NO_TUI", "").lower() in ("1", "true", "yes")
    parser.add_argument(
        "--no-tui",
        action="store_true",
        default=default_no_tui,
        help="Disable TUI mode (headless/CI, env: HITL_NO_TUI=1)",
    )
    # Backward compat: --tui is a no-op (TUI is now the default)
    parser.add_argument("--tui", action="store_true", default=True, help=argparse.SUPPRESS)

    args = parser.parse_args()

    logger.info(f"Starting HITL MCP server on {args.host}:{args.port}")

    if not args.no_tui:
        from .server import configure_tui_mode
        from .tui import HITLApp, HITLQueue

        queue = HITLQueue()
        app = HITLApp(hitl_queue=queue, host=args.host, port=args.port, mcp_app=mcp.http_app())
        configure_tui_mode(queue, app)
        app.run()
        return

    # Display custom banner
    if not args.no_banner:
        display_banner(host=args.host, port=args.port)

    try:
        # Run server with FastMCP banner disabled
        logger.debug(f"Server configuration: host={args.host}, port={args.port}, banner={not args.no_banner}")

        # Configure uvicorn logging based on HITL_LOG_LEVEL
        # Only show access logs if log level is DEBUG
        uvicorn_log_level = "error" if log_level == "ERROR" else log_level.lower()

        # Configure uvicorn to disable access logs unless DEBUG
        uvicorn_config = {}
        if log_level != "DEBUG":
            # Disable access logs by setting level to CRITICAL (effectively disabling them)
            uvicorn_config = {
                "log_config": {
                    "version": 1,
                    "disable_existing_loggers": False,
                    "loggers": {
                        "uvicorn.access": {
                            "level": "CRITICAL",  # Disable access logs
                        },
                    },
                },
            }

        # Suppress expected lifecycle noise from FastMCP stateless HTTP cleanup
        for _logger_name in ("mcp.server.streamable_http", "mcp.server.lowlevel.server"):
            logging.getLogger(_logger_name).addFilter(_SuppressClosedResource())

        # Fix mcp-sdk 1.21.0 bug #823: ClosedResourceError propagates through
        # self._task_group (not through _handle_stateless_request), so except*
        # must be INSIDE run_stateless_server, not wrapping the outer call.
        def _patch_session_manager() -> None:
            from mcp.server.streamable_http import StreamableHTTPServerTransport

            async def _fixed_handle_stateless(  # type: ignore[no-untyped-def]
                self, scope, receive, send
            ) -> None:
                http_transport = StreamableHTTPServerTransport(
                    mcp_session_id=None,
                    is_json_response_enabled=self.json_response,
                    event_store=None,
                    security_settings=self.security_settings,
                )

                async def run_stateless_server(  # type: ignore[no-untyped-def]
                    *, task_status=anyio.TASK_STATUS_IGNORED
                ) -> None:
                    async with http_transport.connect() as streams:
                        read_stream, write_stream = streams
                        task_status.started()
                        try:
                            await self.app.run(
                                read_stream,
                                write_stream,
                                self.app.create_initialization_options(),
                                stateless=True,
                            )
                        except* (anyio.ClosedResourceError, anyio.BrokenResourceError):
                            logger.debug("Client disconnected — stateless session ended cleanly")
                        except* Exception:
                            logger.exception("Stateless session crashed")

                assert self._task_group is not None
                await self._task_group.start(run_stateless_server)
                await http_transport.handle_request(scope, receive, send)
                await http_transport.terminate()

            StreamableHTTPSessionManager._handle_stateless_request = _fixed_handle_stateless  # type: ignore[method-assign]

        _patch_session_manager()

        mcp.run(
            transport="streamable-http",
            host=args.host,
            port=args.port,
            show_banner=False,
            log_level=uvicorn_log_level,
            uvicorn_config=uvicorn_config if uvicorn_config else None,
            # stateless_http=True: required for clients that send each HTTP POST
            # independently (no persistent SSE session). Without this, FastMCP
            # expects a session handshake and raises ClientDisconnect on
            # stateless requests.
            stateless_http=True,
        )
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped by user")
        logger.info("Server shutdown complete")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()

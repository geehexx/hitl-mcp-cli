"""CLI entry point for interactive MCP server."""

import argparse
import logging
import os

from .server import mcp

# Configure logging level from environment
log_level = os.getenv("HITL_LOG_LEVEL", "ERROR").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.ERROR),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Run the interactive MCP server."""
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

    args = parser.parse_args()

    logger.info(f"Starting HITL MCP server on {args.host}:{args.port}")

    from .server import configure_tui_mode
    from .tui import HITLApp, HITLQueue

    queue = HITLQueue()
    app = HITLApp(hitl_queue=queue, host=args.host, port=args.port, mcp_app=mcp.http_app())
    configure_tui_mode(queue, app)
    try:
        app.run()
    except KeyboardInterrupt:
        logger.info("Server shutdown complete")


if __name__ == "__main__":
    main()

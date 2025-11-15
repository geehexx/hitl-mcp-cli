"""CLI entry point for interactive MCP server."""

import argparse
import asyncio
import logging
import os

from .server import mcp
from .ui import display_banner

# Configure logging level from environment
log_level = os.getenv("HITL_LOG_LEVEL", "ERROR").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.ERROR),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


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
    parser.add_argument(
        "--enable-coordination",
        action="store_true",
        default=os.getenv("HITL_ENABLE_COORDINATION", "").lower() in ("1", "true", "yes"),
        help="Enable multi-agent coordination features",
    )

    args = parser.parse_args()

    # Set environment variable for server module
    if args.enable_coordination:
        os.environ["HITL_ENABLE_COORDINATION"] = "1"

    logger.info(f"Starting HITL MCP server on {args.host}:{args.port}")
    if args.enable_coordination:
        logger.info("Multi-agent coordination: ENABLED")

    # Display custom banner
    if not args.no_banner:
        display_banner(host=args.host, port=args.port)

    try:
        # Start coordination backend if enabled
        if args.enable_coordination:
            from .server import coordination_lock_manager

            if coordination_lock_manager:
                # Start lock cleanup task
                asyncio.create_task(coordination_lock_manager.start())
                logger.debug("Coordination lock manager started")

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

        mcp.run(
            transport="streamable-http",
            host=args.host,
            port=args.port,
            show_banner=False,
            log_level=uvicorn_log_level,
            uvicorn_config=uvicorn_config if uvicorn_config else None,
        )
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped by user")
        logger.info("Server shutdown complete")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()

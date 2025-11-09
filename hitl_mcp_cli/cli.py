"""CLI entry point for interactive MCP server."""

import argparse
import logging
import sys
from io import StringIO

from .server import mcp
from .ui import display_banner

logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    """Run the interactive MCP server."""
    parser = argparse.ArgumentParser(description="Interactive MCP Server for User Input")
    parser.add_argument("--port", type=int, default=5555, help="Port to listen on (default: 5555)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)")
    parser.add_argument("--no-banner", action="store_true", help="Disable startup banner")
    parser.add_argument("--no-animation", action="store_true", help="Disable banner animation")

    args = parser.parse_args()

    # Display custom banner
    if not args.no_banner:
        display_banner(host=args.host, port=args.port, animate=not args.no_animation)

    # Suppress FastMCP startup messages by redirecting stdout temporarily
    old_stdout = sys.stdout
    sys.stdout = StringIO()

    try:
        # Restore stdout before running to allow normal operation
        sys.stdout = old_stdout
        mcp.run(transport="streamable-http", host=args.host, port=args.port)
    except KeyboardInterrupt:
        sys.stdout = old_stdout
        print("\n\n👋 Server stopped by user")
    except Exception as e:
        sys.stdout = old_stdout
        logger.error(f"Server error: {e}")
        raise


if __name__ == "__main__":
    main()

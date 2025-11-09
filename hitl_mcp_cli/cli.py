"""CLI entry point for interactive MCP server."""

import argparse
import logging

from .server import mcp

logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    """Run the interactive MCP server."""
    parser = argparse.ArgumentParser(description="Interactive MCP Server for User Input")
    parser.add_argument("--port", type=int, default=5555, help="Port to listen on (default: 5555)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)")

    args = parser.parse_args()

    mcp.run(transport="streamable-http", host=args.host, port=args.port)


if __name__ == "__main__":
    main()

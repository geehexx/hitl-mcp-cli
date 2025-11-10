"""Tests for CLI functionality."""

import subprocess
import sys
from unittest.mock import patch


def test_cli_help() -> None:
    """Test CLI help message."""
    result = subprocess.run(
        [sys.executable, "-m", "hitl_mcp_cli.cli", "--help"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0
    assert "Interactive MCP Server" in result.stdout
    assert "--port" in result.stdout
    assert "--host" in result.stdout
    assert "--no-banner" in result.stdout


def test_banner_display() -> None:
    """Test banner displays correctly."""
    from io import StringIO

    from rich.console import Console

    from hitl_mcp_cli.ui import display_banner

    # Capture output
    output = StringIO()
    test_console = Console(file=output, force_terminal=True, width=120)

    with patch("hitl_mcp_cli.ui.banner.console", test_console):
        display_banner(host="localhost", port=8080)

    result = output.getvalue()
    assert "localhost" in result
    assert "8080" in result


def test_banner_no_duplicate_output() -> None:
    """Test banner displays only once."""
    from io import StringIO

    from rich.console import Console

    from hitl_mcp_cli.ui import display_banner

    output = StringIO()
    test_console = Console(file=output, force_terminal=True, width=120)
    with patch("hitl_mcp_cli.ui.banner.console", test_console):
        display_banner(host="localhost", port=8080)
    result = output.getvalue()
    assert result.count("Streamable-HTTP") == 1

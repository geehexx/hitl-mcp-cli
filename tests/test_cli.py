"""Tests for CLI functionality."""

import subprocess
import sys
from unittest.mock import patch

import pytest


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
    assert "--no-animation" in result.stdout


def test_banner_display_no_animation() -> None:
    """Test banner displays correctly without animation."""
    from hitl_mcp_cli.ui import display_banner
    from io import StringIO
    from rich.console import Console

    # Capture output
    output = StringIO()
    test_console = Console(file=output, force_terminal=True, width=120)

    with patch("hitl_mcp_cli.ui.banner.console", test_console):
        display_banner(host="localhost", port=8080, animate=False)

    result = output.getvalue()
    assert "HITL" in result or "MCP" in result  # Banner text present
    assert "localhost" in result
    assert "8080" in result
    assert "Streamable-HTTP" in result


def test_banner_display_with_animation() -> None:
    """Test banner displays correctly with animation."""
    from hitl_mcp_cli.ui import display_banner
    from io import StringIO
    from rich.console import Console

    # Capture output
    output = StringIO()
    test_console = Console(file=output, force_terminal=True, width=120)

    with patch("hitl_mcp_cli.ui.banner.console", test_console):
        with patch("hitl_mcp_cli.ui.banner.time.sleep"):  # Speed up test
            display_banner(host="localhost", port=8080, animate=True)

    result = output.getvalue()
    assert "localhost" in result
    assert "8080" in result


def test_banner_no_duplicate_output() -> None:
    """Test banner animation prints expected number of frames."""
    from hitl_mcp_cli.ui import display_banner
    from io import StringIO
    from rich.console import Console

    output = StringIO()
    test_console = Console(file=output, force_terminal=True, width=120)

    with patch("hitl_mcp_cli.ui.banner.console", test_console):
        with patch("hitl_mcp_cli.ui.banner.time.sleep"):
            display_banner(host="localhost", port=8080, animate=True)

    result = output.getvalue()
    # Animation prints 3 frames (0.3, 0.6, 1.0 opacity)
    assert result.count("Streamable-HTTP") == 3
    # Without animation should print once
    output2 = StringIO()
    test_console2 = Console(file=output2, force_terminal=True, width=120)
    with patch("hitl_mcp_cli.ui.banner.console", test_console2):
        display_banner(host="localhost", port=8080, animate=False)
    result2 = output2.getvalue()
    assert result2.count("Streamable-HTTP") == 1

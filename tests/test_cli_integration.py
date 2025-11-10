"""Integration tests for CLI module."""

from unittest.mock import patch

import pytest


def test_cli_module_importable() -> None:
    """Test CLI module can be imported."""
    from hitl_mcp_cli import cli

    assert hasattr(cli, "main")


def test_cli_main_with_no_banner() -> None:
    """Test CLI main function with --no-banner flag."""
    from hitl_mcp_cli.cli import main

    with patch("hitl_mcp_cli.cli.mcp.run") as mock_run:
        with patch("sys.argv", ["hitl-mcp", "--no-banner"]):
            with patch("hitl_mcp_cli.cli.display_banner") as mock_banner:
                mock_run.side_effect = KeyboardInterrupt()  # Exit immediately

                try:
                    main()
                except SystemExit:
                    pass

                # Banner should not be called
                mock_banner.assert_not_called()


def test_cli_main_with_banner() -> None:
    """Test CLI main function displays banner by default."""
    from hitl_mcp_cli.cli import main

    with patch("hitl_mcp_cli.cli.mcp.run") as mock_run:
        with patch("sys.argv", ["hitl-mcp"]):
            with patch("hitl_mcp_cli.cli.display_banner") as mock_banner:
                mock_run.side_effect = KeyboardInterrupt()

                try:
                    main()
                except SystemExit:
                    pass

                # Banner should be called
                mock_banner.assert_called_once()


def test_cli_main_with_custom_port() -> None:
    """Test CLI main function with custom port."""
    from hitl_mcp_cli.cli import main

    with patch("hitl_mcp_cli.cli.mcp.run") as mock_run:
        with patch("sys.argv", ["hitl-mcp", "--port", "8080"]):
            with patch("hitl_mcp_cli.cli.display_banner"):
                mock_run.side_effect = KeyboardInterrupt()

                try:
                    main()
                except SystemExit:
                    pass

                # Verify port was passed
                call_kwargs = mock_run.call_args[1]
                assert call_kwargs["port"] == 8080


def test_cli_main_with_custom_host() -> None:
    """Test CLI main function with custom host."""
    from hitl_mcp_cli.cli import main

    with patch("hitl_mcp_cli.cli.mcp.run") as mock_run:
        with patch("sys.argv", ["hitl-mcp", "--host", "0.0.0.0"]):
            with patch("hitl_mcp_cli.cli.display_banner"):
                mock_run.side_effect = KeyboardInterrupt()

                try:
                    main()
                except SystemExit:
                    pass

                call_kwargs = mock_run.call_args[1]
                assert call_kwargs["host"] == "0.0.0.0"


def test_cli_main_keyboard_interrupt() -> None:
    """Test CLI handles Ctrl+C gracefully."""
    from hitl_mcp_cli.cli import main

    with patch("hitl_mcp_cli.cli.mcp.run") as mock_run:
        with patch("sys.argv", ["hitl-mcp", "--no-banner"]):
            mock_run.side_effect = KeyboardInterrupt()
            # Should not raise, just exit gracefully
            main()


def test_cli_main_generic_exception() -> None:
    """Test CLI handles generic exceptions."""
    from hitl_mcp_cli.cli import main

    with patch("hitl_mcp_cli.cli.mcp.run") as mock_run:
        with patch("sys.argv", ["hitl-mcp", "--no-banner"]):
            with patch("hitl_mcp_cli.cli.logger") as mock_logger:
                mock_run.side_effect = RuntimeError("Test error")

                with pytest.raises(RuntimeError):
                    main()

                # Should log error
                mock_logger.error.assert_called_once()


def test_cli_fastmcp_show_banner_disabled() -> None:
    """Test that FastMCP banner is disabled."""
    from hitl_mcp_cli.cli import main

    with patch("hitl_mcp_cli.cli.mcp.run") as mock_run:
        with patch("sys.argv", ["hitl-mcp", "--no-banner"]):
            mock_run.side_effect = KeyboardInterrupt()

            try:
                main()
            except SystemExit:
                pass

            # Verify show_banner=False is passed to FastMCP
            call_kwargs = mock_run.call_args[1]
            assert call_kwargs["show_banner"] is False

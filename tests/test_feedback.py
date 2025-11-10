"""Tests for feedback components."""

from unittest.mock import MagicMock, patch

from hitl_mcp_cli.ui.feedback import loading_indicator, show_error, show_info, show_success, show_warning


def test_loading_indicator_context_manager() -> None:
    """Test loading indicator as context manager."""
    with patch("hitl_mcp_cli.ui.feedback.Live") as mock_live:
        mock_live_instance = MagicMock()
        mock_live.return_value.__enter__ = MagicMock(return_value=mock_live_instance)
        mock_live.return_value.__exit__ = MagicMock(return_value=None)

        with loading_indicator("Processing"):
            pass  # Simulate work

        mock_live.assert_called_once()


def test_loading_indicator_custom_message() -> None:
    """Test loading indicator with custom message."""
    with patch("hitl_mcp_cli.ui.feedback.Live") as mock_live:
        with patch("hitl_mcp_cli.ui.feedback.Spinner") as mock_spinner:
            mock_live.return_value.__enter__ = MagicMock()
            mock_live.return_value.__exit__ = MagicMock()

            with loading_indicator("Custom message"):
                pass

            # Verify spinner was created with message
            mock_spinner.assert_called_once()
            call_args = mock_spinner.call_args
            assert "Custom message" in str(call_args)


def test_show_success() -> None:
    """Test success message display."""
    with patch("hitl_mcp_cli.ui.feedback.console") as mock_console:
        show_success("Operation completed successfully")
        mock_console.print.assert_called_once()

        # Verify message content
        call_args = mock_console.print.call_args[0][0]
        assert "Operation completed successfully" in call_args.plain


def test_show_error() -> None:
    """Test error message display."""
    with patch("hitl_mcp_cli.ui.feedback.console") as mock_console:
        show_error("Operation failed")
        mock_console.print.assert_called_once()

        call_args = mock_console.print.call_args[0][0]
        assert "Operation failed" in call_args.plain


def test_show_info() -> None:
    """Test info message display."""
    with patch("hitl_mcp_cli.ui.feedback.console") as mock_console:
        show_info("Information message")
        mock_console.print.assert_called_once()

        call_args = mock_console.print.call_args[0][0]
        assert "Information message" in call_args.plain


def test_show_warning() -> None:
    """Test warning message display."""
    with patch("hitl_mcp_cli.ui.feedback.console") as mock_console:
        show_warning("Warning message")
        mock_console.print.assert_called_once()

        call_args = mock_console.print.call_args[0][0]
        assert "Warning message" in call_args.plain


def test_feedback_messages_have_icons() -> None:
    """Test that feedback messages include icons."""
    with patch("hitl_mcp_cli.ui.feedback.console") as mock_console:
        show_success("test")
        success_text = mock_console.print.call_args[0][0]
        assert "✓" in success_text.plain

        show_error("test")
        error_text = mock_console.print.call_args[0][0]
        assert "✗" in error_text.plain

        show_info("test")
        info_text = mock_console.print.call_args[0][0]
        assert "ℹ" in info_text.plain

        show_warning("test")
        warning_text = mock_console.print.call_args[0][0]
        assert "⚠" in warning_text.plain

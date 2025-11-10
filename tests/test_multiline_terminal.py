"""Tests for multiline text input terminal behavior."""

from unittest.mock import MagicMock, patch

import pytest

from hitl_mcp_cli.ui.prompts import prompt_text


@pytest.mark.asyncio
async def test_multiline_text_preserves_screen() -> None:
    """Test that multiline text input doesn't clear the terminal."""
    with (
        patch("hitl_mcp_cli.ui.prompts.inquirer.text") as mock_inquirer,
        patch("hitl_mcp_cli.ui.prompts.console") as mock_console,
    ):
        # Setup mock
        mock_prompt = MagicMock()
        mock_prompt.execute.return_value = "Multi\nline\ntext"
        mock_inquirer.return_value = mock_prompt

        # Call with multiline=True
        result = await prompt_text("Enter text:", multiline=True)

        # Verify result
        assert result == "Multi\nline\ntext"

        # Verify console.print was called (for panel and newline)
        assert mock_console.print.call_count >= 2

        # Verify keybindings were set for Esc+Enter
        call_kwargs = mock_inquirer.call_args[1]
        assert "keybindings" in call_kwargs
        assert "answer" in call_kwargs["keybindings"]


@pytest.mark.asyncio
async def test_multiline_text_with_validation() -> None:
    """Test multiline text input with validation pattern."""
    with patch("hitl_mcp_cli.ui.prompts.inquirer.text") as mock_inquirer:
        mock_prompt = MagicMock()
        mock_prompt.execute.return_value = "valid-text"
        mock_inquirer.return_value = mock_prompt

        result = await prompt_text("Enter text:", multiline=True, validate_pattern=r"^[a-z-]+$")

        assert result == "valid-text"

        # Verify validator was passed
        call_kwargs = mock_inquirer.call_args[1]
        assert "validate" in call_kwargs
        assert callable(call_kwargs["validate"])


@pytest.mark.asyncio
async def test_single_line_text_no_keybindings() -> None:
    """Test that single-line text input doesn't set custom keybindings."""
    with patch("hitl_mcp_cli.ui.prompts.inquirer.text") as mock_inquirer:
        mock_prompt = MagicMock()
        mock_prompt.execute.return_value = "single line"
        mock_inquirer.return_value = mock_prompt

        result = await prompt_text("Enter text:", multiline=False)

        assert result == "single line"

        # Verify keybindings were NOT set for single-line
        call_kwargs = mock_inquirer.call_args[1]
        assert "keybindings" not in call_kwargs


@pytest.mark.asyncio
async def test_multiline_text_default_value() -> None:
    """Test multiline text input with default value."""
    with (
        patch("hitl_mcp_cli.ui.prompts.inquirer.text") as mock_inquirer,
        patch("hitl_mcp_cli.ui.prompts.console"),
    ):
        mock_prompt = MagicMock()
        mock_prompt.execute.return_value = "default\nvalue"
        mock_inquirer.return_value = mock_prompt

        result = await prompt_text("Enter text:", default="default\nvalue", multiline=True)

        assert result == "default\nvalue"

        # Verify default was passed
        call_kwargs = mock_inquirer.call_args[1]
        assert call_kwargs["default"] == "default\nvalue"


@pytest.mark.asyncio
async def test_multiline_text_empty_input() -> None:
    """Test multiline text input with empty input."""
    with (
        patch("hitl_mcp_cli.ui.prompts.inquirer.text") as mock_inquirer,
        patch("hitl_mcp_cli.ui.prompts.console"),
    ):
        mock_prompt = MagicMock()
        mock_prompt.execute.return_value = ""
        mock_inquirer.return_value = mock_prompt

        result = await prompt_text("Enter text:", multiline=True)

        assert result == ""

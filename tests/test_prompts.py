"""Tests for prompt functions with minimal mocking."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hitl_mcp_cli.ui.prompts import (
    display_notification,
    prompt_checkbox,
    prompt_confirm,
    prompt_path,
    prompt_select,
    prompt_text,
)


@pytest.mark.asyncio
async def test_prompt_text_basic() -> None:
    """Test basic text input."""
    with patch("hitl_mcp_cli.ui.prompts.inquirer.text") as mock_inquirer:
        mock_result = MagicMock()
        mock_result.execute.return_value = "test input"
        mock_inquirer.return_value = mock_result

        result = await prompt_text("Enter text:")
        assert result == "test input"
        mock_inquirer.assert_called_once()

        # Verify emoji rendering is delegated to Rich (message/qmark empty)
        call_kwargs = mock_inquirer.call_args[1]
        assert call_kwargs["message"] == ""
        assert call_kwargs["qmark"] == ""


@pytest.mark.asyncio
async def test_prompt_text_with_default() -> None:
    """Test text input with default value used as placeholder."""
    with patch("hitl_mcp_cli.ui.prompts.inquirer.text") as mock_inquirer:
        mock_result = MagicMock()
        # Simulate user submitting empty input — should return default
        mock_result.execute.return_value = ""
        mock_inquirer.return_value = mock_result

        result = await prompt_text("Enter text:", default="default value")
        assert result == "default value"

        # Verify default is NOT pre-filled in buffer (placeholder behavior)
        call_kwargs = mock_inquirer.call_args[1]
        assert call_kwargs["default"] == ""
        assert "default value" in call_kwargs["long_instruction"]


@pytest.mark.asyncio
async def test_prompt_text_with_default_user_types() -> None:
    """Test text input where user types over the default."""
    with patch("hitl_mcp_cli.ui.prompts.inquirer.text") as mock_inquirer:
        mock_result = MagicMock()
        mock_result.execute.return_value = "user typed this"
        mock_inquirer.return_value = mock_result

        result = await prompt_text("Enter text:", default="default value")
        assert result == "user typed this"


@pytest.mark.asyncio
async def test_prompt_text_multiline() -> None:
    """Test multiline text input."""
    with patch("hitl_mcp_cli.ui.prompts.inquirer.text") as mock_inquirer:
        with patch("hitl_mcp_cli.ui.prompts.console"):
            mock_result = MagicMock()
            mock_result.execute.return_value = "line1\\nline2"
            mock_inquirer.return_value = mock_result

            result = await prompt_text("Enter text:", multiline=True)
            assert result == "line1\\nline2"


@pytest.mark.asyncio
async def test_prompt_text_validation() -> None:
    """Test text input with regex validation."""
    with patch("hitl_mcp_cli.ui.prompts.inquirer.text") as mock_inquirer:
        mock_result = MagicMock()
        mock_result.execute.return_value = "valid-slug"
        mock_inquirer.return_value = mock_result

        result = await prompt_text("Enter slug:", validate_pattern=r"^[a-z0-9-]+$")
        assert result == "valid-slug"

        # Verify validator was passed
        call_kwargs = mock_inquirer.call_args[1]
        assert "validate" in call_kwargs
        validator = call_kwargs["validate"]

        # Test validator function
        assert validator("valid-slug") is True
        assert validator("Invalid Slug!") is False


@pytest.mark.asyncio
async def test_prompt_select_basic() -> None:
    """Test single selection."""
    with patch("hitl_mcp_cli.ui.prompts.inquirer.select") as mock_inquirer:
        mock_result = MagicMock()
        mock_result.execute.return_value = "Option B"
        mock_inquirer.return_value = mock_result

        result = await prompt_select("Choose:", ["Option A", "Option B", "Option C"])
        assert result == "Option B"

        # Verify emoji rendering delegated to Rich
        call_kwargs = mock_inquirer.call_args[1]
        assert call_kwargs["message"] == ""
        assert call_kwargs["qmark"] == ""


@pytest.mark.asyncio
async def test_prompt_select_with_default() -> None:
    """Test selection with default value."""
    with patch("hitl_mcp_cli.ui.prompts.inquirer.select") as mock_inquirer:
        mock_result = MagicMock()
        mock_result.execute.return_value = "Default"
        mock_inquirer.return_value = mock_result

        result = await prompt_select("Choose:", ["A", "B", "Default"], default="Default")
        assert result == "Default"


@pytest.mark.asyncio
async def test_prompt_checkbox() -> None:
    """Test multiple selection."""
    with patch("hitl_mcp_cli.ui.prompts.inquirer.checkbox") as mock_inquirer:
        mock_result = MagicMock()
        mock_result.execute.return_value = ["Option A", "Option C"]
        mock_inquirer.return_value = mock_result

        result = await prompt_checkbox("Select multiple:", ["Option A", "Option B", "Option C"])
        assert result == ["Option A", "Option C"]
        assert isinstance(result, list)


@pytest.mark.asyncio
async def test_prompt_confirm_yes() -> None:
    """Test confirmation returning True."""
    with patch("hitl_mcp_cli.ui.prompts.inquirer.confirm") as mock_inquirer:
        mock_result = MagicMock()
        mock_result.execute.return_value = True
        mock_inquirer.return_value = mock_result

        result = await prompt_confirm("Proceed?")
        assert result is True


@pytest.mark.asyncio
async def test_prompt_confirm_no() -> None:
    """Test confirmation returning False."""
    with patch("hitl_mcp_cli.ui.prompts.inquirer.confirm") as mock_inquirer:
        mock_result = MagicMock()
        mock_result.execute.return_value = False
        mock_inquirer.return_value = mock_result

        result = await prompt_confirm("Proceed?", default=False)
        assert result is False


@pytest.mark.asyncio
async def test_prompt_confirm_default() -> None:
    """Test confirmation with default value."""
    with patch("hitl_mcp_cli.ui.prompts.inquirer.confirm") as mock_inquirer:
        mock_result = MagicMock()
        mock_result.execute.return_value = True
        mock_inquirer.return_value = mock_result

        await prompt_confirm("Proceed?", default=True)
        call_kwargs = mock_inquirer.call_args[1]
        assert call_kwargs["default"] is True


@pytest.mark.asyncio
async def test_prompt_path_file() -> None:
    """Test file path input."""
    with patch("hitl_mcp_cli.ui.prompts.inquirer.filepath") as mock_inquirer:
        mock_result = MagicMock()
        mock_result.execute.return_value = "/tmp/test.txt"
        mock_inquirer.return_value = mock_result

        result = await prompt_path("Select file:", path_type="file")
        assert "/test.txt" in result
        assert Path(result).is_absolute()


@pytest.mark.asyncio
async def test_prompt_path_directory() -> None:
    """Test directory path input."""
    with patch("hitl_mcp_cli.ui.prompts.inquirer.filepath") as mock_inquirer:
        mock_result = MagicMock()
        mock_result.execute.return_value = "/tmp/testdir"
        mock_inquirer.return_value = mock_result

        result = await prompt_path("Select directory:", path_type="directory")
        assert "/testdir" in result


@pytest.mark.asyncio
async def test_prompt_path_must_exist() -> None:
    """Test path validation for existence."""
    with patch("hitl_mcp_cli.ui.prompts.inquirer.filepath") as mock_inquirer:
        with patch("hitl_mcp_cli.ui.prompts.PathValidator") as mock_validator:
            mock_result = MagicMock()
            mock_result.execute.return_value = "/tmp/exists.txt"
            mock_inquirer.return_value = mock_result

            await prompt_path("Select file:", path_type="file", must_exist=True)
            mock_validator.assert_called_once()


def test_display_notification_success() -> None:
    """Test success notification display."""
    with patch("hitl_mcp_cli.ui.prompts.console") as mock_console:
        display_notification("Success", "Operation completed", "success")
        assert mock_console.print.call_count == 2  # Panel + spacing


def test_display_notification_error() -> None:
    """Test error notification display."""
    with patch("hitl_mcp_cli.ui.prompts.console") as mock_console:
        display_notification("Error", "Operation failed", "error")
        assert mock_console.print.call_count == 2


def test_display_notification_warning() -> None:
    """Test warning notification display."""
    with patch("hitl_mcp_cli.ui.prompts.console") as mock_console:
        display_notification("Warning", "Be careful", "warning")
        assert mock_console.print.call_count == 2


def test_display_notification_info() -> None:
    """Test info notification display."""
    with patch("hitl_mcp_cli.ui.prompts.console") as mock_console:
        display_notification("Info", "FYI", "info")
        assert mock_console.print.call_count == 2


def test_display_notification_default_type() -> None:
    """Test notification with default type."""
    with patch("hitl_mcp_cli.ui.prompts.console") as mock_console:
        display_notification("Title", "Message")
        assert mock_console.print.call_count == 2


@pytest.mark.asyncio
async def test_prompt_text_with_notes() -> None:
    """Test notes are displayed as dim text before prompt."""
    with patch("hitl_mcp_cli.ui.prompts.inquirer.text") as mock_inquirer:
        with patch("hitl_mcp_cli.ui.prompts.console") as mock_console:
            mock_result = MagicMock()
            mock_result.execute.return_value = "answer"
            mock_inquirer.return_value = mock_result

            result = await prompt_text("Question:", notes="Some context")
            assert result == "answer"
            # Verify notes rendered via console.print with dim markup
            print_calls = [str(c) for c in mock_console.print.call_args_list]
            assert any("[dim]" in c or "Some context" in c for c in print_calls)


@pytest.mark.asyncio
async def test_prompt_checkbox_escape_hatch_all_selected() -> None:
    """Test escape hatch triggers when all choices selected."""
    with patch("hitl_mcp_cli.ui.prompts.inquirer.checkbox") as mock_checkbox:
        with patch("hitl_mcp_cli.ui.prompts.inquirer.text") as mock_text:
            mock_cb_result = MagicMock()
            mock_cb_result.execute.return_value = ["A", "B", "C"]
            mock_checkbox.return_value = mock_cb_result

            mock_text_result = MagicMock()
            mock_text_result.execute.return_value = "I need all of them"
            mock_text.return_value = mock_text_result

            result = await prompt_checkbox("Pick:", ["A", "B", "C"])
            assert result == {"selected": ["A", "B", "C"], "note": "I need all of them"}


@pytest.mark.asyncio
async def test_prompt_checkbox_escape_hatch_none_selected() -> None:
    """Test escape hatch triggers when no choices selected."""
    with patch("hitl_mcp_cli.ui.prompts.inquirer.checkbox") as mock_checkbox:
        with patch("hitl_mcp_cli.ui.prompts.inquirer.text") as mock_text:
            mock_cb_result = MagicMock()
            mock_cb_result.execute.return_value = []
            mock_checkbox.return_value = mock_cb_result

            mock_text_result = MagicMock()
            mock_text_result.execute.return_value = "None apply to my case"
            mock_text.return_value = mock_text_result

            result = await prompt_checkbox("Pick:", ["A", "B", "C"])
            assert result == {"selected": [], "note": "None apply to my case"}


@pytest.mark.asyncio
async def test_prompt_checkbox_escape_hatch_skip() -> None:
    """Test escape hatch skipped when user presses Enter without note."""
    with patch("hitl_mcp_cli.ui.prompts.inquirer.checkbox") as mock_checkbox:
        with patch("hitl_mcp_cli.ui.prompts.inquirer.text") as mock_text:
            mock_cb_result = MagicMock()
            mock_cb_result.execute.return_value = ["A", "B", "C"]
            mock_checkbox.return_value = mock_cb_result

            mock_text_result = MagicMock()
            mock_text_result.execute.return_value = ""
            mock_text.return_value = mock_text_result

            result = await prompt_checkbox("Pick:", ["A", "B", "C"])
            assert result == ["A", "B", "C"]


@pytest.mark.asyncio
async def test_prompt_checkbox_partial_no_escape_hatch() -> None:
    """Test no escape hatch for partial selection."""
    with patch("hitl_mcp_cli.ui.prompts.inquirer.checkbox") as mock_checkbox:
        mock_cb_result = MagicMock()
        mock_cb_result.execute.return_value = ["A"]
        mock_checkbox.return_value = mock_cb_result

        result = await prompt_checkbox("Pick:", ["A", "B", "C"])
        assert result == ["A"]


def test_display_notification_with_notes() -> None:
    """Test notification displays notes before panel."""
    with patch("hitl_mcp_cli.ui.prompts.console") as mock_console:
        display_notification("Info", "Message", "info", notes="Extra context")
        # 3 prints: notes dim line + panel + spacing
        assert mock_console.print.call_count == 3

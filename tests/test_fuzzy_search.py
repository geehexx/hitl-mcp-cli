"""Tests for fuzzy search in long choice lists."""

from unittest.mock import MagicMock, patch

import pytest

from hitl_mcp_cli.ui import prompt_checkbox, prompt_select


@pytest.mark.asyncio
async def test_prompt_select_enables_filter_for_long_lists() -> None:
    """Test select prompt uses fuzzy when choices exceed 15."""
    long_choices = [f"Option {i}" for i in range(20)]

    with patch("hitl_mcp_cli.ui.prompts.inquirer.fuzzy") as mock_fuzzy:
        mock_result = MagicMock()
        mock_result.execute.return_value = "Option 5"
        mock_fuzzy.return_value = mock_result

        result = await prompt_select("Choose one:", long_choices)

        assert result == "Option 5"
        mock_fuzzy.assert_called_once()
        call_kwargs = mock_fuzzy.call_args[1]
        assert call_kwargs["max_height"] == "70%"


@pytest.mark.asyncio
async def test_prompt_select_no_filter_for_short_lists() -> None:
    """Test select prompt uses select for short lists."""
    short_choices = [f"Option {i}" for i in range(10)]

    with patch("hitl_mcp_cli.ui.prompts.inquirer.select") as mock_select:
        mock_result = MagicMock()
        mock_result.execute.return_value = "Option 3"
        mock_select.return_value = mock_result

        result = await prompt_select("Choose one:", short_choices)

        assert result == "Option 3"
        mock_select.assert_called_once()
        call_kwargs = mock_select.call_args[1]
        assert call_kwargs["max_height"] == "70%"


@pytest.mark.asyncio
async def test_prompt_select_filter_threshold_exactly_15() -> None:
    """Test select prompt uses select at exactly 15 choices."""
    exactly_15_choices = [f"Option {i}" for i in range(15)]

    with patch("hitl_mcp_cli.ui.prompts.inquirer.select") as mock_select:
        mock_result = MagicMock()
        mock_result.execute.return_value = "Option 7"
        mock_select.return_value = mock_result

        result = await prompt_select("Choose one:", exactly_15_choices)

        assert result == "Option 7"
        # Exactly 15 should use select (threshold is > 15)
        mock_select.assert_called_once()


@pytest.mark.asyncio
async def test_prompt_select_filter_threshold_16() -> None:
    """Test select prompt uses fuzzy at 16 choices."""
    sixteen_choices = [f"Option {i}" for i in range(16)]

    with patch("hitl_mcp_cli.ui.prompts.inquirer.fuzzy") as mock_fuzzy:
        mock_result = MagicMock()
        mock_result.execute.return_value = "Option 8"
        mock_fuzzy.return_value = mock_result

        result = await prompt_select("Choose one:", sixteen_choices)

        assert result == "Option 8"
        # 16 choices should use fuzzy (> 15)
        mock_fuzzy.assert_called_once()


@pytest.mark.asyncio
async def test_prompt_checkbox_enables_filter_for_long_lists() -> None:
    """Test checkbox prompt works with long lists."""
    long_choices = [f"Option {i}" for i in range(25)]

    with patch("hitl_mcp_cli.ui.prompts.inquirer.checkbox") as mock_checkbox:
        mock_result = MagicMock()
        mock_result.execute.return_value = ["Option 5", "Option 10"]
        mock_checkbox.return_value = mock_result

        result = await prompt_checkbox("Choose multiple:", long_choices)

        assert result == ["Option 5", "Option 10"]
        mock_checkbox.assert_called_once()
        call_kwargs = mock_checkbox.call_args[1]
        assert call_kwargs["max_height"] == "70%"


@pytest.mark.asyncio
async def test_prompt_checkbox_no_filter_for_short_lists() -> None:
    """Test checkbox prompt works with short lists."""
    short_choices = [f"Option {i}" for i in range(8)]

    with patch("hitl_mcp_cli.ui.prompts.inquirer.checkbox") as mock_checkbox:
        mock_result = MagicMock()
        mock_result.execute.return_value = ["Option 2", "Option 5"]
        mock_checkbox.return_value = mock_result

        result = await prompt_checkbox("Choose multiple:", short_choices)

        assert result == ["Option 2", "Option 5"]
        mock_checkbox.assert_called_once()
        call_kwargs = mock_checkbox.call_args[1]
        assert call_kwargs["max_height"] == "70%"


@pytest.mark.asyncio
async def test_prompt_select_max_height_always_set() -> None:
    """Test max_height is always set regardless of list length."""
    short_choices = ["A", "B", "C"]
    long_choices = [f"Option {i}" for i in range(50)]

    # Test short list uses select
    with patch("hitl_mcp_cli.ui.prompts.inquirer.select") as mock_select:
        mock_result = MagicMock()
        mock_result.execute.return_value = "A"
        mock_select.return_value = mock_result

        await prompt_select("Choose:", short_choices)
        call_kwargs = mock_select.call_args[1]
        assert call_kwargs["max_height"] == "70%"

    # Test long list uses fuzzy
    with patch("hitl_mcp_cli.ui.prompts.inquirer.fuzzy") as mock_fuzzy:
        mock_result = MagicMock()
        mock_result.execute.return_value = "Option 25"
        mock_fuzzy.return_value = mock_result

        await prompt_select("Choose:", long_choices)
        call_kwargs = mock_fuzzy.call_args[1]
        assert call_kwargs["max_height"] == "70%"

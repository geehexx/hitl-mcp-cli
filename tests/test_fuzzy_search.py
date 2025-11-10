"""Tests for fuzzy search in long choice lists."""

from unittest.mock import MagicMock, patch

import pytest

from hitl_mcp_cli.ui import prompt_checkbox, prompt_select


@pytest.mark.asyncio
async def test_prompt_select_enables_filter_for_long_lists() -> None:
    """Test select prompt enables fuzzy filter when choices exceed 15."""
    long_choices = [f"Option {i}" for i in range(20)]

    with patch("hitl_mcp_cli.ui.prompts.inquirer.select") as mock_inquirer:
        mock_result = MagicMock()
        mock_result.execute.return_value = "Option 5"
        mock_inquirer.return_value = mock_result

        result = await prompt_select("Choose one:", long_choices)

        assert result == "Option 5"
        call_kwargs = mock_inquirer.call_args[1]
        assert call_kwargs["filter_enable"] is True
        assert call_kwargs["max_height"] == "70%"


@pytest.mark.asyncio
async def test_prompt_select_no_filter_for_short_lists() -> None:
    """Test select prompt does not enable filter for short lists."""
    short_choices = [f"Option {i}" for i in range(10)]

    with patch("hitl_mcp_cli.ui.prompts.inquirer.select") as mock_inquirer:
        mock_result = MagicMock()
        mock_result.execute.return_value = "Option 3"
        mock_inquirer.return_value = mock_result

        result = await prompt_select("Choose one:", short_choices)

        assert result == "Option 3"
        call_kwargs = mock_inquirer.call_args[1]
        assert call_kwargs["filter_enable"] is False
        assert call_kwargs["max_height"] == "70%"


@pytest.mark.asyncio
async def test_prompt_select_filter_threshold_exactly_15() -> None:
    """Test select prompt filter threshold at exactly 15 choices."""
    exactly_15_choices = [f"Option {i}" for i in range(15)]

    with patch("hitl_mcp_cli.ui.prompts.inquirer.select") as mock_inquirer:
        mock_result = MagicMock()
        mock_result.execute.return_value = "Option 7"
        mock_inquirer.return_value = mock_result

        result = await prompt_select("Choose one:", exactly_15_choices)

        assert result == "Option 7"
        call_kwargs = mock_inquirer.call_args[1]
        # Exactly 15 should NOT enable filter (threshold is > 15)
        assert call_kwargs["filter_enable"] is False


@pytest.mark.asyncio
async def test_prompt_select_filter_threshold_16() -> None:
    """Test select prompt filter enabled at 16 choices."""
    sixteen_choices = [f"Option {i}" for i in range(16)]

    with patch("hitl_mcp_cli.ui.prompts.inquirer.select") as mock_inquirer:
        mock_result = MagicMock()
        mock_result.execute.return_value = "Option 8"
        mock_inquirer.return_value = mock_result

        result = await prompt_select("Choose one:", sixteen_choices)

        assert result == "Option 8"
        call_kwargs = mock_inquirer.call_args[1]
        # 16 choices should enable filter (> 15)
        assert call_kwargs["filter_enable"] is True


@pytest.mark.asyncio
async def test_prompt_checkbox_enables_filter_for_long_lists() -> None:
    """Test checkbox prompt enables fuzzy filter when choices exceed 15."""
    long_choices = [f"Option {i}" for i in range(25)]

    with patch("hitl_mcp_cli.ui.prompts.inquirer.checkbox") as mock_inquirer:
        mock_result = MagicMock()
        mock_result.execute.return_value = ["Option 5", "Option 10"]
        mock_inquirer.return_value = mock_result

        result = await prompt_checkbox("Choose multiple:", long_choices)

        assert result == ["Option 5", "Option 10"]
        call_kwargs = mock_inquirer.call_args[1]
        assert call_kwargs["filter_enable"] is True
        assert call_kwargs["max_height"] == "70%"


@pytest.mark.asyncio
async def test_prompt_checkbox_no_filter_for_short_lists() -> None:
    """Test checkbox prompt does not enable filter for short lists."""
    short_choices = [f"Option {i}" for i in range(8)]

    with patch("hitl_mcp_cli.ui.prompts.inquirer.checkbox") as mock_inquirer:
        mock_result = MagicMock()
        mock_result.execute.return_value = ["Option 2", "Option 5"]
        mock_inquirer.return_value = mock_result

        result = await prompt_checkbox("Choose multiple:", short_choices)

        assert result == ["Option 2", "Option 5"]
        call_kwargs = mock_inquirer.call_args[1]
        assert call_kwargs["filter_enable"] is False
        assert call_kwargs["max_height"] == "70%"


@pytest.mark.asyncio
async def test_prompt_select_max_height_always_set() -> None:
    """Test max_height is always set regardless of list length."""
    short_choices = ["A", "B", "C"]
    long_choices = [f"Option {i}" for i in range(50)]

    with patch("hitl_mcp_cli.ui.prompts.inquirer.select") as mock_inquirer:
        mock_result = MagicMock()
        mock_result.execute.return_value = "A"
        mock_inquirer.return_value = mock_result

        # Test short list
        await prompt_select("Choose:", short_choices)
        call_kwargs = mock_inquirer.call_args[1]
        assert call_kwargs["max_height"] == "70%"

        # Test long list
        mock_result.execute.return_value = "Option 25"
        await prompt_select("Choose:", long_choices)
        call_kwargs = mock_inquirer.call_args[1]
        assert call_kwargs["max_height"] == "70%"

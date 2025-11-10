"""Regression tests for selection tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp import Client

from hitl_mcp_cli.server import mcp


@pytest.fixture
async def mcp_client() -> Client:
    """Create MCP client connected to the interactive server."""
    async with Client(mcp) as client:
        yield client


@pytest.mark.asyncio
async def test_request_selection_short_list(mcp_client: Client) -> None:
    """Test selection with short list uses select prompt."""
    with patch("hitl_mcp_cli.server.prompt_select", new_callable=AsyncMock) as mock:
        mock.return_value = "Option B"

        result = await mcp_client.call_tool(
            "request_selection",
            {
                "prompt": "Choose an option:",
                "choices": ["Option A", "Option B", "Option C"],
                "default": "Option A",
                "allow_multiple": False,
            },
        )

        assert result is not None
        assert result.data == "Option B"
        mock.assert_called_once_with("Choose an option:", ["Option A", "Option B", "Option C"], "Option A")


@pytest.mark.asyncio
async def test_request_selection_long_list(mcp_client: Client) -> None:
    """Test selection with long list (>15 items) uses fuzzy search."""
    long_choices = [f"Option {i}" for i in range(20)]

    with patch("hitl_mcp_cli.server.prompt_select", new_callable=AsyncMock) as mock:
        mock.return_value = "Option 10"

        result = await mcp_client.call_tool(
            "request_selection",
            {
                "prompt": "Choose from many options:",
                "choices": long_choices,
                "allow_multiple": False,
            },
        )

        assert result is not None
        assert result.data == "Option 10"
        mock.assert_called_once_with("Choose from many options:", long_choices, None)


@pytest.mark.asyncio
async def test_request_selection_multiple(mcp_client: Client) -> None:
    """Test multiple selection uses checkbox prompt."""
    with patch("hitl_mcp_cli.server.prompt_checkbox", new_callable=AsyncMock) as mock:
        mock.return_value = ["Option A", "Option C"]

        result = await mcp_client.call_tool(
            "request_selection",
            {
                "prompt": "Choose multiple:",
                "choices": ["Option A", "Option B", "Option C"],
                "allow_multiple": True,
            },
        )

        assert result is not None
        assert result.data == ["Option A", "Option C"]
        mock.assert_called_once_with("Choose multiple:", ["Option A", "Option B", "Option C"])


@pytest.mark.asyncio
async def test_prompt_select_short_list_uses_select() -> None:
    """Test prompt_select with ≤15 items uses inquirer.select."""
    from hitl_mcp_cli.ui.prompts import prompt_select

    with patch("hitl_mcp_cli.ui.prompts.inquirer.select") as mock_select:
        mock_result = MagicMock()
        mock_result.execute.return_value = "Choice 5"
        mock_select.return_value = mock_result

        choices = [f"Choice {i}" for i in range(15)]
        result = await prompt_select("Select one:", choices)

        assert result == "Choice 5"
        mock_select.assert_called_once()
        # Verify fuzzy was NOT called
        assert mock_select.call_count == 1


@pytest.mark.asyncio
async def test_prompt_select_long_list_uses_fuzzy() -> None:
    """Test prompt_select with >15 items uses inquirer.fuzzy."""
    from hitl_mcp_cli.ui.prompts import prompt_select

    with patch("hitl_mcp_cli.ui.prompts.inquirer.fuzzy") as mock_fuzzy:
        mock_result = MagicMock()
        mock_result.execute.return_value = "Choice 20"
        mock_fuzzy.return_value = mock_result

        choices = [f"Choice {i}" for i in range(20)]
        result = await prompt_select("Select one:", choices)

        assert result == "Choice 20"
        mock_fuzzy.assert_called_once()


@pytest.mark.asyncio
async def test_prompt_select_exactly_15_uses_select() -> None:
    """Test prompt_select with exactly 15 items uses select (boundary test)."""
    from hitl_mcp_cli.ui.prompts import prompt_select

    with patch("hitl_mcp_cli.ui.prompts.inquirer.select") as mock_select:
        mock_result = MagicMock()
        mock_result.execute.return_value = "Choice 15"
        mock_select.return_value = mock_result

        choices = [f"Choice {i}" for i in range(15)]
        result = await prompt_select("Select one:", choices)

        assert result == "Choice 15"
        mock_select.assert_called_once()


@pytest.mark.asyncio
async def test_prompt_select_exactly_16_uses_fuzzy() -> None:
    """Test prompt_select with exactly 16 items uses fuzzy (boundary test)."""
    from hitl_mcp_cli.ui.prompts import prompt_select

    with patch("hitl_mcp_cli.ui.prompts.inquirer.fuzzy") as mock_fuzzy:
        mock_result = MagicMock()
        mock_result.execute.return_value = "Choice 16"
        mock_fuzzy.return_value = mock_result

        choices = [f"Choice {i}" for i in range(16)]
        result = await prompt_select("Select one:", choices)

        assert result == "Choice 16"
        mock_fuzzy.assert_called_once()


@pytest.mark.asyncio
async def test_prompt_select_with_default_short_list() -> None:
    """Test prompt_select passes default to select for short lists."""
    from hitl_mcp_cli.ui.prompts import prompt_select

    with patch("hitl_mcp_cli.ui.prompts.inquirer.select") as mock_select:
        mock_result = MagicMock()
        mock_result.execute.return_value = "Choice 2"
        mock_select.return_value = mock_result

        choices = ["Choice 1", "Choice 2", "Choice 3"]
        result = await prompt_select("Select one:", choices, default="Choice 2")

        assert result == "Choice 2"
        call_kwargs = mock_select.call_args[1]
        assert call_kwargs["default"] == "Choice 2"


@pytest.mark.asyncio
async def test_prompt_select_with_default_long_list() -> None:
    """Test prompt_select passes default to fuzzy for long lists."""
    from hitl_mcp_cli.ui.prompts import prompt_select

    with patch("hitl_mcp_cli.ui.prompts.inquirer.fuzzy") as mock_fuzzy:
        mock_result = MagicMock()
        mock_result.execute.return_value = "Choice 10"
        mock_fuzzy.return_value = mock_result

        choices = [f"Choice {i}" for i in range(20)]
        result = await prompt_select("Select one:", choices, default="Choice 10")

        assert result == "Choice 10"
        call_kwargs = mock_fuzzy.call_args[1]
        assert call_kwargs["default"] == "Choice 10"


@pytest.mark.asyncio
async def test_prompt_select_keyboard_interrupt() -> None:
    """Test prompt_select handles KeyboardInterrupt correctly."""
    from hitl_mcp_cli.ui.prompts import prompt_select

    with patch("hitl_mcp_cli.ui.prompts.inquirer.select") as mock_select:
        mock_result = MagicMock()
        mock_result.execute.side_effect = KeyboardInterrupt()
        mock_select.return_value = mock_result

        with pytest.raises(KeyboardInterrupt):
            await prompt_select("Select one:", ["A", "B", "C"])


@pytest.mark.asyncio
async def test_request_selection_keyboard_interrupt(mcp_client: Client) -> None:
    """Test request_selection converts KeyboardInterrupt to user-friendly error."""
    from fastmcp.exceptions import ToolError

    with patch("hitl_mcp_cli.server.prompt_select", new_callable=AsyncMock) as mock:
        mock.side_effect = KeyboardInterrupt()

        with pytest.raises(ToolError) as exc_info:
            await mcp_client.call_tool(
                "request_selection",
                {"prompt": "Choose:", "choices": ["A", "B"], "allow_multiple": False},
            )

        assert "User cancelled" in str(exc_info.value)


@pytest.mark.asyncio
async def test_request_selection_generic_exception(mcp_client: Client) -> None:
    """Test request_selection wraps generic exceptions with context."""
    from fastmcp.exceptions import ToolError

    with patch("hitl_mcp_cli.server.prompt_select", new_callable=AsyncMock) as mock:
        mock.side_effect = ValueError("Invalid choice")

        with pytest.raises(ToolError) as exc_info:
            await mcp_client.call_tool(
                "request_selection",
                {"prompt": "Choose:", "choices": ["A", "B"], "allow_multiple": False},
            )

        assert "Selection failed" in str(exc_info.value)
        assert "Invalid choice" in str(exc_info.value)

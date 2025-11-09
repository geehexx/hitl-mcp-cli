"""Integration tests for hitl-mcp-cli server.

Tests the full MCP protocol initialization sequence and tool execution.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastmcp import Client

from hitl_mcp_cli.server import mcp


@pytest.fixture
async def mcp_client() -> Client:
    """Create MCP client connected to the interactive server."""
    async with Client(mcp) as client:
        yield client


@pytest.mark.asyncio
async def test_server_initialization(mcp_client: Client) -> None:
    """Test MCP server initializes with correct metadata."""
    # The client fixture handles the full initialization sequence:
    # 1. Client sends initialize request
    # 2. Server responds with capabilities
    # 3. Client sends notifications/initialized
    # 4. Connection is ready for operations
    
    # Verify server info is accessible via initialize_result
    assert mcp_client.initialize_result is not None
    assert mcp_client.initialize_result.serverInfo is not None
    assert mcp_client.initialize_result.serverInfo.name == "Interactive Input Server"


@pytest.mark.asyncio
async def test_tools_list(mcp_client: Client) -> None:
    """Test tools/list returns all registered tools."""
    tools = await mcp_client.list_tools()
    
    tool_names = {tool.name for tool in tools}
    expected_tools = {
        "request_text_input",
        "request_selection",
        "request_confirmation",
        "request_path_input",
        "notify_completion",
    }
    
    assert tool_names == expected_tools
    assert len(tools) == 5


@pytest.mark.asyncio
async def test_tool_schemas(mcp_client: Client) -> None:
    """Test tool schemas are properly defined."""
    tools = await mcp_client.list_tools()
    tools_by_name = {tool.name: tool for tool in tools}
    
    # Verify request_text_input schema
    text_input = tools_by_name["request_text_input"]
    assert text_input.description is not None
    assert "text input" in text_input.description.lower()
    assert text_input.inputSchema is not None
    assert "prompt" in text_input.inputSchema["properties"]
    
    # Verify request_selection schema
    selection = tools_by_name["request_selection"]
    assert selection.description is not None
    assert "select" in selection.description.lower()
    assert selection.inputSchema is not None
    assert "choices" in selection.inputSchema["properties"]
    
    # Verify request_confirmation schema
    confirmation = tools_by_name["request_confirmation"]
    assert confirmation.description is not None
    assert "confirmation" in confirmation.description.lower()
    assert confirmation.inputSchema is not None
    assert "prompt" in confirmation.inputSchema["properties"]
    
    # Verify request_path_input schema
    path_input = tools_by_name["request_path_input"]
    assert path_input.description is not None
    assert "path" in path_input.description.lower()
    assert path_input.inputSchema is not None
    assert "prompt" in path_input.inputSchema["properties"]
    
    # Verify notify_completion schema
    notification = tools_by_name["notify_completion"]
    assert notification.description is not None
    assert "notification" in notification.description.lower()
    assert notification.inputSchema is not None
    assert "title" in notification.inputSchema["properties"]


@pytest.mark.asyncio
async def test_server_capabilities(mcp_client: Client) -> None:
    """Test server advertises correct capabilities."""
    # Server should advertise tools capability
    assert mcp_client.initialize_result is not None
    assert mcp_client.initialize_result.capabilities is not None
    assert mcp_client.initialize_result.capabilities.tools is not None


@pytest.mark.asyncio
async def test_protocol_version(mcp_client: Client) -> None:
    """Test server uses correct MCP protocol version."""
    # Verify protocol version is set in initialize_result
    assert mcp_client.initialize_result is not None
    assert mcp_client.initialize_result.protocolVersion is not None
    # Should be a valid version string (e.g., "2025-03-26")
    assert isinstance(mcp_client.initialize_result.protocolVersion, str)
    assert len(mcp_client.initialize_result.protocolVersion) > 0


@pytest.mark.asyncio
async def test_request_text_input_tool(mcp_client: Client) -> None:
    """Test request_text_input tool execution with mocked input."""
    with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock_prompt:
        mock_prompt.return_value = "Test User Input"
        
        result = await mcp_client.call_tool(
            "request_text_input",
            {"prompt": "Enter your name:", "default": "User"}
        )
        
        assert result is not None
        assert result.data == "Test User Input"
        mock_prompt.assert_called_once_with("Enter your name:", "User", False, None)


@pytest.mark.asyncio
async def test_request_selection_tool(mcp_client: Client) -> None:
    """Test request_selection tool execution with mocked input."""
    with patch("hitl_mcp_cli.server.prompt_select", new_callable=AsyncMock) as mock_select:
        mock_select.return_value = "Option B"
        
        result = await mcp_client.call_tool(
            "request_selection",
            {
                "prompt": "Choose an option:",
                "choices": ["Option A", "Option B", "Option C"],
                "default": "Option A",
                "allow_multiple": False
            }
        )
        
        assert result is not None
        assert result.data == "Option B"
        mock_select.assert_called_once()


@pytest.mark.asyncio
async def test_request_confirmation_tool(mcp_client: Client) -> None:
    """Test request_confirmation tool execution with mocked input."""
    with patch("hitl_mcp_cli.server.prompt_confirm", new_callable=AsyncMock) as mock_confirm:
        mock_confirm.return_value = True
        
        result = await mcp_client.call_tool(
            "request_confirmation",
            {"prompt": "Do you want to continue?", "default": False}
        )
        
        assert result is not None
        assert result.data is True
        mock_confirm.assert_called_once_with("Do you want to continue?", False)


@pytest.mark.asyncio
async def test_request_path_input_tool(mcp_client: Client) -> None:
    """Test request_path_input tool execution with mocked input."""
    with patch("hitl_mcp_cli.server.prompt_path", new_callable=AsyncMock) as mock_path:
        mock_path.return_value = "/tmp/test.txt"
        
        result = await mcp_client.call_tool(
            "request_path_input",
            {
                "prompt": "Enter file path:",
                "path_type": "file",
                "must_exist": False,
                "default": None
            }
        )
        
        assert result is not None
        assert result.data == "/tmp/test.txt"
        mock_path.assert_called_once()


@pytest.mark.asyncio
async def test_notify_completion_tool(mcp_client: Client) -> None:
    """Test notify_completion tool execution with mocked display."""
    with patch("hitl_mcp_cli.server.display_notification") as mock_notify:
        result = await mcp_client.call_tool(
            "notify_completion",
            {
                "title": "Task Complete",
                "message": "Successfully completed the task",
                "notification_type": "success"
            }
        )
        
        assert result is not None
        assert result.data == {"acknowledged": True}
        mock_notify.assert_called_once_with(
            "Task Complete",
            "Successfully completed the task",
            "success"
        )


@pytest.mark.asyncio
async def test_multiple_selection_tool(mcp_client: Client) -> None:
    """Test request_selection with multiple selections."""
    with patch("hitl_mcp_cli.server.prompt_checkbox", new_callable=AsyncMock) as mock_checkbox:
        mock_checkbox.return_value = ["Option A", "Option C"]
        
        result = await mcp_client.call_tool(
            "request_selection",
            {
                "prompt": "Select multiple options:",
                "choices": ["Option A", "Option B", "Option C"],
                "allow_multiple": True
            }
        )
        
        assert result is not None
        assert result.data == ["Option A", "Option C"]
        mock_checkbox.assert_called_once()

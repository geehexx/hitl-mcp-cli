# HITL MCP CLI - Quick Reference for Multi-Agent Coordination Design

## Architecture Summary

**Type**: Stateless, async-first MCP server
**Transport**: HTTP (streamable-http) with JSON-RPC 2.0
**State Management**: None (by design)
**Concurrency**: Thread-safe except global separator state
**Timeout**: Must be infinite (0) on client side

## Key Files

| File | Purpose | Lines | Importance |
|------|---------|-------|-----------|
| `cli.py` | Entry point, server startup | 90 | Critical |
| `server.py` | Tool definitions, MCP protocol | 271 | Critical |
| `ui/prompts.py` | Interactive prompts, validation | 287 | Critical |
| `ui/feedback.py` | Status messages, spinners | 77 | Important |
| `ui/banner.py` | Startup display | 61 | Support |

## 5 Core Tools Exposed

1. **request_text_input** → str
   - Free-form input with regex validation
   - Use: Names, descriptions, config values

2. **request_selection** → str | list[str]
   - Single or multiple choice selection
   - Auto-fuzzy-search for 15+ items
   - Use: Environment selection, feature flags

3. **request_confirmation** → bool
   - Yes/no approval before action
   - Use: Destructive operations, expensive calls

4. **request_path_input** → str (absolute path)
   - File/directory path with validation
   - Tab completion, path expansion
   - Use: Config files, output dirs

5. **notify_completion** → dict
   - Display styled notification (success/info/warning/error)
   - Non-blocking, instant return
   - Use: Status updates, milestones

## Message Flow

```
Agent → MCP Client → HTTP Request → FastMCP → Tool Function
                                        ↓
                                  sync_to_async
                                        ↓
                                   InquirerPy
                                        ↓
                                   Terminal
                                        ↓
                                  User Input
                                        ↓
                      UI Function Returns Result
                                        ↓
                                   Serialize
                                        ↓
                              HTTP Response → Agent
```

## Critical Configuration

```json
{
  "mcpServers": {
    "hitl": {
      "url": "http://127.0.0.1:5555/mcp",
      "transport": "streamable-http",
      "timeout": 0  // ← CRITICAL: Must be infinite
    }
  }
}
```

## State Management Reality

**What EXISTS**:
- Tool schemas (read-only)
- Visual separator flag (global, not thread-safe)
- Rich console instance (global, thread-safe)
- Asyncio event loop (global)

**What DOES NOT EXIST**:
- Session management
- Request correlation/tracking
- Agent identification
- Inter-tool state sharing
- Distributed state backend
- Audit logging/history

## For Multi-Agent Coordination

### What You CAN Do With Current System
- Call tools from multiple agents sequentially
- Get user confirmation/input from multiple agents
- Display status to user from multiple agents

### What You CANNOT Do
- Correlate related tool calls from same agent
- Maintain cross-request context
- Enforce sequential ordering of tool calls
- Rate limit per-agent
- Track request history
- Route prompts to specific agents
- Implement per-agent UI separation

### Required Additions for Multi-Agent Support

1. **Request Correlation Layer**
   - Add request ID/trace ID to all calls
   - Track call chain and relationships
   - Enable request history/audit

2. **Session/Context Layer**
   - Store session state (in-memory or Redis)
   - Associate requests with agent/user
   - Maintain conversation context

3. **Agent Identification**
   - Add agent name/ID to requests
   - Implement per-agent tracking
   - Enable role-based policies

4. **Coordination Primitives**
   - Distributed locks/semaphores
   - Message queues for async patterns
   - Event broadcasting system
   - Transaction support

5. **UI Separation**
   - Multiple terminal sessions or
   - Message queuing for async prompts or
   - Web UI for remote access

6. **Observability**
   - Request ID propagation
   - Structured logging
   - Distributed tracing
   - Metrics/monitoring

## Extensibility Points

### Add New Tool (Easy)
```python
# 1. In server.py:
@mcp.tool()
async def new_tool(param: str) -> str:
    try:
        result = await new_ui_function(param)
        return result
    except KeyboardInterrupt:
        raise Exception("User cancelled...") from None
    except Exception as e:
        raise Exception(f"Operation failed: {str(e)}") from e

# 2. In ui/prompts.py:
@sync_to_async
def new_ui_function(param: str) -> str:
    # InquirerPy or Rich code here
    return result
```

### Customize UI (Easy)
- Edit `ICONS` dict in prompts.py (line 27)
- Edit `color_map` in display_notification (line 240)
- Modify validation logic
- Adjust styling/formatting

### Add Session Layer (Medium)
- Create `SessionManager` class
- Store session state in Redis/dict
- Pass session ID in request context
- Implement cleanup/expiry

### Add Request Correlation (Medium)
- Add `request_id` to function signatures
- Thread request ID through call chain
- Store request metadata
- Implement correlation logging

### Change Transport (Medium)
- In cli.py, change `transport="stdio"` or `"sse"`
- Adjust Uvicorn config if needed
- Test with appropriate client

## Known Limitations & Workarounds

| Issue | Impact | Workaround |
|-------|--------|-----------|
| Global separator state | Non-critical visual | Use sequential calls only (default behavior) |
| No session management | Blocks multi-agent | Add session layer on top |
| No request tracking | Hard to debug | Add logging wrapper |
| Single terminal output | UI mixing | Queue prompts to separate sessions |
| No persistence | State lost on restart | Add state storage |
| No auth/authz | Security issue if exposed | Bind to localhost only |

## Performance Characteristics

- **Tool execution**: Async, non-blocking
- **UI I/O**: Blocking in thread executor (doesn't block event loop)
- **Concurrency**: Can handle multiple clients
- **Rate limit**: Natural limit from human input time
- **Scalability**: Linear with number of concurrent connections
- **Memory**: Minimal (no state storage)

## Testing Strategy

**Integration Tests**: Full MCP flow with mocked UI
```python
@pytest.mark.asyncio
async def test_tool(mcp_client):
    with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock:
        mock.return_value = "Response"
        result = await mcp_client.call_tool("request_text_input", {...})
        assert result.data == "Response"
```

**Unit Tests**: UI components in isolation
```python
def test_show_success():
    with patch("hitl_mcp_cli.ui.feedback.console"):
        show_success("Message")
```

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `HITL_HOST` | 127.0.0.1 | Server bind address |
| `HITL_PORT` | 5555 | Server port |
| `HITL_LOG_LEVEL` | ERROR | Logging level (DEBUG/INFO/WARNING/ERROR) |
| `HITL_NO_BANNER` | false | Disable startup banner |

## Dependencies

- **FastMCP** (2.13.0+): MCP server framework
- **InquirerPy** (0.3.4+): Interactive prompts
- **Rich** (13.0.0+): Terminal styling
- **Python** (3.11+): Base runtime
- **asyncio**: Async I/O (built-in)
- **pathlib**: Path handling (built-in)

## Documentation References

- **ARCHITECTURE.md**: Detailed system design
- **FUTURE.md**: Planned enhancements & limitations
- **ACCESSIBILITY.md**: A11y features & limitations
- **TESTING.md**: Testing guide
- **README.md**: User documentation
- **This file**: Quick reference


# Architecture

## Overview

HITL MCP CLI is built as a layered architecture that separates concerns between protocol handling, user interaction, and presentation.

## Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        AI Agent / MCP Client                │
│                    (Claude, GPT, Custom Agent)              │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP (Streamable-HTTP Transport)
                             │ MCP Protocol (JSON-RPC)
┌────────────────────────────▼────────────────────────────────┐
│                      FastMCP Server Layer                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Tool Registry & Schema Generation                   │   │
│  │  - hitl_collect / hitl_ask                           │   │
│  │  - hitl_choose                                       │   │
│  │  - hitl_confirm                                      │   │
│  │  - hitl_notify                                       │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────┘
                             │ Async Queue (HITLQueue)
┌────────────────────────────▼────────────────────────────────┐
│                        TUI Layer (Textual)                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Screens (screens.py)                                │   │
│  │  - CollectScreen, ChooseScreen, ConfirmScreen        │   │
│  │  - NotifyScreen                                      │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  App (app.py)                                        │   │
│  │  - Sessions panel (color-coded by recency)           │   │
│  │  - Queue panel (full history, clickable rows)        │   │
│  │  - Collapsible messages (>200 chars)                 │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────┘
                             │ Terminal I/O
┌────────────────────────────▼────────────────────────────────┐
│                           User                              │
│                    (Terminal Interface)                     │
└─────────────────────────────────────────────────────────────┘
```

## Module Structure

### `hitl_mcp_cli/server.py`
**Purpose**: MCP protocol implementation and tool registration

- Defines FastMCP server instance
- Registers 5 interactive tools (`hitl_collect`, `hitl_ask`, `hitl_choose`, `hitl_confirm`, `hitl_notify`) with schemas
- Handles tool invocation and error wrapping
- Provides comprehensive tool documentation

**Key Responsibilities**:
- Tool schema generation (automatic via FastMCP)
- Parameter validation
- Error handling and user-friendly error messages
- Async tool execution

### `hitl_mcp_cli/cli.py`
**Purpose**: Command-line interface and server startup

- Argument parsing (host, port, banner options)
- TUI app launch
- Server lifecycle management
- Graceful shutdown handling

**Key Responsibilities**:
- CLI argument parsing
- FastMCP server initialization
- Signal handling (Ctrl+C)

### `hitl_mcp_cli/tui/app.py`
**Purpose**: Textual TUI application

- Split-pane layout: activity log + queue panel
- Sessions panel (toggle with ctrl+b / f3), color-coded by recency
- Queue panel with full history and clickable rows
- Collapsible messages for long content (>200 chars)
- Step indicators ("Step X/Y") when provided

### `hitl_mcp_cli/tui/screens.py`
**Purpose**: Textual screens for each tool type

- `CollectScreen`: text/path/multiline input with validation
- `ChooseScreen`: single/multiple selection
- `ConfirmScreen`: yes/no with severity levels
- `NotifyScreen`: non-blocking notifications

## Data Flow

### Tool Invocation Flow

1. **AI Agent** sends MCP tool call via HTTP
2. **FastMCP** deserializes request and validates parameters
3. **Server** routes to appropriate tool function
4. **Tool Function** enqueues request to HITLQueue
5. **TUI App** dequeues and displays the appropriate screen
6. **User** provides input in the TUI
7. **TUI Screen** validates and resolves the future
8. **Tool Function** returns result to FastMCP
9. **FastMCP** serializes response
10. **AI Agent** receives result and continues

### Error Handling Flow

```
Tool Function
    ├─> Try: Call UI function
    ├─> Catch KeyboardInterrupt: User cancelled (Ctrl+C)
    │   └─> Raise Exception("User cancelled...") from None
    └─> Catch Exception: Unexpected error
        └─> Raise Exception(f"Operation failed: {e}") from e
```

## Design Patterns

### Async-First Design
All public APIs are async. Tool functions enqueue requests and await futures resolved by the TUI:

```python
async def hitl_collect(...) -> str:
    future: asyncio.Future[str] = asyncio.get_event_loop().create_future()
    await queue.put(CollectRequest(future=future, ...))
    return await future
```

### Queue-Based Serialization
HITLQueue (asyncio.PriorityQueue) serializes concurrent tool calls — only one screen is shown at a time.

### Separation of Concerns
- **Server**: Protocol and business logic
- **TUI**: User interaction and presentation
- **CLI**: Application lifecycle

## Technology Stack

- **FastMCP**: MCP protocol implementation
- **Textual**: Full-featured TUI framework (screens, widgets, key bindings)
- **asyncio**: Asynchronous I/O and queue management

## Extension Points

### Adding New Tools

1. Define tool function in `server.py`:
```python
@mcp.tool()
async def new_tool(param: str) -> str:
    future = asyncio.get_event_loop().create_future()
    await queue.put(NewToolRequest(future=future, param=param))
    return await future
```

2. Add a Textual screen in `tui/screens.py`

3. Add tests in `tests/test_server.py`

### Adding Transports

FastMCP supports multiple transports:
- `streamable-http` (default)
- `stdio` (for subprocess communication)
- `sse` (Server-Sent Events)

Change in `cli.py`:
```python
mcp.run(transport="stdio", ...)
```

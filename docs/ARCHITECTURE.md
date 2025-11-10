# Architecture

## Overview

HITL MCP CLI is built as a layered architecture that separates concerns between protocol handling, user interaction, and presentation.

## Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        AI Agent / MCP Client                 │
│                    (Claude, GPT, Custom Agent)               │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP (Streamable-HTTP Transport)
                             │ MCP Protocol (JSON-RPC)
┌────────────────────────────▼────────────────────────────────┐
│                      FastMCP Server Layer                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Tool Registry & Schema Generation                   │   │
│  │  - request_text_input                                │   │
│  │  - request_selection                                 │   │
│  │  - request_confirmation                              │   │
│  │  - request_path_input                                │   │
│  │  - notify_completion                                 │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────┘
                             │ Async Function Calls
┌────────────────────────────▼────────────────────────────────┐
│                        UI Layer                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Prompt Wrappers (prompts.py)                        │   │
│  │  - prompt_text, prompt_select, prompt_checkbox       │   │
│  │  - prompt_confirm, prompt_path                       │   │
│  │  - display_notification                              │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Visual Feedback (feedback.py)                       │   │
│  │  - loading_indicator, show_success, show_error       │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Banner Display (banner.py)                          │   │
│  │  - Startup banner with gradient colors               │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────┘
                             │ Terminal I/O
┌────────────────────────────▼────────────────────────────────┐
│                   Terminal Libraries                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  InquirerPy  │  │     Rich     │  │   asyncio    │      │
│  │  (Prompts)   │  │  (Styling)   │  │  (Async I/O) │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│                           User                               │
│                    (Terminal Interface)                      │
└─────────────────────────────────────────────────────────────┘
```

## Module Structure

### `hitl_mcp_cli/server.py`
**Purpose**: MCP protocol implementation and tool registration

- Defines FastMCP server instance
- Registers 5 interactive tools with schemas
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
- Banner display coordination
- Server lifecycle management
- Graceful shutdown handling

**Key Responsibilities**:
- CLI argument parsing
- Custom banner display
- FastMCP server initialization
- Signal handling (Ctrl+C)

### `hitl_mcp_cli/ui/prompts.py`
**Purpose**: Terminal prompt wrappers

- Wraps InquirerPy for consistent UX
- Adds icons and styling
- Implements validation logic
- Converts sync prompts to async

**Key Responsibilities**:
- Text input with regex validation
- Single/multiple selection
- Yes/no confirmation
- Path input with existence validation
- Notification display

### `hitl_mcp_cli/ui/feedback.py`
**Purpose**: Visual feedback components

- Loading indicators for async operations
- Status messages (success, error, info, warning)
- Consistent styling across feedback types

**Key Responsibilities**:
- Spinner animations
- Status message formatting
- Color-coded feedback

### `hitl_mcp_cli/ui/banner.py`
**Purpose**: Startup banner display

- ASCII art logo
- Gradient color effects
- Fade-in animation
- Server information display

**Key Responsibilities**:
- Banner generation
- Animation control
- Server info formatting

## Data Flow

### Tool Invocation Flow

1. **AI Agent** sends MCP tool call via HTTP
2. **FastMCP** deserializes request and validates parameters
3. **Server** routes to appropriate tool function
4. **Tool Function** calls UI layer (e.g., `prompt_text`)
5. **UI Layer** displays prompt to user via InquirerPy
6. **User** provides input in terminal
7. **UI Layer** validates and returns result
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
All public APIs are async, even when wrapping synchronous libraries:

```python
@sync_to_async
def prompt_text(...) -> str:
    # Synchronous InquirerPy code
    return inquirer.text(...).execute()
```

### Decorator Pattern
`@sync_to_async` converts blocking I/O to async:

```python
def sync_to_async(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await asyncio.get_event_loop().run_in_executor(
            None, lambda: func(*args, **kwargs)
        )
    return wrapper
```

### Separation of Concerns
- **Server**: Protocol and business logic
- **UI**: User interaction and presentation
- **CLI**: Application lifecycle

### Dependency Injection
UI layer is independent and testable:

```python
# Server imports UI functions
from .ui import prompt_text, display_notification

# UI doesn't know about server
```

## Technology Stack

- **FastMCP**: MCP protocol implementation
- **InquirerPy**: Interactive terminal prompts
- **Rich**: Terminal styling and formatting
- **asyncio**: Asynchronous I/O

## Extension Points

### Adding New Tools

1. Define tool function in `server.py`:
```python
@mcp.tool()
async def new_tool(param: str) -> str:
    result = await ui_function(param)
    return result
```

2. Add UI function in `ui/prompts.py`:
```python
@sync_to_async
def ui_function(param: str) -> str:
    # Implementation
    return result
```

3. Add tests in `tests/test_server.py`

### Customizing UI

Modify `ui/prompts.py` to change:
- Icons (ICONS dictionary)
- Colors (style parameters)
- Validation logic
- Prompt formatting

### Adding Transports

FastMCP supports multiple transports:
- `streamable-http` (default)
- `stdio` (for subprocess communication)
- `sse` (Server-Sent Events)

Change in `cli.py`:
```python
mcp.run(transport="stdio", ...)
```

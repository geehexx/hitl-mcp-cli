# HITL MCP CLI - Comprehensive Architecture Analysis

**Project**: Human-in-the-Loop MCP Server for Interactive AI Agent Workflows
**Version**: 0.4.0
**Python**: 3.11+
**Key Dependencies**: FastMCP 2.13.0+, InquirerPy 0.3.4+, Rich 13.0.0+

---

## 1. OVERALL ARCHITECTURE

### High-Level Overview
HITL MCP CLI implements a **layered, event-driven architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────┐
│ AI Agents / MCP Clients (Claude, GPT, Custom Agents)   │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTP (Streamable-HTTP Protocol)
                      │ MCP JSON-RPC Messages
┌─────────────────────▼───────────────────────────────────┐
│ FastMCP Server Layer (server.py)                        │
│ - Tool Registration & Schema Generation                 │
│ - MCP Protocol Handler                                  │
│ - Async Tool Execution                                  │
└─────────────────────┬───────────────────────────────────┘
                      │ Async Function Calls
┌─────────────────────▼───────────────────────────────────┐
│ UI/Interaction Layer (ui/)                              │
│ - Prompt Wrappers (prompts.py)                          │
│ - Visual Feedback (feedback.py)                         │
│ - Banner Display (banner.py)                            │
└─────────────────────┬───────────────────────────────────┘
                      │ Terminal I/O (blocking)
┌─────────────────────▼───────────────────────────────────┐
│ Terminal Libraries                                       │
│ - InquirerPy (Interactive Prompts)                      │
│ - Rich (Terminal Styling & Formatting)                  │
│ - asyncio (Async I/O Management)                        │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│ Terminal Interface (Human)                              │
└─────────────────────────────────────────────────────────┘
```

### Key Architectural Principles

1. **Async-First Design**: All public APIs are async despite wrapping synchronous libraries
2. **Clean Separation of Concerns**: Server, UI, CLI layers are decoupled
3. **Dependency Injection**: UI layer is independent and testable
4. **Stateless Tool Execution**: Each tool call is independent; no inter-tool state
5. **Error Propagation**: Clear exception handling from terminal to MCP protocol
6. **Minimal Global State**: Only separator tracking uses globals (acknowledged limitation)

---

## 2. MCP SERVER IMPLEMENTATION

### Server Initialization (server.py)

**Entry Point**: `from hitl_mcp_cli.server import mcp`

```python
mcp = FastMCP(
    name="Interactive Input Server",
    instructions="[Tool usage guidelines and best practices]"
)
```

**Protocol**: 
- Transport: `streamable-http` (default, also supports `stdio`, `sse`)
- Method: HTTP streaming with JSON-RPC 2.0
- Host: 127.0.0.1 (default, configurable)
- Port: 5555 (default, configurable)
- Endpoint: `http://127.0.0.1:5555/mcp`

**Configuration via Environment Variables**:
- `HITL_HOST`: Server bind address
- `HITL_PORT`: Server port
- `HITL_LOG_LEVEL`: DEBUG/INFO/WARNING/ERROR
- `HITL_NO_BANNER`: Suppress startup banner

### Tool Registration Pattern

FastMCP uses Python decorators for tool registration:

```python
@mcp.tool()
async def tool_name(param1: type1, param2: type2 = default) -> return_type:
    """Tool description for MCP schema."""
    result = await ui_function(param1, param2)
    return result
```

**Key Features**:
- Type hints automatically generate JSON schemas
- Docstrings become tool descriptions
- Async functions integrate with asyncio event loop
- Parameter defaults shown in MCP client UIs

### MCP Protocol Flow

```
1. Client → Server: Initialize Request
   ├─ Client capability negotiation
   └─ Server responds with: name, version, capabilities

2. Client → Server: Tools/List Request
   ├─ Server generates schemas from Python type hints
   └─ Returns 5 tools with full specifications

3. Client → Server: Tool Call (JSON-RPC)
   ├─ Parameters validated by FastMCP
   ├─ Tool function executed asynchronously
   ├─ Result serialized to JSON
   └─ Response sent via HTTP stream

4. Error Handling:
   ├─ KeyboardInterrupt → "User cancelled" error
   ├─ RuntimeError → "Operation failed" error
   └─ MCP wraps errors in standardized error format
```

### Error Handling Strategy

All tools wrap their UI layer calls with try-catch:

```python
try:
    result = await ui_function(...)
    return result
except KeyboardInterrupt:
    raise Exception("User cancelled input (Ctrl+C)") from None
except Exception as e:
    raise Exception(f"Operation failed: {str(e)}") from e
```

**Error Types**:
- KeyboardInterrupt: User explicitly cancelled (Ctrl+C)
- Validation Errors: Invalid input format (regex pattern)
- RuntimeError: Unexpected exceptions during UI interaction

---

## 3. TOOLS/RESOURCES EXPOSED

### 5 Core Tools

#### 1. `request_text_input`
**Purpose**: Collect free-form text input with optional validation

**Parameters**:
- `prompt` (str, required): Question to display
- `default` (str, optional): Pre-filled value
- `multiline` (bool, default: False): Enable multi-line input
- `validate_pattern` (str, optional): Regex pattern for validation

**Return**: str (validated user input)

**Use Cases**:
- Project names, descriptions, API keys
- Configuration values with format validation
- Comments and notes

**Validation**: Regex-based with ReDoS protection warnings

#### 2. `request_selection`
**Purpose**: Present enumerable choices for single or multiple selection

**Parameters**:
- `prompt` (str, required): Selection question
- `choices` (list[str], required): Available options
- `default` (str, optional): Pre-selected choice
- `allow_multiple` (bool, default: False): Checkbox mode

**Return**: str (single choice) or list[str] (multiple)

**Features**:
- Automatically enables fuzzy search for lists > 15 items
- Max display height 70% of terminal
- Keyboard navigation (arrow keys, space, enter)

**Use Cases**:
- Environment selection (Dev/Staging/Prod)
- Feature enablement
- Implementation approach choice
- Multi-select for bulk operations

#### 3. `request_confirmation`
**Purpose**: Binary yes/no approval before proceeding

**Parameters**:
- `prompt` (str, required): Yes/no question
- `default` (bool, default: False): Safe default (False for destructive ops)

**Return**: bool

**Best Practices**:
- Always set `default=False` for destructive operations
- Clearly explain consequences in prompt
- Use with expensive/irreversible operations

**Use Cases**:
- Delete confirmation
- Breaking change approval
- Expensive API call confirmation

#### 4. `request_path_input`
**Purpose**: Collect file/directory paths with validation

**Parameters**:
- `prompt` (str, required): Path request
- `path_type` (Literal["file", "directory", "any"], default: "any")
- `must_exist` (bool, default: False): Validate path exists
- `default` (str, optional): Pre-filled path

**Return**: str (absolute, resolved path)

**Features**:
- Tab completion for paths
- Path expansion (~, ., ..)
- Path validation via PathValidator
- Returns absolute paths

**Use Cases**:
- Configuration file selection
- Output directory specification
- Input file location
- Log file paths

#### 5. `notify_completion`
**Purpose**: Display styled notifications to user

**Parameters**:
- `title` (str, required): Notification title
- `message` (str, required): Detailed message (supports \n)
- `notification_type` (Literal["success", "info", "warning", "error"], default: "info")

**Return**: dict[str, bool] ({"acknowledged": True})

**Styling**:
- success: Green icon (✅) and text
- info: Blue icon (ℹ️) and text
- warning: Yellow icon (⚠️) and text
- error: Red icon (❌) and text

**Use Cases**:
- Operation completion confirmation
- Milestone notifications
- Status updates
- Error/warning alerts

### Tool Characteristics Summary

| Tool | Type | Blocking | Returns | Typical Timeout |
|------|------|----------|---------|-----------------|
| request_text_input | Interactive | Yes | string | ∞ |
| request_selection | Interactive | Yes | string/list | ∞ |
| request_confirmation | Interactive | Yes | boolean | ∞ |
| request_path_input | Interactive | Yes | string | ∞ |
| notify_completion | Notification | No | dict | < 1s |

**Critical Configuration**: All HITL MCP clients MUST set `"timeout": 0` (infinite) because human response time is unpredictable.

---

## 4. COMMUNICATION PATTERNS & MESSAGE HANDLING

### Message Flow Architecture

```
MCP Client Request → FastMCP Deserializer → Tool Function → UI Layer → Terminal
                                                    ↑
                                                    |
                                        Async event loop
                                        (asyncio.run_in_executor)
                                                    |
                                            sync_to_async Wrapper
                                                    |
                                            InquirerPy Call
                                            (blocks executor)
                                                    |
                                            User Input
                                            (terminal I/O)
                                                    |
                                                    ↓
            ← FastMCP Serializer ← Tool Function Returns ← UI Returns ← Terminal
```

### Request-Response Cycle (Detailed)

1. **Initialization Handshake**:
   ```
   Client → {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {...}}
   Server → {"jsonrpc": "2.0", "id": 1, "result": {"serverInfo": {...}, "capabilities": {...}}}
   ```

2. **Tool Discovery**:
   ```
   Client → {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
   Server → {"jsonrpc": "2.0", "id": 2, "result": {"tools": [...]}}
   ```

3. **Tool Execution**:
   ```
   Client → {"jsonrpc": "2.0", "id": 3, "method": "tools/call", 
             "params": {"name": "request_text_input", "arguments": {...}}}
   
   Server (async):
   ├─ Validate parameters against schema
   ├─ Call: tool_function(args)
   ├─ Await result from UI layer
   └─ Serialize result
   
   Server → {"jsonrpc": "2.0", "id": 3, "result": {"content": [{"type": "text", "text": "..."}]}}
   ```

4. **Error Response**:
   ```
   Server → {"jsonrpc": "2.0", "id": 3, "error": {"code": -32603, "message": "User cancelled..."}}
   ```

### Async-to-Sync Bridge

**Problem**: InquirerPy is synchronous, but MCP tools must be async

**Solution**: `sync_to_async` decorator

```python
def sync_to_async(func: Callable) -> Callable:
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Run blocking function in thread pool executor
        return await asyncio.get_event_loop().run_in_executor(
            None, lambda: func(*args, **kwargs)
        )
    return wrapper
```

**Benefits**:
- Doesn't block event loop during I/O wait
- Allows concurrent processing if multiple clients connected
- Maintains async interface for MCP

**Limitation**: 
- Uses default thread pool (unlimited size)
- No backpressure on concurrent requests
- Acceptable because human input is naturally rate-limited

### Message Buffering & Streaming

- **Transport**: HTTP streams with chunked transfer encoding
- **Protocol**: JSON-RPC 2.0 over HTTP
- **Buffer Strategy**: No explicit buffering; each request/response is atomic
- **Concurrency**: Each client connection is independent

### Terminal I/O Coordination

**Global State Management**:
```python
# File: hitl_mcp_cli/ui/prompts.py
_needs_separator = False  # Track whether to print visual separator
```

**Known Issue** (documented in FUTURE.md):
- Not thread-safe for concurrent tool calls
- Acceptable because HITL prompts are typically sequential
- Future: Replace with request-scoped state

**Separator Logic**:
```python
if _needs_separator:
    console.print(Rule(style="dim"))  # Visual divider
    _needs_separator = False

# ... prompt execution ...

_needs_separator = True  # Mark for next prompt
```

---

## 5. SESSION & STATE MANAGEMENT

### Current State Architecture

**CRITICAL FINDING**: The system is **stateless by design**.

- **No Session Concept**: Each tool call is independent
- **No Context Persistence**: No cross-tool state storage
- **No Request Correlation**: Tool calls aren't linked or traced
- **Minimal Global State**: Only visual separator state

### State Scope Analysis

| State Type | Scope | Location | Persistence |
|-----------|-------|----------|-------------|
| Separator tracking | Global | prompts.py line 25 | In-memory, reset on each prompt |
| Tool schemas | Server | FastMCP internal | Generated at startup |
| Event loop | Global | asyncio | Runtime duration |
| Console | Global | Rich | Runtime duration |

### Lack of Session Management - Implications

**Advantages**:
- Simple, testable architecture
- No session cleanup needed
- Scales naturally with multiple clients
- No session hijacking vulnerabilities

**Disadvantages** (for multi-agent scenarios):
- No way to correlate related tool calls
- No shared context across requests
- No request history/audit trail
- No way to enforce sequential tool ordering
- No distributed transaction support

### Acknowledgments in Documentation

From FUTURE.md:

> **Visual Separator State Management - Known Limitation 2025-11-10**
> 
> Problem: Visual separators use global state (`_needs_separator`) which is not thread-safe for concurrent tool calls.
>
> Current Behavior:
> - Works correctly for sequential prompts (typical HITL usage)
> - May show inconsistent separators if multiple prompts execute concurrently
> 
> Proper Solution:
> - Replace global state with request-scoped state (passed as parameter)
> - Use context manager for separator state
> - Or use thread-local storage with proper synchronization

---

## 6. FILE STRUCTURE & KEY MODULES

### Complete File Structure

```
hitl-mcp-cli/
├── hitl_mcp_cli/                          # Main package
│   ├── __init__.py                        # Version: 0.2.0 (note: mismatch with 0.4.0)
│   ├── cli.py                             # Entry point, argument parsing, server startup
│   ├── server.py                          # FastMCP server, tool definitions
│   └── ui/                                # User interaction layer
│       ├── __init__.py                    # Module exports
│       ├── banner.py                      # Startup ASCII banner with gradients
│       ├── feedback.py                    # Status messages, loading indicators
│       └── prompts.py                     # Interactive prompt wrappers
├── tests/                                 # Comprehensive test suite
│   ├── test_server.py                     # MCP protocol tests
│   ├── test_mcp_integration.py           # Full MCP flow tests (no mocking)
│   ├── test_ui.py                        # UI component tests
│   ├── test_cli.py                       # CLI integration tests
│   ├── test_prompts.py                   # Prompt wrapper tests
│   ├── test_feedback.py                  # Feedback component tests
│   ├── test_error_handling.py            # Error scenarios
│   ├── test_timeout_handling.py          # Timeout behavior
│   ├── test_edge_cases.py                # Edge cases
│   ├── test_fuzzy_search.py              # Fuzzy search for long lists
│   ├── test_multiline_terminal.py        # Multiline input
│   ├── test_selection_regression.py      # Selection widget regression
│   └── test_cli_integration.py           # Full CLI tests
├── docs/                                  # Documentation
│   ├── ARCHITECTURE.md                    # System design (excellent reference)
│   ├── FUTURE.md                          # Enhancement ideas and limitations
│   ├── ACCESSIBILITY.md                   # Accessibility features
│   └── TESTING.md                         # Testing guide
├── pyproject.toml                         # Python package metadata
├── README.md                              # User documentation (comprehensive)
├── CHANGELOG.md                           # Version history
├── example.py                             # Usage example
└── test_enhancements.py                   # Enhancement test script
```

### Key Modules Deep Dive

#### 1. `cli.py` (Entry Point)
**Lines**: 90
**Responsibility**: Application lifecycle management

**Key Functions**:
```python
def main() -> None:
    # Parse CLI arguments (--host, --port, --no-banner)
    # Display startup banner
    # Initialize FastMCP server
    # Run event loop until Ctrl+C
    # Handle graceful shutdown
```

**Configuration Sources** (Priority):
1. CLI arguments (highest)
2. Environment variables
3. Hardcoded defaults (lowest)

**Key Code**:
- Lines 21-24: Environment variable defaults
- Lines 26-38: Argument parser definition
- Lines 72-79: FastMCP.run() configuration
- Lines 80-85: Exception handling

**Dependencies**:
- argparse: CLI argument parsing
- logging: Application logging
- FastMCP: Server initialization
- UI layer: Banner display

#### 2. `server.py` (MCP Server & Tools)
**Lines**: 271
**Responsibility**: Tool registration, MCP protocol handling

**Key Objects**:
```python
mcp = FastMCP(...)  # Server instance (singleton)
```

**Tool Functions** (all async):
1. `request_text_input` (lines 101-133)
2. `request_selection` (lines 136-170)
3. `request_confirmation` (lines 173-201)
4. `request_path_input` (lines 204-239)
5. `notify_completion` (lines 242-270)

**Error Handling Pattern** (consistent across all):
```python
try:
    result = await ui_function(...)
    return result
except KeyboardInterrupt:
    raise Exception("User cancelled...") from None
except Exception as e:
    raise Exception(f"Operation failed: ...") from e
```

**Key Code Sections**:
- Lines 9-98: Server initialization and comprehensive instructions
- Lines 101-270: Tool definitions with docstrings and type hints

**Dependencies**:
- FastMCP: Decorator and server instance
- UI functions: All UI layer imports

#### 3. `ui/prompts.py` (Prompt Wrappers)
**Lines**: 287
**Responsibility**: Terminal prompts with consistent styling

**Global State**:
```python
console = Console()          # Rich console instance
_needs_separator = False     # Visual separator tracking
ICONS = {...}              # Emoji icons for each prompt type
```

**Key Functions**:
1. `sync_to_async` decorator (lines 41-48): Converts sync to async
2. `prompt_text` (lines 51-110): Text input with validation
3. `prompt_select` (lines 113-146): Single selection with fuzzy search
4. `prompt_checkbox` (lines 149-173): Multiple selection
5. `prompt_confirm` (lines 176-197): Yes/No confirmation
6. `prompt_path` (lines 200-233): File/directory path input
7. `display_notification` (lines 236-253): Styled notifications
8. Helper functions (lines 255-287): Markdown detection, rendering

**Key Features**:
- All public functions are async (via decorator)
- Markdown support for prompts (lines 255-286)
- Visual separators between prompts (lines 66-69, etc.)
- Fuzzy search for long lists (lines 129-136)
- Path validation with PathValidator (lines 211-218)
- Regex validation for text input (lines 58-64)

**Dependencies**:
- InquirerPy: Interactive prompts
- Rich: Terminal styling, markdown rendering
- asyncio: Async execution
- pathlib: Path handling
- re: Regex validation

#### 4. `ui/feedback.py` (Status Messages)
**Lines**: 77
**Responsibility**: Visual feedback for operations

**Key Functions**:
1. `loading_indicator` (lines 14-28): Context manager with spinner
2. `show_success` (lines 31-40): Green checkmark message
3. `show_error` (lines 43-52): Red X message
4. `show_info` (lines 55-64): Blue info message
5. `show_warning` (lines 67-76): Yellow warning message

**Design**: Simple status output without blocking

**Dependencies**:
- Rich: Spinner and text styling
- contextlib: Context manager protocol

#### 5. `ui/banner.py` (Startup Display)
**Lines**: 61
**Responsibility**: ASCII art banner with gradient colors

**Key Functions**:
1. `create_banner_text` (lines 9-18): ASCII art generation
2. `display_banner` (lines 21-61): Render banner with colors and info

**Design**: Cosmetic but improves user perception

**Dependencies**:
- Rich: Text styling and color gradients

---

## 7. MAIN ENTRY POINTS & SERVER SETUP

### Entry Point Chain

```
1. User: $ hitl-mcp --port 5555
        ↓
2. setup.py entry_point: "hitl-mcp = hitl_mcp_cli.cli:main"
        ↓
3. cli.main()
   ├─ Parse arguments
   ├─ Load environment variables
   ├─ Display banner (if not disabled)
   └─ Call mcp.run()
        ↓
4. FastMCP.run()
   ├─ Bind to host:port
   ├─ Start HTTP server (via Uvicorn)
   ├─ Wait for MCP client connections
   └─ Handle requests in async event loop
        ↓
5. For each client request:
   ├─ Deserialize JSON-RPC message
   ├─ Route to tool function
   ├─ Execute async function
   ├─ Wait for user input (blocking I/O in executor)
   ├─ Serialize result
   └─ Send HTTP response
```

### Server Startup Sequence

**File**: `cli.py`

```python
def main():
    # 1. Parse arguments
    args = parser.parse_args()
    
    # 2. Configure logging
    logging.basicConfig(level=...)
    
    # 3. Display banner
    if not args.no_banner:
        display_banner(args.host, args.port)
    
    # 4. Configure Uvicorn logging
    uvicorn_config = {
        "log_config": {...}  # Disable access logs in production
    }
    
    # 5. Run server
    mcp.run(
        transport="streamable-http",
        host=args.host,
        port=args.port,
        show_banner=False,  # Custom banner instead
        log_level=uvicorn_log_level,
        uvicorn_config=uvicorn_config
    )
    
    # 6. Graceful shutdown (Ctrl+C)
    except KeyboardInterrupt:
        print("Server stopped by user")
```

### Server Configuration

**Environment Variables** (cli.py lines 21-24):
```python
HITL_HOST="127.0.0.1"      # Bind address
HITL_PORT="5555"            # Listen port
HITL_LOG_LEVEL="ERROR"      # Logging level
HITL_NO_BANNER="false"      # Banner display
```

**CLI Arguments**:
```
--host ADDR       Server bind address (default: 127.0.0.1)
--port PORT       Server port (default: 5555)
--no-banner       Disable startup banner
```

**Uvicorn Configuration**:
```python
# Disable access logs unless DEBUG level
if log_level != "DEBUG":
    log_config["loggers"]["uvicorn.access"] = {"level": "CRITICAL"}
```

---

## 8. TOOL IMPLEMENTATIONS & PATTERNS

### Tool Implementation Template

All 5 tools follow the same pattern:

```python
@mcp.tool()
async def tool_name(
    required_param: str,
    optional_param: str | None = None,
) -> return_type:
    """Short description for MCP schema.
    
    Detailed docstring explaining usage, parameters, return value.
    
    Args:
        required_param: What this does
        optional_param: What this does
    
    Returns:
        What is returned
    
    Example:
        result = await tool_name("value")
    """
    try:
        # Call UI layer function
        result: return_type = await ui_function(required_param, optional_param)
        return result
    except KeyboardInterrupt:
        # User cancelled (Ctrl+C)
        raise Exception("User cancelled...") from None
    except Exception as e:
        # Other errors
        raise Exception(f"Operation failed: {str(e)}") from e
```

### Type Hint to Schema Conversion

FastMCP automatically converts Python type hints to JSON Schema:

```python
# Python type hint
async def request_selection(
    prompt: str,
    choices: list[str],
    default: str | None = None,
    allow_multiple: bool = False
) -> str | list[str]:
    ...

# Becomes JSON Schema
{
  "name": "request_selection",
  "description": "...",
  "inputSchema": {
    "type": "object",
    "properties": {
      "prompt": {"type": "string"},
      "choices": {"type": "array", "items": {"type": "string"}},
      "default": {"type": ["string", "null"]},
      "allow_multiple": {"type": "boolean"}
    },
    "required": ["prompt", "choices"]
  }
}
```

### Tool-to-UI Mapping

```python
# In server.py:
@mcp.tool()
async def request_text_input(...):
    result = await prompt_text(...)  # ← imports from ui.prompts

# In ui/__init__.py:
from .prompts import prompt_text

# In ui/prompts.py:
@sync_to_async
def prompt_text(...) -> str:
    # Synchronous InquirerPy call
    return inquirer.text(...).execute()
```

### Validation Patterns

**Text Input Validation** (prompts.py lines 58-64):
```python
def validator(text: str) -> bool:
    if validate_pattern:
        try:
            return bool(re.match(validate_pattern, text))
        except re.error:
            return False
    return True

# Used in prompt:
inquirer.text(validate=validator, ...)
```

**Path Validation** (prompts.py lines 211-218):
```python
if must_exist:
    if path_type == "file":
        validator = PathValidator(is_file=True, message="...")
    elif path_type == "directory":
        validator = PathValidator(is_dir=True, message="...")
    else:
        validator = PathValidator(message="...")

inquirer.filepath(validate=validator, ...)
```

### Error Handling Patterns

**Consistent Error Wrapping** (all tools):
```python
try:
    result = await ui_function(...)
    return result
except KeyboardInterrupt:
    raise Exception("User cancelled input (Ctrl+C)") from None
except Exception as e:
    raise Exception(f"[Operation] failed: {str(e)}") from e
```

**Exception Types**:
1. KeyboardInterrupt: User pressed Ctrl+C (handled specially)
2. Validation Errors: Input doesn't match pattern/constraints
3. IO Errors: Terminal/console issues
4. Generic Exception: Catch-all for unexpected errors

---

## 9. MESSAGE HANDLING ARCHITECTURE

### Request Processing Pipeline

```
HTTP Request (JSON-RPC)
        ↓
FastMCP Deserializer
        ↓
Route to Tool Function
        ↓
Parameter Validation (via FastMCP)
        ↓
Tool Execution (async)
  ├─ Try: Call UI function
  ├─ Await: Async I/O in executor
  └─ Catch: Exception handling
        ↓
Result Serialization (via FastMCP)
        ↓
HTTP Response (JSON-RPC)
```

### Message Format Examples

**Initialize Request** (MCP standard):
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {...},
    "clientInfo": {"name": "Claude Desktop"}
  }
}
```

**Initialize Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "serverInfo": {
      "name": "Interactive Input Server",
      "version": "0.4.0"
    },
    "capabilities": {
      "tools": {}
    },
    "protocolVersion": "2024-11-05"
  }
}
```

**Tool Call Request**:
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "request_text_input",
    "arguments": {
      "prompt": "What is your name?",
      "default": "User",
      "multiline": false,
      "validate_pattern": null
    }
  }
}
```

**Tool Result Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "John Doe"
      }
    ]
  }
}
```

**Error Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "error": {
    "code": -32603,
    "message": "User cancelled input (Ctrl+C)"
  }
}
```

### Concurrent Request Handling

**Current Behavior**:
- Each request runs in a separate async context
- UI I/O runs in thread pool executor
- Multiple clients can have concurrent requests

**Limitation**:
- Global separator state not thread-safe
- But acceptable since HITL prompts are typically sequential

**Evidence** (test_mcp_integration.py lines 291-328):
```python
@pytest.mark.asyncio
async def test_multiple_sequential_calls(mcp_client):
    """Test multiple sequential tool calls work correctly."""
    # Successfully tests 3 sequential calls
    # Confirms sequential execution is supported
```

### Timeout Handling

**Critical Configuration**: `"timeout": 0` (infinite)

**Why**:
- Human response time unpredictable (seconds to minutes)
- Default MCP timeout: 60 seconds
- Tool calls fail if user doesn't respond in time
- Infinite timeout allows any response time

**Server-Side**:
- No timeout enforcement in hitl-mcp-cli
- Timeout is entirely client-side responsibility
- Server waits indefinitely for user input

**Implementation** (prompts.py lines 88-106):
```python
# No explicit timeout in prompt functions
result = inquirer.text(
    message=formatted_prompt,
    default=default or "",
    validate=validator,
    raise_keyboard_interrupt=True,
    # ← No timeout parameter
).execute()
```

---

## 10. STATE MANAGEMENT APPROACHES

### State Scope Matrix

| State | Scope | Mutable | Location | Thread-Safe |
|-------|-------|---------|----------|------------|
| Tool schemas | Server | No | FastMCP internal | N/A |
| Separator flag | Global | Yes | prompts.py:25 | No |
| Console instance | Global | No | prompts.py:18 | Yes |
| Event loop | Global | No | asyncio | N/A |
| Tool results | Request | No | Return values | Yes |
| UI state | Function | No | Local variables | Yes |

### Separation State (The Only Global State)

**File**: `hitl_mcp_cli/ui/prompts.py` lines 20-25

```python
console = Console()           # Rich console (thread-safe)
_needs_separator = False      # Global flag (NOT thread-safe)
ICONS = {...}               # Constants
```

**Purpose**: 
- Visual separator between sequential prompts
- Improves readability in long sessions

**Mechanism**:
```python
# Before prompt
if _needs_separator:
    console.print(Rule(style="dim"))
    _needs_separator = False

# [Prompt execution...]

# After prompt
_needs_separator = True
```

**Known Issue** (FUTURE.md lines 27-53):
- Not thread-safe for concurrent tool calls
- Acceptable because:
  - HITL prompts are typically sequential
  - Human response time prevents concurrency
  - Visual artifact (non-critical)

**Future Solution**:
- Replace with request-scoped state
- Pass state as parameter through call chain
- Or use context manager pattern

### No Session State

**Intentional Design**:
- Each tool invocation is independent
- No shared context between tool calls
- No request correlation
- No history/audit trail

**Implications**:
- Tool calls can't reference each other
- No transaction/atomicity guarantees
- No distributed coordination
- **Gap for multi-agent scenarios**

**Why This Design**:
- Simplicity: Easier to test, debug, maintain
- Scalability: Handles multiple concurrent clients naturally
- Security: No cross-request state leakage
- Isolation: Each agent is independent

---

## 11. KEY FILES & PURPOSES

### By Importance

#### Tier 1: Critical (Must Understand)

**`server.py`** (271 lines)
- Entire MCP server definition
- All 5 tools
- Server configuration and metadata
- Error handling patterns

**`cli.py`** (90 lines)
- Application entry point
- Server startup
- Configuration management
- Graceful shutdown

**`ui/prompts.py`** (287 lines)
- All interactive prompts
- Async-to-sync bridge
- Visual styling
- Input validation
- UI state management

#### Tier 2: Important (Should Understand)

**`ui/__init__.py`** (28 lines)
- Module exports
- Clean public API

**`ui/feedback.py`** (77 lines)
- Status messages
- Context managers

**`ui/banner.py`** (61 lines)
- Startup display
- Branding

#### Tier 3: Support (Reference as Needed)

**`pyproject.toml`**
- Dependencies
- Build configuration
- Project metadata
- Tool versions

**`README.md`**
- User documentation
- Integration examples
- Configuration guide

**`docs/ARCHITECTURE.md`**
- Design overview
- Module descriptions
- Extension points

---

## 12. EXTENSIBILITY POINTS FOR MULTI-AGENT FEATURES

### Current Extension Points

#### 1. Add New Tool
**File**: `server.py`

```python
@mcp.tool()
async def new_tool(param: str) -> str:
    """Tool description."""
    try:
        result = await new_ui_function(param)
        return result
    except KeyboardInterrupt:
        raise Exception("User cancelled...") from None
    except Exception as e:
        raise Exception(f"Operation failed: {str(e)}") from e
```

Then add corresponding UI function in `ui/prompts.py`

#### 2. Customize UI
**File**: `ui/prompts.py`

- Modify ICONS dictionary (line 27)
- Change color_map in display_notification (line 240)
- Adjust validation logic
- Modify formatting/styling

#### 3. Add Transport
**File**: `cli.py`

```python
mcp.run(
    transport="stdio",  # or "sse" instead of "streamable-http"
    ...
)
```

#### 4. Custom Server Configuration
**File**: `cli.py`

- Add environment variables
- Add CLI arguments
- Customize uvicorn config
- Implement custom logging

### Gaps for Multi-Agent Coordination

**NOT CURRENTLY SUPPORTED**:

1. **Request Correlation**
   - No request ID tracking
   - Can't correlate related tool calls
   - No audit trail

2. **Session Management**
   - No session concept
   - Each call is independent
   - No shared context

3. **Tool Ordering/Sequencing**
   - No way to enforce call ordering
   - No dependency tracking
   - No transaction support

4. **Agent Identification**
   - No way to identify which agent made request
   - No per-agent configuration
   - No role-based access control

5. **State Persistence**
   - No between-request storage
   - No state reconstruction
   - No distributed state

6. **Coordination Primitives**
   - No locks/semaphores
   - No message queues
   - No event broadcasting

---

## 13. CRITICAL INSIGHTS FOR MULTI-AGENT DESIGN

### Current Limitations Relevant to Coordination

1. **Stateless by Design**
   - Advantage: Simple, testable
   - Disadvantage: Can't maintain coordinated state
   - **For Multi-Agent**: Need to add session/context layer

2. **No Request Correlation**
   - Each tool call is isolated
   - No way to link related calls
   - **For Multi-Agent**: Need request ID/trace ID propagation

3. **Single Mutable Global State**
   - `_needs_separator` is not thread-safe
   - Shows that concurrency not considered
   - **For Multi-Agent**: Need proper state management

4. **No Agent Identification**
   - Server can't identify which agent called
   - Can't implement per-agent policies
   - **For Multi-Agent**: Need authentication/identification

5. **Blocking I/O Model**
   - Awaits user input in executor
   - Works for single-agent HITL
   - **For Multi-Agent**: May need async prompts/queues

6. **Global Console Instance**
   - All output goes to same terminal
   - Works for one user
   - **For Multi-Agent**: Need to separate per-agent UI or queue messages

### Design Considerations for Extensions

**Recommended Approach**:
1. Add request ID to all tool calls
2. Implement session storage (in-memory or Redis)
3. Add agent identification/context
4. Create coordination primitives (locks, events, queues)
5. Add request tracking/audit logging
6. Implement distributed state backend

**Do NOT**:
- Modify core tools (maintain compatibility)
- Use additional global state
- Bypass async-to-sync bridge
- Assume sequential execution

---

## 14. TESTING STRUCTURE & PATTERNS

### Test Files Overview

```
tests/
├── test_server.py              # MCP protocol, schema validation
├── test_mcp_integration.py     # Full MCP flow (no mocking terminal I/O)
├── test_cli.py                 # CLI argument parsing
├── test_cli_integration.py     # Full CLI startup
├── test_ui.py                  # UI component unit tests
├── test_prompts.py             # Prompt wrapper tests
├── test_feedback.py            # Feedback message tests
├── test_error_handling.py      # Error scenarios
├── test_timeout_handling.py    # Timeout behavior
├── test_edge_cases.py          # Edge cases (multiline, empty input, etc.)
├── test_fuzzy_search.py        # Fuzzy search for long lists
├── test_multiline_terminal.py  # Multiline input behavior
└── test_selection_regression.py # Selection widget fixes
```

### Test Patterns

**Integration Test Pattern** (test_mcp_integration.py):
```python
@pytest.mark.asyncio
async def test_tool_execution(mcp_client: Client):
    with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock:
        mock.return_value = "Test Response"
        
        result = await mcp_client.call_tool(
            "request_text_input",
            {"prompt": "Enter text:"}
        )
        
        assert result.data == "Test Response"
        assert not result.is_error
```

**Mocking Strategy**:
- Mock UI functions (prompt_text, prompt_select, etc.)
- Don't mock FastMCP or server
- Test full protocol flow
- Verify tool call parameters

**Test Categories**:
1. Protocol compliance (initialize, tools/list)
2. Tool execution (each tool tested)
3. Error handling (KeyboardInterrupt, RuntimeError)
4. Parameter handling (required, optional, defaults)
5. Concurrent requests (multiple sequential calls)

---

## SUMMARY: ARCHITECTURE AT A GLANCE

### Strengths
- Clean layered architecture
- Clear separation of concerns
- Comprehensive test coverage
- Type-safe with full type hints
- Async-first design
- Excellent documentation

### Current Gaps (for Multi-Agent)
- No session/context management
- No request correlation
- No agent identification
- No coordination primitives
- No distributed state
- Minimal global state not thread-safe

### Key Architectural Decisions
1. **Stateless by design**: Each tool call independent
2. **Async-first but sync I/O**: Uses executors for blocking prompts
3. **Single terminal**: All output to same stream
4. **Minimal configuration**: Mostly hardcoded/CLI args
5. **No persistence**: In-memory state only

### For Multi-Agent Coordination Design
- Build session/context layer on top
- Add request ID/correlation
- Implement agent identification
- Create coordination primitives
- Add distributed state backend
- Maintain backward compatibility with core tools


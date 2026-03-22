# 🤝 HITL MCP CLI

**Human-in-the-Loop MCP Server** — Bridge the gap between AI autonomy and human judgment

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io)

```
██╗  ██╗██╗████████╗██╗         ███╗   ███╗ ██████╗██████╗
██║  ██║██║╚══██╔══╝██║         ████╗ ████║██╔════╝██╔══██╗
███████║██║   ██║   ██║         ██╔████╔██║██║     ██████╔╝
██╔══██║██║   ██║   ██║         ██║╚██╔╝██║██║     ██╔═══╝
██║  ██║██║   ██║   ███████╗    ██║ ╚═╝ ██║╚██████╗██║
╚═╝  ╚═╝╚═╝   ╚═╝   ╚══════╝    ╚═╝     ╚═╝ ╚═════╝╚═╝
```

---

## 🎯 Why Human-in-the-Loop?

AI agents are transforming how we work, but they shouldn't operate in isolation. **HITL MCP CLI** enables AI agents to request human input at critical decision points, combining the speed of automation with the wisdom of human judgment.

### The Problem

AI agents face situations where they need human guidance:

- **🤔 Ambiguity**: Requirements aren't always clear-cut
- **⚠️ Risk**: Some operations are too sensitive to automate blindly
- **🎨 Preference**: Multiple valid approaches exist, but humans have context
- **✅ Validation**: Assumptions need confirmation before proceeding

### The Solution

HITL MCP CLI provides a **standardized, elegant interface** for AI agents to request human input without breaking their workflow. Instead of agents making potentially wrong assumptions or halting entirely, they can:

- **Ask clarifying questions** when requirements are ambiguous
- **Request approval** before destructive or sensitive operations
- **Present options** and let humans choose the best approach
- **Confirm assumptions** to ensure alignment with human intent

### Real-World Scenarios

```
🤖 Agent: "I found 3 ways to implement this feature. Which approach do you prefer?"
👤 Human: [Selects Option B: Balanced performance and maintainability]
🤖 Agent: "Implementing Option B..."

🤖 Agent: "I'm about to delete 150 deprecated files. Proceed?"
👤 Human: "Yes, proceed"
🤖 Agent: "Deleted 150 files. ✅ Complete"

🤖 Agent: "Should I deploy to staging or production?"
👤 Human: "Staging first"
🤖 Agent: "Deploying to staging environment..."
```

---

## ✨ Features

- **🎯 5 Interactive Tools**: Collect input, ask questions, choose from options, confirm actions, and send notifications
- **🎨 Beautiful Terminal UI**: Icons, gradients, and smooth animations
- **🚀 Instant Setup**: Works with `uvx` — no installation required
- **🔌 MCP Standard**: Seamless integration with any MCP-compatible AI agent
- **⚡ Lightning Fast**: Async-first design with minimal overhead
- **🛡️ Type-Safe**: Full type hints for reliability and IDE support
- **📊 Interaction Logging**: All tool calls logged to `~/.local/state/hitl-mcp/interactions.jsonl`
- **🌈 Visual Feedback**: Loading indicators and status messages
- **🔧 Customizable**: Disable animations, customize host/port

---

## ⚠️ Critical Configuration

**Timeout Setting Required**: HITL operations require **infinite timeout** because human response time is unpredictable. Without this, tool calls will fail after 60 seconds.

Set `"timeout": 0` in your MCP client configuration (see below).

---

## 🚀 Quick Start

### Installation

```bash
# Run directly without installation (recommended)
uvx hitl-mcp-cli

# Or install globally
uv tool install hitl-mcp-cli
```

### Start the Server

```bash
# Default: TUI mode on localhost:5555
hitl-mcp

# Custom host/port
hitl-mcp --host 0.0.0.0 --port 8080

# Headless mode (CI/scripts, no TUI)
hitl-mcp --no-tui

# Disable banner (headless mode only)
hitl-mcp --no-tui --no-banner

# Using environment variables
export HITL_HOST=0.0.0.0
export HITL_PORT=8080
export HITL_LOG_LEVEL=INFO
export HITL_NO_TUI=true
hitl-mcp
```

**Environment Variables**:
- `HITL_HOST`: Server host (default: 127.0.0.1)
- `HITL_PORT`: Server port (default: 5555)
- `HITL_LOG_LEVEL`: Logging level - DEBUG, INFO, WARNING, ERROR (default: ERROR)
- `HITL_NO_BANNER`: Disable startup banner - true/false (default: false)
- `HITL_NO_TUI`: Disable TUI mode - true/false (default: false)

### Configure Your AI Agent

Add to your MCP client configuration (e.g., Claude Desktop, Cline):

```json
{
  "mcpServers": {
    "hitl": {
      "url": "http://127.0.0.1:5555/mcp",
      "transport": "streamable-http",
      "timeout": 0
    }
  }
}
```

**⚠️ Important**: Set `"timeout": 0` for infinite timeout. Human input is unpredictable - users may take seconds or minutes to respond. The default 60-second MCP timeout will cause tool calls to fail if users don't respond quickly enough.

> **Note**: The server runs in stateless HTTP mode, which is required for MCP clients
> that make independent HTTP requests (including Kiro CLI and most MCP clients).

**That's it!** Your AI agent can now request human input.

---

## 🛠️ Available Tools

### 1. `hitl_collect` — Collect Input

Collect a single input value from the user. Use for text, file paths, or multiline content.

**When to use**:
- Collecting names, descriptions, or free-form input
- Getting file/directory paths with completion
- Requesting multi-line content (code snippets, descriptions)

**Example**:
```python
name = await hitl_collect(
    message="What should we name this project?",
    default="my-project",
    validation_pattern=r"^[a-z0-9-]+$"
)

# Path input
config = await hitl_collect(
    message="Select configuration file:",
    input_type="path"
)

# Multiline input
description = await hitl_collect(
    message="Enter project description:",
    input_type="multiline"
)
```

**Parameters**:
- `message` (str): Question to display
- `input_type` (Literal["text", "path", "multiline"]): Input mode (default: "text")
- `default` (str, optional): Pre-filled value
- `validation_pattern` (str, optional): Regex pattern for validation
- `validation_message` (str, optional): Custom validation error message
- `notes` (str, optional): Freeform context displayed as a dimmed line below the message

---

### 2. `hitl_ask` — Ask a Question

Alias for `hitl_collect`. Use whichever name reads more naturally in your agent's workflow.

---

### 3. `hitl_choose` — Present Choices

Present a list of options for the user to select from. Supports single or multiple selection, fuzzy search for long lists, and rich option descriptions.

**When to use**:
- Choosing between implementation approaches
- Selecting deployment environments
- Picking features to enable

**Example**:
```python
# Simple choices
env = await hitl_choose(
    message="Which environment should I deploy to?",
    choices=["Development", "Staging", "Production"],
    default="Staging"
)

# Rich options with descriptions
approach = await hitl_choose(
    message="Select implementation approach:",
    options=[
        {"value": "fast", "label": "Fast", "description": "Quick but uses more memory"},
        {"value": "safe", "label": "Safe", "description": "Slower but reliable"},
    ]
)

# Multiple selections
features = await hitl_choose(
    message="Which features should I enable?",
    choices=["Authentication", "Caching", "Logging", "Monitoring"],
    multiple=True
)
```

**Parameters**:
- `message` (str): Question to display
- `choices` (list[str], optional): Simple option strings
- `options` (list[dict], optional): Rich options with value/label/description
- `multiple` (bool): Enable checkbox mode (default: False)
- `default` (str, optional): Pre-selected option
- `fuzzy_search` (bool, optional): Force fuzzy search on/off (auto for >15 items)
- `notes` (str, optional): Freeform context displayed as a dimmed line below the message

> **Escape hatch**: In multiple-selection mode, if the user selects all or none of the options, they are offered a free-text input to explain their intent.

---

### 4. `hitl_confirm` — Get Confirmation

Ask the user to confirm or reject an action. Use severity='high' for destructive operations.

**When to use**:
- Before destructive operations (delete, overwrite)
- Before expensive operations (API calls, deployments)
- Confirming assumptions or interpretations

**Example**:
```python
# Standard confirmation
result = await hitl_confirm(
    message="I will delete 50 unused dependencies. Proceed?",
    default=False
)
if result["action"] == "accept":
    ...

# High severity — requires typed "yes"
result = await hitl_confirm(
    message="Delete production database?",
    severity="high",
    context="This will affect 10,000 active users.\nDowntime: ~30 seconds."
)

# Timed confirmation
result = await hitl_confirm(
    message="Deploy to production?",
    severity="high",
    timeout_seconds=300
)
if result.get("timed_out"):
    print("Approval timed out")
```

**Parameters**:
- `message` (str): Yes/no question
- `default` (bool): Default answer (default: False)
- `severity` (Literal["low", "medium", "high"]): Confirmation intensity (default: "medium")
- `context` (str, optional): Additional context displayed in a panel above the prompt
- `timeout_seconds` (int): Seconds to wait, 0 = infinite (default: 0)
- `notes` (str, optional): Freeform context displayed as a dimmed line below the message

**Returns**: `{"action": "accept"|"decline"|"cancel"}`. When `timeout_seconds > 0`, also includes `"timed_out": bool`.

---

### 5. `hitl_notify` — Display Notifications

Display a styled notification to the user. Non-blocking — does not wait for input.

**When to use**:
- Confirming successful operations
- Reporting errors or warnings
- Providing progress updates

**Example**:
```python
await hitl_notify(
    message="Successfully deployed v2.1.0 to production\n\nURL: https://app.example.com",
    level="success",
    title="Deployment Complete"
)

await hitl_notify(
    message="The old API will be removed in v3.0",
    level="warning",
    title="Deprecation Warning"
)
```

**Parameters**:
- `message` (str): Detailed message (supports multi-line)
- `level` (Literal["success", "info", "warning", "error"]): Visual style (default: "info")
- `title` (str, optional): Notification title
- `notes` (str, optional): Freeform context displayed as a dimmed line below the notification

---

## 📖 Usage Patterns

### Pattern 1: Clarification

When requirements are ambiguous, ask specific questions:

```python
approach = await hitl_choose(
    message="I can implement this feature in two ways. Which do you prefer?",
    choices=[
        "Option A: Fast implementation, higher memory usage",
        "Option B: Slower but more memory efficient",
        "Option C: Balanced approach (recommended)"
    ],
    default="Option C: Balanced approach (recommended)"
)
```

### Pattern 2: Approval Gate

Request approval before significant actions:

```python
files_to_delete = find_unused_files()
result = await hitl_confirm(
    message=f"I found {len(files_to_delete)} unused files. Delete them?",
    default=False
)

if result["action"] == "accept":
    delete_files(files_to_delete)
    await hitl_notify(
        message=f"Deleted {len(files_to_delete)} unused files",
        level="success",
        title="Cleanup Complete"
    )
else:
    await hitl_notify(
        message="No files were deleted",
        level="info",
        title="Cancelled"
    )
```

### Pattern 3: Information Gathering

Collect structured data through multiple prompts:

```python
project_name = await hitl_collect(
    message="Project name:",
    validation_pattern=r"^[a-z0-9-]+$"
)

language = await hitl_choose(
    message="Programming language:",
    choices=["Python", "TypeScript", "Go", "Rust"]
)

features = await hitl_choose(
    message="Select features to include:",
    choices=["Testing", "Linting", "CI/CD", "Documentation"],
    multiple=True
)

output_dir = await hitl_collect(
    message="Output directory:",
    input_type="path"
)
```

### Pattern 4: Progressive Disclosure

Start with high-level choices, then drill down:

```python
action = await hitl_choose(
    message="What would you like to do?",
    choices=["Deploy", "Rollback", "View Logs", "Run Tests"]
)

if action == "Deploy":
    env = await hitl_choose(
        message="Deploy to which environment?",
        choices=["Staging", "Production"]
    )

    if env == "Production":
        result = await hitl_confirm(
            message="Deploy to PRODUCTION?",
            context="This will affect live users.",
            severity="high"
        )
        if result["action"] == "accept":
            await deploy_to_production()
```

---

## 🏗️ Architecture

```
AI Agent (Claude, GPT, etc.)
         ↓ HTTP (MCP Protocol)
    FastMCP Server
         ↓ Async Calls
      UI Layer (InquirerPy + Rich)
         ↓ Terminal I/O
        User
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture documentation.

---

## 📋 Logs

HITL MCP logs every tool interaction to `~/.local/state/hitl-mcp/interactions.jsonl` as JSONL. Each entry includes tool name, duration, result type, and a preview of the message and result. The log auto-rotates at 10 MB.

A sample logrotate config is provided at [docs/logrotate.conf](docs/logrotate.conf):

```bash
sudo cp docs/logrotate.conf /etc/logrotate.d/hitl-mcp
```

---

## 🧪 Development

### Setup

```bash
git clone https://github.com/geehexx/hitl-mcp-cli.git
cd hitl-mcp-cli
uv sync --all-extras
```

### Testing

```bash
# Run all tests
uv run pytest

# With coverage
uv run pytest --cov --cov-report=html

# Type checking
uv run mypy hitl_mcp_cli/

# Linting
uv run ruff check .
uv run black --check .
```

See [docs/TESTING.md](docs/TESTING.md) for comprehensive testing guide.

### Manual Testing

```bash
# Run example script
uv run python example.py

# Test with FastMCP dev server
fastmcp dev hitl_mcp_cli/server.py

# Test with MCP Inspector
npx @modelcontextprotocol/inspector hitl-mcp
```

---

## 📚 Documentation

- **[Architecture](docs/ARCHITECTURE.md)**: System design and component details
- **[Testing Guide](docs/TESTING.md)**: Comprehensive testing documentation
- **[Accessibility](docs/ACCESSIBILITY.md)**: Accessibility features and guidelines
- **[Future Enhancements](docs/FUTURE.md)**: Planned improvements and ideas
- **[Changelog](CHANGELOG.md)**: Version history and changes

## ♿ Accessibility

HITL MCP CLI is designed to be accessible:

- **✅ Keyboard-only navigation**: All interactions work without a mouse
- **✅ Non-color visual cues**: Icons distinguish prompt types independent of color
- **✅ Color blindness support**: Icons ensure users with color vision deficiencies can use all features
- **✅ Fuzzy search**: Long choice lists (>15 items) automatically enable search filtering
- **✅ Terminal compatibility**: Works with screen readers through terminal emulators

See [docs/ACCESSIBILITY.md](docs/ACCESSIBILITY.md) for detailed accessibility information, testing methodology, and recommendations for users with diverse needs.

---

## 💻 VS Code Terminal

For the best experience in VS Code's integrated terminal, add to your `settings.json`:

```json
{
  "terminal.integrated.allowChords": false,
  "terminal.integrated.sendKeybindingsToShell": true
}
```

This ensures `Ctrl+\` (command palette) and other key bindings reach the TUI.

> **Note**: `ctrl+b` and `ctrl+\` may be intercepted by VS Code. Add these to `commandsToSkipShell` in your VS Code settings, or use `f2` (log level) and `f3` (toggle sessions) as alternatives.

### Key bindings

| Key | Action |
|-----|--------|
| `q` | Quit |
| `ctrl+l` | Clear activity log |
| `ctrl+b` | Toggle sessions panel |
| `f2` | Cycle log level (DEBUG/INFO/WARNING/ERROR) |
| `f3` | Toggle sessions panel (VS Code-safe alternative) |
| `ctrl+\` | Command palette |
| `escape` | Cancel/close dialog |

---

## 🔧 Troubleshooting

### Tool Calls Timeout After 60 Seconds

**Problem**: Tools fail with "Request timed out" error when user takes longer than 60 seconds to respond.

**Solution**: Set `"timeout": 0` in your MCP client configuration:

```json
{
  "mcpServers": {
    "hitl": {
      "url": "http://127.0.0.1:5555/mcp",
      "transport": "streamable-http",
      "timeout": 0
    }
  }
}
```

**Why**: The MCP protocol has a default 60-second timeout. Human input is unpredictable - users may need minutes to make decisions. Setting timeout to 0 means infinite wait.

### Server Won't Start

**Problem**: Port already in use.

**Solution**: Either stop the other process using port 5555, or start the server on a different port:

```bash
hitl-mcp --port 8080
```

Don't forget to update your MCP client configuration to match the new port.

### Tools Not Appearing in Agent

**Problem**: Agent doesn't see the HITL tools.

**Solution**:
1. Verify the server is running (`hitl-mcp` should show startup banner)
2. Check your MCP client configuration file location
3. Restart your MCP client (e.g., Claude Desktop) after configuration changes
4. Verify the URL matches: `http://127.0.0.1:5555/mcp`

### GET /mcp Returns 400 Bad Request

**Problem**: Seeing `"GET /mcp HTTP/1.1" 400 Bad Request` in logs.

**Solution**: This is **expected behavior**. The MCP endpoint only accepts POST requests with JSON-RPC messages. GET requests are not part of the MCP protocol and will return 400. This typically happens when:
- A browser tries to access the endpoint
- A health check system uses GET instead of POST
- An agent incorrectly probes the endpoint

If you need a health check endpoint, this is tracked in docs/FUTURE.md as a future enhancement.

### Verbose Server Logs

**Problem**: Too many INFO logs from uvicorn ("Started server process", "Waiting for application startup", etc.)

**Solution**: The default log level is ERROR, which suppresses these messages. If you're seeing them:
1. Check if `HITL_LOG_LEVEL` environment variable is set to INFO or DEBUG
2. Access logs only appear when `HITL_LOG_LEVEL=DEBUG`
3. To completely silence the server: `HITL_LOG_LEVEL=ERROR hitl-mcp --no-banner`

### Multiline Text Input Clears Terminal

**Problem**: Terminal screen clears after submitting multiline text with Esc+Enter.

**Solution**: This has been fixed in v0.4.0. The multiline input now preserves screen content by:
- Using explicit keybindings for Esc+Enter
- Adding a newline after input to prevent terminal clearing

If you're still experiencing this issue, ensure you're running the latest version:
```bash
uvx hitl-mcp-cli@latest
# or
uv tool upgrade hitl-mcp-cli
```

### Connection Errors or Timeouts

**Problem**: Tool calls fail with connection errors or timeout errors.

**Solution**:
1. **Verify server is running**: Check that `hitl-mcp` is running and accessible
2. **Check network connectivity**: Ensure the MCP client can reach the server URL
3. **Verify timeout configuration**: Ensure `"timeout": 0` is set in MCP client config
4. **Check firewall settings**: Ensure port 5555 (or your custom port) is not blocked

**For AI Agents**: If you encounter timeout or connection errors:
- The error indicates a configuration or network issue, not a user cancellation
- Check the troubleshooting section above
- Inform the user about the error and suggest checking server status
- Do not retry indefinitely - after 2-3 failures, report the issue to the user

### Error Handling Best Practices

**For AI Agent Developers**:

When integrating HITL MCP tools, handle errors appropriately:

```python
try:
    result = await hitl_collect(message="Enter value:")
except Exception as e:
    if "User cancelled" in str(e):
        # User pressed Ctrl+C - respect their decision
        print("Operation cancelled by user")
        return
    elif "timed out" in str(e).lower() or "connection" in str(e).lower():
        # Configuration or network issue
        print("Error: Cannot connect to HITL server")
        print("Please check that hitl-mcp is running and timeout is configured")
        return
    else:
        # Unexpected error
        print(f"Unexpected error: {e}")
        raise
```

> **Note**: `hitl_collect` and `hitl_confirm` return `{"action": "cancel"}` on Ctrl+C instead of raising, so check the return value first.

**Error Categories**:
- **User Cancellation** (Ctrl+C): Respect the cancellation, don't retry
- **Timeout/Connection**: Configuration issue, inform user, don't retry indefinitely
- **Validation Errors**: User input doesn't match requirements, tool will re-prompt automatically
- **Unexpected Errors**: Log and report to user

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Add tests for new functionality
4. Ensure all tests pass (`uv run pytest`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

---

## 📄 License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

Built with:
- [FastMCP](https://github.com/jlowin/fastmcp) - Fast, Pythonic MCP server framework
- [InquirerPy](https://github.com/kazhala/InquirerPy) - Interactive terminal prompts
- [Rich](https://github.com/Textualize/rich) - Beautiful terminal formatting

---

## 💬 Support

- **Issues**: [GitHub Issues](https://github.com/geehexx/hitl-mcp-cli/issues)
- **Discussions**: [GitHub Discussions](https://github.com/geehexx/hitl-mcp-cli/discussions)
- **MCP Community**: [Model Context Protocol](https://modelcontextprotocol.io)

---

<div align="center">

**[⭐ Star this repo](https://github.com/geehexx/hitl-mcp-cli)** if you find it useful!

Made with ❤️ for the AI agent community

</div>

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

- **🎯 5 Interactive Tools**: Text input, selection, confirmation, path input, and notifications
- **🎨 Beautiful Terminal UI**: Icons, gradients, and smooth animations
- **🚀 Instant Setup**: Works with `uvx` — no installation required
- **🔌 MCP Standard**: Seamless integration with any MCP-compatible AI agent
- **⚡ Lightning Fast**: Async-first design with minimal overhead
- **🛡️ Type-Safe**: Full type hints for reliability and IDE support
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

# Or use pip
pip install hitl-mcp-cli
```

### Start the Server

```bash
# Default: localhost:5555
hitl-mcp

# Custom host/port
hitl-mcp --host 0.0.0.0 --port 8080

# Disable banner
hitl-mcp --no-banner

# Using environment variables
export HITL_HOST=0.0.0.0
export HITL_PORT=8080
export HITL_LOG_LEVEL=INFO
export HITL_NO_BANNER=true
hitl-mcp
```

**Environment Variables**:
- `HITL_HOST`: Server host (default: 127.0.0.1)
- `HITL_PORT`: Server port (default: 5555)
- `HITL_LOG_LEVEL`: Logging level - DEBUG, INFO, WARNING, ERROR (default: ERROR)
- `HITL_NO_BANNER`: Disable startup banner - true/false (default: false)

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

**That's it!** Your AI agent can now request human input.

---

## 🛠️ Available Tools

### 1. `request_text_input` — Collect Text Input

Get text from the user with optional validation.

**When to use**:
- Collecting names, descriptions, or free-form input
- Getting configuration values
- Requesting API keys or credentials (with validation)

**Example**:
```python
name = await request_text_input(
    prompt="What should we name this project?",
    default="my-project",
    validate_pattern=r"^[a-z0-9-]+$"  # Only lowercase, numbers, hyphens
)
```

**Parameters**:
- `prompt` (str): Question to display
- `default` (str, optional): Pre-filled value
- `multiline` (bool): Enable multi-line input for longer text
- `validate_pattern` (str, optional): Regex pattern for validation

---

### 2. `request_selection` — Present Choices

Let the user choose from predefined options (single or multiple).

**When to use**:
- Choosing between implementation approaches
- Selecting deployment environments
- Picking features to enable
- Configuring options from a known set

**Example**:
```python
# Single choice
env = await request_selection(
    prompt="Which environment should I deploy to?",
    choices=["Development", "Staging", "Production"],
    default="Staging"
)

# Multiple choices
features = await request_selection(
    prompt="Which features should I enable?",
    choices=["Authentication", "Caching", "Logging", "Monitoring"],
    allow_multiple=True
)
```

**Parameters**:
- `prompt` (str): Question to display
- `choices` (list[str]): Available options
- `default` (str, optional): Pre-selected option
- `allow_multiple` (bool): Enable checkbox mode for multiple selections

---

### 3. `request_confirmation` — Get Yes/No Approval

Request explicit approval before proceeding.

**When to use**:
- Before destructive operations (delete, overwrite)
- Before expensive operations (API calls, deployments)
- Confirming assumptions or interpretations
- Validating generated code or configurations

**Example**:
```python
confirmed = await request_confirmation(
    prompt="I will delete 50 unused dependencies. Proceed?",
    default=False  # Default to safe option
)

if confirmed:
    # Proceed with operation
    await delete_dependencies()
    await notify_completion(
        title="Cleanup Complete",
        message="Removed 50 unused dependencies",
        notification_type="success"
    )
```

**Parameters**:
- `prompt` (str): Yes/no question
- `default` (bool): Default answer (use `False` for destructive operations)

---

### 4. `request_path_input` — Get File/Directory Paths

Collect file or directory paths with validation.

**When to use**:
- Selecting configuration files
- Choosing output directories
- Locating input data
- Specifying log file locations

**Example**:
```python
config_path = await request_path_input(
    prompt="Select the configuration file:",
    path_type="file",
    must_exist=True,
    default="./config.yaml"
)

output_dir = await request_path_input(
    prompt="Where should I save the output?",
    path_type="directory",
    must_exist=False,  # Will be created if needed
    default="./output"
)
```

**Parameters**:
- `prompt` (str): Question to display
- `path_type` (Literal["file", "directory", "any"]): Expected path type
- `must_exist` (bool): Validate that path exists
- `default` (str, optional): Pre-filled path

---

### 5. `notify_completion` — Display Status Notifications

Show styled notifications for important events.

**When to use**:
- Confirming successful operations
- Reporting errors or warnings
- Providing progress updates
- Highlighting important information

**Example**:
```python
# Success notification
await notify_completion(
    title="Deployment Complete",
    message="Successfully deployed v2.1.0 to production\n\nURL: https://app.example.com",
    notification_type="success"
)

# Warning notification
await notify_completion(
    title="Deprecation Warning",
    message="The old API will be removed in v3.0",
    notification_type="warning"
)

# Error notification
await notify_completion(
    title="Build Failed",
    message="TypeScript compilation errors found\n\nRun 'npm run type-check' for details",
    notification_type="error"
)
```

**Parameters**:
- `title` (str): Notification title
- `message` (str): Detailed message (supports multi-line)
- `notification_type` (Literal["success", "info", "warning", "error"]): Visual style

---

## 📖 Usage Patterns

### Pattern 1: Clarification

When requirements are ambiguous, ask specific questions:

```python
# Agent encounters ambiguous requirement
approach = await request_selection(
    prompt="I can implement this feature in two ways. Which do you prefer?",
    choices=[
        "Option A: Fast implementation, higher memory usage",
        "Option B: Slower but more memory efficient",
        "Option C: Balanced approach (recommended)"
    ],
    default="Option C: Balanced approach (recommended)"
)

# Proceed with chosen approach
if "Option A" in approach:
    await implement_fast_version()
elif "Option B" in approach:
    await implement_efficient_version()
else:
    await implement_balanced_version()
```

### Pattern 2: Approval Gate

Request approval before significant actions:

```python
# Explain what will happen
files_to_delete = find_unused_files()
confirmed = await request_confirmation(
    prompt=f"I found {len(files_to_delete)} unused files. Delete them?",
    default=False
)

if confirmed:
    delete_files(files_to_delete)
    await notify_completion(
        title="Cleanup Complete",
        message=f"Deleted {len(files_to_delete)} unused files",
        notification_type="success"
    )
else:
    await notify_completion(
        title="Cancelled",
        message="No files were deleted",
        notification_type="info"
    )
```

### Pattern 3: Information Gathering

Collect structured data through multiple prompts:

```python
# Gather project configuration
project_name = await request_text_input(
    prompt="Project name:",
    validate_pattern=r"^[a-z0-9-]+$"
)

language = await request_selection(
    prompt="Programming language:",
    choices=["Python", "TypeScript", "Go", "Rust"]
)

features = await request_selection(
    prompt="Select features to include:",
    choices=["Testing", "Linting", "CI/CD", "Documentation"],
    allow_multiple=True
)

output_dir = await request_path_input(
    prompt="Output directory:",
    path_type="directory",
    must_exist=False
)

# Generate project with collected information
await generate_project(project_name, language, features, output_dir)
```

### Pattern 4: Progressive Disclosure

Start with high-level choices, then drill down:

```python
# High-level choice
action = await request_selection(
    prompt="What would you like to do?",
    choices=["Deploy", "Rollback", "View Logs", "Run Tests"]
)

if action == "Deploy":
    # Drill down for deployment
    env = await request_selection(
        prompt="Deploy to which environment?",
        choices=["Staging", "Production"]
    )

    if env == "Production":
        # Extra confirmation for production
        confirmed = await request_confirmation(
            prompt="Deploy to PRODUCTION? This will affect live users.",
            default=False
        )
        if confirmed:
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
- **[Future Enhancements](docs/FUTURE.md)**: Planned improvements and ideas
- **[Changelog](CHANGELOG.md)**: Version history and changes

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

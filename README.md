# hitl-mcp-cli

**Human-in-the-Loop MCP Server** - Interactive terminal prompts for AI agents via Model Context Protocol.

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## Features

- 🎯 **5 Interactive Tools**: Text input, selection, confirmation, path input, and notifications
- 🎨 **Rich Terminal UI**: Beautiful prompts with InquirerPy and Rich formatting
- 🔌 **MCP Standard**: Streamable-HTTP transport for seamless AI agent integration
- ⚡ **Fast & Lightweight**: Minimal dependencies, async-first design
- 🛡️ **Type-Safe**: Full type hints for IDE support and reliability

## Quick Start

### Installation with uvx (Recommended)

```bash
# Run directly without installation
uvx hitl-mcp-cli

# Or install globally
uv tool install hitl-mcp-cli
```

### Installation with pip

```bash
pip install hitl-mcp-cli
```

### Usage

Start the server:

```bash
# Default: localhost:5555
hitl-mcp

# Custom host/port
hitl-mcp --host 0.0.0.0 --port 8080
```

### Configure Your AI Agent

Add to your MCP client configuration:

```json
{
  "mcpServers": {
    "hitl": {
      "url": "http://127.0.0.1:5555/mcp",
      "transport": "streamable-http"
    }
  }
}
```

## Available Tools

### 1. request_text_input

Prompt user for text input with optional validation.

```python
result = await request_text_input(
    prompt="Enter your name:",
    default="John Doe",
    multiline=False,
    validate_pattern=r"^[A-Za-z\s]+$"
)
```

**Parameters:**
- `prompt` (str): Question to display
- `default` (str, optional): Default value
- `multiline` (bool): Enable multi-line input
- `validate_pattern` (str, optional): Regex validation pattern

### 2. request_selection

Prompt user to select from options (single or multiple).

```python
choice = await request_selection(
    prompt="Choose deployment environment:",
    choices=["Development", "Staging", "Production"],
    default="Development",
    allow_multiple=False
)
```

**Parameters:**
- `prompt` (str): Question to display
- `choices` (list[str]): Available options
- `default` (str, optional): Default selection
- `allow_multiple` (bool): Enable multi-select (checkbox)

### 3. request_confirmation

Prompt user for yes/no confirmation.

```python
confirmed = await request_confirmation(
    prompt="Delete all files?",
    default=False
)
```

**Parameters:**
- `prompt` (str): Yes/no question
- `default` (bool): Default answer

### 4. request_path_input

Prompt user for file/directory path with validation.

```python
path = await request_path_input(
    prompt="Select configuration file:",
    path_type="file",
    must_exist=True,
    default="./config.yaml"
)
```

**Parameters:**
- `prompt` (str): Prompt message
- `path_type` (Literal["file", "directory", "any"]): Expected path type
- `must_exist` (bool): Whether path must exist
- `default` (str, optional): Default path

### 5. notify_completion

Display styled completion notification.

```python
await notify_completion(
    title="Deployment Complete",
    message="Successfully deployed to production",
    notification_type="success"
)
```

**Parameters:**
- `title` (str): Notification title
- `message` (str): Notification message
- `notification_type` (Literal["success", "info", "warning", "error"]): Visual style

## Usage Patterns

### Clarification Pattern

When requirements are ambiguous:

```python
# Ask specific questions
approach = await request_selection(
    prompt="Which approach should I use?",
    choices=["Option A: Fast but risky", "Option B: Slow but safe"],
)

# Proceed with chosen approach
if "Option A" in approach:
    # Fast implementation
    pass
```

### Approval Pattern

Before performing significant actions:

```python
# Explain what you plan to do
confirmed = await request_confirmation(
    prompt="I will delete 100 files. Proceed?",
    default=False
)

if confirmed:
    # Perform action
    await notify_completion(
        title="Complete",
        message="Deleted 100 files",
        notification_type="success"
    )
```

### Information Gathering Pattern

For collecting structured data:

```python
# Collect multiple inputs
name = await request_text_input(prompt="Project name:")
env = await request_selection(
    prompt="Environment:",
    choices=["dev", "staging", "prod"]
)
config_path = await request_path_input(
    prompt="Config file:",
    path_type="file",
    must_exist=True
)
```

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/geehexx/hitl-mcp-cli.git
cd hitl-mcp-cli

# Install with dev dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov
```

### Testing

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov --cov-report=html

# Type checking
uv run mypy hitl_mcp_cli/

# Linting
uv run ruff check .
uv run black --check .
uv run isort --check .
```

### Testing with FastMCP Dev Server

```bash
fastmcp dev hitl_mcp_cli/server.py
```

Opens web UI at http://localhost:5173 for testing tools.

### Testing with MCP Inspector

```bash
npx @modelcontextprotocol/inspector hitl-mcp
```

## Architecture

```
hitl_mcp_cli/
├── __init__.py          # Package initialization
├── server.py            # FastMCP server with tool definitions
├── cli.py               # CLI entry point
└── ui/
    ├── __init__.py
    └── prompts.py       # InquirerPy wrappers
```

## Design Principles

- **Minimal Dependencies**: Only FastMCP, InquirerPy, and Rich
- **Type-Safe**: Full type hints for IDE support
- **Async-First**: All tools are async-compatible
- **Error-Resilient**: Graceful error handling with clear messages
- **Cross-Platform**: Works on Linux, macOS, Windows

## Why Human-in-the-Loop?

AI agents are powerful but sometimes need human guidance:

- **Clarification**: When requirements are ambiguous
- **Approval**: Before destructive or sensitive operations
- **Choice**: When multiple valid approaches exist
- **Validation**: To confirm assumptions and interpretations

This server provides a standardized way for agents to request human input without breaking their workflow.

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Support

- **Issues**: [GitHub Issues](https://github.com/geehexx/hitl-mcp-cli/issues)
- **Discussions**: [GitHub Discussions](https://github.com/geehexx/hitl-mcp-cli/discussions)

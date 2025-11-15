# 🤝 HITL MCP CLI

**Human-in-the-Loop + Multi-Agent Coordination** — Intelligent AI collaboration with human oversight

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

## What is HITL MCP CLI?

Two powerful capabilities in one MCP server:

1. **Human-in-the-Loop**: AI agents request human input at critical decisions
2. **Multi-Agent Coordination**: Multiple AI agents collaborate through secure channels

## Quick Start

```bash
# Install
uvx hitl-mcp-cli

# Run server
hitl-mcp

# With coordination
hitl-mcp --enable-coordination
```

**⚠️ Critical**: Set `"timeout": 0` in MCP client config (humans respond unpredictably)

## Features at a Glance

### 🤝 Human-in-the-Loop
- ✏️  **Text Input** — Get freeform or multi-line input
- 🎯 **Select** — Choose from options (fuzzy search for 15+ items)
- ☑️  **Checkbox** — Multi-select options
- ❓ **Confirm** — Yes/no decisions
- 📁 **Path** — File/directory selection
- 📢 **Notify** — Display rich messages

### 🔄 Multi-Agent Coordination ⭐ NEW
- 📨 **Channels** — Broadcast communication (10,000 msg capacity)
- 🔒 **Distributed Locks** — Resource synchronization (auto-release: 5min)
- 🔐 **Authentication** — API keys with channel permissions
- 🚦 **Rate Limiting** — Token bucket (configurable per agent)
- 💓 **Heartbeat** — Agent liveness monitoring (30s missing, 60s dead)
- 🔏 **Message Signing** — HMAC-SHA256 integrity
- 📊 **Metrics** — Prometheus-compatible
- 🔍 **Tracing** — OpenTelemetry support

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `HITL_HOST` | `127.0.0.1` | Bind address |
| `HITL_PORT` | `5555` | Port number |
| `HITL_LOG_LEVEL` | `ERROR` | Logging verbosity |
| `HITL_NO_BANNER` | `false` | Disable startup banner |
| **Coordination** | | |
| `HITL_ENABLE_COORDINATION` | `false` | Enable multi-agent features |
| `HITL_COORDINATION_AUTH` | `false` | Require authentication |
| `HITL_COORDINATION_RATE_LIMIT` | `true` | Enable rate limiting |
| `HITL_COORDINATION_HEARTBEAT` | `true` | Enable heartbeat monitoring |
| `HITL_OTLP_ENDPOINT` | — | OpenTelemetry endpoint |

## MCP Client Setup

### Claude Desktop (macOS)

```json
{
  "mcpServers": {
    "hitl": {
      "command": "uvx",
      "args": ["hitl-mcp-cli"],
      "timeout": 0
    }
  }
}
```

**Path**: `~/Library/Application Support/Claude/claude_desktop_config.json`

### With Coordination

```json
{
  "mcpServers": {
    "hitl": {
      "command": "uvx",
      "args": ["hitl-mcp-cli", "--enable-coordination"],
      "timeout": 0,
      "env": {
        "HITL_COORDINATION_AUTH": "1"
      }
    }
  }
}
```

## Usage Examples

### Basic HITL

```python
# Agent asks human for input
response = await session.call_tool("prompt_text", {
    "prompt": "What should we name this feature?",
    "default": "awesome-feature"
})

# Agent asks for confirmation
confirmed = await session.call_tool("prompt_confirm", {
    "prompt": "Delete 150 deprecated files?",
    "default": False
})

# Agent presents options
choice = await session.call_tool("prompt_select", {
    "prompt": "Choose deployment target:",
    "choices": ["staging", "production"],
    "default": "staging"
})
```

### Multi-Agent Coordination

```python
# Agent A joins channel and sends task
await session.call_tool("join_coordination_channel", {
    "channel_name": "project-alpha",
    "agent_id": "agent-a",
    "role": "coordinator"
})

await session.call_tool("send_coordination_message", {
    "channel_name": "project-alpha",
    "agent_id": "agent-a",
    "message_type": "task_assign",
    "content": {
        "task_id": "refactor-auth",
        "assigned_to": "agent-b",
        "priority": "high"
    }
})

# Agent B polls for messages
messages = await session.call_tool("poll_coordination_channel", {
    "channel_name": "project-alpha",
    "agent_id": "agent-b",
    "since_message_id": "last-msg-123"
})

# Agent B acquires lock before modifying shared resource
lock = await session.call_tool("acquire_coordination_lock", {
    "lock_name": "file:auth.py",
    "agent_id": "agent-b",
    "timeout_seconds": 30
})

# ... do work ...

await session.call_tool("release_coordination_lock", {
    "lock_id": lock["lock_id"],
    "agent_id": "agent-b"
})
```

## Performance

Production-ready performance (tested with 104 comprehensive tests):

- **Message throughput**: 67,985 msgs/sec
- **Lock acquisition**: 0.01ms average
- **Rate limiter**: 118,209 checks/sec
- **Heartbeat**: 481,550 beats/sec
- **Full stack latency**: 0.06ms average

## Architecture

```
┌─────────────────────────────────────────────┐
│          AI Agent (MCP Client)              │
│    Claude, GPT-4, Gemini, Custom Agent      │
└─────────────────┬───────────────────────────┘
                  │ MCP Protocol (JSON-RPC)
                  │
┌─────────────────▼───────────────────────────┐
│        HITL MCP Server (FastMCP)            │
│                                             │
│  ┌──────────────┐      ┌────────────────┐  │
│  │ HITL Tools   │      │ Coordination   │  │
│  │              │      │    Tools       │  │
│  │ • prompt_*   │      │ • channels     │  │
│  │ • notify     │      │ • locks        │  │
│  └──────┬───────┘      │ • auth         │  │
│         │              │ • heartbeat    │  │
│         │              └────────┬───────┘  │
│         │                       │          │
│         ▼                       ▼          │
│  ┌──────────────────────────────────────┐  │
│  │  Rich Terminal UI + Live Display    │  │
│  └──────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

## Testing

```bash
# Run all tests
pytest

# Run coordination tests
pytest tests/coordination/

# Run performance benchmarks
pytest tests/coordination/test_performance.py -v -s

# Coverage report
pytest --cov=hitl_mcp_cli --cov-report=html
```

**Coverage**: 89% channels, 94% rate-limiting, 92% signing, 90% schema

## Development

```bash
# Clone repository
git clone https://github.com/yourusername/hitl-mcp-cli.git
cd hitl-mcp-cli

# Install dependencies
uv pip install -e ".[dev]"

# Run tests
pytest

# Format code
ruff format .

# Lint
ruff check .
```

## Documentation

- **[Multi-Agent Coordination Guide](docs/MULTI_AGENT_COORDINATION.md)** — Complete coordination system documentation
- **[Architecture](docs/ARCHITECTURE.md)** — Technical architecture details
- **[Testing Guide](docs/TESTING.md)** — Testing strategies and examples
- **[Accessibility](docs/ACCESSIBILITY.md)** — Accessibility features
- **[Contributing](CONTRIBUTING.md)** — Contribution guidelines
- **[Security](SECURITY.md)** — Security policy
- **[Changelog](CHANGELOG.md)** — Version history

## FAQ

**Q: Do I need to install anything?**
A: No! `uvx hitl-mcp-cli` runs without installation.

**Q: What if my agent makes concurrent requests?**
A: Requests are queued automatically and processed sequentially.

**Q: Can agents coordinate without authentication?**
A: Yes. Auth is optional (`HITL_COORDINATION_AUTH=1` to enable).

**Q: How long are messages stored?**
A: In-memory: until channel reaches 10,000 messages (FIFO eviction).

**Q: Does this work with any AI agent?**
A: Yes! Any MCP-compatible client (Claude, custom agents, etc.).

## Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Apache 2.0 — See [LICENSE](LICENSE) for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/hitl-mcp-cli/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/hitl-mcp-cli/discussions)

---

**Made with ❤️ for the AI agent community**

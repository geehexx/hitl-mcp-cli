# MCP Server Configuration for HITL MCP CLI Development

This document explains how to configure MCP servers for development of the HITL MCP CLI project.

## Overview

HITL MCP CLI **IS** an MCP server itself. During development, you may want to:
1. Use this MCP server in Claude Code for interactive development
2. Connect to other MCP servers for enhanced capabilities

## Using HITL MCP CLI as an MCP Server

### 1. Start the Server

```bash
# In one terminal, start the HITL MCP server
hitl-mcp

# Or use development mode
fastmcp dev hitl_mcp_cli/server.py
```

### 2. Configure Claude Code

Add to your Claude Code MCP configuration (usually `~/.config/claude/mcp.json` or similar):

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

**Critical Settings:**
- `timeout: 0` - REQUIRED for HITL operations (infinite timeout)
- `transport: "streamable-http"` - HTTP transport for the server

### 3. Available Tools

Once configured, Claude Code will have access to:
1. `request_text_input` - Collect text from users
2. `request_selection` - Present choices
3. `request_confirmation` - Get yes/no approval
4. `request_path_input` - Get file/directory paths
5. `notify_completion` - Display status notifications

## Recommended MCP Servers for Development

### 1. GitHub MCP Server (Highly Recommended)

**Purpose:** Direct GitHub integration for issues, PRs, and repository management

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "your_github_token_here"
      }
    }
  }
}
```

**Use cases:**
- Create and manage issues
- Create pull requests
- Review code changes
- Access repository metadata

**Setup:**
1. Create GitHub personal access token at https://github.com/settings/tokens
2. Grant `repo` scope for full access
3. Add token to environment or MCP config

### 2. Filesystem MCP Server (Optional)

**Purpose:** Enhanced file system operations

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem"],
      "env": {
        "ALLOWED_DIRECTORIES": "/home/user/hitl-mcp-cli"
      }
    }
  }
}
```

**Use cases:**
- Safe file operations
- Directory management
- File search

### 3. SQLite MCP Server (For Testing)

**Purpose:** Database testing and query validation

```json
{
  "mcpServers": {
    "sqlite": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sqlite"],
      "env": {
        "SQLITE_DB_PATH": "/home/user/hitl-mcp-cli/test.db"
      }
    }
  }
}
```

**Use cases:**
- Test data generation
- Query validation
- Integration testing

## Complete Configuration Example

Here's a complete MCP configuration for HITL MCP CLI development:

```json
{
  "mcpServers": {
    "hitl": {
      "url": "http://127.0.0.1:5555/mcp",
      "transport": "streamable-http",
      "timeout": 0,
      "description": "HITL MCP CLI for human-in-the-loop interactions"
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      },
      "description": "GitHub integration for issues and PRs"
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem"],
      "env": {
        "ALLOWED_DIRECTORIES": "${HOME}/hitl-mcp-cli"
      },
      "description": "Enhanced file system operations"
    }
  }
}
```

## Environment Variables

Create `.envrc` (or `.env`) in your home directory:

```bash
export GITHUB_TOKEN="ghp_your_token_here"
```

**Security Notes:**
- Never commit tokens to git
- Use environment variables for all secrets
- Rotate tokens regularly
- Limit token permissions to minimum required

## Testing MCP Configuration

### 1. Test Server Availability

```bash
# Check if HITL MCP server is running
curl http://127.0.0.1:5555/mcp

# Expected: 400 Bad Request (GET not supported, POST only)
```

### 2. Use MCP Inspector

```bash
# Test all MCP tools interactively
npx @modelcontextprotocol/inspector hitl-mcp
```

### 3. Verify in Claude Code

Ask Claude Code:
```
What MCP tools are available?
```

Expected response should include all HITL tools.

## Development Workflow with MCP

### Interactive Development

1. **Start HITL MCP server** in one terminal
2. **Open Claude Code** in the project directory
3. **Use HITL tools** during development:
   ```
   Claude, before deploying, please confirm with the user
   using request_confirmation
   ```

### Testing New Features

1. **Modify tool code** in `hitl_mcp_cli/server.py`
2. **Restart server** to load changes
3. **Test with MCP Inspector** or Claude Code
4. **Iterate** based on results

### Integration Testing

1. **Start HITL server**
2. **Run integration tests**:
   ```bash
   uv run pytest tests/test_mcp_integration.py -v
   ```

## Troubleshooting

### HITL Server Not Available

```bash
# Check if server is running
ps aux | grep hitl-mcp

# Check if port is in use
netstat -tuln | grep 5555

# Restart server
pkill -f hitl-mcp
hitl-mcp
```

### Timeout Errors

**Problem:** Tools timeout after 60 seconds

**Solution:** Set `timeout: 0` in MCP config

### Tools Not Appearing

**Problem:** Claude Code doesn't see HITL tools

**Solutions:**
1. Verify server is running
2. Check MCP config file location
3. Restart Claude Code
4. Check logs for errors

### GitHub MCP Authentication Failed

**Problem:** GitHub token rejected

**Solutions:**
1. Verify token is valid
2. Check token permissions (needs `repo` scope)
3. Ensure environment variable is set
4. Try regenerating token

## Best Practices

### 1. Development Environment

- Use separate MCP configs for dev/prod
- Test with MCP Inspector before integration
- Keep server logs visible during development
- Use environment variables for configuration

### 2. Security

- Never commit MCP config with tokens
- Use `.envrc` or `.env` for secrets
- Limit token permissions
- Rotate credentials regularly

### 3. Testing

- Test each tool in isolation
- Verify error handling
- Test timeout behavior
- Validate with MCP Inspector

### 4. Documentation

- Document all MCP servers used
- Explain configuration requirements
- Provide setup instructions
- Include troubleshooting tips

## Additional MCP Servers

### Community Servers

Explore the MCP ecosystem at:
- https://modelcontextprotocol.io/servers
- https://github.com/modelcontextprotocol

### Creating Custom MCP Servers

For project-specific needs, consider creating custom MCP servers using FastMCP (like HITL MCP CLI does):

```python
from fastmcp import FastMCP

mcp = FastMCP("custom-server")

@mcp.tool()
async def custom_tool(param: str) -> str:
    """Custom tool description."""
    return result
```

## Resources

- [MCP Protocol Docs](https://modelcontextprotocol.io)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [MCP Specification](https://spec.modelcontextprotocol.io)
- [HITL MCP CLI README](../README.md)

---

*Last updated: 2025-11-15*

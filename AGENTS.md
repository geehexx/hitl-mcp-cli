# AGENTS.md — hitl-mcp-cli Integration Guide

This file describes how to integrate hitl-mcp-cli as an MCP server in AI agent workflows.

## What this server provides

hitl-mcp-cli gives AI agents a standardized way to pause and request human input. Instead of making assumptions or halting entirely, agents can ask clarifying questions, request approval before sensitive operations, and present choices to the human.

## Quick setup

### 1. Start the server

```bash
# Run without installing (recommended for CI/dev)
uvx hitl-mcp-cli

# Or install and run
uv tool install hitl-mcp-cli
hitl-mcp
```

The server starts on `http://127.0.0.1:5555/mcp` by default.

### 2. Configure your MCP client

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

**`"timeout": 0` is required.** Human response time is unbounded — the default 60-second MCP timeout will cause tool calls to fail if the user takes longer to respond.

### Configuration file locations

| Client | Config file |
|--------|------------|
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) |
| Claude Code | `.mcp.json` in project root, or `~/.claude/mcp.json` |
| Kiro | `.kiro/settings/mcp.json` |
| Cursor | `.cursor/mcp.json` |
| Cline | VS Code settings → MCP servers |

## Available tools

### `hitl_collect` — Collect input

Blocks until the human submits a value. Use for text, file paths, or multiline content.

```
Parameters:
  message           str       — Question to display (required)
  input_type        str       — "text" | "path" | "multiline" (default: "text")
  default           str       — Pre-filled value
  validation_pattern str      — Regex the input must match
  validation_message str      — Custom error shown on validation failure
  context           str       — Additional context shown above the prompt
  required          bool      — Reject empty input (default: false)
  path_type         str       — "file" | "dir" | "any" (when input_type="path")
  agent_name        str       — Your agent's name (shown in Sessions panel)
  project_id        str       — Project identifier for grouping
  step              int       — Current step number
  total_steps       int       — Total steps in workflow
  notes             str       — Dimmed context line below the message

Returns: str — the value the human entered
```

### `hitl_ask` — Alias for `hitl_collect`

Use whichever name reads more naturally in your agent's code.

### `hitl_choose` — Present choices

Blocks until the human selects one or more options. Supports fuzzy search for long lists.

```
Parameters:
  message     str         — Question to display (required)
  choices     list[str]   — Simple string options
  options     list[dict]  — Rich options: [{value, label, description}, ...]
  multiple    bool        — Enable multi-select checkbox mode (default: false)
  default     str         — Pre-selected option
  fuzzy_search bool       — Force fuzzy search on/off (auto-enabled for >15 items)
  context     str         — Additional context shown above the prompt
  agent_name  str         — Your agent's name
  project_id  str         — Project identifier
  step        int         — Current step number
  total_steps int         — Total steps in workflow
  notes       str         — Dimmed context line below the message

Returns: str | list[str] — selected value(s)
```

### `hitl_confirm` — Confirmation gate

Blocks until the human accepts or declines. Use `severity="high"` for destructive operations — it requires the user to type "yes" explicitly.

```
Parameters:
  message          str   — Yes/no question (required)
  default          bool  — Default answer (default: false)
  severity         str   — "low" | "medium" | "high" (default: "medium")
  context          str   — Additional context shown in a panel above the prompt
  timeout_seconds  int   — Seconds to wait; 0 = infinite (default: 0)
  agent_name       str   — Your agent's name
  project_id       str   — Project identifier
  step             int   — Current step number
  total_steps      int   — Total steps in workflow
  notes            str   — Dimmed context line below the message

Returns: {"action": "accept" | "decline" | "cancel"}
         When timeout_seconds > 0, also includes "timed_out": bool
```

### `hitl_notify` — Non-blocking notification

Displays a styled message in the TUI. Does not wait for a response.

```
Parameters:
  message     str   — Notification body, supports multi-line (required)
  level       str   — "success" | "info" | "warning" | "error" (default: "info")
  title       str   — Notification title
  agent_name  str   — Your agent's name
  project_id  str   — Project identifier
  step        int   — Current step number
  total_steps int   — Total steps in workflow
  notes       str   — Dimmed context line below the notification
```

## Readable resources

Poll these to observe HITL state without blocking:

| URI | Returns |
|-----|---------|
| `queue://pending` | JSON list of interactions awaiting human response |
| `queue://history` | JSON list of all completed interactions this session |
| `session://activity` | Per-agent/project activity summary |
| `session://last-user-action-age` | Seconds since the last human response |

## Prompt templates

These are user-invoked templates (slash commands in the MCP host), not agent-callable tools. They provide structured prompts for common HITL decision shapes:

| Name | Use case |
|------|---------|
| `hitl_architectural_fork` | Choose between architectural approaches |
| `hitl_destructive_action` | Confirm a destructive operation with full context |
| `hitl_scope_clarification` | Clarify ambiguous requirements before proceeding |
| `hitl_panel_vote_summary` | Multi-option vote with rationale |

## Example agent workflows

### Workflow 1: Approval gate before destructive action

```python
# Agent discovers files to delete
files = find_unused_files()

result = await mcp.call_tool("hitl_confirm", {
    "message": f"Delete {len(files)} unused files?",
    "severity": "high",
    "context": "\n".join(files[:10]) + ("\n..." if len(files) > 10 else ""),
    "agent_name": "cleanup-agent",
    "project_id": "my-project"
})

if result["action"] == "accept":
    delete(files)
    await mcp.call_tool("hitl_notify", {
        "message": f"Deleted {len(files)} files",
        "level": "success",
        "title": "Cleanup complete"
    })
else:
    # Respect the human's decision — do not retry
    pass
```

### Workflow 2: Gather structured input before starting work

```python
project_name = await mcp.call_tool("hitl_collect", {
    "message": "Project name:",
    "validation_pattern": "^[a-z0-9-]+$",
    "validation_message": "Use lowercase letters, numbers, and hyphens only",
    "step": 1, "total_steps": 3
})

language = await mcp.call_tool("hitl_choose", {
    "message": "Primary language:",
    "choices": ["Python", "TypeScript", "Go", "Rust"],
    "step": 2, "total_steps": 3
})

output_dir = await mcp.call_tool("hitl_collect", {
    "message": "Output directory:",
    "input_type": "path",
    "path_type": "dir",
    "step": 3, "total_steps": 3
})
```

### Workflow 3: Architecture decision

```python
approach = await mcp.call_tool("hitl_choose", {
    "message": "I can implement this in three ways. Which do you prefer?",
    "options": [
        {"value": "fast", "label": "Fast", "description": "Quick to build, higher memory usage"},
        {"value": "safe", "label": "Safe", "description": "More robust, slower execution"},
        {"value": "balanced", "label": "Balanced", "description": "Moderate on both axes (recommended)"}
    ],
    "default": "balanced",
    "agent_name": "architect-agent"
})
```

### Workflow 4: Progressive disclosure

```python
action = await mcp.call_tool("hitl_choose", {
    "message": "What should I do next?",
    "choices": ["Deploy", "Run tests", "View logs", "Cancel"]
})

if action == "Deploy":
    env = await mcp.call_tool("hitl_choose", {
        "message": "Which environment?",
        "choices": ["Staging", "Production"]
    })
    if env == "Production":
        result = await mcp.call_tool("hitl_confirm", {
            "message": "Deploy to PRODUCTION?",
            "severity": "high",
            "context": "This will affect live users."
        })
        if result["action"] == "accept":
            await deploy()
```

## Error handling

```python
result = await mcp.call_tool("hitl_confirm", {"message": "Proceed?"})

# Check action before proceeding
if result["action"] == "cancel":
    # User pressed Ctrl+C — respect it, do not retry
    return

if result.get("timed_out"):
    # Timeout expired — treat as decline or escalate
    return

if result["action"] == "accept":
    proceed()
```

**Error categories:**
- `action: "cancel"` — user pressed Ctrl+C; do not retry
- `timed_out: true` — timeout expired; treat as decline
- Connection/timeout errors — server not running or `timeout` not set to 0; check config
- Validation errors — tool re-prompts automatically; no agent action needed

## Session and project grouping

Pass `agent_name` and `project_id` on every tool call to group interactions in the TUI sessions panel:

```python
common = {
    "agent_name": "deploy-agent",
    "project_id": "my-app-v2"
}

await mcp.call_tool("hitl_confirm", {"message": "...", **common})
await mcp.call_tool("hitl_notify", {"message": "...", **common})
```

## System prompt guidance

Add this to your agent's system prompt to establish when to use HITL tools:

```
You have access to HITL (human-in-the-loop) tools. Use them as follows:

- hitl_confirm (severity="high"): before any destructive, irreversible, or production-affecting action
- hitl_confirm (severity="medium"): before expensive operations or actions with significant side effects
- hitl_choose: when multiple valid approaches exist and the human has context you lack
- hitl_collect: when you need specific input (names, paths, credentials) before proceeding
- hitl_notify: to report completion, errors, or progress without blocking

Do not ask for confirmation on routine, reversible, low-risk operations.
Always respect a "cancel" or "decline" response — do not retry the same action.
```

## Troubleshooting

**Tools time out after 60 seconds**: Set `"timeout": 0` in your MCP client config.

**Tools not visible to agent**: Restart the MCP client after changing config. Verify the server is running and the URL matches.

**`GET /mcp` returns 400**: Expected — the endpoint only accepts POST (JSON-RPC). Ignore GET-based health checks.

**Port already in use**: Start on a different port with `hitl-mcp --port 8080` and update the client config URL.

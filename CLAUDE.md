# hitl-mcp-cli

Human-in-the-loop MCP server that lets AI agents pause and ask a human for
confirmation, input, or a decision before proceeding with sensitive actions.

Service entry point: `hitl-mcp` (installed via `uv run hitl-mcp`)
Tests: `uv run pytest tests/`
Lint/format: `uv run ruff check . --fix && uv run ruff format .`
Type check: `uv run mypy hitl_mcp_cli/`
All checks: `uv run poe check`

## Stack

- Python 3.11+ with uv
- FastMCP ≥2.13 — MCP server framework
- Textual ≥0.89 — terminal UI for the human-facing interaction panel
- Rich — console output and formatting
- pytest + pytest-asyncio — test suite

Never use `pip install`. Always use `uv`.

## Architecture

The server follows FastMCP's three-primitive pattern:

```
hitl_mcp_cli/
  server.py          # FastMCP app wiring — registers tools, resources, prompts
  _server_core.py    # Shared state and session management
  cli.py             # Entry point (hitl-mcp script)
  tools/             # MCP tools (agent-callable actions)
    _collect.py      # hitl_collect — gather structured input from human
    _confirm.py      # hitl_confirm — yes/no confirmation gate
    _notify.py       # hitl_notify — fire-and-forget human notification
  resources/         # MCP resources (readable state)
    _history.py      # interaction history log
    _last_action_age.py
    _metrics.py      # session metrics
    _pending.py      # pending interactions awaiting human response
    _session_activity.py
  prompts/           # MCP prompt templates
    _arch_fork.py    # architecture fork decision prompt
    _destructive.py  # destructive-action confirmation prompt
    _panel_vote.py   # multi-option panel vote prompt
    _scope_clarify.py
  tui/               # Textual TUI — the human-facing panel
  interaction_log.py # Interaction persistence
```

Tools are the primary interface: an AI agent calls `hitl_confirm`, `hitl_collect`,
or `hitl_notify`; the TUI surfaces the request to the human; the tool blocks until
the human responds.

## Key commands

```bash
# Run the MCP server (stdio transport, for use in .mcp.json)
uv run hitl-mcp

# Run tests
uv run pytest tests/ -v

# Run tests with coverage
uv run poe test-cov

# Full check (lint + type-check + tests)
uv run poe check

# Lint and format
uv run poe lint && uv run poe format
```

## Coding standards

- Python 3.11+, uv only (never pip)
- ruff for lint/format (line length 110)
- mypy strict mode
- No AI attribution in commits or docstrings
- Test suite must stay green; `uv run pytest tests/` is the gate

## Global rules

Shared rules live at `~/.claude/rules/` — safety, anti-hallucination,
completion-reports, delegation-contract, pr-hygiene. These apply to all
sessions and are not duplicated here.

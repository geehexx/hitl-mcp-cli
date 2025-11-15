# Multi-Agent Coordination Guide

**Version**: 1.0
**Last Updated**: 2025-11-15

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Core Concepts](#core-concepts)
4. [Coordination Protocol](#coordination-protocol)
5. [Practical Examples](#practical-examples)
6. [API Reference](#api-reference)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## Overview

The HITL MCP Server now supports **multi-agent coordination**, enabling multiple AI agents to communicate, coordinate, and collaborate through MCP-native primitives.

### Key Features

- **Channel-based messaging**: Agents communicate through named channels
- **Structured protocols**: Well-defined message types for different coordination phases
- **Distributed locking**: Prevent conflicts when accessing shared resources
- **MCP-native**: Uses standard MCP resources and tools (no external dependencies)
- **Opt-in**: Single-agent workflows continue unchanged

### Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│  Agent A    │────▶│  HITL MCP Server │◀────│  Agent B    │
│ (Primary)   │     │  ┌────────────┐  │     │(Subordinate)│
└─────────────┘     │  │  Channels  │  │     └─────────────┘
                    │  │  Messages  │  │
                    │  │  Locks     │  │
                    │  └────────────┘  │
                    └──────────────────┘
```

---

## Getting Started

### 1. Enable Coordination

Start the server with coordination enabled:

```bash
# Option 1: Command-line flag
hitl-mcp-cli --enable-coordination

# Option 2: Environment variable
export HITL_ENABLE_COORDINATION=1
hitl-mcp-cli

# Option 3: Both (for port configuration)
HITL_ENABLE_COORDINATION=1 hitl-mcp-cli --port 5555
```

### 2. Verify Coordination is Available

Check server capabilities:

```python
# Using MCP client
capabilities = await client.get_server_info()

# Look for coordination tools:
# - join_coordination_channel
# - send_coordination_message
# - poll_coordination_channel
# - acquire_coordination_lock
# - release_coordination_lock
```

### 3. Simple Two-Agent Example

**Agent A (Primary):**
```python
# 1. Join channel as primary
await client.call_tool(
    "join_coordination_channel",
    channel_name="my-project",
    agent_id="agent-a",
    role="primary"
)

# 2. Send init message
await client.call_tool(
    "send_coordination_message",
    channel_name="my-project",
    from_agent="agent-a",
    message_type="init",
    content="Coordination starting. I am primary agent."
)

# 3. Wait for acknowledgment
while True:
    result = await client.call_tool(
        "poll_coordination_channel",
        channel_name="my-project",
        filter_type="acknowledgment"
    )
    if result["messages"]:
        print(f"Received ack from {result['messages'][0]['from_agent']}")
        break
    await asyncio.sleep(1)
```

**Agent B (Subordinate):**
```python
# 1. Join channel as subordinate
await client.call_tool(
    "join_coordination_channel",
    channel_name="my-project",
    agent_id="agent-b",
    role="subordinate"
)

# 2. Poll for primary's init
result = await client.call_tool(
    "poll_coordination_channel",
    channel_name="my-project",
    filter_type="init"
)

print(f"Primary says: {result['messages'][0]['content']}")

# 3. Send acknowledgment
await client.call_tool(
    "send_coordination_message",
    channel_name="my-project",
    from_agent="agent-b",
    message_type="acknowledgment",
    content='{"role": "subordinate", "status": "ready"}'
)
```

---

## Core Concepts

### 1. Channels

**Channels** are named communication pipes for agents.

- Agents join channels to send/receive messages
- Channels are created automatically on first join
- Multiple agents can join the same channel

**Example:**
```python
result = await join_coordination_channel(
    channel_name="project-alpha",
    agent_id="claude-desktop-1"
)
# Returns: {"channel_name": "...", "other_agents": [...], "message_count": 0}
```

### 2. Messages

Messages are structured with **types** for protocol compliance.

**Message Structure:**
```json
{
    "id": "msg-uuid",
    "from_agent": "agent-a",
    "timestamp": 1731676800.0,
    "type": "task_assign",
    "content": {"task": "Update README"},
    "sequence": 5,
    "metadata": {},
    "reply_to": null
}
```

**Message Types:**

| Phase | Types |
|-------|-------|
| **Discovery** | `init`, `acknowledgment` |
| **Synchronization** | `sync`, `capabilities`, `ownership`, `coordination_complete` |
| **Operational** | `question`, `response`, `task_assign`, `task_complete`, `progress` |
| **Control** | `ready`, `standby`, `stop`, `done` |
| **Conflict** | `conflict_detected`, `conflict_resolved` |

### 3. Locks

**Distributed locks** ensure exclusive access to shared resources.

**Example:**
```python
# Acquire lock
lock = await acquire_coordination_lock(
    lock_name="file:config.yaml",
    agent_id="agent-a",
    timeout_seconds=10,
    auto_release_seconds=300
)

if lock["acquired"]:
    try:
        # Modify file safely
        with open("config.yaml", "w") as f:
            f.write("...")
    finally:
        # Always release
        await release_coordination_lock(lock["lock_id"], "agent-a")
```

**Features:**
- **Timeout**: Wait up to N seconds or fail immediately (timeout=0)
- **Auto-release**: Prevents deadlocks (default: 5 minutes)
- **Quota**: Each agent can hold max 10 locks

---

## Coordination Protocol

### Phase 1: Discovery

Agents find each other and declare roles.

```python
# Primary initiates
await send_message(channel, agent, "init", '{"role": "primary"}')

# Subordinate acknowledges
await send_message(channel, agent, "acknowledgment", '{"role": "subordinate"}')
```

### Phase 2: Synchronization

Agents exchange configuration, capabilities, and ownership.

```python
# Share configuration
await send_message(channel, agent, "sync", json.dumps({
    "rules": {"no_transient_files": True},
    "standards": {"test_coverage": 0.92}
}))

# Declare capabilities
await send_message(channel, agent, "capabilities", json.dumps({
    "knowledge_base": True,
    "session_limit": None
}))

# Declare file ownership
await send_message(channel, agent, "ownership", json.dumps({
    "files": [".amazonq/", "AMAZON_Q.md"]
}))

# Signal sync complete
await send_message(channel, agent, "coordination_complete", "Sync finished")
```

### Phase 3: Operational

Agents work together on tasks.

```python
# Primary assigns task
await send_message(channel, agent, "task_assign", json.dumps({
    "task": "Update README.md",
    "files": ["README.md"],
    "guidelines": "Follow existing style"
}))

# Subordinate sends progress updates
await send_message(channel, agent, "progress", json.dumps({
    "status": "50% complete"
}))

# Subordinate asks question
await send_message(channel, agent, "question", "Should I update CHANGELOG?")

# Primary responds
await send_message(channel, agent, "response", "Yes, follow semver")

# Subordinate reports completion
await send_message(channel, agent, "task_complete", json.dumps({
    "task_id": "update-readme",
    "files_modified": ["README.md", "CHANGELOG.md"]
}))
```

### Phase 4: Conflict Resolution

Handle conflicts when they arise.

```python
# Subordinate detects conflict
await send_message(channel, agent, "conflict_detected", json.dumps({
    "conflict_type": "file_modification",
    "details": "Both agents modified config.yaml",
    "suggested_resolution": "Use primary's version"
}))

# Primary resolves
await send_message(channel, agent, "conflict_resolved", json.dumps({
    "resolution": "Use primary's version",
    "rationale": "Primary has more recent context"
}))
```

---

## Practical Examples

### Example 1: Task Assignment Pattern

```python
# Primary assigns multiple tasks to subordinates
tasks = [
    {"agent": "agent-1", "task": "Frontend", "files": ["src/frontend/*"]},
    {"agent": "agent-2", "task": "Backend", "files": ["src/backend/*"]},
    {"agent": "agent-3", "task": "Tests", "files": ["tests/*"]},
]

for task in tasks:
    await send_message(
        channel="parallel-work",
        from_agent="primary",
        message_type="task_assign",
        content=json.dumps(task)
    )

# Wait for all completions
completed = set()
while len(completed) < 3:
    msgs = await poll_channel("parallel-work", filter_type="task_complete")
    for msg in msgs:
        completed.add(msg["from_agent"])
        print(f"{msg['from_agent']} completed their task")
```

### Example 2: File Coordination with Locks

```python
# Agent wants to modify shared file
lock = await acquire_lock(
    lock_name="file:README.md",
    agent_id="agent-a",
    timeout_seconds=30  # Wait up to 30s
)

if not lock["acquired"]:
    # Another agent holds the lock
    print(f"Lock held by {lock['held_by']}, waiting...")
    await send_message(
        channel="coordination",
        from_agent="agent-a",
        message_type="question",
        content=f"Can I modify README.md? It's locked by {lock['held_by']}"
    )
else:
    try:
        # We have the lock, safe to modify
        with open("README.md", "w") as f:
            f.write("Updated content")
        print("File updated successfully")
    finally:
        await release_lock(lock["lock_id"], "agent-a")
```

### Example 3: Capability Negotiation

```python
# Agent A declares capabilities
await send_message(channel, "agent-a", "capabilities", json.dumps({
    "knowledge_base": True,
    "session_limit": None,
    "tools": ["code_search", "file_read", "web_fetch"]
}))

# Agent B declares capabilities
await send_message(channel, "agent-b", "capabilities", json.dumps({
    "knowledge_base": False,
    "session_limit": 50,
    "tools": ["file_read", "code_analysis"]
}))

# Agent B defers exploration to Agent A (which has knowledge_base)
msgs = await poll_channel(channel, filter_type="capabilities")
agent_a_caps = json.loads(msgs[0]["content"])

if agent_a_caps["knowledge_base"]:
    await send_message(channel, "agent-b", "question",
        "You have knowledge base. Can you explore codebase for error handling?"
    )
```

### Example 4: Progress Tracking

```python
# Long-running task with progress updates
await send_message(channel, agent, "progress", json.dumps({
    "task": "process-large-dataset",
    "percentage": 0,
    "status": "starting"
}))

for i in range(0, 101, 10):
    # Do some work...
    process_batch(i)

    # Update progress
    await send_message(channel, agent, "progress", json.dumps({
        "task": "process-large-dataset",
        "percentage": i,
        "status": f"processing batch {i//10}"
    }))

await send_message(channel, agent, "task_complete", json.dumps({
    "task": "process-large-dataset",
    "status": "done"
}))
```

---

## API Reference

### Tools

#### `join_coordination_channel`

Join a channel to communicate with other agents.

```python
result = await join_coordination_channel(
    channel_name: str,           # "project-alpha"
    agent_id: str,               # "claude-desktop-1"
    role: "primary" | "subordinate" | None = None,
    metadata: dict | None = None
)
# Returns: {"channel_name": ..., "agent_id": ..., "other_agents": [...], "message_count": 0}
```

#### `send_coordination_message`

Send a structured message to channel.

```python
result = await send_coordination_message(
    channel_name: str,           # "project-alpha"
    from_agent: str,             # "claude-desktop-1"
    message_type: str,           # "task_assign", "question", etc.
    content: str,                # JSON string or plain text
    metadata: dict | None = None,
    reply_to: str | None = None  # Message ID being replied to
)
# Returns: {"message_id": "msg-uuid", "timestamp": 1731676800.0, "channel_uri": "..."}
```

#### `poll_coordination_channel`

Check for new messages (non-blocking).

```python
result = await poll_coordination_channel(
    channel_name: str,                 # "project-alpha"
    since_message_id: str | None = None,  # Only return messages after this ID
    filter_type: str | None = None,    # Filter by message type
    max_messages: int = 100            # Maximum to return
)
# Returns: {"messages": [...], "has_more": false, "latest_id": "msg-uuid"}
```

#### `acquire_coordination_lock`

Acquire distributed lock for exclusive access.

```python
result = await acquire_coordination_lock(
    lock_name: str,              # "file:/path/to/file"
    agent_id: str,               # "claude-desktop-1"
    timeout_seconds: int = 30,   # How long to wait (0 = fail immediately)
    auto_release_seconds: int = 300  # Auto-release after 5 minutes
)
# Returns: {"acquired": true, "lock_id": "lock-uuid", "held_by": "...", "expires_at": ...}
```

#### `release_coordination_lock`

Release a previously acquired lock.

```python
result = await release_coordination_lock(
    lock_id: str,     # From acquire_coordination_lock
    agent_id: str     # Must match acquirer
)
# Returns: {"released": true}
```

### Resources

#### `coordination://channels`

List all channels.

```python
channels = await client.read_resource("coordination://channels")
# Returns JSON: [{"name": "...", "members": [...], "message_count": 5}, ...]
```

#### `coordination://{channel}`

Read all messages in channel.

```python
messages = await client.read_resource("coordination://project-alpha")
# Returns JSON: [{"id": "...", "from_agent": "...", "type": "...", ...}, ...]
```

#### `coordination://{channel}/type/{type}`

Filter messages by type.

```python
questions = await client.read_resource("coordination://project-alpha/type/question")
# Returns JSON: [{"id": "...", "type": "question", ...}, ...]
```

---

## Best Practices

### 1. Clear Role Assignment

Explicitly assign roles (primary/subordinate) during discovery phase.

```python
# Good
await join_coordination_channel("project", "agent-a", role="primary")

# Less clear
await join_coordination_channel("project", "agent-a")  # Role unclear
```

### 2. Always Release Locks

Use try/finally to ensure locks are released.

```python
lock = await acquire_lock("resource", "agent-id")
if lock["acquired"]:
    try:
        # Work with resource
        pass
    finally:
        await release_lock(lock["lock_id"], "agent-id")
```

### 3. Poll Efficiently

Use `since_message_id` to avoid re-reading old messages.

```python
last_id = None
while True:
    result = await poll_channel("project", since_message_id=last_id)
    if result["messages"]:
        # Process new messages
        for msg in result["messages"]:
            handle_message(msg)
        last_id = result["latest_id"]
    await asyncio.sleep(1)
```

### 4. Validate Message Content

Ensure message content matches schema for type.

```python
# Good - Task assign with required "task" field
await send_message(channel, agent, "task_assign", json.dumps({
    "task": "Update README",
    "files": ["README.md"]
}))

# Bad - Missing required field
await send_message(channel, agent, "task_assign", json.dumps({
    "files": ["README.md"]  # Missing "task" field!
}))
```

### 5. Handle Conflicts Gracefully

When conflicts arise, subordinate defers to primary.

```python
# Subordinate detects conflict
await send_message(channel, agent, "conflict_detected", json.dumps({
    "conflict_type": "file_modification",
    "details": "Both modified config.yaml"
}))

# Wait for primary's resolution
while True:
    msgs = await poll_channel(channel, filter_type="conflict_resolved")
    if msgs["messages"]:
        resolution = json.loads(msgs["messages"][0]["content"])
        apply_resolution(resolution)
        break
```

---

## Troubleshooting

### Problem: Channel seems empty

**Symptoms**: `poll_coordination_channel` returns no messages, but you expect some.

**Solutions**:
1. Verify you joined the channel: `await join_coordination_channel(...)`
2. Check channel name spelling
3. Verify other agent sent messages to same channel
4. Use resource to inspect: `await read_resource("coordination://channels")`

### Problem: Lock acquisition fails

**Symptoms**: `acquire_coordination_lock` returns `{"acquired": false}`

**Solutions**:
1. Another agent holds the lock - check `held_by` field
2. Wait for lock to expire or be released
3. Increase `timeout_seconds` to wait longer
4. Check lock quota (max 10 per agent)

### Problem: Messages out of order

**Symptoms**: Messages from same agent arrive in unexpected order

**Solutions**:
1. Check `sequence` field - per-agent messages are sequenced
2. Messages from different agents have no ordering guarantee
3. Use `reply_to` field for explicit threading

### Problem: Lock never released

**Symptoms**: Lock stuck, agent can't acquire

**Solutions**:
1. Wait for auto-release (default: 5 minutes)
2. Check if holding agent crashed (no heartbeat)
3. Contact server admin to manually release

### Debug Mode

Enable debug logging to see coordination activity:

```bash
export HITL_LOG_LEVEL=DEBUG
hitl-mcp-cli --enable-coordination
```

---

## Next Steps

1. **Try Examples**: Run the code examples above with two MCP clients
2. **Read Design Doc**: See `MULTI_AGENT_COORDINATION_DESIGN.md` for architecture details
3. **Expert Review**: See `EXPERT_PANEL_REVIEW.md` for design validation and recommendations
4. **Contribute**: Submit issues or PRs to improve coordination features

---

## Support

- **GitHub Issues**: https://github.com/anthropics/hitl-mcp-cli/issues
- **Documentation**: See `docs/` directory
- **Examples**: See `examples/coordination/` (coming soon)

---

**Last Updated**: 2025-11-15
**Version**: 1.0
**License**: MIT

# Multi-Agent Coordination System Design
## Extended HITL MCP Server for Agent-to-Agent Communication

**Version**: 1.0
**Date**: 2025-11-15
**Status**: Design Phase - Expert Review Required

---

## Executive Summary

This document proposes a comprehensive multi-agent coordination extension for the hitl-mcp-cli server that enables multiple AI agents to communicate, coordinate, and collaborate through **MCP-native primitives**. The design leverages:

1. **MCP Resources** for channel-based communication
2. **MCP Sampling** for agent-to-agent LLM requests
3. **Progress Notifications** for real-time coordination status
4. **Session Management** for state persistence
5. **Proven Coordination Patterns** from real multi-agent deployments

### Key Design Principles

- **MCP-Native**: Use MCP primitives (resources, sampling) rather than external mechanisms
- **Layered Architecture**: Build on top of existing tools without breaking changes
- **Opt-In Coordination**: Single-agent workflows continue unchanged
- **Backward Compatible**: All existing functionality preserved
- **Protocol-Driven**: Structured message schemas with validation

---

## 1. Architecture Overview

### 1.1 Three-Layer Design

```
┌─────────────────────────────────────────────────────────┐
│ Layer 3: Coordination Protocol                          │
│ ├─ Message schemas (init, sync, task, conflict)        │
│ ├─ Coordination phases (discovery → operational)        │
│ ├─ Deference protocol (primary/subordinate)            │
│ └─ Conflict resolution                                  │
└───────────────────┬─────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────┐
│ Layer 2: MCP Coordination Primitives                    │
│ ├─ Channel Resources (read/write/subscribe)            │
│ ├─ Agent Registry Resource                              │
│ ├─ Coordination Tools (join, send, poll, lock)         │
│ └─ Session Management                                   │
└───────────────────┬─────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────┐
│ Layer 1: Existing HITL MCP Server (Unchanged)           │
│ ├─ request_text_input                                   │
│ ├─ request_selection                                    │
│ ├─ request_confirmation                                 │
│ ├─ request_path_input                                   │
│ └─ notify_completion                                    │
└─────────────────────────────────────────────────────────┘
```

### 1.2 MCP-Native Communication Model

**Instead of FIFO pipes or external channels, use MCP Resources:**

```
Agent A                          HITL MCP Server                          Agent B
   │                                    │                                    │
   │ 1. tools/call: join_channel       │                                    │
   ├───────────────────────────────────>│                                    │
   │    (channel: "coordination")       │                                    │
   │                                    │ 2. tools/call: join_channel       │
   │                                    │<───────────────────────────────────┤
   │                                    │    (channel: "coordination")       │
   │                                    │                                    │
   │ 3. tools/call: send_message       │                                    │
   ├───────────────────────────────────>│                                    │
   │    (type: "init", role: "primary") │                                    │
   │                                    │                                    │
   │                                    │ 4. resources/read:                 │
   │                                    │    coordination://coordination     │
   │                                    │<───────────────────────────────────┤
   │                                    │                                    │
   │                                    │ Returns: Agent A's init message    │
   │                                    ├───────────────────────────────────>│
   │                                    │                                    │
   │                                    │ 5. tools/call: send_message       │
   │                                    │<───────────────────────────────────┤
   │                                    │    (type: "ack", role: "sub")     │
   │                                    │                                    │
   │ 6. resources/read:                │                                    │
   │    coordination://coordination     │                                    │
   ├───────────────────────────────────>│                                    │
   │                                    │                                    │
   │ Returns: Agent B's ack             │                                    │
   │<───────────────────────────────────┤                                    │
```

**Benefits of MCP Resources over FIFO pipes:**
- ✅ **Standard MCP primitive** - no external dependencies
- ✅ **Built-in persistence** - survives disconnections
- ✅ **Multiple readers** - broadcast to N agents
- ✅ **Resource URIs** - `coordination://channel-name/message-id`
- ✅ **Template support** - `coordination://channel-name/{message_id}`
- ✅ **Subscribe capability** - real-time notifications via MCP subscriptions

---

## 2. Core Components

### 2.1 Channel Resource (MCP Resource)

**Resource URI Scheme**: `coordination://channel-name[/message-id]`

**Examples**:
- `coordination://task-queue` - List all messages in queue
- `coordination://task-queue/msg-123` - Read specific message
- `coordination://agent-status` - Read agent status updates

**Resource Definition**:
```python
@mcp.resource("coordination://{channel_name}")
async def read_channel(channel_name: str) -> str:
    """Read all messages from a coordination channel.

    Returns JSON array of messages in chronological order.
    Each message includes: id, from, timestamp, type, content.
    """

@mcp.resource("coordination://{channel_name}/{message_id}")
async def read_message(channel_name: str, message_id: str) -> str:
    """Read specific message from channel."""
```

**Storage Backend**:
```python
class ChannelStore:
    """In-memory message store with optional persistence."""

    def __init__(self, persist_dir: Path | None = None):
        self.channels: dict[str, list[Message]] = {}
        self.persist_dir = persist_dir
        self.locks: dict[str, asyncio.Lock] = {}

    async def append(self, channel: str, message: Message) -> str:
        """Append message, return message ID."""

    async def read(self, channel: str, since: str | None = None) -> list[Message]:
        """Read messages since message_id (or all if None)."""

    async def subscribe(self, channel: str) -> AsyncIterator[Message]:
        """Subscribe to new messages (using asyncio.Queue)."""
```

### 2.2 Coordination Tools

**Tool 1: Join Channel**
```python
@mcp.tool()
async def join_coordination_channel(
    channel_name: str,
    agent_id: str,
    role: Literal["primary", "subordinate"] | None = None,
    metadata: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Join a coordination channel to communicate with other agents.

    Args:
        channel_name: Unique channel identifier (e.g., "project-alpha")
        agent_id: Unique identifier for this agent (e.g., "claude-desktop-1")
        role: Agent's role in coordination (primary has authority)
        metadata: Additional agent info (capabilities, session_id, etc.)

    Returns:
        {
            "channel_uri": "coordination://project-alpha",
            "agent_id": "claude-desktop-1",
            "joined_at": "2025-11-15T10:30:00Z",
            "other_agents": ["amazon-q-1"],  # Already in channel
            "message_count": 5
        }
    """
```

**Tool 2: Send Message**
```python
@mcp.tool()
async def send_coordination_message(
    channel_name: str,
    from_agent: str,
    message_type: Literal[
        "init", "acknowledgment", "sync", "question", "response",
        "task_assign", "task_complete", "ready", "standby",
        "conflict_detected", "conflict_resolved"
    ],
    content: str,
    metadata: dict[str, Any] | None = None,
    reply_to: str | None = None
) -> dict[str, Any]:
    """Send a coordination message to a channel.

    Args:
        channel_name: Target channel
        from_agent: Sender agent ID
        message_type: Structured message type (see protocol spec)
        content: Message payload (JSON string or plain text)
        metadata: Additional context (files, status, etc.)
        reply_to: Message ID being replied to (for threading)

    Returns:
        {
            "message_id": "msg-uuid",
            "timestamp": "2025-11-15T10:30:01Z",
            "channel_uri": "coordination://project-alpha/msg-uuid"
        }
    """
```

**Tool 3: Poll Channel**
```python
@mcp.tool()
async def poll_coordination_channel(
    channel_name: str,
    since_message_id: str | None = None,
    filter_type: str | None = None,
    max_messages: int = 100
) -> dict[str, Any]:
    """Poll channel for new messages (non-blocking).

    Args:
        channel_name: Channel to poll
        since_message_id: Only return messages after this ID
        filter_type: Only return messages of this type
        max_messages: Maximum messages to return

    Returns:
        {
            "messages": [
                {
                    "id": "msg-uuid",
                    "from": "agent-id",
                    "timestamp": "ISO-8601",
                    "type": "question",
                    "content": "...",
                    "metadata": {...},
                    "reply_to": "msg-uuid" | null
                }
            ],
            "has_more": false,
            "latest_id": "msg-uuid"
        }
    """
```

**Tool 4: Acquire Lock**
```python
@mcp.tool()
async def acquire_coordination_lock(
    lock_name: str,
    agent_id: str,
    timeout_seconds: int = 30,
    auto_release_seconds: int = 300
) -> dict[str, Any]:
    """Acquire distributed lock for exclusive operations.

    Use this to ensure only one agent modifies shared resources.

    Args:
        lock_name: Unique lock identifier (e.g., "file:/path/to/file")
        agent_id: Agent requesting lock
        timeout_seconds: How long to wait for lock (0 = fail immediately)
        auto_release_seconds: Automatically release after this duration

    Returns:
        {
            "acquired": true,
            "lock_id": "lock-uuid",
            "held_by": "agent-id",
            "expires_at": "2025-11-15T10:35:00Z"
        }
    """
```

**Tool 5: Release Lock**
```python
@mcp.tool()
async def release_coordination_lock(
    lock_id: str,
    agent_id: str
) -> dict[str, bool]:
    """Release a previously acquired lock.

    Args:
        lock_id: Lock ID from acquire_coordination_lock
        agent_id: Agent releasing lock (must match acquirer)

    Returns:
        {"released": true}
    """
```

### 2.3 Agent Registry Resource

**Resource**: `coordination://agents`

```python
@mcp.resource("coordination://agents")
async def list_agents() -> str:
    """List all registered agents and their status.

    Returns:
        [
            {
                "agent_id": "claude-desktop-1",
                "role": "primary",
                "status": "active",
                "channels": ["project-alpha", "task-queue"],
                "last_seen": "2025-11-15T10:30:00Z",
                "capabilities": {
                    "knowledge_base": true,
                    "session_limit": null
                }
            }
        ]
    """
```

---

## 3. Coordination Protocol

### 3.1 Message Schema

**Base Message Structure**:
```typescript
interface CoordinationMessage {
    id: string;                    // UUID
    from: string;                  // Agent ID
    timestamp: string;             // ISO-8601
    type: MessageType;
    content: string | object;      // Message payload
    metadata?: Record<string, any>;
    reply_to?: string;             // Message ID being replied to
}

type MessageType =
    // Discovery Phase
    | "init"                       // Start coordination
    | "acknowledgment"             // Confirm receipt/role

    // Synchronization Phase
    | "sync"                       // Share config/rules
    | "capabilities"               // Declare agent capabilities
    | "ownership"                  // Declare file ownership
    | "coordination_complete"      // Sync finished

    // Operational Phase
    | "question"                   // Request information
    | "response"                   // Provide information
    | "task_assign"                // Assign work (primary → sub)
    | "task_complete"              // Report completion
    | "clarification"              // Clarify previous message

    // Control
    | "ready"                      // Signal readiness
    | "standby"                    // Enter passive mode
    | "stop"                       // Halt activity
    | "done"                       // Task finished

    // Conflict Management
    | "conflict_detected"          // Report conflict
    | "conflict_resolved"          // Confirm resolution

    // Status Updates
    | "progress"                   // Progress update
    | "status";                    // Status change
```

### 3.2 Coordination Phases

**Phase 1: Discovery (Agents Find Each Other)**

```
Agent A (Primary)                    Agent B (Subordinate)
    │                                        │
    │ 1. join_coordination_channel          │
    │    (role="primary")                    │
    ├──────────────┐                        │
    │              │                         │
    │ 2. send_message(type="init")          │
    │              │                         │
    │              └────────────────┐        │
    │                               │        │
    │                               │ 3. join_coordination_channel
    │                               │    (role="subordinate")
    │                               │        │
    │                               │ 4. poll_channel
    │                               │        │
    │                               │<───────┤ (sees Agent A's init)
    │                               │        │
    │                               │ 5. send_message(type="ack")
    │                               │        │
    │ 6. poll_channel               │        │
    ├───────────────────────────────┤        │
    │ (sees Agent B's ack)          │        │
```

**Phase 2: Synchronization (Align Rules & Capabilities)**

```
Agent A (Primary)                    Agent B (Subordinate)
    │                                        │
    │ send_message(type="sync")             │
    │   content: {rules, config, standards} │
    ├───────────────────────────────────────>│
    │                                        │
    │                                        │ send_message(type="capabilities")
    │                                        │   content: {tools, limits, config}
    │<───────────────────────────────────────┤
    │                                        │
    │ send_message(type="ownership")        │
    │   content: {exclusive_files: [...]}   │
    ├───────────────────────────────────────>│
    │                                        │
    │                                        │ send_message(type="ownership")
    │                                        │   content: {exclusive_files: [...]}
    │<───────────────────────────────────────┤
    │                                        │
    │ send_message(type="coordination_complete") │
    ├───────────────────────────────────────>│
    │                                        │
    │                                        │ send_message(type="ready")
    │<───────────────────────────────────────┤
```

**Phase 3: Operational (Active Coordination)**

```
Agent A (Primary)                    Agent B (Subordinate)
    │                                        │
    │ send_message(type="task_assign")      │
    │   content: {task: "update docs",      │
    │             files: ["README.md"]}     │
    ├───────────────────────────────────────>│
    │                                        │
    │                                        │ (works on task)
    │                                        │
    │                                        │ send_message(type="progress")
    │                                        │   content: {status: "50% done"}
    │<───────────────────────────────────────┤
    │                                        │
    │                                        │ send_message(type="question")
    │                                        │   content: "Should I update changelog?"
    │<───────────────────────────────────────┤
    │                                        │
    │ send_message(type="response")         │
    │   content: "Yes, follow semver"       │
    ├───────────────────────────────────────>│
    │                                        │
    │                                        │ send_message(type="task_complete")
    │                                        │   content: {files_modified: [...]}
    │<───────────────────────────────────────┤
```

**Phase 4: Conflict Resolution**

```
Agent A (Primary)                    Agent B (Subordinate)
    │                                        │
    │                                        │ send_message(type="conflict_detected")
    │                                        │   content: "Both modified config.yaml"
    │<───────────────────────────────────────┤
    │                                        │
    │ (analyzes conflict)                   │
    │                                        │
    │ send_message(type="conflict_resolved") │
    │   content: {decision: "Use version A", │
    │             rationale: "..."}          │
    ├───────────────────────────────────────>│
    │                                        │
    │                                        │ (applies resolution)
    │                                        │ send_message(type="acknowledgment")
    │<───────────────────────────────────────┤
```

### 3.3 Deference Protocol

**Rule**: Subordinate agents defer to primary agent on:
- Codebase exploration (if primary has superior tools)
- Workflow decisions
- Architectural choices
- Conflict resolution

**Implementation via Messages**:
```python
# Subordinate asks for guidance
{
    "type": "question",
    "from": "agent-b",
    "content": "Should I explore codebase or defer to you?",
    "metadata": {
        "capability_gap": "knowledge_base",
        "reason": "Primary has 10-100x faster search"
    }
}

# Primary provides decision
{
    "type": "response",
    "from": "agent-a",
    "content": "I'll handle exploration. Standby for results.",
    "metadata": {
        "deference_accepted": true
    }
}
```

---

## 4. Implementation Plan

### 4.1 Phase 1: Core Infrastructure (Week 1)

**Deliverables**:
- [ ] `ChannelStore` class (in-memory message storage)
- [ ] `coordination://` resource provider
- [ ] `join_coordination_channel` tool
- [ ] `send_coordination_message` tool
- [ ] `poll_coordination_channel` tool
- [ ] Basic message schema validation
- [ ] Unit tests for channel operations

**Files to Create**:
```
hitl_mcp_cli/
├── coordination/
│   ├── __init__.py
│   ├── channels.py          # ChannelStore, Message classes
│   ├── resources.py         # MCP resource definitions
│   ├── tools.py             # MCP tool definitions
│   ├── schema.py            # Message schemas & validation
│   └── locks.py             # Lock management
└── tests/
    └── coordination/
        ├── test_channels.py
        ├── test_tools.py
        └── test_integration.py
```

### 4.2 Phase 2: Coordination Protocol (Week 2)

**Deliverables**:
- [ ] Message type taxonomy (all 15+ types)
- [ ] Phase state machine (Discovery → Sync → Operational → Complete)
- [ ] Protocol validation (enforce message sequences)
- [ ] Agent registry
- [ ] Deference protocol helpers
- [ ] Integration tests for full coordination flow

### 4.3 Phase 3: Lock Management & Conflict Resolution (Week 3)

**Deliverables**:
- [ ] `acquire_coordination_lock` tool
- [ ] `release_coordination_lock` tool
- [ ] Distributed lock implementation
- [ ] Timeout & auto-release logic
- [ ] Deadlock detection
- [ ] Conflict detection helpers
- [ ] Tests for concurrent access scenarios

### 4.4 Phase 4: Persistence & Advanced Features (Week 4)

**Deliverables**:
- [ ] Optional SQLite persistence for channels
- [ ] Message history & audit log
- [ ] Resource subscriptions (real-time notifications)
- [ ] Metrics & observability
- [ ] Performance optimization
- [ ] Production deployment guide

### 4.5 Phase 5: Documentation & Examples (Week 5)

**Deliverables**:
- [ ] API documentation
- [ ] Multi-agent coordination guide
- [ ] Example workflows (primary/subordinate pattern)
- [ ] Troubleshooting guide
- [ ] Migration guide for existing users
- [ ] Video demos

---

## 5. Example Workflows

### 5.1 Simple Two-Agent Coordination

**Scenario**: Claude Desktop (primary) and Amazon Q (subordinate) working on same codebase.

**Agent A (Claude Desktop) - Primary**:
```python
# 1. Join coordination channel
result = await client.call_tool(
    "join_coordination_channel",
    channel_name="project-alpha",
    agent_id="claude-desktop-1",
    role="primary",
    metadata={"knowledge_base": True, "session_limit": None}
)

# 2. Send init message
await client.call_tool(
    "send_coordination_message",
    channel_name="project-alpha",
    from_agent="claude-desktop-1",
    message_type="init",
    content="Coordination starting. I am primary agent with knowledge base access."
)

# 3. Poll for subordinate acknowledgment
while True:
    messages = await client.call_tool(
        "poll_coordination_channel",
        channel_name="project-alpha",
        filter_type="acknowledgment"
    )
    if messages["messages"]:
        break
    await asyncio.sleep(1)

# 4. Share project rules
await client.call_tool(
    "send_coordination_message",
    channel_name="project-alpha",
    from_agent="claude-desktop-1",
    message_type="sync",
    content=json.dumps({
        "rules": {
            "no_transient_files": True,
            "git_mv_only": True,
            "test_coverage_min": 0.92
        }
    })
)

# 5. Assign task to subordinate
await client.call_tool(
    "send_coordination_message",
    channel_name="project-alpha",
    from_agent="claude-desktop-1",
    message_type="task_assign",
    content=json.dumps({
        "task": "Update README.md with new features",
        "files": ["README.md"],
        "guidelines": "Follow existing tone and style"
    })
)

# 6. Poll for completion
# ... (subordinate works on task)
```

**Agent B (Amazon Q) - Subordinate**:
```python
# 1. Join channel
await client.call_tool(
    "join_coordination_channel",
    channel_name="project-alpha",
    agent_id="amazon-q-1",
    role="subordinate",
    metadata={"session_limit": 50, "knowledge_base": False}
)

# 2. Poll for primary's init
messages = await client.call_tool(
    "poll_coordination_channel",
    channel_name="project-alpha",
    filter_type="init"
)

# 3. Send acknowledgment
await client.call_tool(
    "send_coordination_message",
    channel_name="project-alpha",
    from_agent="amazon-q-1",
    message_type="acknowledgment",
    content=json.dumps({
        "role": "subordinate",
        "status": "ready",
        "capabilities": {
            "knowledge_base": False,
            "session_limit": 50
        }
    })
)

# 4. Receive project rules
messages = await client.call_tool(
    "poll_coordination_channel",
    channel_name="project-alpha",
    filter_type="sync"
)
rules = json.loads(messages["messages"][0]["content"])

# 5. Receive task assignment
messages = await client.call_tool(
    "poll_coordination_channel",
    channel_name="project-alpha",
    filter_type="task_assign"
)
task = json.loads(messages["messages"][0]["content"])

# 6. Acquire lock before modifying
lock = await client.call_tool(
    "acquire_coordination_lock",
    lock_name="file:README.md",
    agent_id="amazon-q-1"
)

# 7. Work on task
# ... (modify README.md)

# 8. Release lock
await client.call_tool(
    "release_coordination_lock",
    lock_id=lock["lock_id"],
    agent_id="amazon-q-1"
)

# 9. Report completion
await client.call_tool(
    "send_coordination_message",
    channel_name="project-alpha",
    from_agent="amazon-q-1",
    message_type="task_complete",
    content=json.dumps({
        "task": "Update README.md",
        "status": "done",
        "files_modified": ["README.md"]
    })
)
```

### 5.2 Multi-Agent Task Decomposition

**Scenario**: 3 agents working in parallel on different modules.

```python
# Primary assigns tasks to 3 subordinates
for agent_id, module in [
    ("agent-1", "frontend"),
    ("agent-2", "backend"),
    ("agent-3", "docs")
]:
    await send_message(
        channel="parallel-work",
        type="task_assign",
        content={
            "module": module,
            "task": f"Implement feature X in {module}"
        }
    )

# Each subordinate polls for their task and works independently
# Primary polls for completion from all 3
completed = set()
while len(completed) < 3:
    messages = poll_channel(
        "parallel-work",
        filter_type="task_complete"
    )
    for msg in messages:
        completed.add(msg["from"])
```

---

## 6. Comparison with FIFO Pipe Approach

| Aspect | FIFO Pipes | MCP Resources (This Design) |
|--------|------------|----------------------------|
| **Standard** | Custom filesystem mechanism | MCP protocol primitive |
| **Persistence** | Lost on pipe close | Configurable (memory/DB) |
| **Multiple readers** | No (pipe consumed on read) | Yes (broadcast) |
| **Discoverability** | File paths | Resource URIs `coordination://` |
| **Client integration** | External file I/O | Native MCP resource reads |
| **Subscriptions** | Manual polling | MCP resource subscriptions |
| **Cross-platform** | Requires OS support | Works anywhere MCP runs |
| **Tooling** | None | MCP Inspector, debuggers |
| **Schema validation** | Manual | Built into MCP resources |
| **State management** | None | Session-scoped via MCP |

**Verdict**: MCP Resources are superior for this use case as they're:
- Protocol-native (no external dependencies)
- Cross-platform compatible
- Built-in persistence options
- Inspectable via standard MCP tools
- Support broadcast and subscriptions natively

---

## 7. Security & Safety Considerations

### 7.1 Agent Authentication

**Problem**: How do we verify agent identity?

**Solutions**:
1. **Shared Secret**: Require `X-Agent-Secret` header
2. **Session Tokens**: Issue JWT tokens on join
3. **Capability-Based**: Agents declare capabilities, server validates

**Recommendation**: Start with capability-based (trust model), add auth later.

### 7.2 Channel Isolation

**Problem**: Can agents read other channels?

**Solution**: Agents can only read channels they've joined.

```python
class ChannelStore:
    async def check_access(self, agent_id: str, channel: str) -> bool:
        """Verify agent has joined channel."""
        return agent_id in self.channel_members[channel]
```

### 7.3 Resource Limits

**Prevent abuse**:
- Max messages per channel: 10,000
- Max message size: 1 MB
- Max channels per agent: 100
- Message TTL: 24 hours (configurable)

### 7.4 Lock Expiry

**Prevent deadlocks**:
- All locks have `auto_release_seconds` (default: 5 min)
- Heartbeat mechanism to extend locks
- Forcible release by primary agent

---

## 8. Observability & Debugging

### 8.1 Structured Logging

```python
logger.info(
    "Coordination message sent",
    extra={
        "agent_id": from_agent,
        "channel": channel_name,
        "message_type": message_type,
        "message_id": message_id,
        "timestamp": timestamp
    }
)
```

### 8.2 Audit Resource

**Resource**: `coordination://audit`

Returns complete audit log of all coordination activity:
```json
[
    {
        "timestamp": "2025-11-15T10:30:00Z",
        "event": "channel_joined",
        "agent_id": "claude-desktop-1",
        "channel": "project-alpha",
        "role": "primary"
    },
    {
        "timestamp": "2025-11-15T10:30:05Z",
        "event": "message_sent",
        "agent_id": "claude-desktop-1",
        "channel": "project-alpha",
        "message_type": "init",
        "message_id": "msg-uuid"
    }
]
```

### 8.3 Metrics

**Expose metrics** (optional Prometheus endpoint):
- `coordination_messages_total{channel, type}`
- `coordination_agents_active{channel}`
- `coordination_locks_held{lock_name}`
- `coordination_lock_wait_seconds{lock_name}`

---

## 9. Testing Strategy

### 9.1 Unit Tests

```python
async def test_channel_message_ordering():
    """Messages returned in chronological order."""
    store = ChannelStore()
    await store.append("test", Message(type="init", content="A"))
    await store.append("test", Message(type="ack", content="B"))

    messages = await store.read("test")
    assert [m.content for m in messages] == ["A", "B"]

async def test_lock_acquisition():
    """Lock prevents concurrent access."""
    locks = LockManager()

    lock1 = await locks.acquire("resource-1", "agent-a", timeout=0)
    assert lock1["acquired"]

    lock2 = await locks.acquire("resource-1", "agent-b", timeout=0)
    assert not lock2["acquired"]
```

### 9.2 Integration Tests

```python
async def test_two_agent_coordination():
    """Full coordination flow with two agents."""
    # Start server
    async with TestMCPServer() as server:
        # Agent A joins
        client_a = MCPClient()
        await client_a.connect(server)
        await client_a.join_channel("test", "agent-a", "primary")
        await client_a.send_message("test", "agent-a", "init", "Hello")

        # Agent B joins
        client_b = MCPClient()
        await client_b.connect(server)
        await client_b.join_channel("test", "agent-b", "subordinate")

        # Agent B polls for A's message
        messages = await client_b.poll_channel("test")
        assert len(messages) == 1
        assert messages[0]["type"] == "init"
```

### 9.3 Chaos Testing

**Test resilience**:
- Kill agent mid-message
- Network partition between agents
- Concurrent lock requests (100+ agents)
- Message flood (10,000 messages/sec)

---

## 10. Migration & Backward Compatibility

### 10.1 Existing Users (Single-Agent)

**No changes required**:
- All existing tools continue to work
- Coordination is opt-in
- Zero performance impact if not used

### 10.2 Enabling Coordination

**Server side** (add flag):
```bash
hitl-mcp-cli --enable-coordination
```

**Client side** (detect capability):
```python
capabilities = await client.get_server_capabilities()
if "coordination" in capabilities.get("experimental", {}):
    # Use coordination features
```

---

## 11. Performance Considerations

### 11.1 Message Throughput

**Target**: 1,000 messages/second (single server instance)

**Optimizations**:
- In-memory channel storage (default)
- Batch polling (read multiple messages at once)
- Message size limits (1 MB max)

### 11.2 Concurrency

**Thread safety**:
- `asyncio.Lock` for channel writes
- Immutable messages (no modification after creation)
- Copy-on-read for message lists

### 11.3 Scaling

**Single server**: 10-100 agents
**Distributed** (future): Redis-backed channels

---

## 12. Open Questions for Expert Review

1. **Message Persistence**: Should we default to in-memory or SQLite?
   - *Pro in-memory*: Fast, simple, no dependencies
   - *Pro SQLite*: Survives restarts, audit trail

2. **Lock Implementation**: Use asyncio.Lock or distributed lock (Redis)?
   - *Pro asyncio*: Simple, no dependencies
   - *Pro Redis*: Multi-server support

3. **Subscription Mechanism**: Push (SSE) or pull (polling)?
   - *Pro push*: Real-time, efficient
   - *Pro pull*: Simpler, more reliable

4. **Agent Authentication**: Required from v1 or add later?
   - *Pro v1*: Security-first
   - *Pro later*: Faster MVP, trust model for early adopters

5. **Channel Discovery**: Should agents list all channels or only joined?
   - *Pro all*: Discovery, transparency
   - *Pro joined*: Privacy, isolation

---

## 13. Success Metrics

### 13.1 Technical Metrics

- ✅ Zero breaking changes to existing API
- ✅ <10ms latency for message send/poll
- ✅ Support 100+ concurrent agents per channel
- ✅ >95% test coverage for coordination module

### 13.2 Usability Metrics

- ✅ <10 lines of code to set up coordination
- ✅ Clear error messages for protocol violations
- ✅ Comprehensive documentation with examples

### 13.3 Adoption Metrics

- ✅ 3+ example workflows documented
- ✅ Integration guide for popular agent frameworks
- ✅ Demo video showing multi-agent coordination

---

## 14. Next Steps

1. **Expert Panel Review** (This Document)
   - Distributed systems expert
   - Multi-agent systems researcher
   - MCP protocol expert
   - Production system SRE

2. **Finalize Design** (Address expert feedback)

3. **Implement Phase 1** (Core Infrastructure)

4. **Internal Testing** (Dogfooding with real agents)

5. **Public Beta** (Release to early adopters)

6. **Production Release** (v1.0)

---

## Appendix A: Message Type Reference

### Discovery Phase
- `init`: Start coordination, declare role
- `acknowledgment`: Confirm receipt, accept role

### Synchronization Phase
- `sync`: Share configuration, rules, standards
- `capabilities`: Declare agent capabilities/limits
- `ownership`: Declare file ownership boundaries
- `coordination_complete`: Sync phase finished

### Operational Phase
- `question`: Request information from another agent
- `response`: Provide requested information
- `task_assign`: Assign work (primary → subordinate)
- `task_complete`: Report task completion
- `clarification`: Clarify previous message
- `progress`: Progress update (% complete, status)

### Control
- `ready`: Signal readiness for work
- `standby`: Enter passive mode, await instructions
- `stop`: Halt current activity
- `done`: Work finished, entering idle state

### Conflict Management
- `conflict_detected`: Report conflict (file, rule, decision)
- `conflict_resolved`: Primary's resolution decision

---

## Appendix B: Resource URI Schemes

```
coordination://channels              # List all channels
coordination://channels/{name}       # All messages in channel
coordination://channels/{name}/{id}  # Specific message

coordination://agents                # List all agents
coordination://agents/{id}           # Specific agent info

coordination://locks                 # List all locks
coordination://locks/{name}          # Specific lock status

coordination://audit                 # Full audit log
coordination://audit/{channel}       # Channel-specific audit
```

---

## Document History

- **2025-11-15**: Initial design (v1.0) - Ready for expert review

---

**Design Status**: 🟡 **Awaiting Expert Panel Review**

**Next Milestone**: Convene expert panel to validate architecture and identify gaps

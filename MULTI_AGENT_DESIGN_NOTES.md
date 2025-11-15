# Multi-Agent Coordination Design - Key Findings

This document summarizes critical architectural insights for designing multi-agent coordination features on top of HITL MCP CLI.

## Executive Summary

**Current State**: HITL MCP CLI is a **stateless, single-agent-centric** MCP server designed for interactive human-in-the-loop workflows.

**Multi-Agent Gap**: The system lacks state management, request correlation, and agent identification needed for coordinating multiple AI agents.

**Design Path**: Build coordination features as **layers on top** of existing tools rather than modifying core server.

---

## Critical Architectural Facts

### 1. Truly Stateless Design

The system maintains **zero request state**:

```
Request 1: Tool Call X
Request 2: Tool Call Y
Request 3: Tool Call Z

↓ No correlation between requests
↓ No shared context
↓ No history/audit trail
↓ Each call is completely independent
```

**Evidence**:
- No session storage (in-memory or persistent)
- No request ID tracking
- No context parameter passing
- Each tool function is self-contained
- No inter-tool communication mechanism

**Implication**: Multi-agent scenarios cannot identify which agent made which request or maintain agent-specific state.

### 2. Single Global Mutable State

Only one mutable global: `_needs_separator` in `ui/prompts.py:25`

```python
_needs_separator = False  # NOT thread-safe
```

**Purpose**: Track whether to print visual separator between prompts

**Issue**: Not thread-safe for concurrent requests

**Acceptable**: HITL prompts are sequential (human response time prevents concurrency)

**Lesson**: Even this minimal state has concurrency issues. Adding more global state would compound problems.

### 3. Single Terminal Interface

All UI output goes to single Rich console instance:

```python
console = Console()  # Global, singleton
```

**Consequence**: 
- Multiple agents' prompts would interleave on screen
- User wouldn't know which agent is asking
- Responses could be ambiguous

**For Multi-Agent**: Need UI separation (multiple terminals, async queues, or web UI)

### 4. Async-to-Sync Bridge via Executor

Tool functions are async but UI operations are blocking:

```python
@sync_to_async
def prompt_text(...) -> str:
    # This blocks in thread executor
    return inquirer.text(...).execute()
```

**Mechanism**:
```python
async def wrapper(*args, **kwargs):
    return await asyncio.get_event_loop().run_in_executor(
        None, lambda: func(*args, **kwargs)
    )
```

**Implication**:
- Blocking I/O doesn't block event loop (good)
- Unbounded thread pool (no backpressure)
- Works for single-agent, may need adjustment for multi-agent

### 5. Minimal Error Handling

Consistent error wrapping across all tools:

```python
try:
    result = await ui_function(...)
    return result
except KeyboardInterrupt:
    raise Exception("User cancelled input (Ctrl+C)") from None
except Exception as e:
    raise Exception(f"Operation failed: {str(e)}") from e
```

**Advantage**: Simple, predictable

**Gap**: No error context (which agent? which request? which step in workflow?)

---

## Message Flow Architecture

### Current Flow (Single Agent)

```
┌─────────────────────────────────────────────┐
│ AI Agent                                    │
│ (e.g., Claude via Claude Desktop)          │
└───────────────┬─────────────────────────────┘
                │
                │ HTTP POST
                │ {jsonrpc: "2.0", method: "tools/call", params: {...}}
                ↓
┌─────────────────────────────────────────────┐
│ FastMCP Server                              │
│ ├─ Deserialize JSON-RPC                    │
│ ├─ Validate parameters                      │
│ └─ Route to tool function                   │
└───────────────┬─────────────────────────────┘
                │
                │ Call tool_function(params)
                ↓
┌─────────────────────────────────────────────┐
│ Tool Function (async)                       │
│ ├─ Try: await ui_function(...)              │
│ ├─ Catch: KeyboardInterrupt, Exception      │
│ └─ Return: result or error                  │
└───────────────┬─────────────────────────────┘
                │
                │ await run_in_executor(...)
                ↓
┌─────────────────────────────────────────────┐
│ UI Layer (blocking in thread)               │
│ ├─ InquirerPy prompt                       │
│ ├─ Validation                               │
│ └─ Return: user input                       │
└───────────────┬─────────────────────────────┘
                │
                │ Serialize result
                ↓
┌─────────────────────────────────────────────┐
│ HTTP Response                               │
│ {jsonrpc: "2.0", result: {...}} or error    │
└───────────────┬─────────────────────────────┘
                │
                │
                ↓
┌─────────────────────────────────────────────┐
│ AI Agent (continues with result)            │
└─────────────────────────────────────────────┘
```

### What's Missing for Multi-Agent

```
Request Flow:
┌─────────────┐     ┌──────────────────┐
│ Agent A     │────▶│ HITL MCP Server  │
├─────────────┤     ├──────────────────┤
│ Tool Call 1 │     │ No request ID    │
│ Tool Call 3 │     │ No agent ID      │
└─────────────┘     │ No correlation   │
                    │ No sequencing    │
┌─────────────┐     │ No locking       │
│ Agent B     │────▶│                  │
├─────────────┤     │ Can't tell       │
│ Tool Call 2 │     │ which agent      │
│ Tool Call 4 │     │ made request     │
└─────────────┘     │                  │
                    │ Can't enforce    │
Request A.2 ≠ A.1  │ sequential order │
Request B.2 ≠ B.1  │                  │
                    │ Can't maintain   │
                    │ per-agent state  │
                    └──────────────────┘
```

---

## State Management Model

### Current (Single-Agent) Model

```
┌────────────────────────────────┐
│ Each Tool Call                 │
├────────────────────────────────┤
│                                │
│  Input Parameters              │
│  (from client)                 │
│        ↓                        │
│  [Tool Function]               │
│        ↓                        │
│  [UI Interaction]              │
│        ↓                        │
│  Return Result                 │
│  (to client)                   │
│                                │
│  ⚠️ NO STATE MAINTAINED       │
│  ⚠️ NO CONTEXT STORED         │
│  ⚠️ NO REQUEST TRACKING        │
│                                │
└────────────────────────────────┘
     Each call is isolated
```

### Required (Multi-Agent) Model

```
┌──────────────────────────────────────────┐
│ Request Enters System                    │
├──────────────────────────────────────────┤
│                                          │
│  1. Generate Request ID                  │
│  2. Store Session Context               │
│  3. Identify Agent                       │
│  4. Associate with Workflow             │
│        ↓                                 │
│  [Existing Tool Logic]                  │
│        ↓                                 │
│  5. Log Request Metadata                │
│  6. Update Session State                │
│  7. Return with Correlation Info        │
│                                          │
│  ✅ REQUEST_ID propagated              │
│  ✅ SESSION_DATA maintained            │
│  ✅ AGENT_ID tracked                   │
│  ✅ WORKFLOW_ID recorded               │
│                                          │
└──────────────────────────────────────────┘
   Built as layers on top of existing tools
```

---

## Required Infrastructure for Multi-Agent Support

### Layer 1: Request Correlation

**Add to All Requests**:
```python
{
    "request_id": "req-123e4567-e89b-12d3-a456-426614174000",
    "agent_id": "agent-claude-desktop",
    "workflow_id": "workflow-abc123",
    "timestamp": 1731676800
}
```

**Implementation**:
- Middleware to inject correlation data
- Pass through tool calls
- Include in responses
- Log for audit trail

### Layer 2: Session Management

**Store Per-Session**:
```python
{
    "session_id": "sess-xyz789",
    "agent_id": "agent-claude",
    "state": {...},
    "created_at": timestamp,
    "last_activity": timestamp,
    "tool_calls": [request_ids],
    "context": {...}
}
```

**Implementation**:
- In-memory dict (single-process) or
- Redis (distributed) or
- Database (persistent)

### Layer 3: Agent Identification

**Options**:
1. From HTTP header: `X-Agent-ID: agent-claude`
2. From request parameter: `{"agent_id": "..."}`
3. From authentication: Parse JWT/API key

**Implementation**:
- Middleware to extract agent ID
- Validate against allowed agents
- Associate with request context

### Layer 4: Coordination Primitives

**For Sequential Ordering**:
- Semaphores/locks per agent
- Queue system for requests
- Transaction boundaries

**For Parallel Execution**:
- Event system
- Condition variables
- Resource pools

**For Distributed State**:
- Distributed locks (Redis/etc)
- State synchronization
- Conflict resolution

### Layer 5: UI Separation

**Current Problem**: All output to single console

**Solution Options**:

**Option A: Async Queue**
```python
class PromptQueue:
    async def request_text(self, agent_id, prompt):
        # Queue prompt
        # Wait for user input
        # Return result to agent
```

**Option B: Multiple Terminals**
```
┌──────────────────────────────┐
│ Terminal 1 (Agent A prompts) │
├──────────────────────────────┤
│ ✏️  Enter project name: _    │
│                              │
└──────────────────────────────┘

┌──────────────────────────────┐
│ Terminal 2 (Agent B prompts) │
├──────────────────────────────┤
│ 🎯 Select deployment env:    │
│  Dev                          │
│  Staging                      │
│  Production                   │
└──────────────────────────────┘
```

**Option C: Web UI**
```
HTTP Server
  ├─ Agent A connects to /prompts/agent-a
  ├─ Agent B connects to /prompts/agent-b
  └─ User views /dashboard
      ├─ Shows pending prompts
      ├─ Responds to each
      └─ Views history
```

### Layer 6: Observability

**Required**:
- Structured logging with request ID
- Distributed tracing
- Metrics (request count, latency, errors)
- Audit log of all interactions

**Implementation**:
```python
logger.info(
    "Tool called",
    extra={
        "request_id": request_id,
        "agent_id": agent_id,
        "tool_name": tool_name,
        "timestamp": timestamp
    }
)
```

---

## Design Recommendations

### DO

1. **Build on Top, Not Inside**
   - Create wrapper layer above core tools
   - Don't modify server.py, ui/prompts.py
   - Maintain backward compatibility
   - Use decorators/middleware pattern

2. **Add Correlation First**
   - Request ID is foundation for debugging
   - Add timestamp, agent ID, workflow ID
   - Thread through all layers
   - Include in all logging

3. **Make State Optional**
   - Session management should be opt-in
   - Single-agent workflows should work unchanged
   - Multi-agent workflows opt into coordination
   - Support both modes simultaneously

4. **Separate Concerns**
   - Correlation layer ≠ session layer ≠ UI layer
   - Each can be implemented independently
   - Can be swapped/customized per deployment
   - Clear interfaces between layers

5. **Test Thoroughly**
   - Add integration tests with multiple agents
   - Test concurrent requests
   - Test error scenarios per-agent
   - Test state consistency

### DON'T

1. **Don't Modify Core Tools**
   - Breaking change for existing users
   - Limits adoption of coordination features
   - Harder to maintain compatibility

2. **Don't Add Global State to prompts.py**
   - Already has thread-safety issues
   - Any mutable global is dangerous
   - Use parameters instead

3. **Don't Assume Sequential Execution**
   - Users may call multiple agents
   - Concurrent requests will happen
   - Design for concurrent safety

4. **Don't Lose Simplicity**
   - Original design is elegant
   - Each layer should be understandable
   - Don't over-engineer early
   - Start with what's minimally needed

5. **Don't Hardcode Coordination Strategy**
   - Different users need different models
   - Some want sequential, some parallel
   - Some need locking, some don't
   - Make it pluggable

---

## Proposed Incremental Implementation

### Phase 1: Request Correlation (Low Risk)
```python
# Add middleware
def correlation_middleware(request):
    request_id = request.headers.get("X-Request-ID", generate_id())
    request.state.request_id = request_id
    return request

# Thread through tools
# Add to all logging
# Return in responses
```

**Benefits**:
- Enables debugging
- No state management
- Backward compatible
- Low complexity

**Effort**: 2-4 hours

### Phase 2: Session Storage (Medium Risk)
```python
# Simple in-memory session manager
class SessionManager:
    def __init__(self):
        self.sessions = {}
    
    async def get_or_create(self, session_id):
        if session_id not in self.sessions:
            self.sessions[session_id] = {"created": now(), "state": {}}
        return self.sessions[session_id]
```

**Benefits**:
- Maintain cross-request context
- Per-agent state isolation
- Conversation history

**Effort**: 4-6 hours

### Phase 3: Agent Identification (Medium Risk)
```python
# Extract from request
def get_agent_id(request) -> str:
    # Option 1: Header
    return request.headers.get("X-Agent-ID")
    # Option 2: Parameter
    return request.params.get("agent_id")
```

**Benefits**:
- Track which agent made request
- Enable per-agent policies
- Route prompts correctly

**Effort**: 1-2 hours

### Phase 4: UI Separation (High Risk)
```python
# Async queue-based prompt routing
class PromptQueue:
    async def enqueue(self, agent_id, prompt_params):
        # Queue for user
        # Wait for response
        # Return to agent
```

**Benefits**:
- Prevent prompt mixing
- Show agent context
- Improve UX

**Effort**: 8-12 hours

### Phase 5: Coordination Primitives (High Risk)
```python
# Distributed lock per agent
class AgentLock:
    async def acquire(self, agent_id):
        # Ensure sequential execution for agent
        # Or parallel for different agents
```

**Benefits**:
- Enforce sequential or parallel execution
- Prevent race conditions
- Enable transactions

**Effort**: 8-16 hours

---

## Architecture for Multi-Agent Version

```
┌────────────────────────────────────────────┐
│ Existing HITL MCP Server                   │
│ ├─ server.py (unchanged)                   │
│ ├─ ui/prompts.py (unchanged)               │
│ └─ cli.py (unchanged)                      │
└──────────────┬─────────────────────────────┘
               │
┌──────────────▼─────────────────────────────┐
│ Coordination Layers (NEW)                  │
├────────────────────────────────────────────┤
│                                            │
│  Layer 1: Correlation Middleware           │
│  ├─ Inject request ID                      │
│  ├─ Track agent ID                         │
│  └─ Log metadata                           │
│                                            │
│  Layer 2: Session Manager                  │
│  ├─ Per-session state storage              │
│  ├─ Conversation history                   │
│  └─ Context maintenance                    │
│                                            │
│  Layer 3: Agent Identification             │
│  ├─ Extract agent ID                       │
│  ├─ Validate against whitelist             │
│  └─ Route to correct session               │
│                                            │
│  Layer 4: Prompt Router                    │
│  ├─ Queue prompts by agent                 │
│  ├─ Show agent context                     │
│  └─ Deliver responses correctly            │
│                                            │
│  Layer 5: Coordination Primitives          │
│  ├─ Locks/semaphores                       │
│  ├─ Events/conditions                      │
│  └─ Transaction boundaries                 │
│                                            │
│  Layer 6: Observability                    │
│  ├─ Structured logging                     │
│  ├─ Distributed tracing                    │
│  └─ Audit logging                          │
│                                            │
└────────────────────────────────────────────┘
```

---

## Summary

### Current State
- Stateless, single-agent focused
- Minimal global state (not thread-safe)
- Single terminal UI
- No request correlation
- Works great for single-agent HITL

### For Multi-Agent
- Add layers on top (don't modify core)
- Implement incrementally
- Start with correlation (debugging)
- Add session/state management
- Solve UI separation last
- Use pluggable architecture

### Key Insight
The system's simplicity and statelessness are **strengths for single-agent** but **gaps for multi-agent**. Design coordination features as optional layers that don't break existing usage.


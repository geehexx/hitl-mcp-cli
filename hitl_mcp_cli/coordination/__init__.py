"""Multi-agent coordination extension for HITL MCP Server.

This module provides MCP-native primitives for agent-to-agent communication:
- Channel Resources: `coordination://channel-name` for message passing
- Coordination Tools: join, send, poll, acquire_lock, release_lock
- Message Protocol: Structured schemas for discovery, sync, work, and conflict resolution

Key Design Principles:
- MCP-Native: Uses MCP resources and tools (no external dependencies)
- Layered: Built on top of existing HITL server (backward compatible)
- Opt-In: Single-agent workflows continue unchanged
- Secure: Authentication, authorization, and message signing
"""

from .auth import Agent, AuthManager
from .channels import Channel, ChannelStore, Message
from .heartbeat import AgentHealth, HeartbeatManager
from .locks import Lock, LockManager
from .ratelimit import RateLimiter, TokenBucket
from .schema import CoordinationError, MessageSchema, MessageType
from .signing import MessageSigner

__all__ = [
    "Agent",
    "AgentHealth",
    "AuthManager",
    "Channel",
    "ChannelStore",
    "CoordinationError",
    "HeartbeatManager",
    "Lock",
    "LockManager",
    "Message",
    "MessageSchema",
    "MessageSigner",
    "MessageType",
    "RateLimiter",
    "TokenBucket",
]

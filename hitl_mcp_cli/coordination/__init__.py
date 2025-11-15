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

from .channels import Channel, ChannelStore, Message
from .locks import Lock, LockManager
from .schema import CoordinationError, MessageSchema, MessageType

__all__ = [
    "Channel",
    "ChannelStore",
    "CoordinationError",
    "Lock",
    "LockManager",
    "Message",
    "MessageSchema",
    "MessageType",
]

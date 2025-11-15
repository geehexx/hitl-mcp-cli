"""Enhanced MCP Tool definitions with auth, rate limiting, and heartbeat."""

import json
import logging
from typing import Any, Literal

from fastmcp import FastMCP

from .auth import AuthManager
from .channels import ChannelStore
from .heartbeat import HeartbeatManager
from .locks import LockManager
from .ratelimit import RateLimiter
from .schema import AuthenticationError, AuthorizationError, MessageType

logger = logging.getLogger(__name__)


def register_coordination_tools_enhanced(
    mcp: FastMCP,
    channel_store: ChannelStore,
    lock_manager: LockManager,
    auth_manager: AuthManager | None = None,
    rate_limiter: RateLimiter | None = None,
    heartbeat_manager: HeartbeatManager | None = None,
) -> None:
    """Register enhanced coordination tools with auth, rate limiting, and heartbeat.

    Args:
        mcp: FastMCP server instance
        channel_store: Channel storage backend
        lock_manager: Lock management backend
        auth_manager: Optional authentication manager
        rate_limiter: Optional rate limiter
        heartbeat_manager: Optional heartbeat manager
    """
    # Use dummy implementations if not provided (backward compat)
    has_auth = auth_manager is not None
    has_rate_limit = rate_limiter is not None
    has_heartbeat = heartbeat_manager is not None

    @mcp.tool()
    async def join_coordination_channel(
        channel_name: str,
        agent_id: str,
        api_key: str | None = None,
        role: Literal["primary", "subordinate"] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Join a coordination channel (with optional authentication)."""
        # Authenticate if enabled
        if has_auth and api_key:
            if not auth_manager.authenticate(agent_id, api_key):
                raise AuthenticationError(f"Invalid credentials for agent {agent_id}")

            if not auth_manager.verify_channel_access(agent_id, channel_name):
                raise AuthorizationError(f"Agent {agent_id} not allowed in channel {channel_name}")

        # Rate limit check
        if has_rate_limit:
            await rate_limiter.check(agent_id, "join_channel")

        result = await channel_store.join_channel(channel_name, agent_id)

        # Send join announcement if role specified
        if role:
            await channel_store.append(
                channel_name=channel_name,
                from_agent=agent_id,
                message_type=MessageType.INIT,
                content=json.dumps({"role": role, "metadata": metadata or {}}),
            )

        return result

    @mcp.tool()
    async def send_coordination_message(
        channel_name: str,
        from_agent: str,
        message_type: Literal[
            "init",
            "acknowledgment",
            "sync",
            "capabilities",
            "ownership",
            "coordination_complete",
            "question",
            "response",
            "task_assign",
            "task_complete",
            "clarification",
            "progress",
            "ready",
            "standby",
            "stop",
            "done",
            "conflict_detected",
            "conflict_resolved",
        ],
        content: str,
        api_key: str | None = None,
        metadata: dict[str, Any] | None = None,
        reply_to: str | None = None,
    ) -> dict[str, Any]:
        """Send a coordination message (with optional authentication)."""
        # Authenticate
        if has_auth and api_key:
            if not auth_manager.authenticate(from_agent, api_key):
                raise AuthenticationError(f"Invalid credentials for agent {from_agent}")

            if not auth_manager.verify_channel_access(from_agent, channel_name):
                raise AuthorizationError(f"Agent {from_agent} not allowed in channel {channel_name}")

            if not auth_manager.verify_permission(from_agent, "write"):
                raise AuthorizationError(f"Agent {from_agent} lacks write permission")

        # Rate limit
        if has_rate_limit:
            await rate_limiter.check(from_agent, "send_message")

        # Parse content if JSON
        parsed_content: str | dict = content
        try:
            parsed_content = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            pass

        # Convert message type
        msg_type = MessageType(message_type)

        # Append message
        message_id = await channel_store.append(
            channel_name=channel_name,
            from_agent=from_agent,
            message_type=msg_type,
            content=parsed_content,
            metadata=metadata or {},
            reply_to=reply_to,
        )

        message = await channel_store.get_message(channel_name, message_id)

        return {
            "message_id": message_id,
            "timestamp": message.timestamp if message else 0,
            "channel_uri": f"coordination://{channel_name}/{message_id}",
        }

    @mcp.tool()
    async def poll_coordination_channel(
        channel_name: str,
        agent_id: str,
        api_key: str | None = None,
        since_message_id: str | None = None,
        filter_type: str | None = None,
        max_messages: int = 100,
    ) -> dict[str, Any]:
        """Poll channel for messages (with optional authentication)."""
        # Authenticate
        if has_auth and api_key:
            if not auth_manager.authenticate(agent_id, api_key):
                raise AuthenticationError(f"Invalid credentials for agent {agent_id}")

            if not auth_manager.verify_channel_access(agent_id, channel_name):
                raise AuthorizationError(f"Agent {agent_id} not allowed in channel {channel_name}")

            if not auth_manager.verify_permission(agent_id, "read"):
                raise AuthorizationError(f"Agent {agent_id} lacks read permission")

        # Rate limit
        if has_rate_limit:
            await rate_limiter.check(agent_id, "poll_channel")

        messages = await channel_store.read(
            channel_name=channel_name,
            since_message_id=since_message_id,
            filter_type=filter_type,
            max_messages=max_messages,
        )

        return {
            "messages": [msg.to_dict() for msg in messages],
            "has_more": len(messages) == max_messages,
            "latest_id": messages[-1].id if messages else None,
        }

    @mcp.tool()
    async def acquire_coordination_lock(
        lock_name: str,
        agent_id: str,
        api_key: str | None = None,
        timeout_seconds: int = 30,
        auto_release_seconds: int = 300,
    ) -> dict[str, Any]:
        """Acquire distributed lock (with optional authentication)."""
        # Authenticate
        if has_auth and api_key:
            if not auth_manager.authenticate(agent_id, api_key):
                raise AuthenticationError(f"Invalid credentials for agent {agent_id}")

            if not auth_manager.verify_permission(agent_id, "lock"):
                raise AuthorizationError(f"Agent {agent_id} lacks lock permission")

        # Rate limit
        if has_rate_limit:
            await rate_limiter.check(agent_id, "acquire_lock")

        result = await lock_manager.acquire(
            lock_name=lock_name,
            agent_id=agent_id,
            timeout_seconds=timeout_seconds,
            auto_release_seconds=auto_release_seconds,
        )

        return result

    @mcp.tool()
    async def release_coordination_lock(
        lock_id: str, agent_id: str, api_key: str | None = None
    ) -> dict[str, bool]:
        """Release lock (with optional authentication)."""
        # Authenticate
        if has_auth and api_key:
            if not auth_manager.authenticate(agent_id, api_key):
                raise AuthenticationError(f"Invalid credentials for agent {agent_id}")

        result = await lock_manager.release(lock_id=lock_id, agent_id=agent_id)
        return result

    @mcp.tool()
    async def heartbeat(agent_id: str, api_key: str | None = None, metadata: dict | None = None) -> dict:
        """Send heartbeat to indicate agent liveness."""
        # Authenticate
        if has_auth and api_key:
            if not auth_manager.authenticate(agent_id, api_key):
                raise AuthenticationError(f"Invalid credentials for agent {agent_id}")

        if not has_heartbeat:
            return {"acknowledged": False, "heartbeat_disabled": True}

        # Rate limit
        if has_rate_limit:
            await rate_limiter.check(agent_id, "heartbeat")

        result = await heartbeat_manager.heartbeat(agent_id, metadata)
        return result

    @mcp.tool()
    async def get_rate_limit_status(agent_id: str, api_key: str | None = None) -> dict:
        """Get rate limit status for agent."""
        if has_auth and api_key:
            if not auth_manager.authenticate(agent_id, api_key):
                raise AuthenticationError("Invalid credentials")

        if not has_rate_limit:
            return {"rate_limiting_disabled": True}

        return await rate_limiter.get_status(agent_id)

    @mcp.tool()
    async def leave_coordination_channel(
        channel_name: str, agent_id: str, api_key: str | None = None
    ) -> dict[str, bool]:
        """Leave a coordination channel."""
        if has_auth and api_key:
            if not auth_manager.authenticate(agent_id, api_key):
                raise AuthenticationError("Invalid credentials")

        await channel_store.leave_channel(channel_name, agent_id)
        return {"left": True}

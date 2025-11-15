"""MCP Tool definitions for multi-agent coordination."""

import json
from typing import Any, Literal

from fastmcp import FastMCP

from .channels import ChannelStore
from .locks import LockManager
from .schema import MessageType


def register_coordination_tools(mcp: FastMCP, channel_store: ChannelStore, lock_manager: LockManager) -> None:
    """Register coordination tools with MCP server.

    Tools enable agents to:
    - Join channels and communicate
    - Send/receive coordination messages
    - Acquire/release locks for exclusive access

    Args:
        mcp: FastMCP server instance
        channel_store: Channel storage backend
        lock_manager: Lock management backend
    """

    @mcp.tool()
    async def join_coordination_channel(
        channel_name: str,
        agent_id: str,
        role: Literal["primary", "subordinate"] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Join a coordination channel to communicate with other agents.

        Agents must join a channel before sending or receiving messages.
        Channels are created automatically on first join.

        Args:
            channel_name: Unique channel identifier (e.g., "project-alpha")
            agent_id: Unique identifier for this agent (e.g., "claude-desktop-1")
            role: Agent's role in coordination ("primary" has decision authority)
            metadata: Additional agent info (capabilities, session_id, etc.)

        Returns:
            {
                "channel_name": "project-alpha",
                "agent_id": "claude-desktop-1",
                "joined_at": 1731676800.0,
                "other_agents": ["amazon-q-1"],
                "message_count": 5
            }

        Example:
            result = await join_coordination_channel(
                channel_name="my-project",
                agent_id="claude-desktop",
                role="primary",
                metadata={"knowledge_base": True}
            )
        """
        result = await channel_store.join_channel(channel_name, agent_id)

        # Optionally send join announcement
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
        metadata: dict[str, Any] | None = None,
        reply_to: str | None = None,
    ) -> dict[str, Any]:
        """Send a coordination message to a channel.

        Messages are broadcast to all agents in the channel.
        Use structured message types for protocol compliance.

        Args:
            channel_name: Target channel
            from_agent: Sender agent ID
            message_type: Structured message type (see MessageType enum)
            content: Message payload (JSON string or plain text)
            metadata: Additional context (files, status, etc.)
            reply_to: Message ID being replied to (for threading)

        Returns:
            {
                "message_id": "msg-uuid",
                "timestamp": 1731676800.0,
                "channel_uri": "coordination://project-alpha/msg-uuid"
            }

        Example:
            result = await send_coordination_message(
                channel_name="my-project",
                from_agent="claude-desktop",
                message_type="task_assign",
                content='{"task": "Update README", "files": ["README.md"]}',
                metadata={"priority": "high"}
            )
        """
        # Parse content if it's JSON
        parsed_content: str | dict = content
        try:
            parsed_content = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            pass  # Keep as string

        # Convert string message_type to enum
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

        # Get the message we just created
        message = await channel_store.get_message(channel_name, message_id)
        timestamp = message.timestamp if message else 0

        return {
            "message_id": message_id,
            "timestamp": timestamp,
            "channel_uri": f"coordination://{channel_name}/{message_id}",
        }

    @mcp.tool()
    async def poll_coordination_channel(
        channel_name: str,
        since_message_id: str | None = None,
        filter_type: str | None = None,
        max_messages: int = 100,
    ) -> dict[str, Any]:
        """Poll channel for new messages (non-blocking).

        Use this to check for new messages from other agents.
        For real-time updates, prefer resource subscriptions if supported.

        Args:
            channel_name: Channel to poll
            since_message_id: Only return messages after this ID
            filter_type: Only return messages of this type
            max_messages: Maximum messages to return (default: 100)

        Returns:
            {
                "messages": [
                    {
                        "id": "msg-uuid",
                        "from_agent": "agent-id",
                        "timestamp": 1731676800.0,
                        "type": "question",
                        "content": "...",
                        "sequence": 5,
                        "metadata": {},
                        "reply_to": null
                    }
                ],
                "has_more": false,
                "latest_id": "msg-uuid"
            }

        Example:
            result = await poll_coordination_channel(
                channel_name="my-project",
                since_message_id="msg-123",
                filter_type="task_complete"
            )
        """
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
        timeout_seconds: int = 30,
        auto_release_seconds: int = 300,
    ) -> dict[str, Any]:
        """Acquire distributed lock for exclusive operations.

        Use locks to ensure only one agent modifies shared resources.
        Locks automatically release after auto_release_seconds to prevent deadlocks.

        Args:
            lock_name: Unique lock identifier (e.g., "file:/path/to/file")
            agent_id: Agent requesting lock
            timeout_seconds: How long to wait for lock (0 = fail immediately)
            auto_release_seconds: Automatically release after this duration (default: 300s)

        Returns:
            {
                "acquired": true,
                "lock_id": "lock-uuid",
                "held_by": "agent-id",
                "expires_at": 1731677100.0
            }

        Example:
            lock = await acquire_coordination_lock(
                lock_name="file:config.yaml",
                agent_id="claude-desktop",
                timeout_seconds=10
            )

            if lock["acquired"]:
                # Modify file
                ...
                await release_coordination_lock(lock["lock_id"], "claude-desktop")
        """
        result = await lock_manager.acquire(
            lock_name=lock_name,
            agent_id=agent_id,
            timeout_seconds=timeout_seconds,
            auto_release_seconds=auto_release_seconds,
        )

        return result

    @mcp.tool()
    async def release_coordination_lock(lock_id: str, agent_id: str) -> dict[str, bool]:
        """Release a previously acquired lock.

        Args:
            lock_id: Lock ID from acquire_coordination_lock
            agent_id: Agent releasing lock (must match acquirer)

        Returns:
            {"released": true}

        Raises:
            ValueError: If lock doesn't exist or agent doesn't own it

        Example:
            await release_coordination_lock(
                lock_id="lock-uuid",
                agent_id="claude-desktop"
            )
        """
        result = await lock_manager.release(lock_id=lock_id, agent_id=agent_id)
        return result

    @mcp.tool()
    async def list_coordination_locks() -> dict[str, Any]:
        """List all active locks in the system.

        Returns:
            {
                "locks": [
                    {
                        "lock_id": "lock-uuid",
                        "name": "file:config.yaml",
                        "held_by": "agent-a",
                        "acquired_at": 1731676800.0,
                        "expires_at": 1731677100.0,
                        "seconds_remaining": 300
                    }
                ]
            }

        Example:
            locks = await list_coordination_locks()
            for lock in locks["locks"]:
                print(f"{lock['name']} held by {lock['held_by']}")
        """
        locks = await lock_manager.list_locks()
        return {"locks": locks}

    @mcp.tool()
    async def leave_coordination_channel(channel_name: str, agent_id: str) -> dict[str, bool]:
        """Leave a coordination channel.

        Agents should leave channels when done to clean up resources.

        Args:
            channel_name: Channel to leave
            agent_id: Agent leaving

        Returns:
            {"left": true}

        Example:
            await leave_coordination_channel(
                channel_name="my-project",
                agent_id="claude-desktop"
            )
        """
        await channel_store.leave_channel(channel_name, agent_id)
        return {"left": True}

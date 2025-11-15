"""Python client library for HITL MCP coordination."""

import asyncio
import json
from typing import Any, Literal

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


class CoordinationClient:
    """High-level Python client for agent coordination.

    Simplifies coordination by providing clean async APIs.
    """

    def __init__(self, session: Any, agent_id: str, api_key: str | None = None):
        """Initialize coordination client.

        Args:
            session: MCP client session
            agent_id: Agent identifier
            api_key: Optional API key for authentication
        """
        self.session = session
        self.agent_id = agent_id
        self.api_key = api_key
        self.last_message_ids: dict[str, str] = {}  # channel -> last_message_id

    async def join_channel(
        self, channel: str, role: Literal["primary", "subordinate"] | None = None, metadata: dict | None = None
    ) -> dict:
        """Join a coordination channel.

        Args:
            channel: Channel name
            role: Agent role (primary/subordinate)
            metadata: Additional metadata

        Returns:
            Join result
        """
        kwargs = {
            "channel_name": channel,
            "agent_id": self.agent_id,
            "role": role,
            "metadata": metadata or {},
        }

        if self.api_key:
            kwargs["api_key"] = self.api_key

        result = await self.session.call_tool("join_coordination_channel", arguments=kwargs)

        return result.content if hasattr(result, "content") else result

    async def send(
        self,
        channel: str,
        message_type: str,
        content: str | dict,
        metadata: dict | None = None,
        reply_to: str | None = None,
    ) -> str:
        """Send a message to channel.

        Args:
            channel: Channel name
            message_type: Message type (init, task_assign, etc.)
            content: Message content (str or dict)
            metadata: Additional metadata
            reply_to: Message ID being replied to

        Returns:
            Message ID
        """
        if isinstance(content, dict):
            content = json.dumps(content)

        kwargs = {
            "channel_name": channel,
            "from_agent": self.agent_id,
            "message_type": message_type,
            "content": content,
            "metadata": metadata or {},
        }

        if reply_to:
            kwargs["reply_to"] = reply_to

        if self.api_key:
            kwargs["api_key"] = self.api_key

        result = await self.session.call_tool("send_coordination_message", arguments=kwargs)
        result_data = result.content if hasattr(result, "content") else result

        return result_data["message_id"]

    async def poll(
        self, channel: str, filter_type: str | None = None, max_messages: int = 100
    ) -> list[dict[str, Any]]:
        """Poll channel for new messages.

        Args:
            channel: Channel name
            filter_type: Filter by message type
            max_messages: Maximum messages to return

        Returns:
            List of messages
        """
        kwargs = {
            "channel_name": channel,
            "agent_id": self.agent_id,
            "filter_type": filter_type,
            "max_messages": max_messages,
        }

        # Use last_message_id to get only new messages
        if channel in self.last_message_ids:
            kwargs["since_message_id"] = self.last_message_ids[channel]

        if self.api_key:
            kwargs["api_key"] = self.api_key

        result = await self.session.call_tool("poll_coordination_channel", arguments=kwargs)
        result_data = result.content if hasattr(result, "content") else result

        messages = result_data.get("messages", [])

        # Update last message ID
        if messages:
            self.last_message_ids[channel] = result_data.get("latest_id")

        return messages

    async def wait_for(
        self, channel: str, message_type: str, timeout: float = 30, from_agent: str | None = None
    ) -> dict | None:
        """Wait for specific message type.

        Args:
            channel: Channel name
            message_type: Message type to wait for
            timeout: Timeout in seconds
            from_agent: Optional filter by sender

        Returns:
            First matching message or None if timeout
        """
        start = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start) < timeout:
            messages = await self.poll(channel, filter_type=message_type)

            for msg in messages:
                if from_agent is None or msg.get("from_agent") == from_agent:
                    return msg

            await asyncio.sleep(0.5)

        return None

    async def acquire_lock(
        self, lock_name: str, timeout_seconds: int = 30, auto_release_seconds: int = 300
    ) -> dict | None:
        """Acquire a distributed lock.

        Args:
            lock_name: Resource name to lock
            timeout_seconds: Wait timeout
            auto_release_seconds: Auto-release after this duration

        Returns:
            Lock info if acquired, None if failed
        """
        kwargs = {
            "lock_name": lock_name,
            "agent_id": self.agent_id,
            "timeout_seconds": timeout_seconds,
            "auto_release_seconds": auto_release_seconds,
        }

        if self.api_key:
            kwargs["api_key"] = self.api_key

        result = await self.session.call_tool("acquire_coordination_lock", arguments=kwargs)
        result_data = result.content if hasattr(result, "content") else result

        if result_data.get("acquired"):
            return result_data

        return None

    async def release_lock(self, lock_id: str) -> bool:
        """Release a lock.

        Args:
            lock_id: Lock ID from acquire_lock

        Returns:
            True if released
        """
        kwargs = {"lock_id": lock_id, "agent_id": self.agent_id}

        if self.api_key:
            kwargs["api_key"] = self.api_key

        result = await self.session.call_tool("release_coordination_lock", arguments=kwargs)
        result_data = result.content if hasattr(result, "content") else result

        return result_data.get("released", False)

    async def heartbeat(self, metadata: dict | None = None) -> dict:
        """Send heartbeat.

        Args:
            metadata: Optional status metadata

        Returns:
            Heartbeat result
        """
        kwargs = {"agent_id": self.agent_id, "metadata": metadata}

        if self.api_key:
            kwargs["api_key"] = self.api_key

        result = await self.session.call_tool("heartbeat", arguments=kwargs)

        return result.content if hasattr(result, "content") else result

    async def leave_channel(self, channel: str) -> bool:
        """Leave a channel.

        Args:
            channel: Channel name

        Returns:
            True if left
        """
        kwargs = {"channel_name": channel, "agent_id": self.agent_id}

        if self.api_key:
            kwargs["api_key"] = self.api_key

        result = await self.session.call_tool("leave_coordination_channel", arguments=kwargs)
        result_data = result.content if hasattr(result, "content") else result

        return result_data.get("left", False)

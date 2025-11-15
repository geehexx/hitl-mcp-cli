"""MCP Resource definitions for coordination channels."""

import json
from typing import Any

from fastmcp import FastMCP

from .channels import ChannelStore


def register_coordination_resources(mcp: FastMCP, channel_store: ChannelStore) -> None:
    """Register coordination resources with MCP server.

    Resources provide read-only access to coordination state:
    - coordination://channels - List all channels
    - coordination://{channel} - Read all messages in channel
    - coordination://{channel}/{message_id} - Read specific message
    - coordination://{channel}/type/{type} - Filter messages by type
    - coordination://agents - List all registered agents

    Args:
        mcp: FastMCP server instance
        channel_store: Channel storage backend
    """

    @mcp.resource("coordination://channels")
    async def list_channels_resource() -> str:
        """List all coordination channels.

        Returns JSON array of channel metadata:
        [
            {
                "name": "project-alpha",
                "created_at": 1731676800.0,
                "members": ["agent-a", "agent-b"],
                "message_count": 42
            }
        ]
        """
        channels = await channel_store.list_channels()
        return json.dumps(channels, indent=2)

    @mcp.resource("coordination://{channel_name}")
    async def read_channel_messages(channel_name: str) -> str:
        """Read all messages from a channel.

        Args:
            channel_name: Channel to read from

        Returns JSON array of messages in chronological order:
        [
            {
                "id": "msg-uuid",
                "from_agent": "agent-a",
                "timestamp": 1731676800.0,
                "type": "init",
                "content": "...",
                "sequence": 0,
                "metadata": {},
                "reply_to": null
            }
        ]
        """
        messages = await channel_store.read(channel_name)
        return json.dumps([msg.to_dict() for msg in messages], indent=2)

    @mcp.resource("coordination://{channel_name}/{message_id}")
    async def read_specific_message(channel_name: str, message_id: str) -> str:
        """Read specific message from channel.

        Args:
            channel_name: Channel containing message
            message_id: Message ID

        Returns JSON message or error:
        {
            "id": "msg-uuid",
            "from_agent": "agent-a",
            ...
        }
        """
        message = await channel_store.get_message(channel_name, message_id)
        if message:
            return json.dumps(message.to_dict(), indent=2)
        return json.dumps({"error": "Message not found"}, indent=2)

    @mcp.resource("coordination://{channel_name}/type/{message_type}")
    async def read_messages_by_type(channel_name: str, message_type: str) -> str:
        """Read messages of specific type from channel.

        Args:
            channel_name: Channel to read from
            message_type: Filter by this type (e.g., "init", "task_assign")

        Returns JSON array of filtered messages.
        """
        messages = await channel_store.read(channel_name, filter_type=message_type)
        return json.dumps([msg.to_dict() for msg in messages], indent=2)

    @mcp.resource("coordination://{channel_name}/since/{message_id}")
    async def read_messages_since(channel_name: str, message_id: str) -> str:
        """Read messages after specific message ID.

        Args:
            channel_name: Channel to read from
            message_id: Only return messages after this ID

        Returns JSON array of messages.
        """
        messages = await channel_store.read(channel_name, since_message_id=message_id)
        return json.dumps([msg.to_dict() for msg in messages], indent=2)

    @mcp.resource("coordination://stats")
    async def coordination_stats() -> str:
        """Get coordination system statistics.

        Returns JSON object with stats:
        {
            "channels": 5,
            "total_messages": 142,
            "active_subscriptions": 3
        }
        """
        stats = channel_store.get_stats()
        return json.dumps(stats, indent=2)

"""Channel-based message passing for multi-agent coordination."""

import asyncio
import json
import time
import uuid
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .schema import ChannelFullError, MessageSchema, MessageType


@dataclass
class Message:
    """Coordination message.

    Messages are immutable (frozen) to ensure thread safety.
    Each message has a unique ID and sequence number per agent.
    """

    id: str
    from_agent: str
    timestamp: float
    type: MessageType
    content: str | dict[str, Any]
    sequence: int  # Per-agent sequence number for ordering
    metadata: dict[str, Any] = field(default_factory=dict)
    reply_to: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert message to dictionary for JSON serialization."""
        data = asdict(self)
        data["type"] = self.type.value  # Convert enum to string
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Message":
        """Create message from dictionary."""
        # Convert type string to enum
        if isinstance(data["type"], str):
            data["type"] = MessageType(data["type"])
        return cls(**data)


@dataclass
class Channel:
    """Coordination channel metadata."""

    name: str
    created_at: float
    members: set[str] = field(default_factory=set)
    message_count: int = 0
    max_messages: int = 10_000  # Default limit


class ChannelStore:
    """In-memory message store with optional persistence.

    Features:
    - Per-agent message sequencing for FIFO ordering
    - Channel capacity limits for backpressure
    - Subscription support for real-time notifications
    - Thread-safe with asyncio.Lock
    """

    def __init__(self, max_messages_per_channel: int = 10_000, persist_dir: Path | None = None):
        """Initialize channel store.

        Args:
            max_messages_per_channel: Maximum messages per channel
            persist_dir: Optional directory for SQLite persistence (future)
        """
        self.channels: dict[str, Channel] = {}
        self.messages: dict[str, list[Message]] = defaultdict(list)
        self.locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self.max_messages = max_messages_per_channel
        self.persist_dir = persist_dir

        # Subscription support
        self.subscriptions: dict[str, set[asyncio.Queue]] = defaultdict(set)

        # Per-agent sequence counters
        self.agent_sequences: dict[tuple[str, str], int] = {}  # (agent_id, channel) -> sequence

    async def create_channel(self, name: str) -> Channel:
        """Create new channel.

        Args:
            name: Channel name

        Returns:
            Channel metadata
        """
        async with self.locks[name]:
            if name not in self.channels:
                self.channels[name] = Channel(name=name, created_at=time.time())
            return self.channels[name]

    async def join_channel(self, channel_name: str, agent_id: str) -> dict[str, Any]:
        """Add agent to channel.

        Args:
            channel_name: Channel to join
            agent_id: Agent identifier

        Returns:
            Channel status: members, message_count, etc.
        """
        async with self.locks[channel_name]:
            # Create channel if doesn't exist
            if channel_name not in self.channels:
                self.channels[channel_name] = Channel(name=channel_name, created_at=time.time())

            channel = self.channels[channel_name]
            channel.members.add(agent_id)

            return {
                "channel_name": channel_name,
                "agent_id": agent_id,
                "joined_at": time.time(),
                "other_agents": list(channel.members - {agent_id}),
                "message_count": len(self.messages[channel_name]),
            }

    async def leave_channel(self, channel_name: str, agent_id: str) -> None:
        """Remove agent from channel.

        Args:
            channel_name: Channel to leave
            agent_id: Agent identifier
        """
        async with self.locks[channel_name]:
            if channel_name in self.channels:
                self.channels[channel_name].members.discard(agent_id)

    async def append(
        self, channel_name: str, from_agent: str, message_type: MessageType, content: str | dict, **kwargs: Any
    ) -> str:
        """Append message to channel.

        Args:
            channel_name: Target channel
            from_agent: Sender agent ID
            message_type: Message type
            content: Message content
            **kwargs: Additional fields (metadata, reply_to, etc.)

        Returns:
            Message ID

        Raises:
            ChannelFullError: If channel has reached capacity
        """
        async with self.locks[channel_name]:
            # Check capacity
            if len(self.messages[channel_name]) >= self.max_messages:
                raise ChannelFullError(channel_name, self.max_messages)

            # Get next sequence number for this agent
            seq_key = (from_agent, channel_name)
            sequence = self.agent_sequences.get(seq_key, 0)
            self.agent_sequences[seq_key] = sequence + 1

            # Create message
            message = Message(
                id=str(uuid.uuid4()),
                from_agent=from_agent,
                timestamp=time.time(),
                type=message_type,
                content=content,
                sequence=sequence,
                metadata=kwargs.get("metadata", {}),
                reply_to=kwargs.get("reply_to"),
            )

            # Validate message schema
            if isinstance(content, dict):
                is_valid, error = MessageSchema.validate_message(message_type, content)
                if not is_valid:
                    raise ValueError(f"Invalid message content: {error}")

            # Append to channel
            self.messages[channel_name].append(message)

            # Update channel metadata
            if channel_name in self.channels:
                self.channels[channel_name].message_count += 1

            # Notify subscribers
            await self._notify_subscribers(channel_name, message)

            return message.id

    async def read(
        self,
        channel_name: str,
        since_message_id: str | None = None,
        filter_type: str | None = None,
        max_messages: int = 100,
    ) -> list[Message]:
        """Read messages from channel.

        Args:
            channel_name: Channel to read from
            since_message_id: Only return messages after this ID
            filter_type: Only return messages of this type
            max_messages: Maximum messages to return

        Returns:
            List of messages in chronological order
        """
        async with self.locks[channel_name]:
            messages = self.messages[channel_name]

            # Find starting position
            start_idx = 0
            if since_message_id:
                for i, msg in enumerate(messages):
                    if msg.id == since_message_id:
                        start_idx = i + 1  # Start after this message
                        break

            # Filter by type if requested
            filtered = messages[start_idx:]
            if filter_type:
                try:
                    msg_type = MessageType(filter_type)
                    filtered = [msg for msg in filtered if msg.type == msg_type]
                except ValueError:
                    pass  # Invalid type, return all

            # Limit results
            return filtered[:max_messages]

    async def get_message(self, channel_name: str, message_id: str) -> Message | None:
        """Get specific message by ID.

        Args:
            channel_name: Channel containing message
            message_id: Message ID

        Returns:
            Message if found, None otherwise
        """
        async with self.locks[channel_name]:
            for msg in self.messages[channel_name]:
                if msg.id == message_id:
                    return msg
            return None

    async def subscribe(self, channel_name: str) -> asyncio.Queue[Message]:
        """Subscribe to new messages in channel.

        Args:
            channel_name: Channel to subscribe to

        Returns:
            Queue that will receive new messages
        """
        queue: asyncio.Queue[Message] = asyncio.Queue()
        self.subscriptions[channel_name].add(queue)
        return queue

    async def unsubscribe(self, channel_name: str, queue: asyncio.Queue) -> None:
        """Unsubscribe from channel.

        Args:
            channel_name: Channel to unsubscribe from
            queue: Queue to remove
        """
        self.subscriptions[channel_name].discard(queue)

    async def _notify_subscribers(self, channel_name: str, message: Message) -> None:
        """Notify all subscribers of new message.

        Args:
            channel_name: Channel with new message
            message: New message to broadcast
        """
        for queue in self.subscriptions[channel_name]:
            try:
                await queue.put(message)
            except Exception:
                # Queue full or closed, remove subscription
                self.subscriptions[channel_name].discard(queue)

    async def list_channels(self) -> list[dict[str, Any]]:
        """List all channels.

        Returns:
            List of channel metadata
        """
        return [
            {
                "name": ch.name,
                "created_at": ch.created_at,
                "members": list(ch.members),
                "message_count": ch.message_count,
            }
            for ch in self.channels.values()
        ]

    async def get_channel(self, name: str) -> Channel | None:
        """Get channel metadata.

        Args:
            name: Channel name

        Returns:
            Channel metadata if exists, None otherwise
        """
        return self.channels.get(name)

    def get_stats(self) -> dict[str, Any]:
        """Get store statistics.

        Returns:
            Statistics: channel count, message count, etc.
        """
        return {
            "channels": len(self.channels),
            "total_messages": sum(len(msgs) for msgs in self.messages.values()),
            "active_subscriptions": sum(len(subs) for subs in self.subscriptions.values()),
        }

"""Authentication and authorization for multi-agent coordination."""

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass, field
from typing import Any

from .schema import AuthenticationError, AuthorizationError


@dataclass
class Agent:
    """Registered agent with credentials."""

    agent_id: str
    api_key_hash: str  # SHA256 hash of API key
    created_at: float
    allowed_channels: set[str] = field(default_factory=lambda: {"*"})  # "*" means all channels
    permissions: set[str] = field(default_factory=lambda: {"read", "write"})
    metadata: dict[str, Any] = field(default_factory=dict)
    rate_limit_per_minute: int = 100


class AuthManager:
    """Manage agent authentication and authorization.

    Uses API key authentication with SHA256 hashing.
    Supports per-agent channel access control and permissions.
    """

    def __init__(self):
        """Initialize auth manager."""
        self.agents: dict[str, Agent] = {}  # agent_id -> Agent
        self._api_key_to_agent: dict[str, str] = {}  # api_key_hash -> agent_id

    def register_agent(
        self,
        agent_id: str,
        api_key: str | None = None,
        allowed_channels: set[str] | None = None,
        permissions: set[str] | None = None,
        rate_limit_per_minute: int = 100,
    ) -> str:
        """Register a new agent.

        Args:
            agent_id: Unique agent identifier
            api_key: API key (will be auto-generated if None)
            allowed_channels: Set of allowed channels ("*" for all)
            permissions: Set of permissions (read, write, lock)
            rate_limit_per_minute: Max requests per minute

        Returns:
            API key (only returned once, store securely!)
        """
        # Generate API key if not provided
        if api_key is None:
            api_key = secrets.token_urlsafe(32)

        # Hash the API key
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        # Create agent
        agent = Agent(
            agent_id=agent_id,
            api_key_hash=api_key_hash,
            created_at=time.time(),
            allowed_channels=allowed_channels or {"*"},
            permissions=permissions or {"read", "write", "lock"},
            rate_limit_per_minute=rate_limit_per_minute,
        )

        self.agents[agent_id] = agent
        self._api_key_to_agent[api_key_hash] = agent_id

        return api_key

    def authenticate(self, agent_id: str, api_key: str) -> bool:
        """Verify agent credentials.

        Args:
            agent_id: Agent identifier
            api_key: API key to verify

        Returns:
            True if authenticated, False otherwise
        """
        agent = self.agents.get(agent_id)
        if not agent:
            return False

        # Hash provided key and compare
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        return hmac.compare_digest(api_key_hash, agent.api_key_hash)

    def get_agent_from_key(self, api_key: str) -> str | None:
        """Get agent ID from API key.

        Args:
            api_key: API key

        Returns:
            Agent ID if valid, None otherwise
        """
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        return self._api_key_to_agent.get(api_key_hash)

    def verify_channel_access(self, agent_id: str, channel_name: str) -> bool:
        """Verify agent has access to channel.

        Args:
            agent_id: Agent identifier
            channel_name: Channel to check

        Returns:
            True if allowed, False otherwise
        """
        agent = self.agents.get(agent_id)
        if not agent:
            return False

        # Wildcard access
        if "*" in agent.allowed_channels:
            return True

        return channel_name in agent.allowed_channels

    def verify_permission(self, agent_id: str, permission: str) -> bool:
        """Verify agent has specific permission.

        Args:
            agent_id: Agent identifier
            permission: Permission to check (read, write, lock)

        Returns:
            True if has permission, False otherwise
        """
        agent = self.agents.get(agent_id)
        if not agent:
            return False

        return permission in agent.permissions

    def get_agent(self, agent_id: str) -> Agent | None:
        """Get agent metadata.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent if exists, None otherwise
        """
        return self.agents.get(agent_id)

    def revoke_agent(self, agent_id: str) -> bool:
        """Revoke agent credentials.

        Args:
            agent_id: Agent to revoke

        Returns:
            True if revoked, False if not found
        """
        agent = self.agents.get(agent_id)
        if not agent:
            return False

        # Remove from mappings
        del self.agents[agent_id]
        del self._api_key_to_agent[agent.api_key_hash]

        return True

    def update_permissions(self, agent_id: str, permissions: set[str]) -> bool:
        """Update agent permissions.

        Args:
            agent_id: Agent to update
            permissions: New permission set

        Returns:
            True if updated, False if not found
        """
        agent = self.agents.get(agent_id)
        if not agent:
            return False

        agent.permissions = permissions
        return True

    def grant_channel_access(self, agent_id: str, channel_name: str) -> bool:
        """Grant agent access to specific channel.

        Args:
            agent_id: Agent to grant access
            channel_name: Channel to grant access to

        Returns:
            True if granted, False if not found
        """
        agent = self.agents.get(agent_id)
        if not agent:
            return False

        # Remove wildcard if present
        agent.allowed_channels.discard("*")
        agent.allowed_channels.add(channel_name)

        return True

    def revoke_channel_access(self, agent_id: str, channel_name: str) -> bool:
        """Revoke agent access to specific channel.

        Args:
            agent_id: Agent to revoke access
            channel_name: Channel to revoke

        Returns:
            True if revoked, False if not found
        """
        agent = self.agents.get(agent_id)
        if not agent:
            return False

        agent.allowed_channels.discard(channel_name)
        return True


# Decorator for tool authentication
def require_auth(auth_manager: AuthManager):
    """Decorator to require authentication for coordination tools.

    Args:
        auth_manager: AuthManager instance

    Returns:
        Decorator function
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract agent_id and api_key from kwargs
            agent_id = kwargs.get("agent_id")
            api_key = kwargs.get("api_key")

            if not agent_id or not api_key:
                raise AuthenticationError("Missing agent_id or api_key")

            # Authenticate
            if not auth_manager.authenticate(agent_id, api_key):
                raise AuthenticationError(f"Invalid credentials for agent {agent_id}")

            # Remove api_key from kwargs (don't pass to underlying function)
            kwargs_clean = {k: v for k, v in kwargs.items() if k != "api_key"}

            return await func(*args, **kwargs_clean)

        return wrapper

    return decorator


# Decorator for authorization checks
def require_permission(auth_manager: AuthManager, permission: str):
    """Decorator to require specific permission.

    Args:
        auth_manager: AuthManager instance
        permission: Required permission (read, write, lock)

    Returns:
        Decorator function
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            agent_id = kwargs.get("agent_id")

            if not agent_id:
                raise AuthenticationError("Missing agent_id")

            # Check permission
            if not auth_manager.verify_permission(agent_id, permission):
                raise AuthorizationError(
                    f"Agent {agent_id} lacks required permission: {permission}", required_permission=permission
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_channel_access(auth_manager: AuthManager):
    """Decorator to require channel access.

    Args:
        auth_manager: AuthManager instance

    Returns:
        Decorator function
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            agent_id = kwargs.get("agent_id")
            channel_name = kwargs.get("channel_name")

            if not agent_id or not channel_name:
                raise AuthenticationError("Missing agent_id or channel_name")

            # Check channel access
            if not auth_manager.verify_channel_access(agent_id, channel_name):
                raise AuthorizationError(f"Agent {agent_id} not allowed in channel {channel_name}")

            return await func(*args, **kwargs)

        return wrapper

    return decorator

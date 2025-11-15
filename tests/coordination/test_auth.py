"""Tests for authentication and authorization."""

import pytest

from hitl_mcp_cli.coordination.auth import AuthManager
from hitl_mcp_cli.coordination.schema import AuthenticationError, AuthorizationError


def test_register_agent():
    """Test agent registration."""
    manager = AuthManager()

    api_key = manager.register_agent("agent-a")

    assert len(api_key) > 0
    assert "agent-a" in manager.agents
    assert manager.agents["agent-a"].api_key_hash


def test_authenticate_valid():
    """Test successful authentication."""
    manager = AuthManager()
    api_key = manager.register_agent("agent-a")

    assert manager.authenticate("agent-a", api_key)


def test_authenticate_invalid_key():
    """Test authentication with invalid key."""
    manager = AuthManager()
    api_key = manager.register_agent("agent-a")

    assert not manager.authenticate("agent-a", "wrong-key")


def test_authenticate_invalid_agent():
    """Test authentication with non-existent agent."""
    manager = AuthManager()

    assert not manager.authenticate("nonexistent", "any-key")


def test_get_agent_from_key():
    """Test retrieving agent ID from API key."""
    manager = AuthManager()
    api_key = manager.register_agent("agent-a")

    agent_id = manager.get_agent_from_key(api_key)

    assert agent_id == "agent-a"


def test_get_agent_from_invalid_key():
    """Test retrieving agent with invalid key."""
    manager = AuthManager()
    manager.register_agent("agent-a")

    agent_id = manager.get_agent_from_key("invalid-key")

    assert agent_id is None


def test_channel_access_wildcard():
    """Test wildcard channel access."""
    manager = AuthManager()
    manager.register_agent("agent-a")  # Default is wildcard

    assert manager.verify_channel_access("agent-a", "any-channel")
    assert manager.verify_channel_access("agent-a", "another-channel")


def test_channel_access_specific():
    """Test specific channel access."""
    manager = AuthManager()
    manager.register_agent("agent-a", allowed_channels={"channel-1", "channel-2"})

    assert manager.verify_channel_access("agent-a", "channel-1")
    assert manager.verify_channel_access("agent-a", "channel-2")
    assert not manager.verify_channel_access("agent-a", "channel-3")


def test_grant_channel_access():
    """Test granting channel access."""
    manager = AuthManager()
    manager.register_agent("agent-a", allowed_channels={"channel-1"})

    assert not manager.verify_channel_access("agent-a", "channel-2")

    manager.grant_channel_access("agent-a", "channel-2")

    assert manager.verify_channel_access("agent-a", "channel-2")


def test_revoke_channel_access():
    """Test revoking channel access."""
    manager = AuthManager()
    manager.register_agent("agent-a", allowed_channels={"channel-1", "channel-2"})

    assert manager.verify_channel_access("agent-a", "channel-2")

    manager.revoke_channel_access("agent-a", "channel-2")

    assert not manager.verify_channel_access("agent-a", "channel-2")
    assert manager.verify_channel_access("agent-a", "channel-1")


def test_verify_permission():
    """Test permission verification."""
    manager = AuthManager()
    manager.register_agent("agent-a", permissions={"read", "write"})

    assert manager.verify_permission("agent-a", "read")
    assert manager.verify_permission("agent-a", "write")
    assert not manager.verify_permission("agent-a", "lock")


def test_update_permissions():
    """Test updating permissions."""
    manager = AuthManager()
    manager.register_agent("agent-a", permissions={"read"})

    assert not manager.verify_permission("agent-a", "write")

    manager.update_permissions("agent-a", {"read", "write", "lock"})

    assert manager.verify_permission("agent-a", "write")
    assert manager.verify_permission("agent-a", "lock")


def test_revoke_agent():
    """Test revoking agent credentials."""
    manager = AuthManager()
    api_key = manager.register_agent("agent-a")

    assert manager.authenticate("agent-a", api_key)

    result = manager.revoke_agent("agent-a")

    assert result is True
    assert not manager.authenticate("agent-a", api_key)
    assert manager.get_agent_from_key(api_key) is None


def test_revoke_nonexistent_agent():
    """Test revoking non-existent agent."""
    manager = AuthManager()

    result = manager.revoke_agent("nonexistent")

    assert result is False


def test_get_agent():
    """Test getting agent metadata."""
    manager = AuthManager()
    manager.register_agent("agent-a", allowed_channels={"ch1"}, permissions={"read"})

    agent = manager.get_agent("agent-a")

    assert agent is not None
    assert agent.agent_id == "agent-a"
    assert "ch1" in agent.allowed_channels
    assert "read" in agent.permissions


def test_custom_rate_limit():
    """Test custom rate limit assignment."""
    manager = AuthManager()
    manager.register_agent("agent-a", rate_limit_per_minute=50)

    agent = manager.get_agent("agent-a")

    assert agent.rate_limit_per_minute == 50

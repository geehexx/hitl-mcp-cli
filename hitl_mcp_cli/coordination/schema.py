"""Message schemas and validation for multi-agent coordination."""

import enum
from typing import Any


class MessageType(str, enum.Enum):
    """Structured message types for coordination protocol.

    Organized by coordination phase:
    - Discovery: init, acknowledgment
    - Synchronization: sync, capabilities, ownership, coordination_complete
    - Operational: question, response, task_assign, task_complete, clarification, progress
    - Control: ready, standby, stop, done
    - Conflict: conflict_detected, conflict_resolved
    """

    # Discovery Phase
    INIT = "init"  # Start coordination, declare role
    ACKNOWLEDGMENT = "acknowledgment"  # Confirm receipt, accept role

    # Synchronization Phase
    SYNC = "sync"  # Share configuration, rules, standards
    CAPABILITIES = "capabilities"  # Declare agent capabilities/limits
    OWNERSHIP = "ownership"  # Declare file ownership boundaries
    COORDINATION_COMPLETE = "coordination_complete"  # Sync phase finished

    # Operational Phase
    QUESTION = "question"  # Request information from another agent
    RESPONSE = "response"  # Provide requested information
    TASK_ASSIGN = "task_assign"  # Assign work (primary → subordinate)
    TASK_COMPLETE = "task_complete"  # Report task completion
    CLARIFICATION = "clarification"  # Clarify previous message
    PROGRESS = "progress"  # Progress update (% complete, status)

    # Control
    READY = "ready"  # Signal readiness for work
    STANDBY = "standby"  # Enter passive mode, await instructions
    STOP = "stop"  # Halt current activity
    DONE = "done"  # Work finished, entering idle state

    # Conflict Management
    CONFLICT_DETECTED = "conflict_detected"  # Report conflict
    CONFLICT_RESOLVED = "conflict_resolved"  # Primary's resolution


class MessageSchema:
    """Validation and schema for coordination messages."""

    # Message type definitions and their required/optional fields
    SCHEMAS = {
        MessageType.INIT: {
            "required": [],
            "optional": ["role", "capabilities"],
            "description": "Initialize coordination session",
        },
        MessageType.ACKNOWLEDGMENT: {
            "required": [],
            "optional": ["role", "status"],
            "description": "Acknowledge message or role",
        },
        MessageType.SYNC: {
            "required": ["config"],
            "optional": ["rules", "standards"],
            "description": "Synchronize configuration",
        },
        MessageType.CAPABILITIES: {
            "required": ["capabilities"],
            "optional": ["protocol_version", "supported_versions"],
            "description": "Declare agent capabilities",
        },
        MessageType.OWNERSHIP: {
            "required": ["files"],
            "optional": ["patterns"],
            "description": "Declare file ownership",
        },
        MessageType.COORDINATION_COMPLETE: {
            "required": [],
            "optional": ["summary"],
            "description": "Synchronization complete",
        },
        MessageType.QUESTION: {
            "required": ["question"],
            "optional": ["context"],
            "description": "Ask question",
        },
        MessageType.RESPONSE: {
            "required": ["answer"],
            "optional": ["reply_to"],
            "description": "Provide answer",
        },
        MessageType.TASK_ASSIGN: {
            "required": ["task"],
            "optional": ["files", "subtasks", "depends_on"],
            "description": "Assign task",
        },
        MessageType.TASK_COMPLETE: {
            "required": ["task_id"],
            "optional": ["files_modified", "status"],
            "description": "Report task completion",
        },
        MessageType.PROGRESS: {
            "required": ["status"],
            "optional": ["percentage", "details"],
            "description": "Progress update",
        },
        MessageType.CONFLICT_DETECTED: {
            "required": ["conflict_type", "details"],
            "optional": ["suggested_resolution"],
            "description": "Report conflict",
        },
        MessageType.CONFLICT_RESOLVED: {
            "required": ["resolution"],
            "optional": ["rationale"],
            "description": "Conflict resolved",
        },
    }

    @staticmethod
    def validate_message(message_type: str | MessageType, content: dict[str, Any]) -> tuple[bool, str | None]:
        """Validate message content against schema.

        Args:
            message_type: Type of message to validate
            content: Message content dictionary

        Returns:
            (is_valid, error_message)
            - (True, None) if valid
            - (False, error_message) if invalid
        """
        # Convert string to enum
        if isinstance(message_type, str):
            try:
                message_type = MessageType(message_type)
            except ValueError:
                return False, f"Invalid message type: {message_type}"

        # Get schema
        schema = MessageSchema.SCHEMAS.get(message_type)
        if not schema:
            return False, f"No schema defined for message type: {message_type}"

        # Check required fields
        for field in schema["required"]:
            if field not in content:
                return False, f"Missing required field: {field}"

        return True, None


class CoordinationError(Exception):
    """Base exception for coordination errors."""

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        help_url: str | None = None,
        suggested_actions: list[str] | None = None,
    ):
        """Initialize coordination error with rich context.

        Args:
            message: Error message
            details: Additional error details
            help_url: Link to documentation
            suggested_actions: List of remediation steps
        """
        super().__init__(message)
        self.details = details or {}
        self.help_url = help_url
        self.suggested_actions = suggested_actions or []

    def __str__(self) -> str:
        """Format error with details and suggested actions."""
        import json

        parts = [f"Error: {self.args[0]}"]

        if self.details:
            parts.append(f"Details: {json.dumps(self.details, indent=2)}")

        if self.suggested_actions:
            parts.append("Suggested actions:")
            for action in self.suggested_actions:
                parts.append(f"  - {action}")

        if self.help_url:
            parts.append(f"Learn more: {self.help_url}")

        return "\n".join(parts)


class ChannelFullError(CoordinationError):
    """Channel has reached maximum message capacity."""

    def __init__(self, channel: str, capacity: int):
        super().__init__(
            f"Channel '{channel}' is full (capacity: {capacity})",
            details={"channel": channel, "capacity": capacity},
            suggested_actions=[
                "Poll and process messages to free up space",
                "Use a different channel for new work",
                "Ask server admin to increase channel capacity",
            ],
        )


class AuthenticationError(CoordinationError):
    """Authentication failed."""

    def __init__(self, message: str):
        super().__init__(
            message,
            suggested_actions=[
                "Check that your API key is correct",
                "Verify agent_id matches the key",
                "Request a new API key from server admin",
            ],
        )


class AuthorizationError(CoordinationError):
    """Authorization failed (not permitted to perform action)."""

    def __init__(self, message: str, required_permission: str | None = None):
        details = {"required_permission": required_permission} if required_permission else {}
        super().__init__(
            message,
            details=details,
            suggested_actions=[
                "Verify you have permission for this channel",
                "Request access from channel owner",
                "Check your agent role (primary vs subordinate)",
            ],
        )


class LockQuotaExceeded(CoordinationError):
    """Agent exceeded maximum lock quota."""

    def __init__(self, agent_id: str, current: int, maximum: int):
        super().__init__(
            f"Agent '{agent_id}' exceeded lock quota ({current}/{maximum})",
            details={"agent_id": agent_id, "current_locks": current, "max_locks": maximum},
            suggested_actions=[
                "Release unused locks",
                "Complete tasks and release their locks",
                "Use coarser-grained locking (fewer locks)",
            ],
        )


class RateLimitExceeded(CoordinationError):
    """Agent exceeded rate limit."""

    def __init__(self, agent_id: str, limit: str):
        super().__init__(
            f"Agent '{agent_id}' exceeded rate limit ({limit})",
            details={"agent_id": agent_id, "limit": limit},
            suggested_actions=[
                "Slow down message sending",
                "Batch multiple updates into single message",
                "Wait before retrying",
            ],
        )

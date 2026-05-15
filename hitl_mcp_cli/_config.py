"""Server-wide timeout configuration from environment variables.

Environment variables:
    HITL_DEFAULT_WAIT   — default timeout_seconds when the caller passes 0 (infinite).
                          Set to a positive integer to impose a server-wide default.
                          0 (default) preserves the original infinite-wait behaviour.
    HITL_MIN_WAIT       — floor applied to every caller-supplied timeout_seconds > 0.
                          Prevents agents from setting unreasonably short timeouts.
                          0 (default) means no floor.
    HITL_MAX_WAIT       — ceiling applied to every caller-supplied timeout_seconds > 0.
                          Prevents agents from blocking indefinitely when a default is set.
                          0 (default) means no ceiling.
"""

from __future__ import annotations

import os


def _read_env_int(name: str, default: int = 0) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
        return max(0, value)
    except ValueError:
        return default


def get_default_wait() -> int:
    """Return HITL_DEFAULT_WAIT (0 = infinite)."""
    return _read_env_int("HITL_DEFAULT_WAIT", 0)


def get_min_wait() -> int:
    """Return HITL_MIN_WAIT floor (0 = no floor)."""
    return _read_env_int("HITL_MIN_WAIT", 0)


def get_max_wait() -> int:
    """Return HITL_MAX_WAIT ceiling (0 = no ceiling)."""
    return _read_env_int("HITL_MAX_WAIT", 0)


def resolve_timeout(timeout_seconds: int) -> int:
    """Apply server-wide min/max/default policy to a caller-supplied timeout.

    Rules (applied in order):
    1. If timeout_seconds == 0, substitute HITL_DEFAULT_WAIT (0 = keep infinite).
    2. If the result > 0 and HITL_MIN_WAIT > 0, clamp up to the floor.
    3. If the result > 0 and HITL_MAX_WAIT > 0, clamp down to the ceiling.

    Returns the resolved timeout (0 = infinite wait).
    """
    resolved = timeout_seconds

    if resolved == 0:
        resolved = get_default_wait()

    if resolved > 0:
        min_wait = get_min_wait()
        if min_wait > 0:
            resolved = max(resolved, min_wait)

        max_wait = get_max_wait()
        if max_wait > 0:
            resolved = min(resolved, max_wait)

    return resolved


__all__ = ["get_default_wait", "get_max_wait", "get_min_wait", "resolve_timeout"]

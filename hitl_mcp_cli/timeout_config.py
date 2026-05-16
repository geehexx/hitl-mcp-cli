"""Configurable timeout settings for HITL tools.

Env vars (all in minutes):
    HITL_DEFAULT_WAIT  — default wait if no per-call max_wait_minutes given (default: 15)
    HITL_MIN_WAIT      — minimum clamp for per-call values (default: 1)
    HITL_MAX_WAIT      — maximum clamp for per-call values (default: 120)
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class TimeoutConfig:
    default_wait: int = 15
    min_wait: int = 1
    max_wait: int = 120

    @classmethod
    def from_env(cls) -> TimeoutConfig:
        return cls(
            default_wait=int(os.environ.get("HITL_DEFAULT_WAIT", 15)),
            min_wait=int(os.environ.get("HITL_MIN_WAIT", 1)),
            max_wait=int(os.environ.get("HITL_MAX_WAIT", 120)),
        )

    def clamp(self, value: float | int | None) -> int:
        """Return value clamped to [min_wait, max_wait], or default_wait if None."""
        if value is None:
            return self.default_wait
        return max(self.min_wait, min(self.max_wait, int(value)))


_config: TimeoutConfig | None = None


def get_timeout_config() -> TimeoutConfig:
    """Return the process-level timeout config (lazy-loaded from env)."""
    global _config
    if _config is None:
        _config = TimeoutConfig.from_env()
    return _config


__all__ = ["TimeoutConfig", "get_timeout_config"]

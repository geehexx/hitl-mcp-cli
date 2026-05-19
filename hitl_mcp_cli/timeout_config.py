"""Configurable timeout settings for HITL tools.

Env vars (all in minutes):
    HITL_DEFAULT_WAIT    — default wait if no per-call max_wait_minutes given (default: 15)
    HITL_MIN_WAIT_MIN    — minimum clamp for per-call values (default: 1)
    HITL_MAX_WAIT_MIN    — maximum clamp for per-call values (default: 120)
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class TimeoutConfig:
    default_wait: float = 15
    min_wait: float = 1
    max_wait: float = 120

    @classmethod
    def from_env(cls) -> TimeoutConfig:
        return cls(
            default_wait=float(os.environ.get("HITL_DEFAULT_WAIT", 15)),
            min_wait=float(os.environ.get("HITL_MIN_WAIT_MIN", 1)),
            max_wait=float(os.environ.get("HITL_MAX_WAIT_MIN", 120)),
        )

    def clamp(self, value: float | int | None) -> float:
        """Return value clamped to [min_wait, max_wait], or default_wait if None."""
        if value is None:
            return self.default_wait
        return max(self.min_wait, min(self.max_wait, float(value)))


_config: TimeoutConfig | None = None


def get_timeout_config() -> TimeoutConfig:
    """Return the process-level timeout config (lazy-loaded from env)."""
    global _config
    if _config is None:
        _config = TimeoutConfig.from_env()
    return _config


__all__ = ["TimeoutConfig", "get_timeout_config"]

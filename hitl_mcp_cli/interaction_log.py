"""JSONL interaction logging for HITL tool calls. No PII logged."""

from __future__ import annotations

import json
import sys
import time
import uuid
from pathlib import Path
from typing import Literal

LOG_DIR = Path.home() / ".local" / "state" / "hitl-mcp"
LOG_FILE = LOG_DIR / "interactions.jsonl"
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB

SESSION_ID: str = str(uuid.uuid4())

ResultType = Literal["value", "cancel", "timeout"]


def _rotate_if_needed() -> None:
    """Rename log to .1 if it exceeds MAX_LOG_SIZE."""
    if LOG_FILE.exists() and LOG_FILE.stat().st_size > MAX_LOG_SIZE:
        try:
            LOG_FILE.rename(LOG_FILE.with_suffix(".jsonl.1"))
        except FileNotFoundError:
            pass


def log_interaction(tool: str, duration_ms: int, result_type: ResultType) -> None:
    """Append one JSONL entry. Errors go to stderr, never propagate."""
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        _rotate_if_needed()
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime()),
            "tool": tool,
            "duration_ms": duration_ms,
            "result_type": result_type,
            "session_id": SESSION_ID,
        }
        with LOG_FILE.open("a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"hitl-mcp: logging error: {e}", file=sys.stderr)

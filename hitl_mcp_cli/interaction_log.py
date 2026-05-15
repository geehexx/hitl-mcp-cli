"""JSONL interaction logging for HITL tool calls. No PII logged."""

from __future__ import annotations

import json
import re
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

_RICH_TAG_RE = re.compile(r"\[/?[a-zA-Z][a-zA-Z0-9_ ]*\]")


def _sanitize(text: str, limit: int) -> str:
    """Strip Rich markup tags and truncate."""
    return _RICH_TAG_RE.sub("", text)[:limit]


def _rotate_if_needed() -> None:
    """Rename log to .1 if it exceeds MAX_LOG_SIZE."""
    if LOG_FILE.exists() and LOG_FILE.stat().st_size > MAX_LOG_SIZE:
        try:
            backup = LOG_FILE.with_suffix(".jsonl.1")
            backup.unlink(missing_ok=True)
            LOG_FILE.rename(backup)
        except FileNotFoundError:
            pass


def log_interaction(
    tool: str,
    duration_ms: int,
    result_type: ResultType,
    message: str | None = None,
    result: str | None = None,
    notes: str | None = None,
) -> None:
    """Append one JSONL entry. Errors go to stderr, never propagate."""
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        _rotate_if_needed()
        entry: dict[str, object] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime()),
            "tool": tool,
            "duration_ms": duration_ms,
            "result_type": result_type,
            "session_id": SESSION_ID,
        }
        if message:
            entry["msg"] = _sanitize(message, 120)
        if result:
            entry["result"] = _sanitize(result, 80)
        if notes:
            entry["notes"] = _sanitize(notes, 80)
        with LOG_FILE.open("a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"hitl-mcp: logging error: {e}", file=sys.stderr)

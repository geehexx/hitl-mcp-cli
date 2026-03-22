"""Shared test fixtures — isolate interaction log from real filesystem."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

import hitl_mcp_cli.interaction_log as interaction_log


@pytest.fixture(autouse=True, scope="session")
def isolate_interaction_log(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Redirect all interaction logging to a temp directory for the entire test session."""
    tmp = tmp_path_factory.mktemp("hitl_log")
    log_file = tmp / "interactions.jsonl"
    with (
        patch.object(interaction_log, "LOG_DIR", tmp),
        patch.object(interaction_log, "LOG_FILE", log_file),
    ):
        yield tmp

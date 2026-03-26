"""Shared test fixtures for hitl-mcp-cli tests."""

from __future__ import annotations

import pytest

from hitl_mcp_cli.server import configure_tui_mode
from hitl_mcp_cli.tui.queue import HITLQueue


@pytest.fixture
async def tui_queue() -> HITLQueue:
    """Create a TUI queue and configure the server to use it."""
    queue = HITLQueue()
    configure_tui_mode(queue, None)  # type: ignore[arg-type]
    yield queue
    configure_tui_mode(None, None)  # type: ignore[arg-type]

"""RED tests for P1 configurable timeouts.

Spec:
- env vars: HITL_DEFAULT_WAIT=15, HITL_MIN_WAIT=1, HITL_MAX_WAIT=120 (minutes)
- per-call max_wait_minutes param on hitl_ask, hitl_choose, hitl_confirm
- timeout returns: {status: "timeout", question_id: <uuid>, retry_after: 60}
"""

from __future__ import annotations

import asyncio
import os
from typing import Any
from unittest.mock import patch

import pytest
from fastmcp import Client

from hitl_mcp_cli import _server_core
from hitl_mcp_cli.server import configure_tui_mode, mcp
from hitl_mcp_cli.tui.queue import HITLQueue


@pytest.fixture(autouse=True)
def _reset_tui_globals() -> Any:
    _server_core._tui_queue = None
    _server_core._tui_app = None
    yield
    _server_core._tui_queue = None
    _server_core._tui_app = None


@pytest.fixture
async def tui_queue() -> Any:
    queue = HITLQueue()
    configure_tui_mode(queue, None)  # type: ignore[arg-type]
    yield queue
    configure_tui_mode(None, None)  # type: ignore[arg-type]


@pytest.fixture
async def mcp_client(tui_queue: HITLQueue) -> Any:
    async with Client(mcp) as client:
        yield client


# ---------------------------------------------------------------------------
# timeout config module
# ---------------------------------------------------------------------------


class TestTimeoutConfig:
    def test_config_module_importable(self) -> None:
        from hitl_mcp_cli.timeout_config import TimeoutConfig  # noqa: F401

    def test_default_values(self) -> None:
        from hitl_mcp_cli.timeout_config import TimeoutConfig

        cfg = TimeoutConfig()
        assert cfg.default_wait == 15
        assert cfg.min_wait == 1
        assert cfg.max_wait == 120

    def test_env_vars_override_defaults(self) -> None:
        from hitl_mcp_cli.timeout_config import TimeoutConfig

        with patch.dict(os.environ, {"HITL_DEFAULT_WAIT": "30", "HITL_MIN_WAIT": "2", "HITL_MAX_WAIT": "60"}):
            cfg = TimeoutConfig.from_env()
        assert cfg.default_wait == 30
        assert cfg.min_wait == 2
        assert cfg.max_wait == 60

    def test_clamp_respects_min(self) -> None:
        from hitl_mcp_cli.timeout_config import TimeoutConfig

        cfg = TimeoutConfig(default_wait=15, min_wait=5, max_wait=120)
        assert cfg.clamp(2) == 5

    def test_clamp_respects_max(self) -> None:
        from hitl_mcp_cli.timeout_config import TimeoutConfig

        cfg = TimeoutConfig(default_wait=15, min_wait=1, max_wait=120)
        assert cfg.clamp(200) == 120

    def test_clamp_within_range_unchanged(self) -> None:
        from hitl_mcp_cli.timeout_config import TimeoutConfig

        cfg = TimeoutConfig(default_wait=15, min_wait=1, max_wait=120)
        assert cfg.clamp(30) == 30

    def test_none_returns_default(self) -> None:
        from hitl_mcp_cli.timeout_config import TimeoutConfig

        cfg = TimeoutConfig(default_wait=15, min_wait=1, max_wait=120)
        assert cfg.clamp(None) == 15


# ---------------------------------------------------------------------------
# hitl_confirm timeout return shape
# ---------------------------------------------------------------------------


class TestConfirmTimeoutShape:
    @pytest.mark.asyncio
    async def test_confirm_timeout_returns_new_shape(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        """max_wait_minutes=0.02 (~1.2s) with no resolution → new timeout shape."""
        result = await mcp_client.call_tool("hitl_confirm", {"message": "Deploy?", "max_wait_minutes": 0.02})
        data = result.data
        assert data["status"] == "timeout"
        assert "question_id" in data
        assert isinstance(data["question_id"], str)
        assert data["retry_after"] == 60

    @pytest.mark.asyncio
    async def test_confirm_fast_response_not_timeout(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        """Fast response within window → normal accept/decline, no timeout key."""

        async def _resolve() -> None:
            req = await tui_queue.get()
            tui_queue.resolve(req, {"action": "accept"})

        task = asyncio.create_task(_resolve())
        result = await mcp_client.call_tool("hitl_confirm", {"message": "Continue?", "max_wait_minutes": 5})
        await task
        assert result.data["action"] == "accept"
        assert result.data.get("status") != "timeout"

    @pytest.mark.asyncio
    async def test_confirm_timeout_question_id_is_uuid(
        self, mcp_client: Client, tui_queue: HITLQueue
    ) -> None:
        import uuid

        result = await mcp_client.call_tool("hitl_confirm", {"message": "Check?", "max_wait_minutes": 0.02})
        # Must be a valid UUID
        uuid.UUID(result.data["question_id"])


# ---------------------------------------------------------------------------
# hitl_ask / hitl_collect timeout shape
# ---------------------------------------------------------------------------


class TestAskTimeoutShape:
    @pytest.mark.asyncio
    async def test_ask_timeout_returns_new_shape(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        result = await mcp_client.call_tool("hitl_ask", {"message": "Name?", "max_wait_minutes": 0.02})
        data = result.data
        assert data["status"] == "timeout"
        assert "question_id" in data
        assert data["retry_after"] == 60

    @pytest.mark.asyncio
    async def test_collect_timeout_returns_new_shape(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        result = await mcp_client.call_tool("hitl_collect", {"message": "Value?", "max_wait_minutes": 0.02})
        data = result.data
        assert data["status"] == "timeout"
        assert "question_id" in data


# ---------------------------------------------------------------------------
# hitl_choose timeout shape
# ---------------------------------------------------------------------------


class TestChooseTimeoutShape:
    @pytest.mark.asyncio
    async def test_choose_timeout_returns_new_shape(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        result = await mcp_client.call_tool(
            "hitl_choose",
            {"message": "Pick one?", "choices": ["a", "b"], "max_wait_minutes": 0.02},
        )
        data = result.data
        assert data["status"] == "timeout"
        assert "question_id" in data
        assert data["retry_after"] == 60

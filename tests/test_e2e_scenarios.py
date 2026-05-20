"""E2E scenario tests: realistic agent workflows through the MCP server."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastmcp import Client

from hitl_mcp_cli.server import configure_tui_mode, mcp
from hitl_mcp_cli.tui.queue import HITLQueue


@pytest.fixture(autouse=True)
def _pin_timeout_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HITL_MIN_WAIT_MIN", "0")
    monkeypatch.setenv("HITL_DEFAULT_WAIT_MIN", "0.1")
    import hitl_mcp_cli.timeout_config as tc

    tc._config = None
    yield
    tc._config = None


@pytest.fixture
async def tui_queue() -> HITLQueue:
    queue = HITLQueue()
    configure_tui_mode(queue, None)  # type: ignore[arg-type]
    yield queue
    configure_tui_mode(None, None)  # type: ignore[arg-type]


@pytest.fixture
async def mcp_client(tui_queue: HITLQueue) -> Client:
    async with Client(mcp) as client:
        yield client


def _resolve_with(queue: HITLQueue, value: Any) -> asyncio.Task[None]:
    async def _r() -> None:
        req = await queue.get()
        queue.resolve(req, value)

    return asyncio.create_task(_r())


class TestApprovalWorkflow:
    """hitl_notify → hitl_confirm → hitl_notify — full round trip."""

    @pytest.mark.asyncio
    async def test_notify_confirm_notify(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        r1 = await mcp_client.call_tool(
            "hitl_notify", {"message": "Starting deploy", "level": "info", "title": "Agent"}
        )
        assert r1.data == {"acknowledged": True}

        task = _resolve_with(tui_queue, {"action": "accept"})
        r2 = await mcp_client.call_tool("hitl_confirm", {"message": "Deploy to prod?", "severity": "medium"})
        await task
        assert r2.data == {"action": "accept", "timed_out": False}

        r3 = await mcp_client.call_tool(
            "hitl_notify", {"message": "Deploy complete!", "level": "success", "title": "Agent"}
        )
        assert r3.data == {"acknowledged": True}

    @pytest.mark.asyncio
    async def test_approval_declined(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        r1 = await mcp_client.call_tool(
            "hitl_notify", {"message": "Preparing destructive action", "level": "warning"}
        )
        assert r1.data == {"acknowledged": True}

        task = _resolve_with(tui_queue, {"action": "decline"})
        r2 = await mcp_client.call_tool("hitl_confirm", {"message": "Delete all data?", "severity": "medium"})
        await task
        assert r2.data == {"action": "decline", "timed_out": False}


class TestMultiStepCollection:
    """hitl_collect → hitl_choose — sequential, second waits for first."""

    @pytest.mark.asyncio
    async def test_collect_then_choose(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        task1 = _resolve_with(tui_queue, "my-project")
        r1 = await mcp_client.call_tool("hitl_collect", {"message": "Project name:", "default": "untitled"})
        await task1
        assert r1.data == "my-project"

        task2 = _resolve_with(tui_queue, "Python")
        r2 = await mcp_client.call_tool(
            "hitl_choose", {"message": "Language:", "choices": ["Python", "TypeScript", "Go"]}
        )
        await task2
        assert r2.data == "Python"

    @pytest.mark.asyncio
    async def test_collect_multiline_then_choose_multiple(
        self, mcp_client: Client, tui_queue: HITLQueue
    ) -> None:
        task1 = _resolve_with(tui_queue, "line1\nline2\nline3")
        r1 = await mcp_client.call_tool(
            "hitl_collect", {"message": "Description:", "input_type": "multiline"}
        )
        await task1
        assert r1.data == "line1\nline2\nline3"

        task2 = _resolve_with(tui_queue, ["lint", "test"])
        r2 = await mcp_client.call_tool(
            "hitl_choose",
            {"message": "CI steps:", "choices": ["lint", "test", "deploy"], "multiple": True},
        )
        await task2
        assert r2.data == ["lint", "test"]

    @pytest.mark.asyncio
    async def test_path_then_confirm(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        task1 = _resolve_with(tui_queue, "/home/user/config.yaml")
        r1 = await mcp_client.call_tool("hitl_collect", {"message": "Config file:", "input_type": "path"})
        await task1
        assert r1.data == "/home/user/config.yaml"

        task2 = _resolve_with(tui_queue, {"action": "accept"})
        r2 = await mcp_client.call_tool("hitl_confirm", {"message": "Apply this config?"})
        await task2
        assert r2.data == {"action": "accept", "timed_out": False}


class TestTimeoutRecovery:
    """Tool times out → new tool call succeeds — server still healthy."""

    @pytest.mark.asyncio
    async def test_timeout_then_success(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        r1 = await mcp_client.call_tool("hitl_confirm", {"message": "Slow op?", "max_wait_minutes": 0.02})
        assert r1.data["status"] == "timeout"

        task = _resolve_with(tui_queue, "recovered")
        r2 = await mcp_client.call_tool("hitl_collect", {"message": "Name:"})
        await task
        assert r2.data == "recovered"

    @pytest.mark.asyncio
    async def test_multiple_timeouts_then_success(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        """Server survives multiple consecutive timeouts."""
        for _ in range(3):
            r = await mcp_client.call_tool("hitl_confirm", {"message": "Timeout?", "max_wait_minutes": 0.02})
            assert r.data["status"] == "timeout"

        r = await mcp_client.call_tool("hitl_notify", {"message": "Still alive"})
        assert r.data == {"acknowledged": True}

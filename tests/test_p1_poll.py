"""RED tests for hitl_poll tool.

Spec: hitl_poll(question_id, wait_minutes=5) re-blocks on a timed-out question.
- If question_id is unknown → {"status": "not_found", "question_id": ...}
- If question already answered → returns the answer immediately
- If question is timed_out → re-blocks for wait_minutes, returns answer or new timeout
"""

from __future__ import annotations

import asyncio
from typing import Any

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


class TestHitlPoll:
    def test_hitl_poll_importable(self) -> None:
        from hitl_mcp_cli.tools._poll import hitl_poll  # noqa: F401

    @pytest.mark.asyncio
    async def test_poll_unknown_question_id_returns_not_found(
        self, mcp_client: Client, tui_queue: HITLQueue
    ) -> None:
        result = await mcp_client.call_tool(
            "hitl_poll", {"question_id": "nonexistent-uuid", "wait_minutes": 0.02}
        )
        assert result.data["status"] == "not_found"
        assert result.data["question_id"] == "nonexistent-uuid"

    @pytest.mark.asyncio
    async def test_poll_answered_question_returns_answer(
        self, mcp_client: Client, tui_queue: HITLQueue
    ) -> None:
        """If the question was already answered, poll returns the stored answer."""

        # First ask a question and answer it
        async def _resolve() -> None:
            req = await tui_queue.get()
            tui_queue.resolve(req, "my answer")

        task = asyncio.create_task(_resolve())
        ask_result = await mcp_client.call_tool("hitl_ask", {"message": "What is your name?"})
        await task
        assert ask_result.data == "my answer"

        # Now poll the same question — should return the cached answer
        # We need the question_id from the queue history
        assert len(tui_queue.history) == 1
        qid = tui_queue.history[0].params.get("_question_id")
        assert qid is not None

        poll_result = await mcp_client.call_tool("hitl_poll", {"question_id": qid, "wait_minutes": 0.02})
        assert poll_result.data["status"] == "answered"
        assert poll_result.data["answer"] == "my answer"

    @pytest.mark.asyncio
    async def test_poll_pending_question_blocks_and_resolves(
        self, mcp_client: Client, tui_queue: HITLQueue
    ) -> None:
        """Poll on a pending question blocks until answered."""
        # First, create a timed-out question
        timeout_result = await mcp_client.call_tool(
            "hitl_ask", {"message": "Slow question?", "max_wait_minutes": 0.02}
        )
        assert timeout_result.data["status"] == "timeout"
        qid = timeout_result.data["question_id"]

        # Now poll it — it should re-block and resolve when answered
        async def _resolve() -> None:
            # Wait for the poll to enqueue a new request
            req = await tui_queue.get()
            tui_queue.resolve(req, "poll answer")

        task = asyncio.create_task(_resolve())
        poll_result = await mcp_client.call_tool("hitl_poll", {"question_id": qid, "wait_minutes": 5})
        await task
        assert poll_result.data["status"] == "answered"
        assert poll_result.data["answer"] == "poll answer"

    @pytest.mark.asyncio
    async def test_poll_times_out_again_returns_timeout(
        self, mcp_client: Client, tui_queue: HITLQueue
    ) -> None:
        """Poll that times out again returns timeout shape with same question_id."""
        timeout_result = await mcp_client.call_tool(
            "hitl_ask", {"message": "Slow?", "max_wait_minutes": 0.02}
        )
        qid = timeout_result.data["question_id"]

        poll_result = await mcp_client.call_tool("hitl_poll", {"question_id": qid, "wait_minutes": 0.02})
        assert poll_result.data["status"] == "timeout"
        assert poll_result.data["question_id"] == qid
        assert poll_result.data["retry_after"] == 60

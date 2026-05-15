"""Property tests for ``HITLQueue`` invariants — added in v1.0.0rc1."""

from __future__ import annotations

import asyncio

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from hitl_mcp_cli.tui.queue import HITLQueue, HITLRequest


def _make_request(priority: int) -> HITLRequest:
    """Build a minimal HITLRequest at a given priority for property testing."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    future: asyncio.Future[object] = loop.create_future()
    return HITLRequest(tool="t", params={"message": "m"}, future=future, priority=priority)


@given(priorities=st.lists(st.integers(min_value=0, max_value=9), min_size=1, max_size=20))
@settings(max_examples=50, deadline=None)
def test_priority_ordering_is_monotonic(priorities: list[int]) -> None:
    """Dequeued priorities must be sorted ascending (priority 0 = highest)."""
    queue = HITLQueue()

    async def run() -> list[int]:
        for p in priorities:
            await queue.put(_make_request(p))
        out: list[int] = []
        while queue.size > 0:
            req = await queue.get()
            out.append(req.priority)
        return out

    out = asyncio.run(run())
    assert out == sorted(priorities)


@given(priorities=st.lists(st.integers(min_value=0, max_value=9), min_size=2, max_size=20))
@settings(max_examples=50, deadline=None)
def test_history_records_every_enqueue(priorities: list[int]) -> None:
    """Every enqueued request must be recorded in ``history`` exactly once."""
    queue = HITLQueue()

    async def run() -> int:
        for p in priorities:
            await queue.put(_make_request(p))
        return len(queue.history)

    n = asyncio.run(run())
    assert n == len(priorities)


@pytest.mark.parametrize("status", ["answered", "cancelled", "minimized"])
def test_status_marker_is_idempotent(status: str) -> None:
    """Calling ``mark_*`` repeatedly leaves the request in the same final state."""
    queue = HITLQueue()
    req = _make_request(5)
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(queue.put(req))
    finally:
        loop.close()

    marker = getattr(queue, f"mark_{status}")
    if status == "answered":
        marker(req.request_id, "ans")
        marker(req.request_id, "ans")
    else:
        marker(req.request_id)
        marker(req.request_id)
    assert req.status == status

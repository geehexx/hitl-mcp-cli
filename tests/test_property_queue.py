"""Property tests for ``HITLQueue`` invariants and question lifecycle state machine."""

from __future__ import annotations

import asyncio

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from hitl_mcp_cli.tui.queue import HITLQueue, HITLRequest


def _make_request(priority: int) -> HITLRequest:
    """Build a minimal HITLRequest at a given priority — must be called from a running loop."""
    loop = asyncio.get_running_loop()
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

    async def _put() -> HITLRequest:
        req = _make_request(5)
        await queue.put(req)
        return req

    req = asyncio.run(_put())

    marker = getattr(queue, f"mark_{status}")
    if status == "answered":
        marker(req.request_id, "ans")
        marker(req.request_id, "ans")
    else:
        marker(req.request_id)
        marker(req.request_id)
    assert req.status == status


# ---------------------------------------------------------------------------
# State machine property tests — question lifecycle
# ---------------------------------------------------------------------------
# Valid transitions: pending → answered | cancelled | minimized
# Invariants:
#   1. A request starts in "pending" state.
#   2. Once resolved, resolved_answer is set.
#   3. Resolving a future-done request is a no-op (idempotent).
#   4. Rejecting a request does not set resolved_answer.
#   5. get_by_id always returns the same object that was enqueued.


def _make_request_sync(priority: int = 5) -> tuple[HITLQueue, HITLRequest]:
    """Create a queue + request without a running event loop."""

    async def _build() -> tuple[HITLQueue, HITLRequest]:
        q = HITLQueue()
        req = _make_request(priority)
        await q.put(req)
        return q, req

    return asyncio.run(_build())


def test_new_request_starts_pending() -> None:
    """Every freshly enqueued request must start in 'pending' state."""
    _, req = _make_request_sync()
    assert req.status == "pending"


def test_new_request_has_no_resolved_answer() -> None:
    """resolved_answer must be None until the request is resolved."""
    _, req = _make_request_sync()
    assert req.resolved_answer is None


@given(answer=st.one_of(st.text(min_size=1, max_size=50), st.booleans(), st.integers()))
@settings(max_examples=30, deadline=None)
def test_resolve_sets_resolved_answer(answer: object) -> None:
    """After resolve(), resolved_answer equals the supplied value."""
    queue, req = _make_request_sync()
    queue.resolve(req, answer)
    assert req.resolved_answer == answer


def test_resolve_is_idempotent() -> None:
    """Calling resolve() twice does not raise and keeps the first answer."""
    queue, req = _make_request_sync()
    queue.resolve(req, "first")
    queue.resolve(req, "second")  # must not raise
    assert req.resolved_answer == "first"


def test_reject_does_not_set_resolved_answer() -> None:
    """reject() sets an exception on the future but leaves resolved_answer None."""
    queue, req = _make_request_sync()
    queue.reject(req, ValueError("bad"))
    assert req.resolved_answer is None


def test_reject_is_idempotent() -> None:
    """Calling reject() twice does not raise."""
    queue, req = _make_request_sync()
    queue.reject(req, ValueError("first"))
    queue.reject(req, ValueError("second"))  # must not raise


def test_get_by_id_returns_same_object() -> None:
    """get_by_id must return the exact object that was enqueued."""
    queue, req = _make_request_sync()
    looked_up = queue.get_by_id(req.request_id)
    assert looked_up is req


def test_get_by_id_unknown_returns_none() -> None:
    """get_by_id with an unknown id must return None."""
    queue, _ = _make_request_sync()
    assert queue.get_by_id("nonexistent-id") is None


@given(n=st.integers(min_value=1, max_value=10))
@settings(max_examples=20, deadline=None)
def test_history_length_equals_enqueue_count(n: int) -> None:
    """history must contain exactly as many entries as were enqueued."""

    async def run() -> int:
        q = HITLQueue()
        for _ in range(n):
            req = _make_request(5)
            await q.put(req)
        return len(q.history)

    assert asyncio.run(run()) == n


@given(status=st.sampled_from(["answered", "cancelled", "minimized"]))
@settings(max_examples=10, deadline=None)
def test_mark_sets_expected_status(status: str) -> None:
    """mark_<status>() must set request.status to the named status."""
    q, req = _make_request_sync()
    if status == "answered":
        q.mark_answered(req.request_id, "ans")
    else:
        getattr(q, f"mark_{status}")(req.request_id)
    assert req.status == status


def test_mark_unknown_id_is_noop() -> None:
    """mark_* with an unknown request_id must not raise."""
    q, _ = _make_request_sync()
    q.mark_answered("no-such-id", "x")
    q.mark_cancelled("no-such-id")
    q.mark_minimized("no-such-id")

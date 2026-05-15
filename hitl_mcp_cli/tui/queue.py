"""Asyncio-based priority queue for serializing concurrent HITL tool calls."""

from __future__ import annotations

import asyncio
import itertools
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from rich.markup import escape


def _sanitize(value: str | None) -> str | None:
    """Strip Rich markup from agent-provided strings."""
    if value is None:
        return None
    return escape(value)


def _sanitize_params(params: dict[str, Any]) -> dict[str, Any]:
    """Sanitize display-facing string values in params dict.

    Only sanitizes keys that will be rendered in the TUI. Functional
    params (validation_pattern, choices, etc.) are left untouched.
    """
    _DISPLAY_KEYS = {"message", "context", "title", "validation_message", "default", "notes"}
    out: dict[str, Any] = {}
    for k, v in params.items():
        out[k] = escape(v) if isinstance(v, str) and k in _DISPLAY_KEYS else v
    if "choices" in out and isinstance(out["choices"], list):
        out["choices"] = [escape(c) if isinstance(c, str) else c for c in out["choices"]]
    return out


@dataclass(order=False)
class HITLRequest:
    """A single HITL request awaiting user response."""

    tool: str
    params: dict[str, Any]
    future: asyncio.Future[Any]
    priority: int = 5
    request_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: float = field(default_factory=time.monotonic)
    # Status tracking (v0.9.0)
    status: str = "pending"  # "pending", "answered", "cancelled", "minimized"
    answer_preview: str = ""  # truncated answer for display
    _resolved_at: float | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self.params = _sanitize_params(self.params)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, HITLRequest):
            return NotImplemented
        return (self.priority, self.created_at) < (other.priority, other.created_at)


class HITLQueue:
    """Priority queue that serializes concurrent HITL tool calls.

    Items are dequeued in priority order (0=highest). Within the same
    priority, FIFO ordering is maintained via a monotonic sequence number.
    """

    _seq: itertools.count[int] = itertools.count(1)

    def __init__(self) -> None:
        self._queue: asyncio.PriorityQueue[tuple[int, int, HITLRequest]] = asyncio.PriorityQueue()
        self._caller_loop: asyncio.AbstractEventLoop | None = None
        self._textual_loop: asyncio.AbstractEventLoop | None = None
        # History: all requests ever enqueued (never removed)
        self.history: list[HITLRequest] = []
        self._by_id: dict[str, HITLRequest] = {}

    def set_caller_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Register the event loop that creates futures (uvicorn thread)."""
        self._caller_loop = loop

    def set_textual_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Register the Textual event loop that owns the asyncio.PriorityQueue."""
        self._textual_loop = loop

    def _register(self, request: HITLRequest) -> None:
        """Add request to history and lookup dict."""
        self.history.append(request)
        self._by_id[request.request_id] = request

    def get_by_id(self, request_id: str) -> HITLRequest | None:
        """Look up a request by its ID."""
        return self._by_id.get(request_id)

    def mark_answered(self, request_id: str, answer_preview: str = "") -> None:
        """Mark a request as answered."""
        req = self._by_id.get(request_id)
        if req is not None:
            req.status = "answered"
            req.answer_preview = answer_preview[:60]
            req._resolved_at = time.monotonic()

    def mark_cancelled(self, request_id: str) -> None:
        """Mark a request as cancelled."""
        req = self._by_id.get(request_id)
        if req is not None:
            req.status = "cancelled"
            req._resolved_at = time.monotonic()

    def mark_minimized(self, request_id: str) -> None:
        """Mark a request as minimized."""
        req = self._by_id.get(request_id)
        if req is not None:
            req.status = "minimized"

    async def put(self, request: HITLRequest) -> None:
        """Enqueue a request. The sequence number breaks priority ties (FIFO)."""
        self._register(request)
        seq = next(HITLQueue._seq)
        await self._queue.put((request.priority, seq, request))

    def put_threadsafe(self, request: HITLRequest) -> None:
        """Enqueue from a foreign thread (HTTP/uvicorn → Textual direction).

        Schedules put_nowait on the Textual event loop via
        call_soon_threadsafe.  Safe for unbounded PriorityQueue.
        """
        self._register(request)
        seq = next(HITLQueue._seq)
        item = (request.priority, seq, request)
        loop = self._textual_loop
        if loop is not None and loop.is_running():
            loop.call_soon_threadsafe(self._queue.put_nowait, item)
        else:
            self._queue.put_nowait(item)

    async def get(self) -> HITLRequest:
        """Dequeue the next highest-priority request. Awaits if empty."""
        _, _, request = await self._queue.get()
        return request

    def resolve(self, request: HITLRequest, result: Any) -> None:
        """Resolve a request's future with the user's response.

        Uses call_soon_threadsafe to schedule resolution on the uvicorn
        event loop from the Textual thread. This is the correct primitive
        for cross-loop future resolution (Textual → uvicorn direction).
        run_coroutine_threadsafe is wrong here — it's for scheduling
        coroutines, not resolving existing futures.
        """
        if request.future.done():
            return
        loop = self._caller_loop
        if loop is not None and loop.is_running():

            def _resolve(fut: asyncio.Future[Any], val: Any) -> None:
                if not fut.done():
                    fut.set_result(val)

            loop.call_soon_threadsafe(_resolve, request.future, result)
        else:
            if not request.future.done():
                request.future.set_result(result)

    def reject(self, request: HITLRequest, exc: Exception) -> None:
        """Reject a request's future with an exception."""
        if request.future.done():
            return
        loop = self._caller_loop
        if loop is not None and loop.is_running():

            def _reject(fut: asyncio.Future[Any], error: Exception) -> None:
                if not fut.done():
                    fut.set_exception(error)

            loop.call_soon_threadsafe(_reject, request.future, exc)
        else:
            if not request.future.done():
                request.future.set_exception(exc)

    @property
    def size(self) -> int:
        """Number of pending requests."""
        return self._queue.qsize()

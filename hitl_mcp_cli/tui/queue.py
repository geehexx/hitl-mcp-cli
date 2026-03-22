"""Asyncio-based priority queue for serializing concurrent HITL tool calls."""

from __future__ import annotations

import asyncio
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
    _DISPLAY_KEYS = {"message", "context", "title", "validation_message", "default"}
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

    def __init__(self) -> None:
        self._queue: asyncio.PriorityQueue[tuple[int, int, HITLRequest]] = asyncio.PriorityQueue()
        self._seq: int = 0
        self._caller_loop: asyncio.AbstractEventLoop | None = None

    def set_caller_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Register the event loop that creates futures (uvicorn thread)."""
        self._caller_loop = loop

    async def put(self, request: HITLRequest) -> None:
        """Enqueue a request. The sequence number breaks priority ties (FIFO)."""
        self._seq += 1
        await self._queue.put((request.priority, self._seq, request))

    async def get(self) -> HITLRequest:
        """Dequeue the next highest-priority request. Awaits if empty."""
        _, _, request = await self._queue.get()
        return request

    def resolve(self, request: HITLRequest, result: Any) -> None:
        """Resolve a request's future with the user's response.

        Uses call_soon_threadsafe when the future belongs to a different
        event loop (uvicorn thread) than the caller (Textual thread).
        """
        if request.future.done():
            return
        loop = self._caller_loop
        if loop is not None and loop.is_running():
            loop.call_soon_threadsafe(request.future.set_result, result)
        else:
            request.future.set_result(result)

    def reject(self, request: HITLRequest, exc: Exception) -> None:
        """Reject a request's future with an exception."""
        if request.future.done():
            return
        loop = self._caller_loop
        if loop is not None and loop.is_running():
            loop.call_soon_threadsafe(request.future.set_exception, exc)
        else:
            request.future.set_exception(exc)

    @property
    def size(self) -> int:
        """Number of pending requests."""
        return self._queue.qsize()

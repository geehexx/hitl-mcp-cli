"""Request queue for handling concurrent HITL requests."""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


@dataclass(order=True)
class HitlRequest:
    """Represents a queued HITL request."""

    priority: int = field(compare=True)  # 0=critical, 1=normal, 2=low
    timestamp: datetime = field(compare=True)
    agent_id: str = field(compare=False)
    tool_name: str = field(compare=False)
    handler: Callable[[dict[str, Any]], Awaitable[Any]] = field(compare=False, repr=False)
    params: dict[str, Any] = field(compare=False, default_factory=dict)


class RequestQueue:
    """Manages HITL requests with intelligent queueing.

    Features:
    - Priority-based processing (critical > normal > low)
    - FIFO within same priority
    - Single active request at a time
    - Queue status display
    - Automatic request context switching
    """

    def __init__(self):
        """Initialize request queue."""
        self.queue: asyncio.PriorityQueue[HitlRequest] = asyncio.PriorityQueue()
        self.active_lock = asyncio.Lock()
        self.processing = False
        self._processor_task: asyncio.Task[None] | None = None

    async def submit(
        self,
        agent_id: str,
        tool_name: str,
        handler: Callable[[dict[str, Any]], Awaitable[Any]],
        params: dict[str, Any],
        priority: int = 1,
    ) -> Any:
        """Submit request to queue and wait for result.

        Args:
            agent_id: ID of agent making request
            tool_name: Name of HITL tool being called
            handler: Async function to execute
            params: Tool parameters
            priority: 0=critical, 1=normal (default), 2=low

        Returns:
            Result from handler execution
        """
        # Create request
        request = HitlRequest(
            priority=priority,
            timestamp=datetime.now(),
            agent_id=agent_id,
            tool_name=tool_name,
            handler=handler,
            params=params,
        )

        # Add to queue
        await self.queue.put(request)

        # Start processor if not running
        if not self.processing:
            self._processor_task = asyncio.create_task(self._process_queue())

        # Wait for our request to be processed
        # This is handled by the processor calling the handler
        # For now, we return immediately and let the processor handle it
        # In a full implementation, we'd use a Future to wait for results
        return None

    async def submit_and_wait(
        self,
        agent_id: str,
        tool_name: str,
        handler: Callable[[dict[str, Any]], Awaitable[Any]],
        params: dict[str, Any],
        priority: int = 1,
    ) -> Any:
        """Submit request and wait for result.

        Args:
            agent_id: ID of agent making request
            tool_name: Name of HITL tool being called
            handler: Async function to execute
            params: Tool parameters
            priority: 0=critical, 1=normal (default), 2=low

        Returns:
            Result from handler execution
        """
        # Use future for result
        result_future: asyncio.Future[Any] = asyncio.Future()

        async def wrapped_handler(p: dict[str, Any]) -> Any:
            try:
                result = await handler(p)
                result_future.set_result(result)
                return result
            except Exception as e:
                result_future.set_exception(e)
                raise

        # Create request
        request = HitlRequest(
            priority=priority,
            timestamp=datetime.now(),
            agent_id=agent_id,
            tool_name=tool_name,
            handler=wrapped_handler,
            params=params,
        )

        # Add to queue
        await self.queue.put(request)

        # Start processor if not running
        if not self.processing:
            self._processor_task = asyncio.create_task(self._process_queue())

        # Wait for result
        return await result_future

    async def _process_queue(self) -> None:
        """Process requests from queue sequentially."""
        self.processing = True

        try:
            while not self.queue.empty():
                # Get next request (automatically sorted by priority + timestamp)
                request = await self.queue.get()

                # Show which agent is requesting
                self._display_request_context(request)

                # Execute request with active lock
                async with self.active_lock:
                    try:
                        await request.handler(request.params)
                    except Exception as e:
                        console.print(f"[red]Error processing request: {e}[/red]")
                    finally:
                        self.queue.task_done()

        finally:
            self.processing = False

    def _display_request_context(self, request: HitlRequest) -> None:
        """Display request context before processing.

        Args:
            request: Request being processed
        """
        # Priority indicator
        priority_text = {0: "[red]CRITICAL[/]", 1: "[yellow]NORMAL[/]", 2: "[dim]LOW[/]"}.get(
            request.priority, "[yellow]NORMAL[/]"
        )

        # Create context panel
        context = Text()
        context.append("Agent: ", style="dim")
        context.append(request.agent_id, style="cyan bold")
        context.append("  |  Tool: ", style="dim")
        context.append(request.tool_name, style="magenta")
        context.append("  |  Priority: ", style="dim")
        context.append(priority_text)

        # Show queue size if there are pending requests
        queue_size = self.queue.qsize()
        if queue_size > 0:
            context.append("  |  Queued: ", style="dim")
            context.append(str(queue_size), style="yellow")

        console.print(Panel(context, border_style="dim", padding=(0, 1)))

    def get_status(self) -> dict[str, Any]:
        """Get current queue status.

        Returns:
            Status dictionary with queue size and processing state
        """
        return {"queue_size": self.queue.qsize(), "processing": self.processing}


# Global request queue instance
_global_queue: RequestQueue | None = None


def get_request_queue() -> RequestQueue:
    """Get global request queue instance.

    Returns:
        Shared RequestQueue instance
    """
    global _global_queue
    if _global_queue is None:
        _global_queue = RequestQueue()
    return _global_queue

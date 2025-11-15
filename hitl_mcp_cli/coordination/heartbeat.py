"""Heartbeat mechanism for agent liveness detection."""

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable

logger = logging.getLogger(__name__)


@dataclass
class AgentHealth:
    """Agent health status."""

    agent_id: str
    last_heartbeat: float
    heartbeat_count: int
    status: str  # "alive", "missing", "dead"
    metadata: dict


class HeartbeatManager:
    """Manage agent heartbeats and liveness detection.

    Features:
    - Agents send heartbeats every N seconds
    - Mark agents as missing after M missed heartbeats
    - Mark agents as dead after K missed heartbeats
    - Trigger cleanup callbacks for dead agents
    """

    def __init__(
        self,
        heartbeat_interval: int = 30,  # Expected interval (seconds)
        missing_threshold: int = 2,  # Missed beats before "missing"
        dead_threshold: int = 3,  # Missed beats before "dead"
    ):
        """Initialize heartbeat manager.

        Args:
            heartbeat_interval: Expected heartbeat interval in seconds
            missing_threshold: Missed heartbeats before marking missing
            dead_threshold: Missed heartbeats before marking dead
        """
        self.heartbeat_interval = heartbeat_interval
        self.missing_threshold = missing_threshold
        self.dead_threshold = dead_threshold

        # Agent health tracking
        self.agents: dict[str, AgentHealth] = {}

        # Callbacks for state changes
        self.on_missing_callbacks: list[Callable[[str], None]] = []
        self.on_dead_callbacks: list[Callable[[str], None]] = []

        # Background task
        self._monitor_task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        """Start heartbeat monitoring."""
        if not self._running:
            self._running = True
            self._monitor_task = asyncio.create_task(self._monitor_loop())
            logger.info("Heartbeat manager started")

    async def stop(self) -> None:
        """Stop heartbeat monitoring."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Heartbeat manager stopped")

    async def heartbeat(self, agent_id: str, metadata: dict | None = None) -> dict[str, float | str]:
        """Record agent heartbeat.

        Args:
            agent_id: Agent identifier
            metadata: Optional metadata (load, status, etc.)

        Returns:
            Status dict with next heartbeat time
        """
        now = time.time()

        if agent_id not in self.agents:
            self.agents[agent_id] = AgentHealth(
                agent_id=agent_id,
                last_heartbeat=now,
                heartbeat_count=1,
                status="alive",
                metadata=metadata or {},
            )
        else:
            agent = self.agents[agent_id]
            agent.last_heartbeat = now
            agent.heartbeat_count += 1
            agent.status = "alive"
            if metadata:
                agent.metadata.update(metadata)

        return {
            "acknowledged": True,
            "next_heartbeat_by": now + self.heartbeat_interval,
            "status": "alive",
        }

    async def get_agent_status(self, agent_id: str) -> dict[str, str | float | int] | None:
        """Get agent health status.

        Args:
            agent_id: Agent identifier

        Returns:
            Health status dict or None if not tracked
        """
        agent = self.agents.get(agent_id)
        if not agent:
            return None

        now = time.time()
        seconds_since_heartbeat = now - agent.last_heartbeat
        missed_beats = int(seconds_since_heartbeat / self.heartbeat_interval)

        return {
            "agent_id": agent.agent_id,
            "status": agent.status,
            "last_heartbeat": agent.last_heartbeat,
            "seconds_since_heartbeat": seconds_since_heartbeat,
            "missed_beats": missed_beats,
            "total_heartbeats": agent.heartbeat_count,
            "metadata": agent.metadata,
        }

    async def list_agents(self, status_filter: str | None = None) -> list[dict]:
        """List all tracked agents.

        Args:
            status_filter: Filter by status (alive, missing, dead)

        Returns:
            List of agent status dicts
        """
        agents = []
        for agent_id in self.agents:
            status = await self.get_agent_status(agent_id)
            if status and (status_filter is None or status["status"] == status_filter):
                agents.append(status)

        return agents

    def register_missing_callback(self, callback: Callable[[str], None]) -> None:
        """Register callback for when agent goes missing.

        Args:
            callback: Function to call with agent_id
        """
        self.on_missing_callbacks.append(callback)

    def register_dead_callback(self, callback: Callable[[str], None]) -> None:
        """Register callback for when agent is marked dead.

        Args:
            callback: Function to call with agent_id
        """
        self.on_dead_callbacks.append(callback)

    async def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while self._running:
            try:
                await asyncio.sleep(self.heartbeat_interval / 2)  # Check twice per interval
                await self._check_agents()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat monitor: {e}", exc_info=True)

    async def _check_agents(self) -> None:
        """Check agent health and trigger callbacks."""
        now = time.time()

        for agent_id, agent in list(self.agents.items()):
            seconds_since = now - agent.last_heartbeat
            missed_beats = int(seconds_since / self.heartbeat_interval)

            # Determine new status
            new_status = agent.status

            if missed_beats >= self.dead_threshold:
                new_status = "dead"
            elif missed_beats >= self.missing_threshold:
                new_status = "missing"
            else:
                new_status = "alive"

            # Trigger callbacks on state change
            if new_status != agent.status:
                old_status = agent.status
                agent.status = new_status

                logger.warning(
                    f"Agent {agent_id} status changed: {old_status} -> {new_status} "
                    f"(missed {missed_beats} heartbeats)"
                )

                # Trigger callbacks
                if new_status == "missing" and old_status == "alive":
                    for callback in self.on_missing_callbacks:
                        try:
                            callback(agent_id)
                        except Exception as e:
                            logger.error(f"Error in missing callback: {e}")

                elif new_status == "dead":
                    for callback in self.on_dead_callbacks:
                        try:
                            callback(agent_id)
                        except Exception as e:
                            logger.error(f"Error in dead callback: {e}")

    def get_stats(self) -> dict[str, int]:
        """Get heartbeat manager statistics.

        Returns:
            Stats dict
        """
        alive = sum(1 for a in self.agents.values() if a.status == "alive")
        missing = sum(1 for a in self.agents.values() if a.status == "missing")
        dead = sum(1 for a in self.agents.values() if a.status == "dead")

        return {
            "total_agents": len(self.agents),
            "alive": alive,
            "missing": missing,
            "dead": dead,
            "heartbeat_interval": self.heartbeat_interval,
        }

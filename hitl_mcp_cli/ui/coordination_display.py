"""Live coordination status display."""

import asyncio
from datetime import datetime
from typing import Any

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


class CoordinationMonitor:
    """Display live coordination activity in terminal.

    Shows:
    - Active channels
    - Recent messages
    - Agent heartbeat status
    - Active locks
    """

    def __init__(
        self,
        channel_store: Any | None = None,
        lock_manager: Any | None = None,
        heartbeat_manager: Any | None = None,
        update_interval: float = 2.0,
    ):
        """Initialize coordination monitor.

        Args:
            channel_store: ChannelStore instance
            lock_manager: LockManager instance
            heartbeat_manager: HeartbeatManager instance
            update_interval: How often to refresh display (seconds)
        """
        self.channel_store = channel_store
        self.lock_manager = lock_manager
        self.heartbeat_manager = heartbeat_manager
        self.update_interval = update_interval
        self._running = False

    def _create_channels_panel(self) -> Panel:
        """Create panel showing active channels.

        Returns:
            Panel with channel information
        """
        if not self.channel_store:
            return Panel("[dim]Coordination disabled[/]", title="Channels", border_style="dim")

        table = Table.grid(padding=(0, 2))
        table.add_column(style="cyan", justify="left")
        table.add_column(style="green", justify="right")

        try:
            stats = self.channel_store.get_stats()
            total_channels = stats.get("channels", 0)
            total_messages = stats.get("total_messages", 0)

            if total_channels == 0:
                table.add_row("[dim]No active channels[/]", "")
            else:
                # Get list of channels
                channels = asyncio.create_task(self.channel_store.list_channels())
                # Note: This is simplified - in real impl, cache channel list

                table.add_row("Active channels", str(total_channels))
                table.add_row("Total messages", str(total_messages))

        except Exception:
            table.add_row("[dim]Error fetching channel data[/]", "")

        return Panel(table, title="📨 Channels", border_style="cyan", padding=(0, 1))

    def _create_agents_panel(self) -> Panel:
        """Create panel showing agent heartbeat status.

        Returns:
            Panel with agent information
        """
        if not self.heartbeat_manager:
            return Panel("[dim]Heartbeat disabled[/]", title="Agents", border_style="dim")

        table = Table.grid(padding=(0, 2))
        table.add_column(style="green", justify="left")
        table.add_column(style="yellow", justify="right")

        try:
            agents = self.heartbeat_manager.list_agents()
            alive_count = len([a for a in agents if a.get("status") == "alive"])
            missing_count = len([a for a in agents if a.get("status") == "missing"])
            dead_count = len([a for a in agents if a.get("status") == "dead"])

            if not agents:
                table.add_row("[dim]No agents registered[/]", "")
            else:
                table.add_row("🟢 Alive", str(alive_count))
                if missing_count > 0:
                    table.add_row("🟡 Missing", str(missing_count))
                if dead_count > 0:
                    table.add_row("🔴 Dead", str(dead_count))

        except Exception:
            table.add_row("[dim]Error fetching agent data[/]", "")

        return Panel(table, title="💓 Agents", border_style="green", padding=(0, 1))

    def _create_locks_panel(self) -> Panel:
        """Create panel showing active locks.

        Returns:
            Panel with lock information
        """
        if not self.lock_manager:
            return Panel("[dim]Locks disabled[/]", title="Locks", border_style="dim")

        table = Table.grid(padding=(0, 2))
        table.add_column(style="yellow", justify="left")
        table.add_column(style="white", justify="right")

        try:
            locks = self.lock_manager.list_locks()
            active_locks = [l for l in locks if l.get("status") == "held"]

            if not active_locks:
                table.add_row("[dim]No active locks[/]", "")
            else:
                table.add_row("Active locks", str(len(active_locks)))
                # Show most recent lock
                if active_locks:
                    latest = active_locks[0]
                    table.add_row(f"  {latest.get('lock_name', 'unknown')}", f"{latest.get('held_by', 'unknown')}")

        except Exception:
            table.add_row("[dim]Error fetching lock data[/]", "")

        return Panel(table, title="🔒 Locks", border_style="yellow", padding=(0, 1))

    def create_display(self) -> Layout:
        """Create complete coordination display layout.

        Returns:
            Rich Layout with all panels
        """
        layout = Layout()

        # Create horizontal layout with all panels
        layout.split_row(
            Layout(self._create_channels_panel(), name="channels"),
            Layout(self._create_agents_panel(), name="agents"),
            Layout(self._create_locks_panel(), name="locks"),
        )

        return layout

    async def run(self) -> None:
        """Run live coordination monitor (blocking).

        Displays live panel that updates every `update_interval` seconds.
        """
        self._running = True

        try:
            with Live(self.create_display(), refresh_per_second=0.5, console=console) as live:
                while self._running:
                    await asyncio.sleep(self.update_interval)
                    live.update(self.create_display())
        except Exception as e:
            console.print(f"[red]Coordination monitor error: {e}[/red]")
        finally:
            self._running = False

    def stop(self) -> None:
        """Stop the coordination monitor."""
        self._running = False

    def render_once(self) -> None:
        """Render coordination status once (non-blocking).

        Useful for showing status on demand without live updates.
        """
        console.print(self.create_display())


def display_coordination_summary(
    channel_store: Any | None = None,
    lock_manager: Any | None = None,
    heartbeat_manager: Any | None = None,
) -> None:
    """Display one-time coordination summary.

    Args:
        channel_store: ChannelStore instance
        lock_manager: LockManager instance
        heartbeat_manager: HeartbeatManager instance
    """
    monitor = CoordinationMonitor(
        channel_store=channel_store,
        lock_manager=lock_manager,
        heartbeat_manager=heartbeat_manager,
    )

    monitor.render_once()

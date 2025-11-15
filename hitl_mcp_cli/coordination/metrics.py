"""Prometheus metrics for coordination system."""

from prometheus_client import Counter, Gauge, Histogram

# Message metrics
messages_sent_total = Counter(
    "coordination_messages_sent_total",
    "Total messages sent to channels",
    ["channel", "message_type", "agent_id"],
)

messages_received_total = Counter(
    "coordination_messages_received_total", "Total messages polled from channels", ["channel", "agent_id"]
)

# Channel metrics
channels_active = Gauge("coordination_channels_active", "Number of active channels")

channel_members = Gauge("coordination_channel_members", "Members in channel", ["channel"])

channel_message_count = Gauge("coordination_channel_messages", "Messages in channel", ["channel"])

# Lock metrics
locks_acquired_total = Counter("coordination_locks_acquired_total", "Total locks acquired", ["agent_id"])

locks_failed_total = Counter("coordination_locks_failed_total", "Total lock acquisitions failed", ["agent_id"])

locks_active = Gauge("coordination_locks_active", "Number of active locks")

lock_wait_seconds = Histogram(
    "coordination_lock_wait_seconds", "Time waited for lock acquisition", ["lock_name"], buckets=[0.1, 0.5, 1, 5, 10, 30]
)

# Auth metrics
auth_attempts_total = Counter("coordination_auth_attempts_total", "Authentication attempts", ["agent_id", "success"])

auth_failures_total = Counter("coordination_auth_failures_total", "Authentication failures", ["agent_id"])

# Rate limit metrics
rate_limit_exceeded_total = Counter(
    "coordination_rate_limit_exceeded_total", "Rate limit exceeded events", ["agent_id"]
)

rate_limit_tokens_available = Gauge(
    "coordination_rate_limit_tokens_available", "Available rate limit tokens", ["agent_id"]
)

# Heartbeat metrics
heartbeat_total = Counter("coordination_heartbeat_total", "Total heartbeats received", ["agent_id"])

agents_alive = Gauge("coordination_agents_alive", "Number of alive agents")

agents_missing = Gauge("coordination_agents_missing", "Number of missing agents")

agents_dead = Gauge("coordination_agents_dead", "Number of dead agents")

# Performance metrics
operation_duration_seconds = Histogram(
    "coordination_operation_duration_seconds",
    "Operation duration",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
)


def update_metrics(channel_store, lock_manager, heartbeat_manager=None):
    """Update gauge metrics from backend state.

    Call this periodically to keep metrics in sync.
    """
    # Channel metrics
    channels_active.set(len(channel_store.channels))

    for ch_name, messages in channel_store.messages.items():
        channel_message_count.labels(channel=ch_name).set(len(messages))

    for ch_name, channel in channel_store.channels.items():
        channel_members.labels(channel=ch_name).set(len(channel.members))

    # Lock metrics
    locks_active.set(len(lock_manager.locks))

    # Heartbeat metrics
    if heartbeat_manager:
        stats = heartbeat_manager.get_stats()
        agents_alive.set(stats["alive"])
        agents_missing.set(stats["missing"])
        agents_dead.set(stats["dead"])

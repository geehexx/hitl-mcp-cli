"""Cross-platform OS desktop notification helper.

Tries notify-send (Linux/freedesktop), osascript (macOS), and
win10toast/Windows toast in that order. Silently no-ops if none are
available — OS notifications are a best-effort side-channel, never
load-bearing.
"""

from __future__ import annotations

import shutil
import subprocess  # nosec B404
import sys


def _notify_linux(title: str, body: str, urgency: str) -> bool:
    """Fire notify-send. Returns True on success."""
    if not shutil.which("notify-send"):
        return False
    ns_urgency = "critical" if urgency == "error" else "normal"
    try:
        completed = subprocess.run(  # nosec B603 B607
            ["notify-send", "--urgency", ns_urgency, "--app-name", "hitl-mcp", title, body],
            timeout=3,
            check=False,
            capture_output=True,
        )
        return completed.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _notify_macos(title: str, body: str) -> bool:
    """Fire osascript display notification. Returns True on success."""
    if not shutil.which("osascript"):
        return False
    try:
        completed = subprocess.run(  # nosec B603 B607
            [
                "osascript",
                "-e",
                "on run argv",
                "-e",
                "display notification (item 2 of argv) with title (item 1 of argv)",
                "-e",
                "end run",
                "--",
                title,
                body,
            ],
            timeout=3,
            check=False,
            capture_output=True,
        )
        return completed.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def send_os_notification(
    title: str,
    body: str,
    level: str = "info",
) -> bool:
    """Send a best-effort desktop notification.

    Args:
        title: Short notification title.
        body: Notification body text.
        level: One of ``"success"``, ``"info"``, ``"warning"``, ``"error"``.

    Returns:
        ``True`` if a notification was dispatched, ``False`` if no backend
        was available or the call failed.
    """
    platform = sys.platform
    if platform.startswith("linux"):
        return _notify_linux(title, body, level)
    if platform == "darwin":
        return _notify_macos(title, body)
    return False


__all__ = ["send_os_notification"]

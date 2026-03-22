"""Tests for transport-level log filtering."""

import logging

from hitl_mcp_cli.cli import _SuppressClosedResource


def test_log_filters_suppress_closed_resource() -> None:
    """Verify ClosedResourceError noise is suppressed from FastMCP loggers."""
    f = _SuppressClosedResource()

    suppressed = [
        "ClosedResourceError",
        "ClientDisconnect",
        "Error in message router",
        "Received exception from stream",
    ]
    for msg in suppressed:
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg=msg,
            args=(),
            exc_info=None,
        )
        assert f.filter(record) is False, f"Should suppress: {msg}"

    record_ok = logging.LogRecord(
        name="test",
        level=logging.ERROR,
        pathname="",
        lineno=0,
        msg="Some real error",
        args=(),
        exc_info=None,
    )
    assert f.filter(record_ok) is True

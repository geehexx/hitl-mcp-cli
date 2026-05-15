"""Tests for interaction logging."""

import json
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

from hitl_mcp_cli import interaction_log
from hitl_mcp_cli.interaction_log import MAX_LOG_SIZE, log_interaction


@pytest.fixture()
def log_dir(tmp_path: Path) -> Path:
    """Redirect logging to a temp directory."""
    log_file = tmp_path / "interactions.jsonl"
    with (
        patch.object(interaction_log, "LOG_DIR", tmp_path),
        patch.object(interaction_log, "LOG_FILE", log_file),
    ):
        yield tmp_path


def _read_entries(log_dir: Path) -> list[dict]:
    log_file = log_dir / "interactions.jsonl"
    return [json.loads(line) for line in log_file.read_text().splitlines() if line.strip()]


class TestLogFileCreation:
    def test_creates_log_file_on_first_write(self, log_dir: Path) -> None:
        log_interaction("hitl_collect", 100, "value")
        assert (log_dir / "interactions.jsonl").exists()

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b"
        log_file = nested / "interactions.jsonl"
        with (
            patch.object(interaction_log, "LOG_DIR", nested),
            patch.object(interaction_log, "LOG_FILE", log_file),
        ):
            log_interaction("hitl_notify", 5, "value")
        assert log_file.exists()


class TestEntryFormat:
    def test_entry_has_required_fields(self, log_dir: Path) -> None:
        log_interaction("hitl_collect", 1234, "value")
        entries = _read_entries(log_dir)
        assert len(entries) == 1
        entry = entries[0]
        assert set(entry.keys()) == {"ts", "tool", "duration_ms", "result_type", "session_id"}

    def test_tool_name_preserved(self, log_dir: Path) -> None:
        log_interaction("hitl_confirm", 500, "cancel")
        assert _read_entries(log_dir)[0]["tool"] == "hitl_confirm"

    def test_duration_ms_is_int(self, log_dir: Path) -> None:
        log_interaction("hitl_ask", 42, "value")
        assert _read_entries(log_dir)[0]["duration_ms"] == 42

    def test_result_types(self, log_dir: Path) -> None:
        for rt in ("value", "cancel", "timeout"):
            log_interaction("hitl_confirm", 10, rt)
        entries = _read_entries(log_dir)
        assert [e["result_type"] for e in entries] == ["value", "cancel", "timeout"]

    def test_session_id_is_uuid(self, log_dir: Path) -> None:
        log_interaction("hitl_collect", 10, "value")
        sid = _read_entries(log_dir)[0]["session_id"]
        uuid.UUID(sid)  # raises if invalid

    def test_session_id_consistent(self, log_dir: Path) -> None:
        log_interaction("hitl_collect", 10, "value")
        log_interaction("hitl_ask", 20, "value")
        entries = _read_entries(log_dir)
        assert entries[0]["session_id"] == entries[1]["session_id"]

    def test_ts_is_iso8601(self, log_dir: Path) -> None:
        log_interaction("hitl_notify", 5, "value")
        ts = _read_entries(log_dir)[0]["ts"]
        assert "T" in ts  # basic ISO8601 check

    def test_multiple_entries_appended(self, log_dir: Path) -> None:
        for i in range(5):
            log_interaction("hitl_notify", i, "value")
        assert len(_read_entries(log_dir)) == 5


class TestRotation:
    def test_rotates_when_exceeds_max_size(self, log_dir: Path) -> None:
        log_file = log_dir / "interactions.jsonl"
        # Write a file just over the limit
        log_file.write_text("x" * (MAX_LOG_SIZE + 1))
        log_interaction("hitl_collect", 10, "value")
        # Old file rotated
        assert (log_dir / "interactions.jsonl.1").exists()
        # New file has only the new entry
        entries = _read_entries(log_dir)
        assert len(entries) == 1

    def test_no_rotation_under_limit(self, log_dir: Path) -> None:
        log_file = log_dir / "interactions.jsonl"
        log_file.write_text("x" * 100)
        log_interaction("hitl_collect", 10, "value")
        assert not (log_dir / "interactions.jsonl.1").exists()


class TestErrorSuppression:
    def test_logging_error_does_not_propagate(self, log_dir: Path) -> None:
        with patch.object(interaction_log, "LOG_DIR", Path("/nonexistent/readonly/path")):
            with patch.object(interaction_log, "LOG_FILE", Path("/nonexistent/readonly/path/x.jsonl")):
                # Should not raise
                log_interaction("hitl_collect", 10, "value")

    def test_logging_error_prints_to_stderr(self, log_dir: Path, capsys: pytest.CaptureFixture) -> None:
        with patch.object(interaction_log, "LOG_DIR", Path("/nonexistent/readonly/path")):
            with patch.object(interaction_log, "LOG_FILE", Path("/nonexistent/readonly/path/x.jsonl")):
                log_interaction("hitl_collect", 10, "value")
        assert "logging error" in capsys.readouterr().err

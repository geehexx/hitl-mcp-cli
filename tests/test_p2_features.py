"""Tests for P2 features: OS notifications, question rejection, elaboration,
quick recommendations, and agent-skills support."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastmcp import Client

from hitl_mcp_cli import _server_core
from hitl_mcp_cli.server import configure_tui_mode, mcp
from hitl_mcp_cli.tui.queue import HITLQueue

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_tui_globals() -> Any:
    _server_core._tui_queue = None
    _server_core._tui_app = None
    yield
    _server_core._tui_queue = None
    _server_core._tui_app = None


@pytest.fixture
async def tui_queue() -> Any:
    queue = HITLQueue()
    configure_tui_mode(queue, None)  # type: ignore[arg-type]
    yield queue
    configure_tui_mode(None, None)  # type: ignore[arg-type]


@pytest.fixture
async def mcp_client(tui_queue: HITLQueue) -> Any:
    async with Client(mcp) as client:
        yield client


# ---------------------------------------------------------------------------
# Feature 9: OS notifications
# ---------------------------------------------------------------------------


class TestOsNotify:
    def test_module_importable(self) -> None:
        from hitl_mcp_cli._os_notify import send_os_notification  # noqa: F401

    def test_send_os_notification_returns_bool(self) -> None:
        from hitl_mcp_cli._os_notify import send_os_notification

        result = send_os_notification("Test", "body", "info")
        assert isinstance(result, bool)

    def test_linux_notify_send_called(self) -> None:
        from hitl_mcp_cli._os_notify import _notify_linux

        with patch("shutil.which", return_value="/usr/bin/notify-send"), patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = _notify_linux("Title", "Body", "info")
        assert result is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "notify-send" in args
        assert "Title" in args
        assert "Body" in args

    def test_linux_notify_send_missing_returns_false(self) -> None:
        from hitl_mcp_cli._os_notify import _notify_linux

        with patch("shutil.which", return_value=None):
            result = _notify_linux("Title", "Body", "info")
        assert result is False

    def test_linux_error_urgency_maps_to_critical(self) -> None:
        from hitl_mcp_cli._os_notify import _notify_linux

        with patch("shutil.which", return_value="/usr/bin/notify-send"), patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            _notify_linux("Title", "Body", "error")
        args = mock_run.call_args[0][0]
        assert "critical" in args

    def test_macos_osascript_called(self) -> None:
        from hitl_mcp_cli._os_notify import _notify_macos

        with patch("shutil.which", return_value="/usr/bin/osascript"), patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = _notify_macos("Title", "Body")
        assert result is True

    def test_send_os_notification_linux_dispatch(self) -> None:
        from hitl_mcp_cli._os_notify import send_os_notification

        with (
            patch("sys.platform", "linux"),
            patch("hitl_mcp_cli._os_notify._notify_linux", return_value=True) as mock_linux,
        ):
            result = send_os_notification("T", "B", "warning")
        assert result is True
        mock_linux.assert_called_once_with("T", "B", "warning")

    def test_send_os_notification_macos_dispatch(self) -> None:
        from hitl_mcp_cli._os_notify import send_os_notification

        with (
            patch("sys.platform", "darwin"),
            patch("hitl_mcp_cli._os_notify._notify_macos", return_value=True) as mock_mac,
        ):
            result = send_os_notification("T", "B", "info")
        assert result is True
        mock_mac.assert_called_once_with("T", "B")

    def test_send_os_notification_windows_returns_false(self) -> None:
        from hitl_mcp_cli._os_notify import send_os_notification

        with patch("sys.platform", "win32"):
            result = send_os_notification("T", "B", "info")
        assert result is False

    def test_tui_enqueue_fires_os_notification_on_put(self) -> None:
        """send_os_notification is called inside tui_enqueue after put_threadsafe."""
        import inspect

        import hitl_mcp_cli._server_core as sc

        src = inspect.getsource(sc.tui_enqueue)
        assert "send_os_notification" in src, "tui_enqueue must call send_os_notification as a side-effect"

    def test_notify_tool_calls_send_os_notification(self) -> None:
        """hitl_notify imports and calls send_os_notification."""
        import inspect

        import hitl_mcp_cli.tools._notify as nm

        src = inspect.getsource(nm)
        assert "send_os_notification" in src


# ---------------------------------------------------------------------------
# Feature 10: Question rejection
# ---------------------------------------------------------------------------


class TestQuestionRejection:
    def test_module_importable(self) -> None:
        from hitl_mcp_cli.tools._reject import hitl_reject_question  # noqa: F401

    @pytest.mark.asyncio
    async def test_reject_returns_status_rejected_question(self, mcp_client: Client) -> None:
        result = await mcp_client.call_tool(
            "hitl_reject_question",
            {"reason": "Question is ambiguous — missing PR number."},
        )
        assert result.data["status"] == "rejected_question"
        assert "ambiguous" in result.data["reason"]

    @pytest.mark.asyncio
    async def test_reject_includes_question_id_when_provided(self, mcp_client: Client) -> None:
        result = await mcp_client.call_tool(
            "hitl_reject_question",
            {
                "reason": "Missing context",
                "question_id": "abc-123",
                "original_message": "Which branch?",
            },
        )
        assert result.data["question_id"] == "abc-123"

    @pytest.mark.asyncio
    async def test_reject_without_question_id(self, mcp_client: Client) -> None:
        result = await mcp_client.call_tool(
            "hitl_reject_question",
            {"reason": "Out of scope"},
        )
        assert result.data["status"] == "rejected_question"
        assert "question_id" not in result.data


# ---------------------------------------------------------------------------
# Feature 11: Elaboration requesting
# ---------------------------------------------------------------------------


class TestElaborationRequesting:
    def test_module_importable(self) -> None:
        from hitl_mcp_cli.tools._elaborate import hitl_request_elaboration  # noqa: F401

    @pytest.mark.asyncio
    async def test_elaboration_enqueues_enriched_question(
        self, mcp_client: Client, tui_queue: HITLQueue
    ) -> None:
        async def _resolve() -> None:
            await asyncio.sleep(0.05)
            req = await tui_queue.get()
            # Verify the enriched message contains both original + elaboration
            assert "Which branch?" in req.params["message"]
            assert "Elaboration" in req.params["message"]
            tui_queue.resolve(req, "main")

        _task = asyncio.create_task(_resolve())
        result = await mcp_client.call_tool(
            "hitl_request_elaboration",
            {
                "original_message": "Which branch?",
                "elaboration": "Available: main, develop, feat/x",
                "agent_name": "test-agent",
            },
        )
        await _task
        assert result.data == "main"

    @pytest.mark.asyncio
    async def test_elaboration_marks_elaboration_flag_in_params(
        self, mcp_client: Client, tui_queue: HITLQueue
    ) -> None:
        captured: list[Any] = []

        async def _resolve() -> None:
            await asyncio.sleep(0.05)
            req = await tui_queue.get()
            captured.append(req.params)
            tui_queue.resolve(req, "develop")

        _task = asyncio.create_task(_resolve())
        await mcp_client.call_tool(
            "hitl_request_elaboration",
            {"original_message": "Pick env", "elaboration": "staging or prod"},
        )
        await _task
        assert captured[0].get("_elaboration") is True


# ---------------------------------------------------------------------------
# Feature 12: Quick recommendations auto-selection
# ---------------------------------------------------------------------------


class TestQuickRecommendations:
    def test_module_importable(self) -> None:
        from hitl_mcp_cli.tools._recommend import hitl_recommend  # noqa: F401

    @pytest.mark.asyncio
    async def test_auto_accepted_when_timer_expires(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        # Don't resolve — let the timer expire (override_seconds=0 → immediate)
        result = await mcp_client.call_tool(
            "hitl_recommend",
            {
                "message": "Deploy now?",
                "recommendation": "yes",
                "choices": ["yes", "no"],
                "override_seconds": 0,
            },
        )
        assert result.data["status"] == "auto_accepted"
        assert result.data["value"] == "yes"
        assert "elapsed_seconds" in result.data

    @pytest.mark.asyncio
    async def test_user_selected_when_user_responds(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        async def _resolve() -> None:
            await asyncio.sleep(0.05)
            req = await tui_queue.get()
            tui_queue.resolve(req, "no")

        _task = asyncio.create_task(_resolve())
        result = await mcp_client.call_tool(
            "hitl_recommend",
            {
                "message": "Merge to main?",
                "recommendation": "yes",
                "choices": ["yes", "no"],
                "override_seconds": 30,
            },
        )
        await _task
        assert result.data["status"] == "user_selected"
        assert result.data["value"] == "no"

    @pytest.mark.asyncio
    async def test_recommendation_is_first_choice(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        captured: list[Any] = []

        async def _resolve() -> None:
            await asyncio.sleep(0.05)
            req = await tui_queue.get()
            captured.append(req.params)
            tui_queue.resolve(req, "yes")

        _task = asyncio.create_task(_resolve())
        await mcp_client.call_tool(
            "hitl_recommend",
            {
                "message": "Continue?",
                "recommendation": "yes",
                "choices": ["yes", "no", "defer"],
                "override_seconds": 30,
            },
        )
        await _task
        assert captured[0]["choices"][0] == "yes"
        assert captured[0]["default"] == "yes"

    @pytest.mark.asyncio
    async def test_recommendation_without_choices(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        async def _resolve() -> None:
            await asyncio.sleep(0.05)
            req = await tui_queue.get()
            tui_queue.resolve(req, "proceed")

        _task = asyncio.create_task(_resolve())
        result = await mcp_client.call_tool(
            "hitl_recommend",
            {"message": "Proceed?", "recommendation": "proceed", "override_seconds": 30},
        )
        await _task
        assert result.data["status"] == "user_selected"
        assert result.data["value"] == "proceed"


# ---------------------------------------------------------------------------
# Feature 13: Agent-skills support — skill file exists and is well-formed
# ---------------------------------------------------------------------------


class TestAgentSkillsSupport:
    def test_skill_file_exists(self) -> None:
        skill_path = Path(__file__).parent.parent / ".claude" / "skills" / "hitl-mcp-usage" / "SKILL.md"
        assert skill_path.exists(), f"SKILL.md not found at {skill_path}"

    def test_skill_file_has_frontmatter(self) -> None:
        skill_path = Path(__file__).parent.parent / ".claude" / "skills" / "hitl-mcp-usage" / "SKILL.md"
        content = skill_path.read_text()
        assert content.startswith("---"), "SKILL.md must start with YAML frontmatter"
        assert "name:" in content
        assert "description:" in content
        assert "activation:" in content

    def test_skill_file_covers_all_p2_tools(self) -> None:
        skill_path = Path(__file__).parent.parent / ".claude" / "skills" / "hitl-mcp-usage" / "SKILL.md"
        content = skill_path.read_text()
        for tool in [
            "hitl_reject_question",
            "hitl_request_elaboration",
            "hitl_recommend",
            "hitl_notify",
            "hitl_poll",
        ]:
            assert tool in content, f"SKILL.md missing reference to {tool}"

    def test_skill_file_has_code_examples(self) -> None:
        skill_path = Path(__file__).parent.parent / ".claude" / "skills" / "hitl-mcp-usage" / "SKILL.md"
        content = skill_path.read_text()
        assert "```python" in content, "SKILL.md should contain Python code examples"

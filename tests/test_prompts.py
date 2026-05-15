"""Tests for hitl_mcp_cli prompt templates."""

from __future__ import annotations

import pytest

from hitl_mcp_cli.prompts._arch_fork import architectural_fork
from hitl_mcp_cli.prompts._destructive import destructive_action
from hitl_mcp_cli.prompts._panel_vote import panel_vote_summary
from hitl_mcp_cli.prompts._scope_clarify import scope_clarification


def _body(msgs: list) -> str:
    content = msgs[0].content
    return content.text if hasattr(content, "text") else str(content)


class TestArchitecturalFork:
    @pytest.mark.asyncio
    async def test_required_fields_present(self):
        msgs = await architectural_fork.render({"decision": "Use SQL or NoSQL?", "options": "- SQL\n- NoSQL"})
        body = _body(msgs)
        assert "Use SQL or NoSQL?" in body
        assert "SQL" in body

    @pytest.mark.asyncio
    async def test_optional_constraints_included(self):
        msgs = await architectural_fork.render(
            {"decision": "Pick a queue", "options": "- Redis\n- SQS", "constraints": "Must be self-hosted"}
        )
        assert "Must be self-hosted" in _body(msgs)

    @pytest.mark.asyncio
    async def test_optional_recommendation_included(self):
        msgs = await architectural_fork.render(
            {
                "decision": "Pick a queue",
                "options": "- Redis\n- SQS",
                "recommendation": "Redis for simplicity",
            }
        )
        assert "Redis for simplicity" in _body(msgs)

    @pytest.mark.asyncio
    async def test_omitted_optionals_absent(self):
        msgs = await architectural_fork.render({"decision": "Pick a queue", "options": "- Redis\n- SQS"})
        body = _body(msgs)
        assert "Constraints" not in body
        assert "recommendation" not in body.lower()

    @pytest.mark.asyncio
    async def test_returns_user_role(self):
        msgs = await architectural_fork.render({"decision": "d", "options": "o"})
        assert msgs[0].role == "user"


class TestDestructiveAction:
    @pytest.mark.asyncio
    async def test_required_fields_present(self):
        msgs = await destructive_action.render(
            {"action": "Drop the users table", "blast_radius": "All user data"}
        )
        body = _body(msgs)
        assert "Drop the users table" in body
        assert "All user data" in body

    @pytest.mark.asyncio
    async def test_rollback_path_included(self):
        msgs = await destructive_action.render(
            {
                "action": "Delete S3 bucket",
                "blast_radius": "All uploads",
                "rollback_path": "Restore from Glacier",
            }
        )
        assert "Restore from Glacier" in _body(msgs)

    @pytest.mark.asyncio
    async def test_missing_rollback_warns(self):
        msgs = await destructive_action.render({"action": "Wipe DB", "blast_radius": "Everything"})
        assert "no rollback documented" in _body(msgs)

    @pytest.mark.asyncio
    async def test_returns_user_role(self):
        msgs = await destructive_action.render({"action": "a", "blast_radius": "b"})
        assert msgs[0].role == "user"


class TestPanelVoteSummary:
    @pytest.mark.asyncio
    async def test_all_fields_present(self):
        msgs = await panel_vote_summary.render(
            {
                "decision": "Merge feature X",
                "votes": "Agent A: APPROVE\nAgent B: REJECT",
                "counter_arguments": "Agent B: too risky",
                "quorum_outcome": "REJECTED",
            }
        )
        body = _body(msgs)
        assert "Merge feature X" in body
        assert "Agent A: APPROVE" in body
        assert "Agent B: too risky" in body
        assert "REJECTED" in body

    @pytest.mark.asyncio
    async def test_returns_user_role(self):
        msgs = await panel_vote_summary.render(
            {"decision": "d", "votes": "v", "counter_arguments": "c", "quorum_outcome": "o"}
        )
        assert msgs[0].role == "user"


class TestScopeClarification:
    @pytest.mark.asyncio
    async def test_all_fields_present(self):
        msgs = await scope_clarification.render(
            {
                "task": "Refactor auth module",
                "ambiguity": "Which auth module?",
                "interpretations": "- Legacy JWT\n- New OAuth",
            }
        )
        body = _body(msgs)
        assert "Refactor auth module" in body
        assert "Which auth module?" in body
        assert "Legacy JWT" in body

    @pytest.mark.asyncio
    async def test_returns_user_role(self):
        msgs = await scope_clarification.render({"task": "t", "ambiguity": "a", "interpretations": "i"})
        assert msgs[0].role == "user"

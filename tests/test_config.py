"""Tests for hitl_mcp_cli._config timeout resolution."""

from __future__ import annotations

from hitl_mcp_cli._config import resolve_timeout


class TestResolveTimeout:
    def test_zero_returns_zero_by_default(self):
        assert resolve_timeout(0) == 0

    def test_positive_passthrough(self):
        assert resolve_timeout(30) == 30

    def test_default_wait_substitutes_zero(self, monkeypatch):
        monkeypatch.setenv("HITL_DEFAULT_WAIT", "60")
        assert resolve_timeout(0) == 60

    def test_default_wait_zero_keeps_infinite(self, monkeypatch):
        monkeypatch.setenv("HITL_DEFAULT_WAIT", "0")
        assert resolve_timeout(0) == 0

    def test_min_wait_clamps_up(self, monkeypatch):
        monkeypatch.setenv("HITL_MIN_WAIT", "10")
        assert resolve_timeout(5) == 10

    def test_min_wait_no_effect_when_above_floor(self, monkeypatch):
        monkeypatch.setenv("HITL_MIN_WAIT", "10")
        assert resolve_timeout(30) == 30

    def test_max_wait_clamps_down(self, monkeypatch):
        monkeypatch.setenv("HITL_MAX_WAIT", "120")
        assert resolve_timeout(300) == 120

    def test_max_wait_no_effect_when_below_ceiling(self, monkeypatch):
        monkeypatch.setenv("HITL_MAX_WAIT", "120")
        assert resolve_timeout(60) == 60

    def test_min_and_max_together(self, monkeypatch):
        monkeypatch.setenv("HITL_MIN_WAIT", "10")
        monkeypatch.setenv("HITL_MAX_WAIT", "120")
        assert resolve_timeout(5) == 10
        assert resolve_timeout(60) == 60
        assert resolve_timeout(300) == 120

    def test_default_then_max(self, monkeypatch):
        monkeypatch.setenv("HITL_DEFAULT_WAIT", "300")
        monkeypatch.setenv("HITL_MAX_WAIT", "120")
        assert resolve_timeout(0) == 120

    def test_default_then_min(self, monkeypatch):
        monkeypatch.setenv("HITL_DEFAULT_WAIT", "5")
        monkeypatch.setenv("HITL_MIN_WAIT", "10")
        assert resolve_timeout(0) == 10

    def test_invalid_env_var_falls_back_to_zero(self, monkeypatch):
        monkeypatch.setenv("HITL_DEFAULT_WAIT", "notanumber")
        assert resolve_timeout(0) == 0

    def test_negative_env_var_treated_as_zero(self, monkeypatch):
        monkeypatch.setenv("HITL_MIN_WAIT", "-5")
        assert resolve_timeout(3) == 3

    def test_min_does_not_apply_to_infinite(self, monkeypatch):
        """HITL_MIN_WAIT must not convert infinite (0) to a finite timeout."""
        monkeypatch.setenv("HITL_MIN_WAIT", "10")
        assert resolve_timeout(0) == 0

    def test_max_does_not_apply_to_infinite(self, monkeypatch):
        """HITL_MAX_WAIT must not convert infinite (0) to a finite timeout."""
        monkeypatch.setenv("HITL_MAX_WAIT", "120")
        assert resolve_timeout(0) == 0

    def test_env_vars_cleared_between_tests(self):
        """Verify monkeypatch isolation — no env bleed from prior tests."""
        assert resolve_timeout(0) == 0
        assert resolve_timeout(30) == 30

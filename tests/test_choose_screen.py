"""Tests for ChooseScreen BadIdentifier fix (index-based button IDs)."""

from __future__ import annotations

import asyncio
import re
from typing import Any, ClassVar

import pytest
from textual.widgets import OptionList

from hitl_mcp_cli.tui.app import HITLApp
from hitl_mcp_cli.tui.queue import HITLQueue, HITLRequest
from hitl_mcp_cli.tui.screens import ChooseScreen


def _make_request(params: dict[str, Any]) -> HITLRequest:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    return HITLRequest(tool="hitl_choose", params=params, future=loop.create_future())


class _TestApp(HITLApp):
    CSS_PATH: ClassVar[list[str]] = []  # type: ignore[assignment]

    def start_queue_worker(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Unit tests on mapping logic (no TUI rendering needed)
# ---------------------------------------------------------------------------


def test_choice_index_map_uses_indices() -> None:
    """_choice_index_map keys must be 'choice-N', values the original strings."""
    choices = ["A — Missing vendor sources (Section 3.2)", "B / C", "D (extra)"]
    loop = asyncio.new_event_loop()
    screen = ChooseScreen(
        HITLRequest(
            tool="hitl_choose", params={"message": "Pick", "choices": choices}, future=loop.create_future()
        )
    )
    loop.close()
    assert screen._choice_index_map == {
        "choice-0": "A — Missing vendor sources (Section 3.2)",
        "choice-1": "B / C",
        "choice-2": "D (extra)",
    }


def test_sanitize_option_id_strips_special_chars() -> None:
    """Sanitized IDs must match [a-zA-Z0-9_-]* and start with a letter/digit."""
    cases = [
        ("simple", 0, "simple"),
        ("hello world", 0, "hello-world"),
        ("A — em dash", 0, "A---em-dash"),
        ("---leading-dashes", 0, "leading-dashes"),
        ("", 3, "opt-3"),
        ("123numeric", 0, "123numeric"),
    ]
    for value, idx, expected in cases:
        result = ChooseScreen._sanitize_option_id(value, idx)
        assert result == expected, f"sanitize({value!r}) → {result!r}, want {expected!r}"
        assert re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]*", result), f"Invalid ID: {result!r}"


def test_option_value_map_round_trips() -> None:
    """_option_value_map must map sanitized ID back to original value."""
    options = [
        {"value": "opt_a", "label": "Option A"},
        {"value": "hello world", "label": "Hello World"},
        {"value": "A — special", "label": "Special"},
    ]
    loop = asyncio.new_event_loop()
    screen = ChooseScreen(
        HITLRequest(
            tool="hitl_choose", params={"message": "Pick", "options": options}, future=loop.create_future()
        )
    )
    loop.close()
    for i, opt in enumerate(options):
        original = opt["value"]
        sanitized = ChooseScreen._sanitize_option_id(original, i)
        assert screen._option_value_map.get(sanitized) == original


# ---------------------------------------------------------------------------
# TUI rendering tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_choices_with_special_chars_no_crash() -> None:
    """ChooseScreen with choices containing spaces, em-dashes, parens renders without BadIdentifier."""
    choices = [
        "A — Missing vendor sources (Section 3.2)",
        "B / C: something",
        "D (extra info)",
    ]
    app = _TestApp(hitl_queue=HITLQueue())
    async with app.run_test(size=(80, 24)) as pilot:
        req = _make_request({"message": "Pick one", "choices": choices})
        screen = ChooseScreen(req)
        app.push_screen(screen)
        await pilot.pause()
        # If BadIdentifier was raised, push_screen would have thrown — reaching here means pass
        assert screen.query_one("#choose-list", OptionList) is not None


@pytest.mark.asyncio
async def test_correct_value_returned_after_selection() -> None:
    """Selecting choice-0 button in multiple mode returns the original choice string."""
    choices = ["A — Missing vendor sources (Section 3.2)", "B simple"]
    results: list[Any] = []
    app = _TestApp(hitl_queue=HITLQueue())

    async with app.run_test(size=(80, 24)) as pilot:
        req = _make_request({"message": "Pick", "choices": choices, "multiple": True})
        app.push_screen(ChooseScreen(req), callback=results.append)
        await pilot.pause()
        await pilot.click("#choice-0")
        await pilot.pause(0.05)
        await pilot.click("#done")
        await pilot.pause(0.05)

    assert results, "dismiss was never called"
    assert results[0] == ["A — Missing vendor sources (Section 3.2)"]


@pytest.mark.asyncio
async def test_options_value_used_as_id() -> None:
    """Options dict with short value field uses sanitized value as OptionList ID."""
    options = [
        {"value": "opt_a", "label": "Option A", "description": "First"},
        {"value": "opt_b", "label": "Option B"},
    ]
    app = _TestApp(hitl_queue=HITLQueue())
    async with app.run_test(size=(80, 24)) as pilot:
        req = _make_request({"message": "Pick", "options": options})
        screen = ChooseScreen(req)
        app.push_screen(screen)
        await pilot.pause()
        assert screen.query_one("#choose-list", OptionList) is not None


@pytest.mark.asyncio
async def test_options_label_shown_not_value() -> None:
    """OptionList shows the label field, not the value field."""
    options = [
        {"value": "internal_key", "label": "Human Readable Label"},
    ]
    app = _TestApp(hitl_queue=HITLQueue())
    async with app.run_test(size=(80, 24)) as pilot:
        req = _make_request({"message": "Pick", "options": options})
        screen = ChooseScreen(req)
        app.push_screen(screen)
        await pilot.pause()
        opt_list = screen.query_one("#choose-list", OptionList)
        option = opt_list.get_option_at_index(0)
        assert "Human Readable Label" in str(option.prompt)
        assert "internal_key" not in str(option.prompt)

"""Textual ModalScreen subclasses for each HITL tool type."""

from __future__ import annotations

import re
from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static, TextArea

from .queue import HITLRequest


class ConfirmScreen(ModalScreen[dict[str, Any]]):
    """Yes/No confirmation with severity styling."""

    DEFAULT_CSS = """
    ConfirmScreen {
        align: center middle;
    }
    #confirm-dialog {
        width: 60;
        max-height: 20;
        padding: 1 2;
        background: $surface;
        border: thick $accent;
    }
    #confirm-dialog.severity-high {
        border: thick red;
    }
    #confirm-dialog.severity-medium {
        border: thick yellow;
    }
    #confirm-buttons {
        height: 3;
        align: center middle;
    }
    """

    def __init__(self, request: HITLRequest) -> None:
        super().__init__()
        self._message: str = request.params.get("message", "")
        self._severity: str = request.params.get("severity", "medium")
        self._ctx_text: str | None = request.params.get("context")

    def compose(self) -> ComposeResult:
        severity_class = f"severity-{self._severity}"
        with Vertical(id="confirm-dialog", classes=severity_class):
            if self._ctx_text:
                yield Static(self._ctx_text, classes="context")
            yield Label(self._message)
            if self._severity == "high":
                yield Input(placeholder='Type "yes" to confirm', id="high-input")
            else:
                with Horizontal(id="confirm-buttons"):
                    yield Button("Yes", variant="success", id="yes")
                    yield Button("No", variant="error", id="no")

    @on(Button.Pressed, "#yes")
    def _on_yes(self) -> None:
        self.dismiss({"action": "accept"})

    @on(Button.Pressed, "#no")
    def _on_no(self) -> None:
        self.dismiss({"action": "decline"})

    @on(Input.Submitted, "#high-input")
    def _on_high_submit(self, event: Input.Submitted) -> None:
        if event.value.strip().lower() == "yes":
            self.dismiss({"action": "accept"})
        else:
            self.dismiss({"action": "decline"})


class CollectScreen(ModalScreen[str | dict[str, str]]):
    """Text/path/multiline input collection."""

    DEFAULT_CSS = """
    CollectScreen {
        align: center middle;
    }
    #collect-dialog {
        width: 70;
        max-height: 24;
        padding: 1 2;
        background: $surface;
        border: thick $accent;
    }
    .validation-error {
        color: red;
        display: none;
    }
    .validation-error.visible {
        display: block;
    }
    """

    def __init__(self, request: HITLRequest) -> None:
        super().__init__()
        self._message: str = request.params.get("message", "")
        self._input_type: str = request.params.get("input_type", "text")
        self._default_val: str | None = request.params.get("default")
        self._validation_pattern: str | None = request.params.get("validation_pattern")
        self._validation_message: str | None = request.params.get("validation_message")

    def compose(self) -> ComposeResult:
        with Vertical(id="collect-dialog"):
            yield Label(self._message)
            if self._input_type == "multiline":
                yield TextArea(self._default_val or "", id="collect-input")
            else:
                yield Input(
                    value=self._default_val or "",
                    placeholder="Enter value...",
                    id="collect-input",
                )
            yield Label(
                self._validation_message or "Invalid input",
                classes="validation-error",
                id="validation-msg",
            )
            with Horizontal(id="collect-buttons"):
                yield Button("Submit", variant="success", id="submit")
                yield Button("Cancel", variant="error", id="cancel")

    def _get_value(self) -> str:
        widget = self.query_one("#collect-input")
        if isinstance(widget, TextArea):
            return widget.text
        if isinstance(widget, Input):
            return widget.value
        return ""

    def _validate(self, value: str) -> bool:
        if self._validation_pattern:
            return bool(re.match(self._validation_pattern, value))
        return True

    @on(Button.Pressed, "#submit")
    def _on_submit(self) -> None:
        value = self._get_value()
        if not self._validate(value):
            self.query_one("#validation-msg").add_class("visible")
            return
        self.dismiss(value)

    @on(Button.Pressed, "#cancel")
    def _on_cancel(self) -> None:
        self.dismiss({"action": "cancel"})

    @on(Input.Submitted, "#collect-input")
    def _on_input_submit(self, event: Input.Submitted) -> None:
        self._on_submit()


class ChooseScreen(ModalScreen[str | list[str] | dict[str, str]]):
    """Selection from a list of choices."""

    DEFAULT_CSS = """
    ChooseScreen {
        align: center middle;
    }
    #choose-dialog {
        width: 60;
        max-height: 24;
        padding: 1 2;
        background: $surface;
        border: thick $accent;
    }
    """

    def __init__(self, request: HITLRequest) -> None:
        super().__init__()
        self._message: str = request.params.get("message", "")
        self._choices: list[str] = request.params.get("choices", [])
        self._multiple: bool = request.params.get("multiple", False)
        self._selected: set[str] = set()

    def compose(self) -> ComposeResult:
        with Vertical(id="choose-dialog"):
            yield Label(self._message)
            if self._multiple:
                for choice in self._choices:
                    yield Button(f"☐ {choice}", id=f"choice-{choice}", classes="choice-btn")
                with Horizontal():
                    yield Button("Done", variant="success", id="done")
                    yield Button("Cancel", variant="error", id="cancel")
            else:
                options = [(c, c) for c in self._choices]
                yield Select[str](options, id="choose-select", allow_blank=False)
                with Horizontal():
                    yield Button("OK", variant="success", id="ok")
                    yield Button("Cancel", variant="error", id="cancel")

    @on(Button.Pressed, ".choice-btn")
    def _toggle_choice(self, event: Button.Pressed) -> None:
        btn = event.button
        label = str(btn.label)
        choice = label.lstrip("☐☑ ")
        if choice in self._selected:
            self._selected.discard(choice)
            btn.label = f"☐ {choice}"
        else:
            self._selected.add(choice)
            btn.label = f"☑ {choice}"

    @on(Button.Pressed, "#done")
    def _on_done(self) -> None:
        self.dismiss(sorted(self._selected))

    @on(Button.Pressed, "#ok")
    def _on_ok(self) -> None:
        select = self.query_one("#choose-select", Select)
        value = select.value
        if value is not Select.BLANK:
            self.dismiss(str(value))
        else:
            self.dismiss(self._choices[0] if self._choices else "")

    @on(Button.Pressed, "#cancel")
    def _on_cancel(self) -> None:
        self.dismiss({"action": "cancel"})


class NotifyScreen(ModalScreen[bool]):
    """Auto-dismissing notification display."""

    AUTO_DISMISS_SECONDS: float = 3.0

    DEFAULT_CSS = """
    NotifyScreen {
        align: center middle;
    }
    #notify-dialog {
        width: 50;
        max-height: 12;
        padding: 1 2;
        background: $surface;
        border: thick $accent;
    }
    #notify-dialog.level-success { border: thick green; }
    #notify-dialog.level-error { border: thick red; }
    #notify-dialog.level-warning { border: thick yellow; }
    #notify-dialog.level-info { border: thick blue; }
    """

    def __init__(self, request: HITLRequest) -> None:
        super().__init__()
        self._message: str = request.params.get("message", "")
        self._level: str = request.params.get("level", "info")
        self._title_text: str | None = request.params.get("title")

    def compose(self) -> ComposeResult:
        level_class = f"level-{self._level}"
        with Vertical(id="notify-dialog", classes=level_class):
            if self._title_text:
                yield Label(f"[bold]{self._title_text}[/bold]")
            yield Static(self._message)
            yield Button("OK", variant="primary", id="dismiss")

    def on_mount(self) -> None:
        self.set_timer(self.AUTO_DISMISS_SECONDS, self._auto_dismiss)

    async def _auto_dismiss(self) -> None:
        if self.is_current:
            self.dismiss(True)

    @on(Button.Pressed, "#dismiss")
    def _on_dismiss(self) -> None:
        self.dismiss(True)


def screen_for(request: HITLRequest) -> ModalScreen[Any]:
    """Factory: return the appropriate screen for a given HITL request."""
    tool = request.tool
    if tool in ("hitl_confirm", "confirm"):
        return ConfirmScreen(request)
    elif tool in ("hitl_collect", "hitl_ask", "collect"):
        return CollectScreen(request)
    elif tool in ("hitl_choose", "choose"):
        return ChooseScreen(request)
    elif tool in ("hitl_notify", "notify"):
        return NotifyScreen(request)
    else:
        return NotifyScreen(request)

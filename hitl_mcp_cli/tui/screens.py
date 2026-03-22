"""Textual ModalScreen subclasses for each HITL tool type."""

from __future__ import annotations

import re
from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Markdown, OptionList, Static, TextArea
from textual.widgets.option_list import Option

from .queue import HITLRequest


def _expand_escapes(text: str) -> str:
    """Expand literal backslash-n sequences to real newlines."""
    return text.replace("\\n", "\n")


def _has_markdown(text: str) -> bool:
    """Detect if text contains markdown formatting."""
    if len(text) > 10000:
        return False
    return any(
        [
            "```" in text,
            text.lstrip().startswith("# ") or "\n# " in text,
            ("**" in text and ("\n- " in text or "\n* " in text or "\n1. " in text)),
        ]
    )


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
        """Initialize confirmation screen from HITL request."""
        super().__init__()
        self._message: str = request.params.get("message", "")
        self._severity: str = request.params.get("severity", "medium")
        self._ctx_text: str | None = request.params.get("context")

    def compose(self) -> ComposeResult:
        """Compose the confirmation dialog UI."""
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
        """Handle yes button press."""
        self.dismiss({"action": "accept"})

    @on(Button.Pressed, "#no")
    def _on_no(self) -> None:
        """Handle no button press."""
        self.dismiss({"action": "decline"})

    @on(Input.Submitted, "#high-input")
    def _on_high_submit(self, event: Input.Submitted) -> None:
        """Handle high-severity confirmation input submission."""
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
        """Initialize collection screen from HITL request."""
        super().__init__()
        self._message: str = request.params.get("message", "")
        self._input_type: str = request.params.get("input_type", "text")
        self._default_val: str | None = request.params.get("default")
        self._validation_pattern: str | None = request.params.get("validation_pattern")
        self._validation_message: str | None = request.params.get("validation_message")

    def compose(self) -> ComposeResult:
        """Compose the collection dialog UI."""
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
        """Get the current input value from the widget."""
        widget = self.query_one("#collect-input")
        if isinstance(widget, TextArea):
            return widget.text
        if isinstance(widget, Input):
            return widget.value
        return ""

    def _validate(self, value: str) -> bool:
        """Validate input against the validation pattern."""
        if self._validation_pattern:
            return bool(re.match(self._validation_pattern, value))
        return True

    @on(Button.Pressed, "#submit")
    def _on_submit(self) -> None:
        """Handle submit button press."""
        value = self._get_value()
        if not self._validate(value):
            self.query_one("#validation-msg").add_class("visible")
            return
        self.dismiss(value)

    @on(Button.Pressed, "#cancel")
    def _on_cancel(self) -> None:
        """Handle cancel button press."""
        self.dismiss({"action": "cancel"})

    @on(Input.Submitted, "#collect-input")
    def _on_input_submit(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        self._on_submit()


class ChooseScreen(ModalScreen[str | list[str] | dict[str, str]]):
    """Selection from a list of choices, shown inline with keyboard navigation."""

    DEFAULT_CSS = """
    ChooseScreen {
        align: center middle;
    }
    #choose-dialog {
        width: 70;
        max-height: 30;
        padding: 1 2;
        background: $surface;
        border: thick $accent;
    }
    #choose-list { height: auto; max-height: 16; }
    #custom-input { margin-top: 1; }
    """

    def __init__(self, request: HITLRequest) -> None:
        """Initialize choice screen from HITL request."""
        super().__init__()
        self._message: str = request.params.get("message", "")
        self._choices: list[str] = request.params.get("choices", [])
        self._options: list[dict[str, str]] = request.params.get("options", [])
        self._multiple: bool = request.params.get("multiple", False)
        self._selected: set[str] = set()

    def _build_options(self) -> list[Option]:
        """Build OptionList options from choices or rich options param."""
        if self._options:
            return [
                Option(
                    f"{o.get('label', o['value'])}"
                    + (f"\n[dim]{o['description']}[/dim]" if o.get("description") else ""),
                    id=o["value"],
                )
                for o in self._options
            ]
        return [Option(c, id=c) for c in self._choices]

    def compose(self) -> ComposeResult:
        """Compose the choice selection dialog UI."""
        with Vertical(id="choose-dialog"):
            yield Label(self._message)
            if self._multiple:
                for choice in self._choices:
                    yield Button(f"☐ {choice}", id=f"choice-{choice}", classes="choice-btn")
                with Horizontal():
                    yield Button("Done", variant="success", id="done")
                    yield Button("Cancel", variant="error", id="cancel")
            else:
                yield OptionList(*self._build_options(), id="choose-list")
                yield Input(placeholder="Or type a custom value...", id="custom-input")
                with Horizontal():
                    yield Button("Cancel", variant="error", id="cancel")

    @on(OptionList.OptionSelected, "#choose-list")
    def _on_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Immediately dismiss on option selection (Enter key)."""
        self.dismiss(str(event.option.id))

    @on(Input.Submitted, "#custom-input")
    def _on_custom_submit(self, event: Input.Submitted) -> None:
        """Submit custom free-text value."""
        value = event.value.strip()
        if value:
            self.dismiss(value)

    @on(Button.Pressed, ".choice-btn")
    def _toggle_choice(self, event: Button.Pressed) -> None:
        """Toggle a choice button selection state."""
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
        """Handle done button press for multiple selection."""
        self.dismiss(sorted(self._selected))

    @on(Button.Pressed, "#cancel")
    def _on_cancel(self) -> None:
        """Handle cancel button press."""
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
        """Initialize notification screen from HITL request."""
        super().__init__()
        self._message: str = _expand_escapes(request.params.get("message", ""))
        self._level: str = request.params.get("level", "info")
        self._title_text: str | None = request.params.get("title")
        if self._title_text:
            self._title_text = _expand_escapes(self._title_text)

    def compose(self) -> ComposeResult:
        """Compose the notification dialog UI."""
        level_class = f"level-{self._level}"
        with Vertical(id="notify-dialog", classes=level_class):
            if self._title_text:
                yield Label(f"[bold]{self._title_text}[/bold]")
            if _has_markdown(self._message):
                yield Markdown(self._message)
            else:
                yield Static(self._message)
            yield Button("OK", variant="primary", id="dismiss")

    def on_mount(self) -> None:
        """Set up auto-dismiss timer on mount."""
        self.set_timer(self.AUTO_DISMISS_SECONDS, self._auto_dismiss)

    async def _auto_dismiss(self) -> None:
        """Auto-dismiss the notification after timeout."""
        if self.is_current:
            self.dismiss(True)

    @on(Button.Pressed, "#dismiss")
    def _on_dismiss(self) -> None:
        """Handle dismiss button press."""
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

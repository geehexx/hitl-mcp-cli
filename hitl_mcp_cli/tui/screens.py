"""Textual Screen subclasses for each HITL tool type.

FIX 2 rationale (focus management): Screens use non-modal Screen (not
ModalScreen) and support Escape-to-minimize. Pressing Escape dismisses
the screen with a _MINIMIZED sentinel; the queue worker in app.py detects
this, waits for the user to press Escape again on the main app, then
re-pushes a fresh screen. This lets users inspect Sessions/Activity panes
between prompt interactions without losing the pending request.
"""

from __future__ import annotations

import re
from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Markdown, OptionList, Static, TextArea
from textual.widgets.option_list import Option

from .queue import HITLRequest

# Sentinel value for Escape-to-minimize (FIX 2).
_MINIMIZED: dict[str, str] = {"action": "__minimized__"}

# Shared CSS for non-modal overlay behavior (FIX 2) and text wrapping (FIX 1).
_OVERLAY_CSS = """
    background: $background 60%;
    overflow-y: auto;

    Static {
        width: 1fr;
    }
"""

# Shared CSS for notes display (FIX 3 + FIX A: distinct styling).
# F2: reduced gap from 2 (margin-top:1 + padding-top:1) to 1 (padding-top only).
_NOTES_CSS = """
    .notes {
        color: $text-muted;
        text-style: dim italic;
        width: 1fr;
        border-top: solid $panel-darken-1;
        padding-top: 1;
    }
"""


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


def _notes_widget(notes: str | None) -> Static | None:
    """Return a Static widget for notes, or None if empty."""
    if notes:
        return Static(
            f"[bold cyan]ℹ[/bold cyan] [dim italic]{_expand_escapes(notes)}[/dim italic]", classes="notes"
        )
    return None


class ConfirmScreen(Screen[dict[str, Any]]):
    """Yes/No confirmation with severity styling."""

    BINDINGS = [Binding("escape", "minimize", "Minimize", show=False)]

    DEFAULT_CSS = (
        """
    ConfirmScreen {
        align: center middle;
        """
        + _OVERLAY_CSS
        + """
    }
    #confirm-dialog {
        width: 95%;
        max-width: 120;
        height: auto;
        max-height: 90%;
        padding: 1 2;
        background: $surface;
        border: thick $accent;
        overflow-y: auto;
    }
    #confirm-dialog.severity-high {
        border: thick red;
    }
    #confirm-dialog.severity-medium {
        border: thick yellow;
    }
    .context {
        width: 1fr;
    }
    #confirm-buttons {
        height: 3;
        width: 1fr;
        align: center middle;
    }
    #confirm-buttons Button {
        width: 1fr;
    }
    """
        + _NOTES_CSS
    )

    def __init__(self, request: HITLRequest) -> None:
        """Initialize confirmation screen from HITL request."""
        super().__init__()
        self._message: str = request.params.get("message", "")
        self._severity: str = request.params.get("severity", "medium")
        self._ctx_text: str | None = request.params.get("context")
        self._notes: str | None = request.params.get("notes")

    def compose(self) -> ComposeResult:
        """Compose the confirmation dialog UI."""
        severity_class = f"severity-{self._severity}"
        with Vertical(id="confirm-dialog", classes=severity_class):
            if self._ctx_text:
                yield Static(_expand_escapes(self._ctx_text), classes="context")
            yield Static(self._message)
            notes_w = _notes_widget(self._notes)
            if notes_w:
                yield notes_w
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

    def action_minimize(self) -> None:
        """Minimize prompt so user can inspect background panes."""
        self.dismiss(_MINIMIZED)


class CollectScreen(Screen[str | dict[str, str]]):
    """Text/path/multiline input collection."""

    BINDINGS = [
        Binding("escape", "minimize", "Minimize", show=False),
        Binding("ctrl+j", "submit", "Submit (Ctrl+Enter)", show=True),
    ]

    DEFAULT_CSS = (
        """
    CollectScreen {
        align: center middle;
        """
        + _OVERLAY_CSS
        + """
    }
    #collect-dialog {
        width: 95%;
        max-width: 120;
        height: 90%;
        padding: 1 2;
        background: $surface;
        border: thick $accent;
        overflow-y: auto;
    }
    #collect-input {
        min-height: 3;
        max-height: 8;
        margin-top: 1;
        margin-bottom: 1;
    }
    .validation-error {
        color: red;
        display: none;
    }
    .validation-error.visible {
        display: block;
    }
    #collect-buttons {
        width: 1fr;
        align: center middle;
    }
    #collect-buttons Button {
        width: 1fr;
    }
    """
        + _NOTES_CSS
    )

    def __init__(self, request: HITLRequest) -> None:
        """Initialize collection screen from HITL request."""
        super().__init__()
        self._message: str = request.params.get("message", "")
        self._input_type: str = request.params.get("input_type", "text")
        self._default_val: str | None = request.params.get("default")
        self._validation_pattern: str | None = request.params.get("validation_pattern")
        self._validation_message: str | None = request.params.get("validation_message")
        self._notes: str | None = request.params.get("notes")

    def compose(self) -> ComposeResult:
        """Compose the collection dialog UI."""
        with Vertical(id="collect-dialog"):
            yield Static(self._message)
            notes_w = _notes_widget(self._notes)
            if notes_w:
                yield notes_w
            yield TextArea(self._default_val or "", id="collect-input")
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
        return self.query_one("#collect-input", TextArea).text

    def _validate(self, value: str) -> bool:
        """Validate input against the validation pattern."""
        if self._validation_pattern:
            try:
                return bool(re.match(self._validation_pattern, value))
            except re.error:
                return False
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

    def action_submit(self) -> None:
        """Handle Ctrl+Enter submission."""
        self._on_submit()

    def action_minimize(self) -> None:
        """Minimize prompt so user can inspect background panes."""
        self.dismiss(_MINIMIZED)


class ChooseScreen(Screen[str | list[str] | dict[str, str]]):
    """Selection from a list of choices, shown inline with keyboard navigation."""

    BINDINGS = [Binding("escape", "minimize", "Minimize", show=False)]

    DEFAULT_CSS = (
        """
    ChooseScreen {
        align: center middle;
        """
        + _OVERLAY_CSS
        + """
    }
    #choose-dialog {
        width: 95%;
        max-width: 120;
        height: auto;
        max-height: 90%;
        padding: 1 2;
        background: $surface;
        border: thick $accent;
        overflow-y: auto;
    }
    #choose-list { height: auto; max-height: 16; width: 1fr; }
    .choice-btn { width: 1fr; }
    #custom-input { margin-top: 1; }
    #choose-dialog Horizontal {
        width: 1fr;
        align: center middle;
    }
    #choose-dialog Horizontal Button {
        width: 1fr;
    }
    """
        + _NOTES_CSS
    )

    def __init__(self, request: HITLRequest) -> None:
        """Initialize choice screen from HITL request."""
        super().__init__()
        self._message: str = request.params.get("message", "")
        self._choices: list[str] = request.params.get("choices", [])
        self._options: list[dict[str, str]] = request.params.get("options", [])
        self._multiple: bool = request.params.get("multiple", False)
        self._selected: set[str] = set()
        self._notes: str | None = request.params.get("notes")

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
            yield Static(self._message)
            notes_w = _notes_widget(self._notes)
            if notes_w:
                yield notes_w
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

    def action_minimize(self) -> None:
        """Minimize prompt so user can inspect background panes."""
        self.dismiss(_MINIMIZED)


class NotifyScreen(Screen[bool]):
    """Auto-dismissing notification display."""

    AUTO_DISMISS_SECONDS: float = 3.0

    DEFAULT_CSS = (
        """
    NotifyScreen {
        align: center middle;
        """
        + _OVERLAY_CSS
        + """
    }
    #notify-dialog {
        width: 95%;
        max-width: 120;
        height: auto;
        max-height: 90%;
        padding: 1 2;
        background: $surface;
        border: thick $accent;
        overflow-y: auto;
    }
    #notify-dialog.level-success { border: thick green; }
    #notify-dialog.level-error { border: thick red; }
    #notify-dialog.level-warning { border: thick yellow; }
    #notify-dialog.level-info { border: thick blue; }
    """
    )

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


def screen_for(request: HITLRequest) -> Screen[Any]:
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

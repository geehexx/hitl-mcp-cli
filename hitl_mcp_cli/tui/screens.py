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
from typing import Any, ClassVar

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.validation import Regex
from textual.widgets import Button, Collapsible, Input, Label, Markdown, OptionList, Static, TextArea
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

# CSS for collapsible long messages.
_COLLAPSIBLE_CSS = """
    .msg-collapsible {
        width: 1fr;
        margin-bottom: 1;
    }
    .msg-inline {
        width: 1fr;
        margin-bottom: 1;
    }
    .context-panel {
        width: 1fr;
        background: $panel-darken-1;
        padding: 1;
        margin-bottom: 1;
        border-left: thick $accent;
    }
    .step-indicator {
        color: $text-muted;
        text-style: dim;
        width: 1fr;
        margin-bottom: 1;
    }
"""

_MSG_COLLAPSE_THRESHOLD = 200
_MSG_PREVIEW_LEN = 100


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
            f"[bold cyan][i][/bold cyan] [dim italic]{_expand_escapes(notes)}[/dim italic]", classes="notes"
        )
    return None


def _message_widgets(message: str) -> list[Any]:
    """Return widget(s) for a message, using Collapsible if > threshold."""
    expanded = _expand_escapes(message)
    if len(message) <= _MSG_COLLAPSE_THRESHOLD:
        return [Static(expanded, classes="msg-inline")]
    preview = expanded[:_MSG_PREVIEW_LEN].rstrip() + "…"
    inner: Any = Markdown(expanded) if _has_markdown(expanded) else Static(expanded)
    return [Collapsible(inner, title=preview, collapsed=True, classes="msg-collapsible")]


def _context_widget(context_text: str | None) -> Static | None:
    """Return a context panel widget, or None if empty."""
    if context_text:
        return Static(_expand_escapes(context_text), classes="context-panel")
    return None


def _step_widget(step: int | None, total_steps: int | None) -> Static | None:
    """Return a step indicator widget, or None if not provided."""
    if step is not None and total_steps is not None:
        return Static(f"Step {step}/{total_steps}", classes="step-indicator")
    return None


class ConfirmScreen(Screen[dict[str, Any]]):
    """Yes/No confirmation with severity styling."""

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("escape", "minimize", "Minimize", show=False)
    ]

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
        max-width: 90;
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
        + _COLLAPSIBLE_CSS
    )

    def __init__(self, request: HITLRequest) -> None:
        """Initialize confirmation screen from HITL request."""
        super().__init__()
        self._message: str = request.params.get("message", "")
        self._severity: str = request.params.get("severity", "medium")
        self._ctx_text: str | None = request.params.get("context")
        self._notes: str | None = request.params.get("notes")
        self._step: int | None = request.params.get("step")
        self._total_steps: int | None = request.params.get("total_steps")

    def compose(self) -> ComposeResult:
        """Compose the confirmation dialog UI."""
        severity_class = f"severity-{self._severity}"
        with Vertical(id="confirm-dialog", classes=severity_class):
            step_w = _step_widget(self._step, self._total_steps)
            if step_w:
                yield step_w
            if self._ctx_text:
                yield Static(_expand_escapes(self._ctx_text), classes="context")
            yield from _message_widgets(self._message)
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

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("escape", "minimize", "Minimize", show=False),
        Binding("ctrl+j", "submit", "Submit (Ctrl+Enter)", show=True),
    ]

    _PLACEHOLDERS: ClassVar[dict[str, str]] = {
        "text": "Type your response...",
        "path": "Enter file path...",
    }

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
        max-width: 90;
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
    .prompt-row {
        height: 1;
        width: 1fr;
    }
    .prompt-icon {
        width: auto;
    }
    #collect-input.-valid {
        border: tall $success 60%;
    }
    #collect-input.-valid:focus {
        border: tall $success;
    }
    #collect-input.-invalid {
        border: tall $error 60%;
    }
    #collect-input.-invalid:focus {
        border: tall $error;
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
        + _COLLAPSIBLE_CSS
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
        self._ctx_text: str | None = request.params.get("context")
        self._step: int | None = request.params.get("step")
        self._total_steps: int | None = request.params.get("total_steps")
        self._is_multiline: bool = self._input_type == "multiline"

    def compose(self) -> ComposeResult:
        """Compose the collection dialog UI."""
        with Vertical(id="collect-dialog"):
            step_w = _step_widget(self._step, self._total_steps)
            if step_w:
                yield step_w
            ctx_w = _context_widget(self._ctx_text)
            if ctx_w:
                yield ctx_w
            if self._is_multiline:
                yield from _message_widgets(self._message)
            else:
                with Horizontal(classes="prompt-row"):
                    yield Static("[bold cyan]>[/bold cyan] ", classes="prompt-icon")
                    yield from _message_widgets(self._message)
            notes_w = _notes_widget(self._notes)
            if notes_w:
                yield notes_w
            if self._is_multiline:
                yield TextArea(self._default_val or "", id="collect-input")
            else:
                validators = []
                if self._validation_pattern:
                    validators.append(
                        Regex(
                            self._validation_pattern,
                            failure_description=self._validation_message or "Invalid input",
                        )
                    )
                yield Input(
                    value=self._default_val or "",
                    placeholder=self._PLACEHOLDERS.get(self._input_type, "Type your response..."),
                    id="collect-input",
                    validators=validators,
                    validate_on=["submitted"],
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
        if self._is_multiline:
            return self.query_one("#collect-input", TextArea).text
        return self.query_one("#collect-input", Input).value

    def _validate(self, value: str) -> bool:
        """Validate input against the validation pattern."""
        if self._validation_pattern:
            try:
                return bool(re.match(self._validation_pattern, value))
            except re.error:
                return False
        return True

    @on(Input.Submitted, "#collect-input")
    def _on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key submission from Input widget."""
        if event.validation_result and not event.validation_result.is_valid:
            msg = self.query_one("#validation-msg", Label)
            msg.update(event.validation_result.failure_descriptions[0])
            msg.add_class("visible")
            return
        self.dismiss(event.value)

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

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("escape", "minimize", "Minimize", show=False)
    ]

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
        max-width: 90;
        height: auto;
        max-height: 90%;
        padding: 1 2;
        background: $surface;
        border: thick $accent;
        overflow-y: auto;
    }
    #choose-list { height: auto; max-height: 16; width: 1fr; }
    #choose-buttons { height: auto; max-height: 16; width: 1fr; overflow-y: auto; }
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
        + _COLLAPSIBLE_CSS
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
        self._ctx_text: str | None = request.params.get("context")
        self._step: int | None = request.params.get("step")
        self._total_steps: int | None = request.params.get("total_steps")
        # Index-based ID → original value maps (prevents BadIdentifier on special chars)
        self._choice_index_map: dict[str, str] = {
            f"choice-{i}": choice for i, choice in enumerate(self._choices)
        }
        self._option_value_map: dict[str, str] = {
            self._sanitize_option_id(o["value"], i): o["value"] for i, o in enumerate(self._options)
        }

    @staticmethod
    def _sanitize_option_id(value: str, index: int) -> str:
        """Sanitize an option value into a valid Textual widget ID."""
        sanitized = re.sub(r"[^a-zA-Z0-9_-]", "-", str(value)).lstrip("-")
        return sanitized if sanitized else f"opt-{index}"

    def _build_options(self) -> list[Option]:
        """Build OptionList options from choices or rich options param."""
        if self._options:
            return [
                Option(
                    f"{o.get('label', o['value'])}"
                    + (f"\n[dim]{o['description']}[/dim]" if o.get("description") else ""),
                    id=self._sanitize_option_id(o["value"], i),
                )
                for i, o in enumerate(self._options)
            ]
        return [Option(c, id=f"choice-{i}") for i, c in enumerate(self._choices)]

    def compose(self) -> ComposeResult:
        """Compose the choice selection dialog UI."""
        with Vertical(id="choose-dialog"):
            step_w = _step_widget(self._step, self._total_steps)
            if step_w:
                yield step_w
            ctx_w = _context_widget(self._ctx_text)
            if ctx_w:
                yield ctx_w
            yield from _message_widgets(self._message)
            notes_w = _notes_widget(self._notes)
            if notes_w:
                yield notes_w
            if self._multiple:
                with Vertical(id="choose-buttons"):
                    for i, choice in enumerate(self._choices):
                        yield Button(f"☐ {choice}", id=f"choice-{i}", classes="choice-btn")
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
        option_id = str(event.option.id)
        # Check choices map first (index-based IDs), then options map (sanitized value IDs)
        value = self._choice_index_map.get(option_id) or self._option_value_map.get(option_id, option_id)
        self.dismiss(value)

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
        btn_id = btn.id or ""
        choice = self._choice_index_map.get(btn_id, str(btn.label).lstrip("☐☑ "))
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
        max-width: 90;
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

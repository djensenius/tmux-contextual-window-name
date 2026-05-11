from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .context import label_for_pane
from .copilot_workspace import find_workspace_state
from .osc_title import normalize_title
from .state_store import StateStore
from .tmux_runtime import TmuxWindow


@dataclass(frozen=True)
class PickerEntry:
    target: str
    display: str
    preview: str


def _short(value: str, max_length: int = 96) -> str:
    if len(value) <= max_length:
        return value
    return f"{value[: max_length - 1]}…"


def _state_for_window(
    window: TmuxWindow,
    store: StateStore | None,
    ttl_seconds: int,
) -> tuple[dict[str, Any] | None, str]:
    state = store.read_pane(window.pane_id) if store and window.pane_id else None
    status = store.state_status(state, ttl_seconds) if store else "missing"
    workspace_state = find_workspace_state(window.path) if window.command == "copilot" else None
    if workspace_state:
        state = {**workspace_state, **(state or {})}
        for key, value in workspace_state.items():
            if state.get(key) in (None, "", {}, []):
                state[key] = value
        if status in ("missing", "stale"):
            status = f"{status}+workspace"
    return state, status


def _changes(state: dict[str, Any] | None) -> str | None:
    changes = state.get("changes") if isinstance((state or {}).get("changes"), dict) else {}
    added = changes.get("lines_added")
    removed = changes.get("lines_removed")
    if added is None and removed is None:
        return None
    return f"+{added or 0} -{removed or 0}"


def _context(state: dict[str, Any] | None) -> str | None:
    context = state.get("context") if isinstance((state or {}).get("context"), dict) else {}
    percentage = context.get("current_context_used_percentage", context.get("used_percentage"))
    if percentage is not None:
        return f"{percentage}%"
    tokens = context.get("current_tokens")
    if tokens is not None:
        return f"{tokens} tokens"
    return None


def _copilot_details(window: TmuxWindow, state: dict[str, Any] | None, status: str) -> list[str]:
    normalized = normalize_title(window.title, state.get("session_name") if state else None)
    intent = (
        "idle"
        if normalized.is_copilot and normalized.is_idle
        else normalized.current_intent or (state or {}).get("current_intent") or "idle"
    )
    session = (state or {}).get("session_name") or "unknown session"
    model = (state or {}).get("model") if isinstance((state or {}).get("model"), dict) else {}
    model_name = model.get("display_name") or "unknown model"
    lines = [
        _short(f"Title: {window.title or 'none'}"),
        _short(f"Intent: {intent}"),
        _short(f"Session: {session} | Model: {model_name} | State: {status}"),
    ]
    extra = []
    context = _context(state)
    changes = _changes(state)
    if context:
        extra.append(f"Context: {context}")
    if changes:
        extra.append(f"Changes: {changes}")
    if extra:
        lines.append(_short(" | ".join(extra)))
    return lines


def _generic_details(window: TmuxWindow) -> list[str]:
    normalized = normalize_title(window.title)
    if normalized.current_intent:
        return [_short(f"Title: {window.title}"), _short(f"Intent: {normalized.current_intent}")]
    if window.title and window.title not in (window.command, window.path):
        return [_short(f"Title: {window.title}")]
    return []


def _row_summary(window: TmuxWindow, state: dict[str, Any] | None, status: str) -> str:
    normalized = normalize_title(window.title, state.get("session_name") if state else None)
    if window.command == "copilot" or state:
        intent = (
            "idle"
            if normalized.is_copilot and normalized.is_idle
            else normalized.current_intent or (state or {}).get("current_intent") or "idle"
        )
        session = (state or {}).get("session_name")
        context = _context(state)
        parts = [f"intent: {intent}"]
        if session:
            parts.append(f"session: {session}")
        if context:
            parts.append(f"context: {context}")
        parts.append(f"state: {status}")
        return " | ".join(parts)
    if normalized.current_intent:
        return f"intent: {normalized.current_intent}"
    if window.title and window.title not in (window.command, window.path):
        return f"title: {window.title}"
    return ""


def render_window_picker(windows: list[TmuxWindow], state_dir: str | None = None, ttl_seconds: int = 300) -> str:
    lines = ["Windows", "Tip: press Ctrl-R in fzf mode to refresh pane status.", ""]
    if not windows:
        return "Windows\n\nNo windows found.\n\nPress Enter to close"

    store = StateStore(state_dir) if state_dir is not None else None
    for row, window in enumerate(windows, start=1):
        marker = "*" if window.active else " "
        label = label_for_pane(command=window.command, path=window.path, pane_pid=window.pane_pid)
        panes = f"{window.panes} panes" if window.panes != "1" else "1 pane"
        command = window.command or "pane"
        lines.append(
            f"{row:>2}. {marker} {window.index}.{window.pane_index}: "
            f"{window.name} {label} [{command}] ({panes})"
        )
        state, status = _state_for_window(window, store, ttl_seconds)
        details = _copilot_details(window, state, status) if command == "copilot" or state else _generic_details(window)
        for detail in details:
            lines.append(f"      {detail}")

    lines.extend(["", "Select a window number, or press Enter to close: "])
    return "\n".join(lines)


def build_picker_entries(
    windows: list[TmuxWindow],
    state_dir: str | None = None,
    ttl_seconds: int = 300,
) -> list[PickerEntry]:
    store = StateStore(state_dir) if state_dir is not None else None
    entries: list[PickerEntry] = []
    for window in windows:
        marker = "*" if window.active else " "
        label = label_for_pane(command=window.command, path=window.path, pane_pid=window.pane_pid)
        command = window.command or "pane"
        state, status = _state_for_window(window, store, ttl_seconds)
        details = _copilot_details(window, state, status) if command == "copilot" or state else _generic_details(window)
        panes = f"{window.panes} panes" if window.panes != "1" else "1 pane"
        summary = _row_summary(window, state, status)
        summary_text = f" — {summary}" if summary else ""
        row_text = (
            f"{marker} {window.index:>2}.{window.pane_index:<2} {window.name} "
            f"{label:<24} {command:<10} {panes}{summary_text}"
        )
        display = _short(
            row_text,
            180,
        )
        preview_lines = [
            f"Window: {window.index} ({window.id})",
            f"Pane: {window.pane_index} ({window.pane_id})",
            f"Name: {window.name}",
            f"Command: {command}",
            f"Path: {window.path or 'unknown'}",
            f"Panes: {panes}",
            "",
            "Tip: press Ctrl-R to refresh this picker.",
        ]
        if details:
            preview_lines.extend(["", *details])
        entries.append(PickerEntry(target=window.pane_id, display=display, preview="\n".join(preview_lines)))
    return entries


def render_picker_source(windows: list[TmuxWindow], state_dir: str | None = None, ttl_seconds: int = 300) -> str:
    entries = build_picker_entries(windows, state_dir=state_dir, ttl_seconds=ttl_seconds)
    active_index = next((index for index, window in enumerate(windows, start=1) if window.active), 1)
    ordered_entries = entries[active_index - 1 :] + entries[: active_index - 1]
    return "\n".join(f"{entry.target}\t{entry.display}" for entry in ordered_entries)


def render_picker_preview(
    target: str,
    windows: list[TmuxWindow],
    state_dir: str | None = None,
    ttl_seconds: int = 300,
) -> str:
    entries = build_picker_entries(windows, state_dir=state_dir, ttl_seconds=ttl_seconds)
    for entry in entries:
        if entry.target == target:
            return entry.preview
    return f"Pane not found: {target}"


def resolve_selection(selection: str, windows: list[TmuxWindow]) -> str | None:
    value = selection.strip()
    if not value:
        return None
    if "\t" in value:
        target = value.split("\t", 1)[0].strip()
        return target or None
    if value.isdigit():
        row = int(value)
        if 1 <= row <= len(windows):
            return windows[row - 1].pane_id
        for window in windows:
            if window.index == value:
                return window.pane_id
    return None

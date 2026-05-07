from __future__ import annotations

import json
from typing import Any

from .context import current_branch, git_root, path_slug
from .copilot_workspace import find_workspace_state
from .osc_title import normalize_title
from .state_store import StateStore


def _value(value: Any, fallback: str = "unknown") -> str:
    if value is None or value == "":
        return fallback
    return str(value)


def _changes(state: dict[str, Any]) -> str:
    changes = state.get("changes") if isinstance(state.get("changes"), dict) else {}
    added = changes.get("lines_added")
    removed = changes.get("lines_removed")
    if added is None and removed is None:
        return "unknown"
    return f"+{added or 0} -{removed or 0}"


def _context_usage(state: dict[str, Any]) -> str:
    context = state.get("context") if isinstance(state.get("context"), dict) else {}
    usage = context.get("current_context_used_percentage", context.get("used_percentage"))
    if usage is not None:
        return f"{usage}%"
    tokens = context.get("current_tokens")
    if tokens is not None:
        return f"{tokens} tokens"
    return "unknown"


def _remote(state: dict[str, Any]) -> str:
    for key in ("remote", "pull_request"):
        value = state.get(key)
        if value:
            if isinstance(value, (dict, list)):
                if isinstance(value, dict):
                    value = {k: v for k, v in value.items() if v not in (None, "", [], {})}
                    if not value:
                        continue
                return json.dumps(value, ensure_ascii=False)
            return str(value)
    return "none"


def render_popup(
    *,
    pane_id: str,
    window_id: str | None,
    command: str | None,
    path: str | None,
    title: str | None,
    state: dict[str, Any] | None,
    state_status: str,
) -> str:
    normalized_title = normalize_title(title, state.get("session_name") if state else None)
    is_copilot = (
        (command or "").strip() == "copilot" or bool(state and state.get("session_id")) or normalized_title.is_copilot
    )

    if is_copilot:
        merged = dict(state or {})
        if normalized_title.current_intent:
            merged["current_intent"] = normalized_title.current_intent
        elif normalized_title.is_copilot and normalized_title.is_idle:
            merged["current_intent"] = None
        cwd = merged.get("cwd") or path
        model = merged.get("model") if isinstance(merged.get("model"), dict) else {}
        lines = [
            "Copilot",
            f"Session: {_value(merged.get('session_name'))}",
            f"Intent: {_value(merged.get('current_intent'), 'idle')}",
            f"Repo: {_value(merged.get('repo_slug') or path_slug(cwd, command))}",
            f"CWD: {_value(cwd)}",
            f"Model: {_value(model.get('display_name'))}",
            f"Context: {_context_usage(merged)}",
            f"Changes: {_changes(merged)}",
            f"Transcript: {_value(merged.get('transcript_path'))}",
            f"Remote: {_remote(merged)}",
            f"State: {state_status}",
        ]
    else:
        root = git_root(path)
        lines = [
            _value(command, "pane"),
            f"Path: {_value(path)}",
            f"Repo: {_value(root, 'none')}",
            f"Branch: {_value(current_branch(path), 'none')}",
            f"Window: {_value(window_id)}",
            f"Pane: {_value(pane_id)}",
        ]
        if title:
            lines.append(f"Title: {title}")

    lines.extend(["", "Press Enter to close"])
    return "\n".join(lines)


def popup_text(
    *,
    pane_id: str,
    window_id: str | None,
    command: str | None,
    path: str | None,
    title: str | None,
    state_dir: str | None,
    ttl_seconds: int,
) -> str:
    store = StateStore(state_dir)
    state = store.read_pane(pane_id)
    status = store.state_status(state, ttl_seconds)
    workspace_state = find_workspace_state(path) if command == "copilot" else None
    if workspace_state:
        state = {**workspace_state, **(state or {})}
        for key, value in workspace_state.items():
            if state.get(key) in (None, "", {}, []):
                state[key] = value
        if status in ("missing", "stale"):
            status = f"{status}+workspace"
    return render_popup(
        pane_id=pane_id,
        window_id=window_id,
        command=command,
        path=path,
        title=title,
        state=state,
        state_status=status,
    )

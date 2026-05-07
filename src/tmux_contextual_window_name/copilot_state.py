from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

from .context import path_slug
from .osc_title import normalize_title
from .state_store import StateStore


def build_state(payload: dict[str, Any], pane_id: str | None = None) -> dict[str, Any]:
    cwd = payload.get("cwd")
    model = payload.get("model") if isinstance(payload.get("model"), dict) else {}
    title = payload.get("title") if isinstance(payload.get("title"), str) else None
    normalized = normalize_title(title, payload.get("session_name"))

    return {
        "pane_id": pane_id,
        "pane_bound": pane_id is not None,
        "session_id": payload.get("session_id"),
        "session_name": payload.get("session_name"),
        "transcript_path": payload.get("transcript_path"),
        "cwd": cwd,
        "repo_slug": path_slug(cwd, payload.get("session_name")),
        "model": {
            "id": model.get("id"),
            "display_name": model.get("display_name"),
        },
        "username": payload.get("username"),
        "remote": payload.get("remote") or payload.get("task") or payload.get("repository"),
        "pull_request": payload.get("pull_request") or payload.get("pr"),
        "changes": {
            "lines_added": payload.get("lines_added"),
            "lines_removed": payload.get("lines_removed"),
            "files_changed": payload.get("files_changed"),
        },
        "context": {
            "current_context_used_percentage": payload.get("current_context_used_percentage"),
            "used_percentage": payload.get("context_window_used_percentage"),
        },
        "current_intent": payload.get("current_intent") or normalized.current_intent,
        "title": normalized.raw,
        "timestamp": time.time(),
    }


def write_statusline(stdin: Any = sys.stdin, environ: dict[str, str] | None = None) -> None:
    env = environ or os.environ
    raw = stdin.read()
    if not raw.strip():
        return
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("Copilot statusLine payload must be a JSON object")

    store = StateStore(env.get("TMUX_CONTEXTUAL_WINDOW_NAME_STATE_DIR"))
    pane_id = env.get("TMUX_PANE")
    state = build_state(payload, pane_id=pane_id)
    if pane_id:
        store.write_pane(pane_id, state)
        return

    session_id = payload.get("session_id")
    if not session_id:
        raise ValueError("Copilot statusLine payload requires session_id when TMUX_PANE is missing")
    store.write_session(str(session_id), state)

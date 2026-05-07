from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .context import path_slug


def _parse_simple_yaml(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return values

    for line in lines:
        if not line or line.startswith(" ") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def _configured_model() -> str | None:
    path = Path.home() / ".copilot" / "settings.json"
    try:
        raw = "\n".join(
            line for line in path.read_text(encoding="utf-8").splitlines() if not line.strip().startswith("//")
        )
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return None
    model = data.get("model")
    return model if isinstance(model, str) and model else None


def _event_metrics(events_path: Path) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    if not events_path.exists():
        return metrics
    try:
        lines = events_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return metrics

    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        data = event.get("data")
        if not isinstance(data, dict):
            continue
        event_type = event.get("type")
        if event_type == "session.model_change":
            model = data.get("newModel")
            if isinstance(model, str) and model:
                metrics["model"] = {"id": model, "display_name": model}
        elif event_type == "session.resume":
            model = data.get("selectedModel")
            if isinstance(model, str) and model:
                metrics["model"] = {"id": model, "display_name": model}
        elif event_type == "session.shutdown":
            model = data.get("currentModel")
            if isinstance(model, str) and model:
                metrics["model"] = {"id": model, "display_name": model}
            changes = data.get("codeChanges")
            if isinstance(changes, dict):
                metrics["changes"] = {
                    "lines_added": changes.get("linesAdded"),
                    "lines_removed": changes.get("linesRemoved"),
                    "files_changed": len(changes.get("filesModified", []))
                    if isinstance(changes.get("filesModified"), list)
                    else None,
                }
            if data.get("currentTokens") is not None:
                metrics["context"] = {"current_tokens": data.get("currentTokens")}
    return metrics


def find_workspace_state(cwd: str | None) -> dict[str, Any] | None:
    if not cwd:
        return None
    target = Path(cwd).expanduser()
    root = Path.home() / ".copilot" / "session-state"
    if not root.exists():
        return None

    candidates = sorted(root.glob("*/workspace.yaml"), key=lambda item: item.stat().st_mtime, reverse=True)
    for workspace in candidates:
        values = _parse_simple_yaml(workspace)
        workspace_cwd = values.get("cwd")
        if not workspace_cwd:
            continue
        try:
            if Path(workspace_cwd).expanduser().resolve(strict=False) != target.resolve(strict=False):
                continue
        except OSError:
            if workspace_cwd != cwd:
                continue

        session_id = values.get("id") or workspace.parent.name
        session_name = values.get("name") or values.get("summary")
        events_path = workspace.parent / "events.jsonl"
        model = _configured_model()
        state = {
            "session_id": session_id,
            "session_name": session_name,
            "cwd": workspace_cwd,
            "repo_slug": path_slug(workspace_cwd, session_name),
            "model": {"id": model, "display_name": model},
            "remote": {
                "repository": values.get("repository"),
                "branch": values.get("branch"),
            },
            "transcript_path": str(events_path) if events_path.exists() else None,
            "workspace_path": str(workspace),
            "workspace_updated_at": values.get("updated_at"),
        }
        event_metrics = _event_metrics(events_path)
        state.update(event_metrics)
        if not state.get("model", {}).get("display_name") and model:
            state["model"] = {"id": model, "display_name": model}
        return state
    return None

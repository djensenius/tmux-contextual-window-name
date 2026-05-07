from __future__ import annotations

import json
import os
import re
import tempfile
import time
from contextlib import suppress
from pathlib import Path
from typing import Any

DEFAULT_STATE_DIR = "~/.local/state/tmux-contextual-window-name"


def expand_state_dir(value: str | None = None) -> Path:
    configured = value or os.environ.get("TMUX_CONTEXTUAL_WINDOW_NAME_STATE_DIR") or DEFAULT_STATE_DIR
    return Path(os.path.expanduser(configured))


def safe_id(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.%-]", "_", value)
    if not safe:
        raise ValueError("state id cannot be empty")
    return safe


class StateStore:
    def __init__(self, state_dir: str | Path | None = None):
        self.root = expand_state_dir(str(state_dir) if state_dir is not None else None)

    @property
    def panes_dir(self) -> Path:
        return self.root / "panes"

    @property
    def sessions_dir(self) -> Path:
        return self.root / "sessions"

    def pane_path(self, pane_id: str) -> Path:
        return self.panes_dir / f"{safe_id(pane_id)}.json"

    def session_path(self, session_id: str) -> Path:
        return self.sessions_dir / f"{safe_id(session_id)}.json"

    def write_pane(self, pane_id: str, state: dict[str, Any]) -> None:
        self._write_json(self.pane_path(pane_id), state)

    def write_session(self, session_id: str, state: dict[str, Any]) -> None:
        self._write_json(self.session_path(session_id), state)

    def read_pane(self, pane_id: str) -> dict[str, Any] | None:
        return self._read_json(self.pane_path(pane_id))

    def delete_pane(self, pane_id: str) -> None:
        try:
            self.pane_path(pane_id).unlink()
        except FileNotFoundError:
            return

    def prune_missing_panes(self, live_panes: set[str]) -> int:
        removed = 0
        if not self.panes_dir.exists():
            return removed
        for path in self.panes_dir.glob("*.json"):
            pane_id = path.stem
            if pane_id not in live_panes:
                path.unlink(missing_ok=True)
                removed += 1
        return removed

    def state_status(self, state: dict[str, Any] | None, ttl_seconds: int) -> str:
        if not state:
            return "missing"
        timestamp = state.get("timestamp")
        if not isinstance(timestamp, (int, float)):
            return "stale"
        return "stale" if time.time() - timestamp > ttl_seconds else "live"

    def _read_json(self, path: Path) -> dict[str, Any] | None:
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except FileNotFoundError:
            return None
        if not isinstance(data, dict):
            return None
        return data

    def _write_json(self, path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(path.parent, 0o700)
        fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, sort_keys=True)
                handle.write("\n")
            os.chmod(tmp_name, 0o600)
            os.replace(tmp_name, path)
        except Exception:
            with suppress(FileNotFoundError):
                os.unlink(tmp_name)
            raise

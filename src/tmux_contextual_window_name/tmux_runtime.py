from __future__ import annotations

import subprocess
from dataclasses import dataclass


def tmux_option(name: str, default: str) -> str:
    try:
        result = subprocess.run(
            ["tmux", "show-option", "-gqv", name],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=0.25,
        )
    except (OSError, subprocess.SubprocessError):
        return default
    value = result.stdout.strip()
    return value if value else default


def live_panes() -> set[str]:
    try:
        result = subprocess.run(
            ["tmux", "list-panes", "-a", "-F", "#{pane_id}"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=1.0,
        )
    except (OSError, subprocess.SubprocessError):
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


@dataclass(frozen=True)
class TmuxWindow:
    index: str
    id: str
    pane_id: str
    pane_index: str
    name: str
    active: bool
    panes: str
    command: str
    path: str
    title: str


def list_windows() -> list[TmuxWindow]:
    separator = "\t"
    fmt = separator.join(
        (
            "#{window_index}",
            "#{window_id}",
            "#{pane_id}",
            "#{pane_index}",
            "#{window_name}",
            "#{window_active}",
            "#{pane_active}",
            "#{window_panes}",
            "#{pane_current_command}",
            "#{pane_current_path}",
            "#{pane_title}",
        )
    )
    try:
        result = subprocess.run(
            ["tmux", "list-panes", "-a", "-F", fmt],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=1.0,
        )
    except (OSError, subprocess.SubprocessError):
        return []

    windows: list[TmuxWindow] = []
    for line in result.stdout.splitlines():
        parts = line.split(separator)
        if len(parts) != 11:
            continue
        windows.append(
            TmuxWindow(
                index=parts[0],
                id=parts[1],
                pane_id=parts[2],
                pane_index=parts[3],
                name=parts[4],
                active=parts[5] == "1" and parts[6] == "1",
                panes=parts[7],
                command=parts[8],
                path=parts[9],
                title=parts[10],
            )
        )
    return windows


def select_window(target: str) -> bool:
    command = (
        ["tmux", "select-pane", "-t", target]
        if target.startswith("%")
        else ["tmux", "select-window", "-t", target]
    )
    try:
        subprocess.run(
            command,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=1.0,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return True


def pane_context(pane_id: str) -> dict[str, str] | None:
    separator = "\t"
    fmt = separator.join(("#{window_id}", "#{pane_current_command}", "#{pane_current_path}", "#{pane_title}"))
    try:
        result = subprocess.run(
            ["tmux", "display-message", "-p", "-t", pane_id, fmt],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=1.0,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    parts = result.stdout.rstrip("\n").split(separator)
    if len(parts) != 4:
        return None
    return {
        "window_id": parts[0],
        "command": parts[1],
        "path": parts[2],
        "title": parts[3],
    }

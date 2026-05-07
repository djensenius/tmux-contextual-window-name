from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

DEFAULT_CONTEXT_COMMANDS = ("copilot", "nvim", "fish")


def command_name(command: str | None) -> str:
    value = (command or "").strip()
    if not value:
        return ""
    return os.path.basename(value)


def configured_commands(value: str | None) -> set[str]:
    if not value:
        return set(DEFAULT_CONTEXT_COMMANDS)
    return {part.strip() for part in value.split() if part.strip()}


def normalize_slug(value: str | None) -> str:
    if value is None:
        return ""
    normalized = re.sub(r"\s+", " ", str(value)).strip()
    return normalized


def truncate(value: str, max_length: int) -> str:
    if max_length <= 0 or len(value) <= max_length:
        return value
    if max_length <= 1:
        return value[:max_length]
    return f"{value[: max_length - 1]}…"


def git_root(path: str | None) -> str | None:
    if not path:
        return None
    expanded = Path(os.path.expanduser(path))
    if not expanded.exists():
        return None
    cwd = expanded if expanded.is_dir() else expanded.parent
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=0.35,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    root = result.stdout.strip()
    return root or None


def current_branch(path: str | None) -> str | None:
    if not path:
        return None
    expanded = Path(os.path.expanduser(path))
    if not expanded.exists():
        return None
    cwd = expanded if expanded.is_dir() else expanded.parent
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), "branch", "--show-current"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=0.35,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    branch = result.stdout.strip()
    return branch or None


def path_slug(path: str | None, fallback: str | None = None) -> str:
    if not path:
        return normalize_slug(fallback)

    expanded = Path(os.path.expanduser(path))
    home = Path.home()
    try:
        if expanded.resolve(strict=False) == home.resolve(strict=False):
            return "~"
    except OSError:
        pass

    root = git_root(path)
    if root:
        return normalize_slug(Path(root).name)

    name = expanded.name
    if name:
        return normalize_slug(name)
    return normalize_slug(fallback)


def label_for_pane(
    *,
    command: str | None,
    path: str | None,
    commands: str | None = None,
    max_length: int = 24,
    fallback_max_length: int = 16,
) -> str:
    cmd = command_name(command)
    if cmd in configured_commands(commands):
        slug = path_slug(path, cmd) or cmd
        return truncate(slug, max_length)
    return truncate(normalize_slug(cmd) or path_slug(path, ""), fallback_max_length)

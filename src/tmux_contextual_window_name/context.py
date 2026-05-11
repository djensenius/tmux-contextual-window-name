from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
from pathlib import Path

DEFAULT_CONTEXT_COMMANDS = ("copilot", "nvim", "fish")
NODE_COMMANDS = {"node", "nodejs"}
SHELL_COMMANDS = {"bash", "dash", "fish", "sh", "tmux", "zsh"}
NODE_OPTIONS_WITH_VALUE = {
    "--conditions",
    "--cpu-prof-dir",
    "--diagnostic-dir",
    "--eval",
    "--experimental-config-file",
    "--experimental-loader",
    "--experimental-policy",
    "--heap-prof-dir",
    "--icu-data-dir",
    "--import",
    "--input-type",
    "--inspect-port",
    "--inspect-publish-uid",
    "--loader",
    "--max-http-header-size",
    "--openssl-config",
    "--policy-integrity",
    "--prof-process",
    "--redirect-warnings",
    "--require",
    "--secure-heap-min",
    "--secure-heap",
    "--snapshot-blob",
    "--test-name-pattern",
    "--test-reporter-destination",
    "--test-reporter",
    "--title",
    "--trace-event-categories",
    "--trace-event-file-pattern",
    "--watch-path",
    "-C",
    "-e",
    "-r",
}


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


def package_json_name(path: str | None) -> str:
    if not path:
        return ""
    expanded = Path(os.path.expanduser(path))
    cwd = expanded if expanded.is_dir() else expanded.parent
    for directory in (cwd, *cwd.parents):
        package_json = directory / "package.json"
        if package_json.exists():
            try:
                data = json.loads(package_json.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return ""
            return normalize_slug(data.get("name"))
    return ""


def _process_rows() -> list[tuple[int, int, str, str]]:
    try:
        result = subprocess.run(
            ["ps", "-ax", "-o", "pid=", "-o", "ppid=", "-o", "comm=", "-o", "command="],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=0.35,
        )
    except (OSError, subprocess.SubprocessError):
        return []

    rows: list[tuple[int, int, str, str]] = []
    for line in result.stdout.splitlines():
        parts = line.strip().split(None, 3)
        if len(parts) < 4:
            continue
        try:
            pid = int(parts[0])
            ppid = int(parts[1])
        except ValueError:
            continue
        rows.append((pid, ppid, parts[2], parts[3]))
    return rows


def _process_tree_for_pid(pid: str | int | None) -> list[tuple[int, int, str, str, int]]:
    try:
        root_pid = int(str(pid or "").strip())
    except ValueError:
        return []

    rows = _process_rows()
    by_parent: dict[int, list[tuple[int, int, str, str]]] = {}
    by_pid: dict[int, tuple[int, int, str, str]] = {}
    for row in rows:
        by_pid[row[0]] = row
        by_parent.setdefault(row[1], []).append(row)

    blocked: set[int] = set()
    queue = [os.getpid()]
    while queue:
        current = queue.pop(0)
        if current in blocked:
            continue
        blocked.add(current)
        queue.extend(child[0] for child in by_parent.get(current, []))

    tree: list[tuple[int, int, str, str, int]] = []
    queue: list[tuple[int, int]] = [(root_pid, 0)]
    seen: set[int] = set()
    while queue:
        current, depth = queue.pop(0)
        if current in seen or current in blocked:
            continue
        seen.add(current)
        row = by_pid.get(current)
        if row:
            tree.append((*row, depth))
        for child in by_parent.get(current, []):
            queue.append((child[0], depth + 1))
    return tree


def _node_command_line_for_pid(pid: str | int | None) -> str:
    candidates = [
        (depth, process_id, command_line)
        for process_id, _, comm, command_line, depth in _process_tree_for_pid(pid)
        if command_name(comm) in NODE_COMMANDS
    ]
    if not candidates:
        return ""
    return max(candidates, key=lambda item: (item[0], item[1]))[2]


def _renamed_node_label_for_pid(pid: str | int | None) -> str:
    candidates = []
    for process_id, _, comm, command_line, depth in _process_tree_for_pid(pid):
        label = command_name(comm)
        if not label or label in NODE_COMMANDS or label in SHELL_COMMANDS:
            continue
        if command_name(command_line.split(maxsplit=1)[0] if command_line else "") in SHELL_COMMANDS:
            continue
        candidates.append((depth, process_id, label))
    if not candidates:
        return ""
    return normalize_slug(max(candidates, key=lambda item: (item[0], item[1]))[2])


def _looks_like_node_binary(value: str) -> bool:
    return command_name(value) in NODE_COMMANDS


def _node_script_name(script: str) -> str:
    cleaned = script.strip()
    if not cleaned:
        return ""
    path = Path(cleaned)
    name = path.name
    if not name:
        return ""
    if name in (".", ".."):
        return ""
    while Path(name).suffix in (".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx"):
        name = Path(name).stem
    return normalize_slug(name)


def node_process_name_from_command_line(command_line: str | None, path: str | None = None) -> str:
    if not command_line:
        return ""
    try:
        parts = shlex.split(command_line)
    except ValueError:
        parts = command_line.split()

    node_index = next((index for index, part in enumerate(parts) if _looks_like_node_binary(part)), -1)
    if node_index < 0:
        return ""

    index = node_index + 1
    while index < len(parts):
        part = parts[index]
        if part == "--":
            index += 1
            break
        if part.startswith("--"):
            option = part.split("=", 1)[0]
            index += 2 if "=" not in part and option in NODE_OPTIONS_WITH_VALUE else 1
            continue
        if part.startswith("-") and part not in ("-",):
            index += 2 if part in NODE_OPTIONS_WITH_VALUE else 1
            continue
        break

    if index < len(parts):
        return _node_script_name(parts[index])
    return package_json_name(path)


def node_process_name(
    command: str | None,
    path: str | None = None,
    *,
    pane_pid: str | int | None = None,
    process_command_line: str | None = None,
) -> str:
    if command_name(command) not in NODE_COMMANDS:
        return ""
    command_line = process_command_line or _node_command_line_for_pid(pane_pid)
    return node_process_name_from_command_line(command_line, path) or _renamed_node_label_for_pid(pane_pid) or package_json_name(path)


def label_for_pane(
    *,
    command: str | None,
    path: str | None,
    commands: str | None = None,
    max_length: int = 24,
    fallback_max_length: int = 16,
    pane_pid: str | int | None = None,
    process_command_line: str | None = None,
) -> str:
    cmd = command_name(command)
    if cmd in NODE_COMMANDS:
        process_name = node_process_name(
            cmd,
            path,
            pane_pid=pane_pid,
            process_command_line=process_command_line,
        )
        if process_name:
            return truncate(process_name, fallback_max_length)
    if cmd in configured_commands(commands):
        slug = path_slug(path, cmd) or cmd
        return truncate(slug, max_length)
    return truncate(normalize_slug(cmd) or path_slug(path, ""), fallback_max_length)

from __future__ import annotations

import argparse
import contextlib
import select
import shlex
import shutil
import subprocess
import sys
import termios
import time
import tty

from .context import label_for_pane
from .copilot_state import write_statusline
from .osc_title import normalize_title
from .popup import popup_text
from .state_store import StateStore
from .tmux_runtime import list_windows, live_panes, pane_context, select_window, tmux_option
from .window_picker import render_picker_preview, render_picker_source, render_window_picker, resolve_selection


def _int_option(name: str, default: int) -> int:
    value = tmux_option(name, str(default))
    try:
        return int(value)
    except ValueError:
        return default


def _state_dir() -> str:
    return tmux_option("@contextual-window-name-state-dir", "~/.local/state/tmux-contextual-window-name")


def _ttl() -> int:
    return _int_option("@contextual-window-name-state-ttl-seconds", 300)


def cmd_name(args: argparse.Namespace) -> int:
    max_length = _int_option("@contextual-window-name-max-length", 24)
    fallback_max_length = _int_option("@contextual-window-name-fallback-max-length", 16)
    commands = tmux_option("@contextual-window-name-commands", "copilot nvim fish")
    context = pane_context(args.pane) if args.pane and not args.pane_pid else None
    label = label_for_pane(
        command=args.command or (context or {}).get("command"),
        path=args.path or (context or {}).get("path"),
        commands=commands,
        max_length=max_length,
        fallback_max_length=fallback_max_length,
        pane_pid=args.pane_pid or (context or {}).get("pane_pid"),
    )

    title = normalize_title(args.title)
    if args.pane and title.is_copilot:
        store = StateStore(_state_dir())
        state = store.read_pane(args.pane) or {"pane_id": args.pane, "pane_bound": True}
        state["title"] = title.raw
        state["current_intent"] = title.current_intent
        state["timestamp"] = time.time()
        store.write_pane(args.pane, state)

    print(label, end="")
    return 0


def cmd_popup(args: argparse.Namespace) -> int:
    if args.watch:
        return _watch_popup(args)
    print(_popup_text_from_args(args))
    with contextlib.suppress(EOFError):
        input()
    return 0


def _popup_text_from_args(args: argparse.Namespace) -> str:
    context = pane_context(args.pane)
    return popup_text(
        pane_id=args.pane,
        window_id=(context or {}).get("window_id", args.window),
        command=(context or {}).get("command", args.command),
        path=(context or {}).get("path", args.path),
        title=(context or {}).get("title", args.title),
        state_dir=_state_dir(),
        ttl_seconds=_ttl(),
    )


def _watch_popup(args: argparse.Namespace) -> int:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print(_popup_text_from_args(args))
        return 0

    old_settings = termios.tcgetattr(sys.stdin)
    try:
        tty.setcbreak(sys.stdin.fileno())
        while True:
            print("\033[H\033[2J", end="")
            print(_popup_text_from_args(args))
            print("\nAuto-refreshing every 2s. Press Enter, q, or Esc to close.", flush=True)
            ready, _, _ = select.select([sys.stdin], [], [], 2.0)
            if ready:
                char = sys.stdin.read(1)
                if char in ("\n", "\r", "q", "Q", "\x1b"):
                    return 0
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


def cmd_statusline(_: argparse.Namespace) -> int:
    write_statusline()
    return 0


def _fzf_select_window(windows) -> tuple[bool, str | None]:
    if not shutil.which("fzf") or not sys.stdin.isatty() or not sys.stdout.isatty():
        return False, None

    source_text = render_picker_source(windows, state_dir=_state_dir(), ttl_seconds=_ttl())
    if not source_text:
        return False, None

    command = shlex.join([sys.executable, "-m", "tmux_contextual_window_name.cli"])
    source_command = f"{command} windows-source"
    preview_command = f"{command} windows-preview --target {{1}}"
    try:
        result = subprocess.run(
            [
                "fzf",
                "--ansi",
                "--no-sort",
                "--layout=reverse",
                "--border=rounded",
                "--prompt=windows> ",
                "--pointer=▶",
                "--delimiter=\t",
                "--with-nth=2",
                "--header=Enter: select • Ctrl-R: refresh • Esc: close",
                f"--bind=ctrl-r:reload({source_command})+refresh-preview",
                f"--preview={preview_command}",
                "--preview-window=down:55%:wrap",
            ],
            input=source_text + "\n",
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
    except OSError:
        return False, None
    if result.returncode != 0:
        return True, None
    return True, resolve_selection(result.stdout, windows)


def cmd_windows(args: argparse.Namespace) -> int:
    windows = list_windows()
    if not args.plain:
        attempted_fzf, target = _fzf_select_window(windows)
        if attempted_fzf:
            if target is None:
                return 0
            return 0 if select_window(target) else 1

    print(render_window_picker(windows, state_dir=_state_dir(), ttl_seconds=_ttl()), end="", flush=True)
    try:
        selection = input()
    except EOFError:
        return 0
    target = resolve_selection(selection, windows)
    if target is None:
        return 0
    return 0 if select_window(target) else 1


def cmd_windows_source(_: argparse.Namespace) -> int:
    print(render_picker_source(list_windows(), state_dir=_state_dir(), ttl_seconds=_ttl()))
    return 0


def cmd_windows_preview(args: argparse.Namespace) -> int:
    print(render_picker_preview(args.target, list_windows(), state_dir=_state_dir(), ttl_seconds=_ttl()))
    return 0


def cmd_prune(args: argparse.Namespace) -> int:
    store = StateStore(_state_dir())
    if args.pane:
        store.delete_pane(args.pane)
    else:
        store.prune_missing_panes(live_panes())
    return 0


def cmd_diagnose(_: argparse.Namespace) -> int:
    print("tmux-contextual-window-name")
    print(f"state_dir: {_state_dir()}")
    print(f"commands: {tmux_option('@contextual-window-name-commands', 'copilot nvim fish')}")
    print("window_icon: load this plugin before tmux-nerd-font-window-name so #{window_icon} is expanded")
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="tmux-contextual-window-name")
    subcommands = root.add_subparsers(dest="command_name", required=True)

    name = subcommands.add_parser("name")
    name.add_argument("--pane", default="")
    name.add_argument("--window", default="")
    name.add_argument("--command", default="")
    name.add_argument("--path", default="")
    name.add_argument("--title", default="")
    name.add_argument("--pane-pid", default="")
    name.set_defaults(func=cmd_name)

    popup = subcommands.add_parser("popup")
    popup.add_argument("--pane", required=True)
    popup.add_argument("--window", default="")
    popup.add_argument("--command", default="")
    popup.add_argument("--path", default="")
    popup.add_argument("--title", default="")
    popup.add_argument("--watch", action="store_true")
    popup.set_defaults(func=cmd_popup)

    statusline = subcommands.add_parser("statusline")
    statusline.set_defaults(func=cmd_statusline)

    windows = subcommands.add_parser("windows")
    windows.add_argument("--plain", action="store_true")
    windows.set_defaults(func=cmd_windows)

    windows_source = subcommands.add_parser("windows-source")
    windows_source.set_defaults(func=cmd_windows_source)

    windows_preview = subcommands.add_parser("windows-preview")
    windows_preview.add_argument("--target", required=True)
    windows_preview.set_defaults(func=cmd_windows_preview)

    prune = subcommands.add_parser("prune")
    prune.add_argument("--pane", default="")
    prune.set_defaults(func=cmd_prune)

    diagnose = subcommands.add_parser("diagnose")
    diagnose.set_defaults(func=cmd_diagnose)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

# tmux-contextual-window-name

A companion tmux plugin for `tmux-nerd-font-window-name` that keeps the Nerd Font icon mapping and adds compact repo/path context for selected commands.

## Install

Install with TPM before `tmux-nerd-font-window-name`:

```tmux
set -g @plugin 'djensenius/tmux-contextual-window-name'
set -g @plugin 'joshmedeski/tmux-nerd-font-window-name'
```

For local development, symlink the checkout into TPM's plugin directory and use any plugin spec whose basename is `tmux-contextual-window-name`:

```sh
ln -sfn ~/Developer/tmux-contextual-window-name ~/.config/tmux/plugins/tmux-contextual-window-name
```

```tmux
set -g @plugin 'local/tmux-contextual-window-name'
```

The plugin sets tmux window names to the Nerd Font icon and configures the popup binding. The visible Catppuccin tab text can then compose `#W` with a tmux-format context fallback:

```tmux
set -g automatic-rename on
set -g automatic-rename-format "<nerd-font-icon-format>"
set -g @catppuccin_window_text " #W <repo-or-path-context>"
```

## Configuration

```tmux
set -g @contextual-window-name-commands "copilot nvim fish"
set -g @contextual-window-name-max-length 24
set -g @contextual-window-name-fallback-max-length 16
set -g @contextual-window-name-state-dir "~/.local/state/tmux-contextual-window-name"
set -g @contextual-window-name-state-ttl-seconds 300
set -g @contextual-window-name-python-bin "python3"
set -g @contextual-window-name-observe-osc-title "off"
set -g @contextual-window-name-popup-width "85%"
set -g @contextual-window-name-popup-height "80%"
set -g @contextual-window-name-popup-key "X"
set -g @contextual-window-name-window-picker-key "W"
set -g @contextual-window-name-customize-key "C"
```

By default, `copilot`, `nvim`, and `fish` windows render the git-root basename or current path basename. Other commands render the command name.

## Copilot status line

The TPM entrypoint automatically installs a private copy of the statusLine helper under the standard per-user libexec area:

Configure Copilot CLI to write pane-scoped state:

```json
{
  "statusLine": {
    "type": "command",
    "command": "~/.local/libexec/tmux-contextual-window-name/bin/copilot-statusline"
  }
}
```

The status writer reads JSON from stdin, keys live data by `TMUX_PANE`, writes private state under `~/.local/state/tmux-contextual-window-name`, and prints nothing. Keeping the command in `~/.local/libexec` avoids executing the mutable development checkout from Copilot's statusLine hook. You can refresh the libexec copy manually with `make install-statusline`, but normal TPM plugin loading also keeps it installed.

Copilot OSC title updates exposed by tmux as `#{pane_title}` are used to derive the current intent when titles look like `🤖 Exploring codebase` or `Copilot: Exploring codebase`.

## Popup

The plugin binds `prefix X` by default to a tmux popup showing Copilot session context for Copilot panes and generic path/repo information for other panes. It refreshes every two seconds while open so title/intent/state changes show up without reopening. Change `@contextual-window-name-popup-key` to use a different key. `prefix C` is left on tmux's default `customize-mode -Z` binding and can be changed with `@contextual-window-name-customize-key`.

It also binds `prefix W` by default to an fzf-style fuller-context window/pane picker. Change `@contextual-window-name-window-picker-key` to use a different key. Every pane in every window gets its own row, so multiple Copilot/agent panes are shown independently with their own OSC 2 title, intent, session/model/context/change details, and state source when available. Press Enter to switch to the selected pane, Ctrl-R to reload the pane list and preview from live tmux/status state, or Esc to close it.

If `fzf` is unavailable or the command is run outside a TTY, it falls back to a numbered plain-text picker. You can force that mode with:

```sh
bin/tmux-contextual-window-name windows --plain
```

You can run the popup renderer directly:

```sh
bin/tmux-contextual-window-name popup --pane "$TMUX_PANE" --command copilot --path "$PWD"
```

## OSC 9;4 progress

This plugin does not parse or emit OSC 9;4 progress. Use `tmux-osc-9-4` for pane-scoped progress ownership.

## Development

```sh
make lint
make test
```

GitHub Actions runs both commands on pushes to `main`, pull requests, and manual workflow dispatches.

## License

MIT

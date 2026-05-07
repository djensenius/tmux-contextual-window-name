#!/usr/bin/env bash
set -euo pipefail

CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_BIN="$CURRENT_DIR/bin/tmux-contextual-window-name"
NERD_FORMAT_GENERATOR="$HOME/.config/tmux/plugins/tmux-nerd-font-window-name/bin/generate-tmux-format"
STATUSLINE_INSTALL_DIR="$HOME/.local/libexec/tmux-contextual-window-name"

set_default() {
  local option="$1"
  local value="$2"

  if [ -z "$(tmux show-option -gqv "$option")" ]; then
    tmux set-option -gq "$option" "$value"
  fi
}

install_statusline() {
  local tmp_dir="$STATUSLINE_INSTALL_DIR.tmp"

  rm -rf "$tmp_dir"
  install -d -m 700 "$tmp_dir/bin" "$tmp_dir/src"
  cp -R "$CURRENT_DIR/bin/." "$tmp_dir/bin/"
  cp -R "$CURRENT_DIR/src/." "$tmp_dir/src/"
  find "$tmp_dir" -type d -exec chmod 700 {} +
  find "$tmp_dir" -type f -exec chmod 600 {} +
  chmod 700 "$tmp_dir/bin/tmux-contextual-window-name" "$tmp_dir/bin/copilot-statusline"
  rm -rf "$STATUSLINE_INSTALL_DIR"
  mv "$tmp_dir" "$STATUSLINE_INSTALL_DIR"
}

set_default "@contextual-window-name-commands" "copilot nvim fish"
set_default "@contextual-window-name-max-length" "24"
set_default "@contextual-window-name-fallback-max-length" "16"
set_default "@contextual-window-name-state-dir" "~/.local/state/tmux-contextual-window-name"
set_default "@contextual-window-name-state-ttl-seconds" "300"
set_default "@contextual-window-name-python-bin" "python3"
set_default "@contextual-window-name-observe-osc-title" "off"
set_default "@contextual-window-name-popup-width" "85%"
set_default "@contextual-window-name-popup-height" "80%"

install_statusline

tmux set-option -gq automatic-rename on

if [ -x "$NERD_FORMAT_GENERATOR" ]; then
  icon_format="$("$NERD_FORMAT_GENERATOR")"
else
  icon_format="#{window_icon}"
fi

tmux set-option -gq automatic-rename-format "$icon_format"

popup_width="$(tmux show-option -gqv @contextual-window-name-popup-width)"
popup_height="$(tmux show-option -gqv @contextual-window-name-popup-height)"

tmux bind-key C customize-mode -Z
tmux bind-key X run-shell "tmux display-popup -w '$popup_width' -h '$popup_height' -E \"$PLUGIN_BIN popup --watch --pane #{q:pane_id} --window #{q:window_id} --command #{q:pane_current_command} --path #{q:pane_current_path} --title #{q:pane_title}\""
tmux bind-key W display-popup -w "$popup_width" -h "$popup_height" -E "$PLUGIN_BIN windows"

tmux set-hook -g pane-exited[99] "run-shell '$PLUGIN_BIN prune --pane \"#{pane_id}\"'"

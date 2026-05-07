.PHONY: test lint diagnose install-statusline

test:
	PYTHONPATH=src python3 -m unittest discover -s tests

lint:
	PYTHONPATH=src ruff check .

diagnose:
	bin/tmux-contextual-window-name diagnose

install-statusline:
	rm -rf "$(HOME)/.local/libexec/tmux-contextual-window-name.tmp"
	install -d -m 700 "$(HOME)/.local/libexec/tmux-contextual-window-name.tmp/bin" "$(HOME)/.local/libexec/tmux-contextual-window-name.tmp/src"
	cp -R bin/. "$(HOME)/.local/libexec/tmux-contextual-window-name.tmp/bin/"
	cp -R src/. "$(HOME)/.local/libexec/tmux-contextual-window-name.tmp/src/"
	find "$(HOME)/.local/libexec/tmux-contextual-window-name.tmp" -type d -exec chmod 700 {} +
	find "$(HOME)/.local/libexec/tmux-contextual-window-name.tmp" -type f -exec chmod 600 {} +
	chmod 700 "$(HOME)/.local/libexec/tmux-contextual-window-name.tmp/bin/tmux-contextual-window-name" "$(HOME)/.local/libexec/tmux-contextual-window-name.tmp/bin/copilot-statusline"
	rm -rf "$(HOME)/.local/libexec/tmux-contextual-window-name"
	mv "$(HOME)/.local/libexec/tmux-contextual-window-name.tmp" "$(HOME)/.local/libexec/tmux-contextual-window-name"

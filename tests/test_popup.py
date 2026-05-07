import tempfile
import time
import unittest

from tmux_contextual_window_name.popup import popup_text, render_popup
from tmux_contextual_window_name.state_store import StateStore


class PopupTests(unittest.TestCase):
    def test_copilot_live_popup(self):
        state = {
            "session_id": "s1",
            "session_name": "Plugin",
            "repo_slug": "tmux-contextual-window-name",
            "cwd": "/tmp/project",
            "model": {"display_name": "GPT-5.5"},
            "context": {"current_context_used_percentage": 50},
            "changes": {"lines_added": 2, "lines_removed": 1},
            "transcript_path": "/tmp/t.jsonl",
            "current_intent": "Implementing",
        }
        text = render_popup(
            pane_id="%1",
            window_id="@1",
            command="copilot",
            path="/tmp/project",
            title="",
            state=state,
            state_status="live",
        )
        self.assertIn("Copilot", text)
        self.assertIn("Intent: Implementing", text)
        self.assertIn("State: live", text)

    def test_missing_copilot_state(self):
        text = render_popup(
            pane_id="%1",
            window_id="@1",
            command="copilot",
            path="/tmp/project",
            title="🤖 Busy",
            state=None,
            state_status="missing",
        )
        self.assertIn("Intent: Busy", text)
        self.assertIn("State: missing", text)

    def test_idle_copilot_title_clears_stored_intent(self):
        text = render_popup(
            pane_id="%1",
            window_id="@1",
            command="copilot",
            path="/tmp/project",
            title="GitHub Copilot",
            state={"current_intent": "Stale intent", "session_id": "s1"},
            state_status="live",
        )
        self.assertIn("Intent: idle", text)
        self.assertNotIn("Stale intent", text)

    def test_stale_state_popup(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = StateStore(tmp)
            store.write_pane("%1", {"session_id": "s1", "timestamp": time.time() - 400})
            text = popup_text(
                pane_id="%1",
                window_id="@1",
                command="copilot",
                path="/tmp",
                title="",
                state_dir=tmp,
                ttl_seconds=300,
            )
            self.assertIn("State: stale", text)

    def test_generic_popup(self):
        text = render_popup(
            pane_id="%1",
            window_id="@1",
            command="fish",
            path="/tmp",
            title="",
            state=None,
            state_status="missing",
        )
        self.assertIn("fish", text)
        self.assertIn("Path: /tmp", text)


if __name__ == "__main__":
    unittest.main()

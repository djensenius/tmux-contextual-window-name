import io
import json
import tempfile
import unittest

from tmux_contextual_window_name.copilot_state import build_state, write_statusline
from tmux_contextual_window_name.state_store import StateStore


class CopilotStateTests(unittest.TestCase):
    def sample(self):
        return {
            "session_id": "s1",
            "session_name": "Working on plugin",
            "transcript_path": "/tmp/transcript.jsonl",
            "cwd": "/tmp",
            "model": {"id": "gpt-5.5", "display_name": "GPT-5.5"},
            "username": "user",
            "current_context_used_percentage": 42,
            "lines_added": 10,
            "lines_removed": 3,
        }

    def test_build_state_includes_core_fields(self):
        state = build_state(self.sample(), "%1")
        self.assertEqual(state["pane_id"], "%1")
        self.assertTrue(state["pane_bound"])
        self.assertEqual(state["session_id"], "s1")
        self.assertEqual(state["model"]["display_name"], "GPT-5.5")

    def test_statusline_writes_pane_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_statusline(
                io.StringIO(json.dumps(self.sample())),
                {"TMUX_PANE": "%1", "TMUX_CONTEXTUAL_WINDOW_NAME_STATE_DIR": tmp},
            )
            state = StateStore(tmp).read_pane("%1")
            self.assertEqual(state["session_id"], "s1")

    def test_statusline_writes_session_state_without_tmux_pane(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_statusline(io.StringIO(json.dumps(self.sample())), {"TMUX_CONTEXTUAL_WINDOW_NAME_STATE_DIR": tmp})
            state = StateStore(tmp)._read_json(StateStore(tmp).session_path("s1"))
            self.assertFalse(state["pane_bound"])


if __name__ == "__main__":
    unittest.main()

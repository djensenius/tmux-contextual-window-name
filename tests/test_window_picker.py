import unittest

from tmux_contextual_window_name.tmux_runtime import TmuxWindow
from tmux_contextual_window_name.window_picker import build_picker_entries, render_window_picker, resolve_selection


class WindowPickerTests(unittest.TestCase):
    def windows(self):
        return [
            TmuxWindow("1", "@1", "%1", "0", "", False, "1", "fish", "/tmp/project", "fish title"),
            TmuxWindow("2", "@2", "%2", "0", "", True, "2", "copilot", "/tmp/agent", "🤖 Working"),
            TmuxWindow("2", "@2", "%3", "1", "", False, "2", "copilot", "/tmp/other-agent", "🤖 Hidden agent"),
        ]

    def test_render_window_picker_lists_windows(self):
        text = render_window_picker(self.windows())
        self.assertIn("1.0:  project", text)
        self.assertIn("* 2.0:  agent", text)
        self.assertIn("2.1:  other-agent", text)
        self.assertIn("Intent: Working", text)
        self.assertIn("Intent: Hidden agent", text)
        self.assertIn("Title: 🤖 Working", text)
        self.assertIn("Title: fish title", text)
        self.assertIn("Ctrl-R", text)
        self.assertIn("2 panes", text)

    def test_resolve_selection_by_row(self):
        self.assertEqual(resolve_selection("1", self.windows()), "%1")

    def test_build_picker_entries_for_fzf(self):
        entries = build_picker_entries(self.windows())
        self.assertEqual(entries[0].target, "%1")
        self.assertIn("fish", entries[0].display)
        self.assertIn("Path: /tmp/project", entries[0].preview)
        self.assertIn("Pane: 0 (%1)", entries[0].preview)
        self.assertIn("Ctrl-R", entries[0].preview)
        self.assertIn("Intent: Working", entries[1].preview)
        self.assertIn("Hidden agent", entries[2].preview)

    def test_idle_copilot_title_ignores_stale_state_intent(self):
        windows = [TmuxWindow("1", "@1", "%1", "0", "", True, "1", "copilot", "/tmp/agent", "GitHub Copilot")]
        text = render_window_picker(windows)
        self.assertIn("Intent: idle", text)
        self.assertNotIn("Stale", text)

    def test_resolve_fzf_selection_by_hidden_target(self):
        self.assertEqual(resolve_selection("%2\t* 2 window\t/tmp/preview", self.windows()), "%2")

    def test_resolve_selection_by_window_index_when_row_is_out_of_range(self):
        windows = [TmuxWindow("9", "@9", "%9", "0", "name", False, "1", "fish", "/tmp/project", "")]
        self.assertEqual(resolve_selection("9", windows), "%9")

    def test_blank_selection_closes(self):
        self.assertIsNone(resolve_selection("", self.windows()))


if __name__ == "__main__":
    unittest.main()

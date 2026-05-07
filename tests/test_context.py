import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from tmux_contextual_window_name.context import label_for_pane, path_slug


class ContextTests(unittest.TestCase):
    def test_git_repo_slug(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "example repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            child = repo / "src"
            child.mkdir()
            self.assertEqual(path_slug(str(child)), "example repo")

    def test_non_git_path_slug(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plain"
            path.mkdir()
            self.assertEqual(path_slug(str(path)), "plain")

    def test_home_slug(self):
        self.assertEqual(path_slug(str(Path.home())), "~")

    def test_missing_path_falls_back_to_command(self):
        self.assertEqual(label_for_pane(command="copilot", path="", max_length=24), "copilot")

    def test_contextual_command_uses_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "project"
            path.mkdir()
            self.assertEqual(label_for_pane(command="nvim", path=str(path)), "project")

    def test_unknown_command_uses_command(self):
        self.assertEqual(label_for_pane(command="python", path=os.getcwd()), "python")

    def test_truncates_contextual_and_fallback_labels(self):
        self.assertEqual(
            label_for_pane(command="copilot", path="/tmp/abcdefghijklmnopqrstuvwxyz", max_length=8),
            "abcdefg…",
        )
        self.assertEqual(label_for_pane(command="verylongcommand", path="/tmp", fallback_max_length=8), "verylon…")


if __name__ == "__main__":
    unittest.main()

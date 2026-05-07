import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tmux_contextual_window_name import copilot_workspace


class CopilotWorkspaceTests(unittest.TestCase):
    def test_find_workspace_state_by_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            project = home / "Developer" / "project"
            project.mkdir(parents=True)
            session = home / ".copilot" / "session-state" / "s1"
            session.mkdir(parents=True)
            (session / "workspace.yaml").write_text(
                "\n".join(
                    [
                        "id: s1",
                        f"cwd: {project}",
                        "name: Test Session",
                        "repository: owner/repo",
                        "branch: main",
                    ]
                ),
                encoding="utf-8",
            )
            (session / "events.jsonl").write_text("", encoding="utf-8")
            settings = home / ".copilot" / "settings.json"
            settings.write_text(json.dumps({"model": "gpt-5.5"}), encoding="utf-8")

            with patch.object(copilot_workspace.Path, "home", return_value=home):
                state = copilot_workspace.find_workspace_state(str(project))

            self.assertEqual(state["session_id"], "s1")
            self.assertEqual(state["session_name"], "Test Session")
            self.assertEqual(state["model"]["display_name"], "gpt-5.5")
            self.assertEqual(state["remote"]["repository"], "owner/repo")
            self.assertEqual(state["transcript_path"], str(session / "events.jsonl"))

    def test_workspace_state_includes_event_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            project = home / "project"
            project.mkdir()
            session = home / ".copilot" / "session-state" / "s1"
            session.mkdir(parents=True)
            (session / "workspace.yaml").write_text(f"id: s1\ncwd: {project}\n", encoding="utf-8")
            (session / "events.jsonl").write_text(
                "\n".join(
                    [
                        json.dumps({"type": "session.model_change", "data": {"newModel": "gpt-5.5"}}),
                        json.dumps(
                            {
                                "type": "session.shutdown",
                                "data": {
                                    "currentTokens": 1234,
                                    "codeChanges": {
                                        "linesAdded": 10,
                                        "linesRemoved": 2,
                                        "filesModified": ["a", "b"],
                                    },
                                },
                            }
                        ),
                    ]
                ),
                encoding="utf-8",
            )

            with patch.object(copilot_workspace.Path, "home", return_value=home):
                state = copilot_workspace.find_workspace_state(str(project))

            self.assertEqual(state["model"]["display_name"], "gpt-5.5")
            self.assertEqual(state["context"]["current_tokens"], 1234)
            self.assertEqual(state["changes"]["lines_added"], 10)
            self.assertEqual(state["changes"]["files_changed"], 2)


if __name__ == "__main__":
    unittest.main()

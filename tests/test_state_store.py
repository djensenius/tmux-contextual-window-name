import os
import stat
import tempfile
import time
import unittest

from tmux_contextual_window_name.state_store import StateStore


class StateStoreTests(unittest.TestCase):
    def test_atomic_private_pane_write_and_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = StateStore(tmp)
            store.write_pane("%1", {"pane_id": "%1", "timestamp": time.time()})
            state = store.read_pane("%1")
            self.assertEqual(state["pane_id"], "%1")
            mode = stat.S_IMODE(os.stat(store.pane_path("%1")).st_mode)
            self.assertEqual(mode, 0o600)

    def test_multiple_panes_are_separate(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = StateStore(tmp)
            store.write_pane("%1", {"pane_id": "%1"})
            store.write_pane("%2", {"pane_id": "%2"})
            self.assertEqual(store.read_pane("%1")["pane_id"], "%1")
            self.assertEqual(store.read_pane("%2")["pane_id"], "%2")

    def test_state_status(self):
        store = StateStore(tempfile.mkdtemp())
        self.assertEqual(store.state_status(None, 300), "missing")
        self.assertEqual(store.state_status({"timestamp": time.time()}, 300), "live")
        self.assertEqual(store.state_status({"timestamp": time.time() - 400}, 300), "stale")


if __name__ == "__main__":
    unittest.main()

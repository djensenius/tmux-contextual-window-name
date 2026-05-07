import unittest

from tmux_contextual_window_name.osc_title import normalize_title


class OscTitleTests(unittest.TestCase):
    def test_robot_title_is_current_intent(self):
        title = normalize_title("🤖 Exploring codebase")
        self.assertTrue(title.is_copilot)
        self.assertFalse(title.is_idle)
        self.assertEqual(title.current_intent, "Exploring codebase")

    def test_screen_reader_title_is_current_intent(self):
        self.assertEqual(normalize_title("Copilot: Exploring codebase").current_intent, "Exploring codebase")

    def test_default_copilot_title_is_idle(self):
        title = normalize_title("GitHub Copilot")
        self.assertTrue(title.is_copilot)
        self.assertTrue(title.is_idle)
        self.assertIsNone(title.current_intent)

    def test_blank_title_is_idle(self):
        title = normalize_title("")
        self.assertFalse(title.is_copilot)
        self.assertTrue(title.is_idle)

    def test_session_title_is_idle(self):
        title = normalize_title("Implement plugin", "Implement plugin")
        self.assertTrue(title.is_copilot)
        self.assertTrue(title.is_idle)


if __name__ == "__main__":
    unittest.main()

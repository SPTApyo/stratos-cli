import unittest
from unittest.mock import MagicMock
from stratos.core.pool import Blackboard

class TestBlackboard(unittest.TestCase):
    def setUp(self):
        self.sandbox = MagicMock()
        self.sandbox.get_structure_tree.return_value = "root/"
        self.logger = MagicMock()
        self.blackboard = Blackboard(self.sandbox, self.logger)

    def test_post_and_get(self):
        self.blackboard.post("PLAN", "Step 1")
        self.assertEqual(self.blackboard.data["PLAN"], "Step 1")

    def test_compute_diff_new_file(self):
        self.blackboard.last_snapshot = {"old.txt": "content"}
        new_snapshot = {"old.txt": "content", "new.txt": "fresh"}
        diff = self.blackboard.compute_diff(new_snapshot)
        self.assertIn("[NEW] new.txt", diff)

    def test_compute_diff_modified_file(self):
        self.blackboard.last_snapshot = {"file.txt": "line1\nline2"}
        new_snapshot = {"file.txt": "line1\nchanged"}
        diff = self.blackboard.compute_diff(new_snapshot)
        self.assertIn("[MOD] file.txt", diff)
        self.assertIn("-line2", diff)
        self.assertIn("+changed", diff)

    def test_compute_diff_no_changes(self):
        snap = {"a.py": "code"}
        self.blackboard.last_snapshot = snap
        diff = self.blackboard.compute_diff(snap)
        self.assertEqual(diff, "NO_CHANGES")

    def test_context_truncation(self):
        # Fill team log with many entries
        for i in range(100):
            self.blackboard.post_discussion("AGENT", f"Message {i}")
        
        context = self.blackboard.get_all_context()
        # Should only contain last 8 logs (since it's under 60k threshold)
        self.assertIn("Message 99", context)
        self.assertNotIn("Message 0", context)

if __name__ == "__main__":
    unittest.main()

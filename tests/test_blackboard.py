import unittest
from stratos.core.pool import Blackboard

class MockSandbox:
    def get_structure_tree(self):
        return "root/\n  file1.py"

class TestBlackboard(unittest.TestCase):
    def setUp(self):
        self.bb = Blackboard(MockSandbox(), None)

    def test_post_and_get(self):
        self.bb.post("KEY", "VALUE")
        self.assertEqual(self.bb.data["KEY"], "VALUE")

    def test_compute_diff_new_file(self):
        self.bb.last_snapshot = {"a.py": "content"}
        new_snap = {"a.py": "content", "b.py": "new"}
        diff = self.bb.compute_diff(new_snap)
        self.assertIn("[NEW] b.py", diff)

    def test_compute_diff_modified_file(self):
        self.bb.last_snapshot = {"a.py": "old line"}
        new_snap = {"a.py": "new line"}
        diff = self.bb.compute_diff(new_snap)
        self.assertIn("[MOD] a.py", diff)
        self.assertIn("-old line", diff)
        self.assertIn("+new line", diff)

    def test_context_generation(self):
        self.bb.post("TODO", "Task 1")
        ctx = self.bb.get_full_context(current_diff="No changes")
        self.assertIn("REAL_FILESYSTEM_STATE", ctx)
        self.assertIn("Task 1", ctx)

if __name__ == "__main__":
    unittest.main()

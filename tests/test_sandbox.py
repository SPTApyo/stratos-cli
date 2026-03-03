import unittest
import os
import shutil
import tempfile
from pathlib import Path
from stratos.core.sandbox import Sandbox

class TestSandbox(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.sandbox = Sandbox(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_properties_propagation(self):
        mock_logger = unittest.mock.MagicMock()
        self.sandbox.logger_instance = mock_logger
        self.assertEqual(self.sandbox.logger_instance, mock_logger)
        self.assertEqual(self.sandbox.files.logger, mock_logger)
        self.assertEqual(self.sandbox.shell.logger, mock_logger)

        self.sandbox.auto_approve = True
        self.assertTrue(self.sandbox.approval.auto_approve)
        self.assertTrue(self.sandbox.auto_approve)

    def test_file_operations_delegation(self):
        self.sandbox.write_file("test.txt", "hello")
        self.assertEqual(self.sandbox.read_file("test.txt"), "hello")
        
        self.assertEqual(self.sandbox.glob_search("*.txt"), ["test.txt"])
        self.assertIn("test.txt", self.sandbox.grep_search("hello"))
        
        self.sandbox.smart_replace("test.txt", "hello", "world")
        self.assertEqual(self.sandbox.read_file("test.txt"), "world")

    def test_shell_delegation(self):
        res = self.sandbox.execute_command("echo 'hey'")
        self.assertIn("STDOUT: hey", res)
        
        self.assertIn("CODE_", self.sandbox.git_init())
        self.assertIn("ERROR", self.sandbox.install_dependencies())

    def test_structure_and_snapshot(self):
        self.sandbox.write_file("dir1/a.txt", "content A")
        self.sandbox.write_file("b.txt", "content B")
        
        tree = self.sandbox.get_structure_tree()
        self.assertIn("dir1/", tree)
        self.assertIn("a.txt", tree)
        self.assertIn("b.txt", tree)
        
        snap = self.sandbox.get_snapshot()
        self.assertEqual(snap["dir1/a.txt"], "content A")
        self.assertEqual(snap["b.txt"], "content B")

    def test_interaction_delegation(self):
        self.sandbox.approval.ask = unittest.mock.MagicMock(return_value="ans")
        self.assertEqual(self.sandbox.ask_user("q"), "ans")
        
        self.sandbox.approval.confirm = unittest.mock.MagicMock(return_value=True)
        self.assertTrue(self.sandbox.request_confirmation("a"))

if __name__ == "__main__":
    unittest.main()

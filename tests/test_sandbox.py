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

    # --- _safe_path tests ---
    def test_safe_path_valid(self):
        path = self.sandbox._safe_path("test.txt")
        self.assertEqual(path, Path(self.test_dir) / "test.txt")

    def test_safe_path_escape_attempt(self):
        with self.assertRaises(PermissionError):
            self.sandbox._safe_path("../outside.txt")

    def test_safe_path_absolute_outside(self):
        with self.assertRaises(PermissionError):
            self.sandbox._safe_path("/etc/passwd")

    # --- write_file tests ---
    def test_write_file_success(self):
        res = self.sandbox.write_file("hello.txt", "world")
        self.assertIn("SUCCESS", res)
        with open(os.path.join(self.test_dir, "hello.txt"), "r") as f:
            self.assertEqual(f.read(), "world")

    def test_write_file_subdir(self):
        res = self.sandbox.write_file("subdir/deep/file.txt", "content")
        self.assertIn("SUCCESS", res)
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "subdir/deep/file.txt")))

    # --- read_file tests ---
    def test_read_file_success(self):
        with open(os.path.join(self.test_dir, "read.txt"), "w") as f:
            f.write("line1\nline2\nline3")
        res = self.sandbox.read_file("read.txt")
        self.assertEqual(res, "line1\nline2\nline3")

    def test_read_file_not_found(self):
        res = self.sandbox.read_file("missing.txt")
        self.assertIn("ERROR", res)

    def test_read_file_chunking(self):
        with open(os.path.join(self.test_dir, "chunk.txt"), "w") as f:
            f.write("1\n2\n3\n4\n5")
        res = self.sandbox.read_file("chunk.txt", start_line=2, end_line=4)
        self.assertEqual(res, "2\n3\n4")

    # --- smart_replace tests ---
    def test_smart_replace_success(self):
        self.sandbox.write_file("replace.txt", "The quick brown fox")
        res = self.sandbox.smart_replace("replace.txt", "brown", "red")
        self.assertIn("SUCCESS", res)
        content = self.sandbox.read_file("replace.txt")
        self.assertEqual(content, "The quick red fox")

    def test_smart_replace_not_found(self):
        self.sandbox.write_file("replace.txt", "Content")
        res = self.sandbox.smart_replace("replace.txt", "missing", "new")
        self.assertIn("ERROR", res)

    # --- safety tests ---
    def test_validate_command_safe(self):
        try:
            self.sandbox._validate_command_safety("ls -la")
        except PermissionError:
            self.fail("_validate_command_safety raised PermissionError unexpectedly")

    def test_validate_command_dangerous(self):
        with self.assertRaises(PermissionError):
            self.sandbox._validate_command_safety("rm -rf /")
        with self.assertRaises(PermissionError):
            self.sandbox._validate_command_safety("mkfs.ext4 /dev/sda1")

    # --- execute_command tests ---
    def test_execute_command_success(self):
        res = self.sandbox.execute_command("echo 'hello'")
        self.assertIn("CODE_0", res)
        self.assertIn("hello", res)

    def test_execute_command_fail(self):
        res = self.sandbox.execute_command("nonexistentcommand")
        self.assertNotIn("CODE_0", res)

if __name__ == "__main__":
    unittest.main()

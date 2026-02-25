import unittest
import shutil
import os
from pathlib import Path
from stratos.core.io.file_manager import FileManager

class TestFileManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("test_sandbox_io").resolve()
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.fm = FileManager(self.test_dir)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_write_read(self):
        res = self.fm.write("test.txt", "hello world")
        self.assertIn("SUCCESS", res)
        content = self.fm.read("test.txt")
        self.assertEqual(content, "hello world")

    def test_safe_path(self):
        res = self.fm.read("../outside.txt")
        self.assertIn("RESTRICTED", res)

    def test_glob(self):
        self.fm.write("a.py", "print(1)")
        self.fm.write("b.txt", "hello")
        files = self.fm.glob("*.py")
        self.assertEqual(files, ["a.py"])

    def test_replace(self):
        self.fm.write("replace.txt", "old content")
        self.fm.replace("replace.txt", "old", "new")
        self.assertEqual(self.fm.read("replace.txt"), "new content")

    def test_grep(self):
        self.fm.write("grep.txt", "line1\ntarget\nline3")
        res = self.fm.grep("target")
        self.assertIn("grep.txt:2:target", res)

if __name__ == "__main__":
    unittest.main()

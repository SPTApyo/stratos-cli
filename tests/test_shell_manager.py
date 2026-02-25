import unittest
from pathlib import Path
import shutil
from stratos.core.io.shell_manager import ShellManager

class TestShellManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("test_shell_io").resolve()
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir()
        self.sm = ShellManager(self.test_dir)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_execute_safe(self):
        res = self.sm.execute("echo 'hello'")
        self.assertIn("STDOUT: hello", res)
        self.assertIn("CODE_0", res)

    def test_execute_dangerous(self):
        res = self.sm.execute("rm -rf /")
        self.assertIn("CRASH: DANGEROUS COMMAND BLOCKED", res)

    def test_git_init(self):
        res = self.sm.git_init()
        self.assertIn("CODE_0", res)
        self.assertTrue((self.test_dir / ".git").exists())

if __name__ == "__main__":
    unittest.main()

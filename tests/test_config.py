import unittest
import os
from pathlib import Path
from stratos.utils.config import STRATOS_HOME, ensure_home

class TestStratosConfig(unittest.TestCase):
    def test_config_path(self):
        """Verify the configuration path is in the user's home .config folder."""
        expected = Path.home() / ".config" / "stratos"
        self.assertEqual(STRATOS_HOME, expected)

    def test_ensure_home(self):
        """Check if the config directory creation logic works."""
        # This just tests if the function runs without error
        try:
            ensure_home()
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"ensure_home failed: {str(e)}")

if __name__ == "__main__":
    unittest.main()

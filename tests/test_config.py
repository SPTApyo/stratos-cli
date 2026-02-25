import unittest
import os
import json
from pathlib import Path
from stratos.utils.config import ConfigManager, ConfigFileHandler

class TestConfigSystem(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("test_config_home")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.cm = ConfigManager()
        # Override paths for testing
        self.cm.CONFIG_PATH = self.test_dir / "config.json"
        self.cm.ENV_PATH = self.test_dir / ".env"

    def tearDown(self):
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_default_config_load(self):
        config = self.cm.load()
        self.cm.save(config) # Force write to verify path
        self.assertEqual(config["theme"], "stratos_dark")
        self.assertTrue(self.cm.CONFIG_PATH.exists())

    def test_config_merge(self):
        # Create a partial config file
        with open(self.cm.CONFIG_PATH, "w") as f:
            json.dump({"theme": "custom_theme"}, f)
        
        config = self.cm.load()
        self.assertEqual(config["theme"], "custom_theme")
        # Ensure default key still exists
        self.assertEqual(config["display_mode"], "dashboard")

    def test_env_var_persistence(self):
        self.cm.save_env("TEST_KEY", "TEST_VALUE")
        val = self.cm.get_api_key("TEST_KEY")
        self.assertEqual(val, "TEST_VALUE")
        
        # Verify file content
        content = self.cm.ENV_PATH.read_text()
        self.assertIn("TEST_KEY=TEST_VALUE", content)

if __name__ == "__main__":
    unittest.main()

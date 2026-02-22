import unittest
import stratos

class TestStratosBasic(unittest.TestCase):
    def test_version_exists(self):
        """Verify that the version is defined."""
        self.assertTrue(hasattr(stratos, "__version__"))
        self.assertIsInstance(stratos.__version__, str)

    def test_metadata_exists(self):
        """Verify that essential metadata is present."""
        self.assertTrue(hasattr(stratos, "__app_name__"))
        self.assertEqual(stratos.__app_name__, "stratos-cli")
        self.assertTrue(hasattr(stratos, "__license__"))

    def test_import_cli(self):
        """Check if CLI entry points are importable."""
        try:
            from stratos import cli
            from stratos.ui import dashboard
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Import failed: {str(e)}")

if __name__ == "__main__":
    unittest.main()

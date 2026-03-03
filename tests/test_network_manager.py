import unittest
from unittest.mock import patch, MagicMock
from stratos.core.io.network_manager import NetworkManager

class TestNetworkManager(unittest.TestCase):
    def setUp(self):
        self.mgr = NetworkManager()

    @patch('subprocess.run')
    def test_fetch_success(self, mock_run):
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = "<html>Content</html>"
        mock_res.stderr = ""
        mock_run.return_value = mock_res
        
        res = self.mgr.fetch("https://google.com")
        self.assertIn("CODE_0", res)
        self.assertIn("<html>Content</html>", res)

    @patch('stratos.core.io.network_manager.DDGS')
    def test_search_success(self, mock_ddgs):
        # Setup mock for DuckDuckGo
        mock_instance = mock_ddgs.return_value.__enter__.return_value
        mock_instance.text.return_value = [
            {"title": "Result 1", "href": "url1", "body": "Snippet 1"}
        ]
        
        with patch('stratos.core.io.network_manager.HAS_DDG', True):
            res = self.mgr.search("Python coding")
            self.assertIn("Result #1", res)
            self.assertIn("Python coding", res)

    def test_search_missing_lib(self):
        with patch('stratos.core.io.network_manager.HAS_DDG', False):
            res = self.mgr.search("anything")
            self.assertIn("library missing", res)

if __name__ == "__main__":
    unittest.main()

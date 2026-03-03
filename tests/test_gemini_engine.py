import unittest
from unittest.mock import MagicMock, patch
from stratos.core.engines.gemini_engine import GeminiEngine

class TestGeminiEngine(unittest.TestCase):
    def setUp(self):
        with patch('google.genai.Client'):
            self.engine = GeminiEngine("fake_api_key", "gemini-2.0-flash")
            self.mock_client = self.engine.client

    def test_generate_content_stream_processing(self):
        """Tests that GeminiEngine correctly accumulates streaming parts and tokens."""
        part = MagicMock()
        part.text = "Hello Gemini"
        part.function_call = None
        
        chunk = MagicMock()
        chunk.usage_metadata = MagicMock(prompt_token_count=100, candidates_token_count=50)
        chunk.candidates = [MagicMock()]
        chunk.candidates[0].content.parts = [part]
        
        self.mock_client.models.generate_content_stream.return_value = [chunk]
        
        logger = MagicMock()
        res = self.engine.generate_content([], [], 1, logger)
        
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].text, "Hello Gemini")
        self.assertEqual(self.engine.total_input_tokens, 100)
        self.assertEqual(self.engine.total_output_tokens, 50)

    def test_generate_content_with_function_call(self):
        """Tests that GeminiEngine correctly processes function calls."""
        fc = MagicMock()
        fc.name = "write_file"
        fc.args = {"path": "test.txt", "content": "hello"}
        
        part = MagicMock()
        part.text = None
        part.function_call = fc
        
        chunk = MagicMock()
        chunk.usage_metadata = None
        chunk.candidates = [MagicMock()]
        chunk.candidates[0].content.parts = [part]
        
        self.mock_client.models.generate_content_stream.return_value = [chunk]
        
        logger = MagicMock()
        res = self.engine.generate_content([], [], 1, logger)
        
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].tool_call.name, "write_file")
        self.assertEqual(res[0].tool_call.args["path"], "test.txt")

    def test_list_models_filtering(self):
        """Tests that list_models correctly filters and cleans names."""
        m1 = MagicMock(); m1.name = "models/gemini-pro"; m1.supported_actions = ["generateContent"]
        m2 = MagicMock(); m2.name = "models/imagen-3"; m2.supported_actions = ["generateContent"]
        
        self.mock_client.models.list.return_value = [m1, m2]
        
        models = self.engine.list_models()
        self.assertIn("gemini-pro", models)
        self.assertNotIn("imagen-3", models)

    def test_gemini_costs(self):
        """Tests cost calculation for Gemini 2.0."""
        self.engine.total_input_tokens = 1_000_000
        self.engine.total_output_tokens = 1_000_000
        self.assertEqual(self.engine.get_costs(), 0.50)

if __name__ == "__main__":
    unittest.main()

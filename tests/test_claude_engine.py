import unittest
from unittest.mock import MagicMock, patch
import sys

mock_anthropic = MagicMock()
if 'anthropic' not in sys.modules:
    sys.modules['anthropic'] = mock_anthropic

from stratos.core.engines.claude_engine import ClaudeEngine

class TestClaudeEngine(unittest.TestCase):
    def setUp(self):
        self.engine = ClaudeEngine("fake_api_key", "claude-3-sonnet")
        if self.engine.client is None:
            self.engine.client = MagicMock()
        self.mock_client = self.engine.client

    def test_generate_content_text_response(self):
        """Tests ClaudeEngine text response generation via streaming."""
        event_delta = MagicMock()
        event_delta.type = "content_block_delta"
        event_delta.delta.type = "text_delta"
        event_delta.delta.text = "Hello"
        
        event_usage = MagicMock()
        event_usage.type = "message_delta"
        event_usage.usage.input_tokens = 10
        event_usage.usage.output_tokens = 5
        
        final_msg = MagicMock()
        final_msg.content = [] 
        
        mock_stream = MagicMock()
        mock_stream.__iter__.return_value = [event_delta, event_usage]
        mock_stream.get_final_message.return_value = final_msg
        
        self.mock_client.messages.stream.return_value.__enter__.return_value = mock_stream
        
        logger = MagicMock()
        res = self.engine.generate_content([], [], 1, logger)
        
        if isinstance(res, str):
            self.fail(f"Engine returned an error: {res}")
            
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].text, "Hello")
        self.assertEqual(self.engine.total_input_tokens, 10)
        self.assertEqual(self.engine.total_output_tokens, 5)

    def test_list_models(self):
        models = self.engine.list_models()
        self.assertIn("claude-3-7-sonnet-latest", models)

    def test_claude_costs(self):
        self.engine.total_input_tokens = 1_000_000
        self.engine.total_output_tokens = 1_000_000
        self.assertEqual(self.engine.get_costs(), 18.0)

    def test_init_no_sdk(self):
        engine = ClaudeEngine("key", "model")
        engine.client = None 
        res = engine.generate_content([], [], 1, MagicMock())
        self.assertIn("SDK not found", res)

if __name__ == "__main__":
    unittest.main()

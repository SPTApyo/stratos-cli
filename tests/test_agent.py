import unittest
from unittest.mock import MagicMock, patch
from stratos.core.agent import AIAgent

class TestAIAgentDeep(unittest.TestCase):
    def setUp(self):
        self.mock_sandbox = MagicMock()
        self.mock_logger = MagicMock()
        self.mock_logger.state = MagicMock()
        project_info = {"name": "P", "desc": "D"}
        with patch('google.genai.Client'):
            self.agent = AIAgent("T", "R", self.mock_sandbox, self.mock_logger, "k", project_info)

    def test_call_llm_stream_processing(self):
        # Mocking the Gemini stream return value
        from google.genai import types
        
        # Create a mock part and chunk
        part = MagicMock()
        part.text = "Streaming text"
        part.function_call = None
        
        chunk = MagicMock()
        chunk.usage_metadata = MagicMock(prompt_token_count=10, candidates_token_count=5)
        chunk.candidates = [MagicMock()]
        chunk.candidates[0].content.parts = [part]
        
        # Setup the client mock
        mock_stream = [chunk]
        self.agent.client.models.generate_content_stream.return_value = mock_stream
        
        # Test _call_llm specifically to increase coverage inside it
        messages = [types.Content(role="user", parts=[types.Part(text="hi")])]
        res = self.agent._call_llm(messages, 1)
        
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].text, "Streaming text")
        self.assertEqual(self.agent.total_input_tokens, 10)

    def test_call_llm_with_function_call(self):
        # Test function call recognition inside the stream
        fc = MagicMock()
        fc.name = "test_tool"
        
        part = MagicMock()
        part.text = None
        part.function_call = fc
        
        chunk = MagicMock()
        chunk.usage_metadata = None
        chunk.candidates = [MagicMock()]
        chunk.candidates[0].content.parts = [part]
        
        self.agent.client.models.generate_content_stream.return_value = [chunk]
        
        res = self.agent._call_llm([], 1)
        self.assertEqual(res[0].function_call.name, "test_tool")

    def test_execute_tools_not_found(self):
        fc = MagicMock(); fc.name = "unknown"; fc.args = {}
        res = self.agent._execute_tools([fc])
        self.assertIn("Unknown tool", res[0].function_response.response["result"])

    def test_get_costs(self):
        self.agent.total_input_tokens = 1_000_000
        self.agent.total_output_tokens = 1_000_000
        self.assertEqual(self.agent.get_costs(), 0.50)

if __name__ == "__main__":
    unittest.main()

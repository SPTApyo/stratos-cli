import unittest
from unittest.mock import MagicMock, patch
from stratos.core.agent import AIAgent
from stratos.core.engines.protocol import Message, MessagePart, ToolCall, ToolResponse

class TestAIAgentLogic(unittest.TestCase):
    def setUp(self):
        self.mock_sandbox = MagicMock()
        self.mock_logger = MagicMock()
        self.mock_engine = MagicMock()
        project_info = {"name": "TestProj", "desc": "TestDesc"}
        
        with patch('stratos.core.roles.AgentRole.is_valid_role', return_value=True):
            self.agent = AIAgent("AgentX", "MANAGER", self.mock_sandbox, self.mock_logger, self.mock_engine, project_info)

    def test_think_and_act_basic_flow(self):
        """Tests that the agent calls the engine and processes the response."""
        self.mock_engine.generate_content.return_value = [MessagePart(text="Hello world")]
        
        self.agent._review_prompt = MagicMock(return_value="Prompt")
        
        result = self.agent.think_and_act("Say hi")
        
        self.assertEqual(result, "Hello world")
        self.mock_engine.generate_content.assert_called_once()

    def test_execute_tools_dispatch(self):
        """Tests that the agent correctly dispatches tool calls to the sandbox."""
        self.agent.tool_map["test_tool"] = MagicMock(return_value="ToolSuccess")
        
        tc = ToolCall(name="test_tool", args={"data": "val"}, id="call_123")
        
        results = self.agent._execute_tools([tc])
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].tool_response.result, "ToolSuccess")
        self.assertEqual(results[0].tool_response.id, "call_123")
        self.agent.tool_map["test_tool"].assert_called_with(data="val")

if __name__ == "__main__":
    unittest.main()

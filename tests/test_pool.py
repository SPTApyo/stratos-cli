import unittest
from unittest.mock import MagicMock, patch
from stratos.core.pool import AIPool, Blackboard

class TestAIPoolEnhanced(unittest.TestCase):
    def setUp(self):
        self.mock_sandbox = MagicMock()
        self.mock_logger = MagicMock()
        self.mock_logger.state = MagicMock()
        self.api_key = "fake-key"
        self.project_info = {"name": "P", "desc": "D"}
        
        # Patch AIAgent to return a distinct mock for each instance
        with patch('stratos.core.agent.AIAgent') as mock_agent_class:
            mock_agent_class.side_effect = lambda *args, **kwargs: MagicMock()
            self.pool = AIPool(self.mock_sandbox, self.mock_logger, self.api_key, self.project_info)
            self.pool.setup_default_pool()

    def test_sync_metrics(self):
        # Reset all agents to 0 tokens
        for agent in self.pool.agents.values():
            agent.total_input_tokens = 0
            agent.total_output_tokens = 0
            
        # Set dummy tokens for one agent
        self.pool.agents["CODER"].total_input_tokens = 500
        self.pool.agents["CODER"].total_output_tokens = 200
        
        self.pool._sync_metrics()
        self.mock_logger.update_tokens.assert_called_with(700)

    def test_request_specialist(self):
        with patch('stratos.core.agent.AIAgent'):
            res = self.pool.request_specialist("PYTEST_EXPERT", "Writes unit tests")
            self.assertIn("SUCCESS", res)
            self.assertIn("PYTEST_EXPERT", self.pool.specialists)

    @patch('stratos.core.agent.AIAgent.think_and_act', return_value="STATUS: READY")
    def test_broadcast_task_completion(self, mock_think):
        with patch.object(self.pool, '_run_agent', return_value="STATUS: READY"):
            res = self.pool.broadcast_task("Build a web app")
            self.assertEqual(res, "SUCCESS")

    def test_blackboard_team_log(self):
        self.pool.blackboard.post_discussion("CODER", "I'm working on it")
        ctx = self.pool.blackboard.get_full_context()
        self.assertIn("[CODER] I'm working on it", ctx)

if __name__ == "__main__":
    unittest.main()

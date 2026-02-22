import unittest
from stratos.utils.logger import ProjectLogger

class TestLogger(unittest.TestCase):
    def setUp(self):
        self.config = {"show_results": True, "max_logs": 10}
        self.logger = ProjectLogger(self.config)

    def test_log_basic(self):
        self.logger.log("CODER", "Writing code", style="info")
        self.assertEqual(len(self.logger.logs), 1)
        entry = self.logger.logs[0]
        self.assertEqual(entry["agent"], "CODER")
        self.assertEqual(entry["msg"], "Writing code")
        self.assertIn("INFO", entry["tag"])

    def test_log_auto_tag(self):
        self.logger.log("REVIEWER", "SUCCESS: All tests passed")
        entry = self.logger.logs[0]
        self.assertIn("OK", entry["tag"])
        self.assertEqual(entry["msg"], "All tests passed")

    def test_log_error_count(self):
        self.logger.log("SYSTEM", "ERROR: Something broke")
        self.assertEqual(self.logger.error_count, 1)

    def test_log_result_filtering(self):
        self.logger.show_results = False
        self.logger.log("CODER", "RESULT: code snippet")
        self.assertEqual(len(self.logger.logs), 0)

    def test_set_todo(self):
        todo_content = "- [x] Task 1\n- [/] Task 2\n- [ ] Task 3"
        self.logger.set_todo(todo_content)
        self.assertEqual(len(self.logger.todo_list), 3)
        self.assertEqual(self.logger.todo_list[0]["status"], "done")
        self.assertEqual(self.logger.todo_list[1]["status"], "active")
        self.assertEqual(self.logger.todo_list[2]["status"], "pending")

    def test_prompt_state(self):
        self.logger.start_prompt("MANAGER", "Confirm delete?", options=[{"label": "Yes"}, {"label": "No"}])
        self.assertEqual(self.logger.prompt_mode, 'menu')
        self.assertEqual(len(self.logger.prompt_options), 2)
        
        self.logger.stop_prompt()
        self.assertIsNone(self.logger.active_prompt)
        self.assertEqual(len(self.logger.prompt_options), 0)

if __name__ == "__main__":
    unittest.main()

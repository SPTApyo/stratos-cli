import unittest
import time
import threading
from stratos.utils.logger import LogParser, MissionState, ProjectLogger

class TestLoggerEnhanced(unittest.TestCase):
    def setUp(self):
        self.config = {"projects_path": "/tmp", "max_logs": 100, "show_thoughts": True}
        self.logger = ProjectLogger(self.config, "/tmp/proj")

    def test_log_parser_full(self):
        # Test all styles
        for style in LogParser.STYLE_MAP:
            tag, _ = LogParser.parse("A", "msg", style)
            self.assertEqual(tag, LogParser.STYLE_MAP[style])
        
        # Test unknown style
        tag, _ = LogParser.parse("A", "msg", "unknown")
        self.assertEqual(tag, "INFO")

    def test_prompt_priority(self):
        # SYSTEM prompt (priority 10)
        sid1 = self.logger.start_prompt("SYSTEM", "High Priority")
        self.assertEqual(sid1, 1)
        
        # AGENT prompt (priority 0) - should be rejected
        sid2 = self.logger.start_prompt("AGENT_CODER", "Low Priority")
        self.assertEqual(sid2, -1)
        self.assertEqual(self.logger.state.active_prompt["agent"], "SYSTEM")

    def test_pause_and_wait(self):
        self.logger.state.paused = True
        
        def resume_after_delay():
            time.sleep(0.2)
            self.logger.state.paused = False
            
        threading.Thread(target=resume_after_delay).start()
        
        start = time.time()
        self.logger.wait_if_paused()
        self.assertGreaterEqual(time.time() - start, 0.2)

    def test_set_todo_parsing(self):
        content = "[x] Task 1\n[/] Task 2\n[ ] Task 3"
        self.logger.set_todo(content)
        todo = self.logger.state.todo_list
        self.assertEqual(todo[0]["status"], "done")
        self.assertEqual(todo[1]["status"], "active")
        self.assertEqual(todo[2]["status"], "pending")

    def test_lifecycle_methods(self):
        self.logger.start_cycle(5)
        self.assertEqual(self.logger.state.current_cycle, 5)
        
        self.logger.agent_takeover("AGENT_TEST", "Role X")
        self.assertEqual(self.logger.state.current_agent, "AGENT_TEST")
        
        self.logger.update_spinner("Thinking", "Deep thoughts")
        self.assertEqual(self.logger.state.current_thought, "Deep thoughts")

if __name__ == "__main__":
    unittest.main()

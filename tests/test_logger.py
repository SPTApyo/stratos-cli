import unittest
from stratos.utils.logger import LogParser, MissionState, ProjectLogger

class TestLoggerCore(unittest.TestCase):
    def test_log_parser_tags(self):
        # Test standard mapping
        tag, msg = LogParser.parse("AGENT", "Doing something", "exec")
        self.assertEqual(tag, "EXEC")
        
        # Test inline priority tags
        tag, msg = LogParser.parse("AGENT", "SUCCESS: Task finished", "info")
        self.assertEqual(tag, "OK")
        self.assertEqual(msg, "Task finished")
        
        tag, msg = LogParser.parse("AGENT", "ERROR: Something failed", "info")
        self.assertEqual(tag, "ERR")
        
    def test_log_parser_sanitization(self):
        # Test newline removal and multi-space compression
        raw = "Line 1\nLine 2    with spaces"
        _, msg = LogParser.parse("AGENT", raw, "info")
        self.assertEqual(msg, "Line 1 Line 2 with spaces")

    def test_mission_state_initialization(self):
        config = {"projects_path": "/tmp"}
        state = MissionState(config, "/tmp/project")
        self.assertEqual(state.project_path, "/tmp/project")
        self.assertFalse(state.paused)
        self.assertEqual(len(state.logs), 0)

    def test_project_logger_error_tracking(self):
        config = {"max_logs": 10}
        logger = ProjectLogger(config, "/tmp")
        
        logger.log("SYSTEM", "Info message", "info")
        self.assertEqual(logger.state.error_count, 0)
        
        logger.log("SYSTEM", "Fatal error", "error")
        self.assertEqual(logger.state.error_count, 1)
        self.assertEqual(len(logger.state.logs), 2)

if __name__ == "__main__":
    unittest.main()

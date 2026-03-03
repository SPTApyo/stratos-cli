import unittest
import threading
from stratos.core.io.approval_manager import ApprovalManager

class MockLogger:
    def __init__(self):
        self.active_prompt = {"sid": 1}
        self.prompt_input = ""
        self.prompt_ready = threading.Event()

class TestApprovalManagerDeep(unittest.TestCase):
    def test_request_approval_denied_with_reason(self):
        logger = MockLogger()
        mgr = ApprovalManager(logger)
        
        logger.prompt_input = "Don't use rm"
        logger.prompt_ready.set()
        
        allowed, reason = mgr.request_approval("AGENT", "rm file.txt")
        self.assertFalse(allowed)
        self.assertEqual(reason, "Don't use rm")

    def test_confirm_helper(self):
        logger = MockLogger()
        mgr = ApprovalManager(logger)
        logger.prompt_input = "y"
        logger.prompt_ready.set()
        self.assertTrue(mgr.confirm("Action"))

if __name__ == "__main__":
    unittest.main()

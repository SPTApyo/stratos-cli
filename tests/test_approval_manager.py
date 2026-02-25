import unittest
import threading
from stratos.core.io.approval_manager import ApprovalManager

class MockLogger:
    def __init__(self):
        self.active_prompt = {"sid": 1}
        self.prompt_input = ""
        self.prompt_ready = threading.Event()

class TestApprovalManager(unittest.TestCase):
    def test_auto_approve(self):
        manager = ApprovalManager(None)
        manager.auto_approve = True
        allowed, msg = manager.request_approval("AGENT", "ls -la")
        self.assertTrue(allowed)
        self.assertIn("Auto-approved", msg)

    def test_manual_approval_yes(self):
        logger = MockLogger()
        manager = ApprovalManager(logger)
        
        # Simulate user typing 'y' in another thread/loop
        logger.prompt_input = "y"
        logger.prompt_ready.set()
        
        allowed, _ = manager.request_approval("AGENT", "ls")
        self.assertTrue(allowed)

    def test_manual_approval_no(self):
        logger = MockLogger()
        manager = ApprovalManager(logger)
        
        logger.prompt_input = "n"
        logger.prompt_ready.set()
        
        allowed, msg = manager.request_approval("AGENT", "rm -rf /")
        self.assertFalse(allowed)
        self.assertIn("User denied", msg)

if __name__ == "__main__":
    unittest.main()

import time

class ApprovalManager:
    """Manages the human validation and interaction logic, decoupling it from system logic."""

    def __init__(self, logger):
        self.logger = logger
        self.auto_approve = False

    def ask(self, question: str) -> str:
        """Prompts the user for a textual answer."""
        if hasattr(self.logger, 'prompt_ready'):
            sid = self.logger.active_prompt.get('sid')
            while True:
                self.logger.prompt_ready.wait()
                current_prompt = self.logger.active_prompt
                if current_prompt and current_prompt.get('sid') == sid:
                    return self.logger.prompt_input
                else:
                    self.logger.prompt_ready.clear()
        return ""

    def confirm(self, action: str) -> bool:
        """Prompts the user for a Yes/No confirmation."""
        res = self.ask(f"CONFIRMATION: {action}")
        return res.strip().lower() == 'y'

    def request_approval(self, agent_name: str, command: str) -> tuple[bool, str]:
        """Requests human approval for a specific command execution."""
        if self.auto_approve:
            return True, "Auto-approved by user mode."

        if hasattr(self.logger, 'prompt_ready'):
            sid = self.logger.active_prompt.get('sid')
            while True:
                self.logger.prompt_ready.wait()
                current_prompt = self.logger.active_prompt
                if current_prompt and current_prompt.get('sid') == sid:
                    answer = self.logger.prompt_input.strip()
                    if answer.lower() == 'y': return True, command
                    elif answer.lower() == 'n': return False, "User denied."
                    else:
                        if not answer: return False, "User denied (empty order)."
                        return False, answer
                else:
                    self.logger.prompt_ready.clear()
                    
        return False, "User denied (No UI available)."

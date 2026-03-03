import subprocess
import sys
import re
from pathlib import Path

class ShellManager:
    """Handles execution of system commands, Git operations, and dependency management."""
    
    DANGEROUS_PATTERNS = [
        r"rm\s+-rf\s+/", r"rm\s+-rf\s+~", r"rm\s+-rf\s+\.\.",
        r"mkfs", r"dd\s+if=", r":\(\)\{ :\|:& \};:",
        r">\s+/dev/sd", r">\s+/dev/nvme", r"chmod\s+777\s+/",
        r"chown\s+ root:root", r"shutdown", r"reboot"
    ]

    def __init__(self, root_dir, logger=None):
        self.root_dir = Path(root_dir).resolve()
        self.logger = logger

    def validate_command(self, command: str):
        """Checks for dangerous command patterns."""
        cmd = command.strip()
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, cmd):
                raise PermissionError(f"DANGEROUS COMMAND BLOCKED: '{cmd}' matches forbidden pattern '{pattern}'")

    def execute(self, command: str, timeout: int = 60) -> str:
        """Executes a bash command within the root directory."""
        if self.logger: self.logger.debug(f"[EXEC-START] {command} (in {self.root_dir})")
        try:
            self.validate_command(command)
            result = subprocess.run(
                command, shell=True, cwd=self.root_dir,
                capture_output=True, text=True, timeout=timeout
            )
            if self.logger: self.logger.debug(f"[EXEC-SUCCESS] Return Code: {result.returncode}")
            return f"CODE_{result.returncode}\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        except subprocess.TimeoutExpired:
            if self.logger: self.logger.debug("[EXEC-TIMEOUT] Command timed out.")
            return "ERROR: Command timed out."
        except Exception as e:
            if self.logger: self.logger.debug(f"[EXEC-CRASH] {str(e)}")
            return f"CRASH: {str(e)}"

    def git_init(self) -> str:
        """Initializes a Git repository with standard AI config."""
        return self.execute("git init && git config user.name 'AI' && git config user.email 'ai@factory'")

    def git_commit(self, message: str) -> str:
        """Adds all changes and commits with the given message."""
        clean_msg = message.replace("'", "")
        return self.execute(f"git add . && git commit -m '{clean_msg}'")

    def install_dependencies(self) -> str:
        """Installs Python dependencies from requirements.txt."""
        req = self.root_dir / "requirements.txt"
        if not req.exists():
            return "ERROR: requirements.txt missing."
        return self.execute(f"{sys.executable} -m pip install -r requirements.txt")

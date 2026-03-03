import os
from pathlib import Path
from stratos.core.io.file_manager import FileManager
from stratos.core.io.shell_manager import ShellManager
from stratos.core.io.approval_manager import ApprovalManager
from stratos.core.io.network_manager import NetworkManager

class Sandbox:
    """
    Coordinator class for all IO and system operations.
    Refactored for Clean Code: delegates responsibilities to specialized managers.
    """
    
    def __init__(self, root_dir):
        self.root_dir = Path(root_dir).resolve()
        if not self.root_dir.exists():
            self.root_dir.mkdir(parents=True)
            
        self.live_instance = None
        self._logger_instance = None
        self.ui_active_event = None

        self.files = FileManager(self.root_dir)
        self.shell = ShellManager(self.root_dir)
        self.approval = ApprovalManager(None)
        self.network = NetworkManager()

    @property
    def logger_instance(self):
        return self._logger_instance

    @logger_instance.setter
    def logger_instance(self, value):
        self._logger_instance = value
        self.files.logger = value
        self.shell.logger = value
        self.approval.logger = value
        self.network.logger = value

    @property
    def auto_approve(self):
        return self.approval.auto_approve

    @auto_approve.setter
    def auto_approve(self, value):
        self.approval.auto_approve = value


    def write_file(self, path: str, content: str) -> str:
        if self.logger_instance: self.logger_instance.debug(f"[FILE-WRITE] {path}")
        return self.files.write(path, content)

    def read_file(self, path: str, start_line: int = None, end_line: int = None) -> str:
        if self.logger_instance: self.logger_instance.debug(f"[FILE-READ] {path}")
        return self.files.read(path, start_line, end_line)

    def glob_search(self, pattern: str) -> list[str]:
        return self.files.glob(pattern)

    def grep_search(self, pattern: str, path: str = ".") -> str:
        return self.files.grep(pattern, path)

    def smart_replace(self, path: str, old_text: str, new_text: str) -> str:
        if self.logger_instance: self.logger_instance.debug(f"[SMART-REPLACE] {path}")
        return self.files.replace(path, old_text, new_text)


    def execute_command(self, command: str) -> str:
        if self.logger_instance: self.logger_instance.debug(f"[EXEC] {command}")
        return self.shell.execute(command)

    def git_init(self) -> str:
        return self.shell.git_init()

    def git_commit(self, message: str) -> str:
        return self.shell.git_commit(message)

    def install_dependencies(self) -> str:
        return self.shell.install_dependencies()


    def ask_user(self, question: str) -> str:
        return self.approval.ask(question)

    def request_confirmation(self, action: str) -> bool:
        return self.approval.confirm(action)

    def request_command_approval(self, agent_name: str, command: str) -> tuple[bool, str]:
        return self.approval.request_approval(agent_name, command)


    def web_fetch(self, url: str) -> str:
        return self.network.fetch(url)

    def search_web(self, query: str) -> str:
        return self.network.search(query)


    def update_todo_list(self, todo_content: str) -> str:
        """Updates the global team TODO_LIST (Logic placeholder)."""
        return "SUCCESS: TODO_LIST updated."

    def get_structure_tree(self) -> str:
        """Returns the project structure as a tree."""
        tree = []
        for root, dirs, files in os.walk(self.root_dir):
            if ".git" in root: continue
            rel = Path(root).relative_to(self.root_dir)
            indent = "  " * len(rel.parts)
            tree.append(f"{indent}{os.path.basename(root) or '.'}/")
            for f in files:
                tree.append(f"  {indent}{f}")
        return "\n".join(tree)

    def get_snapshot(self) -> dict:
        """Captures all file contents."""
        snap = {}
        for p in self.root_dir.rglob("*"):
            if p.is_file() and ".git" not in p.parts:
                try: snap[str(p.relative_to(self.root_dir))] = p.read_text(encoding="utf-8")
                except: pass
        return snap

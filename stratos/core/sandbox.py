import os
import shutil
import subprocess
import sys
import fnmatch
import json
from pathlib import Path
from rich.prompt import Prompt, Confirm
try:
    from duckduckgo_search import DDGS
    HAS_DDG = True
except ImportError:
    HAS_DDG = False

class Sandbox:
    def __init__(self, root_dir):
        """Initializes the sandbox."""
        self.root_dir = Path(root_dir).resolve()
        if not self.root_dir.exists():
            self.root_dir.mkdir(parents=True)
        self.live_instance = None
        self.logger_instance = None
        self.ui_active_event = None # threading.Event from engine
        self.auto_approve = False # Toggle via UI to skip confirmations

    def _safe_path(self, path):
        target_path = Path(self.root_dir / path).resolve()
        if not str(target_path).startswith(str(self.root_dir)):
            raise PermissionError(f"RESTRICTED: {path} is outside sandbox.")
        if target_path.is_symlink() and not str(target_path.readlink().resolve()).startswith(str(self.root_dir)):
            raise PermissionError(f"RESTRICTED: Symlink {path} points outside sandbox.")
        return target_path

    # --- FILES & SEARCH ---

    def write_file(self, path: str, content: str) -> str:
        """Writes content to a file. Overwrites if exists."""
        if self.logger_instance: self.logger_instance.debug(f"[FILE-WRITE] {path} ({len(content)} chars)")
        try:
            target = self._safe_path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                f.write(content)
            return f"SUCCESS: {path} written."
        except Exception as e:
            if self.logger_instance: self.logger_instance.debug(f"[FILE-WRITE-ERR] {str(e)}")
            return f"ERROR: {str(e)}"

    def read_file(self, path: str, start_line: int = None, end_line: int = None) -> str:
        """Reads a file's content. Supports chunking via start_line and end_line."""
        if self.logger_instance: self.logger_instance.debug(f"[FILE-READ] {path} ({start_line}-{end_line})")
        target = self._safe_path(path)
        if not target.exists(): 
            if self.logger_instance: self.logger_instance.debug(f"[FILE-READ-ERR] Not found: {path}")
            return f"ERROR: {path} not found."
        try:
            lines = target.read_text(encoding="utf-8").splitlines()
            if start_line is not None and end_line is not None:
                start = max(0, int(start_line) - 1)
                end = min(len(lines), int(end_line))
                lines = lines[start:end]
            return "\n".join(lines)
        except Exception as e:
            if self.logger_instance: self.logger_instance.debug(f"[FILE-READ-ERR] {str(e)}")
            return f"ERROR: {str(e)}"

    def glob_search(self, pattern: str) -> list[str]:
        """Finds files matching a glob pattern (e.g., '**/*.py')."""
        files = []
        for p in self.root_dir.rglob(pattern):
            if p.is_file() and ".git" not in p.parts:
                files.append(str(p.relative_to(self.root_dir)))
        return files

    def grep_search(self, pattern: str, path: str = ".") -> str:
        """Searches for a regex pattern in files (cross-platform)."""
        import re
        target = self._safe_path(path)
        try:
            regex = re.compile(pattern)
        except re.error as e:
            return f"ERROR: Invalid regex pattern - {str(e)}"
        
        results = []
        search_paths = [target] if target.is_file() else target.rglob("*")
        
        for p in search_paths:
            if p.is_file() and ".git" not in p.parts:
                try:
                    lines = p.read_text(encoding="utf-8").splitlines()
                    for i, line in enumerate(lines):
                        if regex.search(line):
                            rel_path = p.relative_to(self.root_dir)
                            results.append(f"{rel_path}:{i+1}:{line.strip()}")
                except UnicodeDecodeError:
                    pass # Skip binary files
        return "\n".join(results) if results else "No matches found."

    def smart_replace(self, path: str, old_text: str, new_text: str) -> str:
        """Replaces exact text within a file (like a surgical update)."""
        if self.logger_instance: self.logger_instance.debug(f"[SMART-REPLACE] {path}")
        try:
            target = self._safe_path(path)
            if not target.exists(): return f"ERROR: {path} not found."
            content = target.read_text(encoding="utf-8")
            if old_text not in content:
                if self.logger_instance: self.logger_instance.debug(f"[REPLACE-FAIL] Old text not found:\n{old_text[:100]}")
                return f"ERROR: 'old_text' not found in {path}."
            new_content = content.replace(old_text, new_text)
            target.write_text(new_content, encoding="utf-8")
            return f"SUCCESS: {path} updated."
        except Exception as e:
            if self.logger_instance: self.logger_instance.debug(f"[REPLACE-ERR] {str(e)}")
            return f"ERROR: {str(e)}"

    # --- SYSTEM & NETWORK ---

    def _validate_command_safety(self, command: str) -> None:
        """Checks for dangerous command patterns."""
        import re
        cmd = command.strip()
        
        # Blacklist of absolute destructive commands
        dangerous_patterns = [
            r"rm\s+-rf\s+/",       # rm -rf /
            r"rm\s+-rf\s+~",       # rm -rf ~
            r"rm\s+-rf\s+\.\.",    # rm -rf ..
            r"mkfs",               # disk formatting
            r"dd\s+if=",           # disk writing
            r":\(\)\{ :\|:& \};:", # fork bomb
            r">\s+/dev/sd",        # writing to raw device
            r">\s+/dev/nvme",      # writing to raw device
            r"chmod\s+777\s+/",    # system-wide permission change
            r"chown\s+ root:root", # root ownership change
            r"shutdown", r"reboot", r"init\s+0", r"init\s+6"
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, cmd):
                raise PermissionError(f"DANGEROUS COMMAND BLOCKED: '{cmd}' matches forbidden pattern '{pattern}'")

        # Prevent leaving the sandbox via cd
        # Note: This is a basic check. 'cd /' effects are limited because subprocess spawns a new shell,
        # but coupled with '&& rm' it could be bad.
        if "cd /" in cmd or "cd ~" in cmd or "cd .." in cmd:
             if self.logger_instance: self.logger_instance.warning(f"SUSPICIOUS NAVIGATION DETECTED in command: {cmd}")

    def execute_command(self, command: str) -> str:
        """Executes a bash command. Supports manual override/confirmation if needed."""
        if self.logger_instance:
            self.logger_instance.debug(f"[EXEC-START] {command} (in {self.root_dir})")
            
        try:
            # 1. Safety Check
            self._validate_command_safety(command)
            
            # 2. Execution
            result = subprocess.run(
                command, shell=True, cwd=self.root_dir,
                capture_output=True, text=True, timeout=60
            )
            
            output = f"CODE_{result.returncode}\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
            
            if self.logger_instance:
                if result.returncode == 0:
                    self.logger_instance.debug(f"[EXEC-SUCCESS] Return Code: 0")
                else:
                    self.logger_instance.debug(f"[EXEC-FAIL] Return Code: {result.returncode}\nSTDERR: {result.stderr[:200]}...")
            
            return output
        except Exception as e:
            if self.logger_instance:
                self.logger_instance.debug(f"[EXEC-CRASH] {str(e)}")
            return f"CRASH: {str(e)}"

    def request_command_approval(self, agent_name, command) -> tuple[bool, str]:
        """Specific UI logic for command approval. Returns (is_allowed, modified_command_or_order)."""
        if self.auto_approve:
            if self.logger_instance: self.logger_instance.debug(f"[AUTO-APPROVE] {command}")
            return True, "Auto-approved by user mode."

        if self.logger_instance and hasattr(self.logger_instance, 'prompt_ready'):
            self.logger_instance.prompt_ready.wait()
            answer = self.logger_instance.prompt_input.strip()
            
            if answer.lower() == 'y':
                return True, command
            elif answer.lower() == 'n':
                return False, "User denied."
            else:
                if not answer:
                    return False, "User denied (empty order)."
                # Anything else is treated as a specific order/message
                return False, answer
                
        # Fallback if logger is not properly configured
        if self.ui_active_event: self.ui_active_event.clear()
        if self.live_instance: self.live_instance.stop()
        if self.logger_instance: self.logger_instance.print_current_frame()
        choice = Prompt.ask("\n[bold yellow]› ACTION[/] ([white]y[/]:yes, [white]n[/]:no, [white]o[/]:order)", choices=["y", "n", "o"], default="y", show_choices=False)
        allowed = False
        final_cmd = command
        if choice == "y": allowed = True
        elif choice == "o":
            final_cmd = Prompt.ask("[bold cyan]› SPECIFIC ORDER[/]")
            allowed = False 
        if self.live_instance: self.live_instance.start()
        if self.ui_active_event: self.ui_active_event.set()
        return allowed, final_cmd

    def web_fetch(self, url: str) -> str:
        """Fetches the content of a URL (HTML/Text)."""
        cmd = f"curl -L -s '{url}'"
        return self.execute_command(cmd)

    def search_web(self, query: str) -> str:
        """Searches the web for information using DuckDuckGo."""
        if self.logger_instance: self.logger_instance.debug(f"[WEB-SEARCH] Query: {query}")
        
        if not HAS_DDG:
            return "ERROR: 'duckduckgo-search' library is missing. Install it with 'pip install duckduckgo-search' to use this feature."
            
        try:
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=5):
                    results.append(r)
            
            if not results:
                return "No results found."
                
            formatted = f"SEARCH RESULTS for '{query}':\n\n"
            for i, r in enumerate(results, 1):
                formatted += f"Result #{i}:\n"
                formatted += f"Title: {r.get('title', 'N/A')}\n"
                formatted += f"URL: {r.get('href', 'N/A')}\n"
                formatted += f"Snippet: {r.get('body', 'N/A')}\n"
                formatted += "-" * 40 + "\n"
                
            return formatted
        except Exception as e:
            if self.logger_instance: self.logger_instance.debug(f"[WEB-SEARCH-ERR] {str(e)}")
            return f"ERROR: Search failed - {str(e)}"

    def install_dependencies(self) -> str:
        """Installs Python dependencies from requirements.txt."""
        req = self.root_dir / "requirements.txt"
        if not req.exists(): 
            if self.logger_instance: self.logger_instance.debug("[PIP-INSTALL] requirements.txt not found.")
            return "ERROR: requirements.txt missing."
        if self.logger_instance: self.logger_instance.debug("[PIP-INSTALL] Installing from requirements.txt")
        return self.execute_command(f"{sys.executable} -m pip install -r requirements.txt")

    # --- HUMAN INTERACTION ---

    def ask_user(self, question: str) -> str:
        """Asks the human user a question and returns the answer."""
        # We don't stop Live. We just wait for the engine to fill prompt_input
        if self.logger_instance and hasattr(self.logger_instance, 'prompt_ready'):
            self.logger_instance.prompt_ready.wait()
            answer = self.logger_instance.prompt_input
            return answer
        
        # Fallback if logger is not properly configured
        if self.ui_active_event: self.ui_active_event.clear()
        if self.live_instance: self.live_instance.stop()
        if self.logger_instance: self.logger_instance.print_current_frame()
        answer = Prompt.ask("\n[bold yellow]› YOUR ANSWER[/]")
        if self.live_instance: self.live_instance.start()
        if self.ui_active_event: self.ui_active_event.set()
        return answer

    def request_confirmation(self, action: str) -> bool:
        """Requests a Yes/No confirmation from the user."""
        if self.logger_instance and hasattr(self.logger_instance, 'prompt_ready'):
            self.logger_instance.prompt_ready.wait()
            answer = self.logger_instance.prompt_input.strip().lower()
            return answer == 'y'
            
        # Fallback if logger is not properly configured
        if self.ui_active_event: self.ui_active_event.clear()
        if self.live_instance: self.live_instance.stop()
        if self.logger_instance: self.logger_instance.print_current_frame()
        res = Confirm.ask(f"\n[bold yellow]› ALLOW ACTION?[/]")
        if self.live_instance: self.live_instance.start()
        if self.ui_active_event: self.ui_active_event.set()
        return res

    # --- GIT ---

    def git_init(self) -> str:
        """Initializes a Git repository."""
        if self.logger_instance: self.logger_instance.debug(f"[GIT-INIT] Initializing repo in {self.root_dir}")
        return self.execute_command("git init && git config user.name 'AI' && git config user.email 'ai@factory'")

    def git_commit(self, message: str) -> str:
        """Commits all changes to Git."""
        clean_msg = message.replace("'", "")
        if self.logger_instance: self.logger_instance.debug(f"[GIT-COMMIT] Message: {clean_msg}")
        return self.execute_command(f"git add . && git commit -m '{clean_msg}'")

    # --- UTILITIES ---

    def update_todo_list(self, todo_content: str) -> str:
        """Updates the global team TODO_LIST."""
        return f"SUCCESS: TODO_LIST updated."

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

import os
import re
from pathlib import Path

class FileManager:
    """Handles all file-system operations within a restricted root directory."""
    
    def __init__(self, root_dir, logger=None):
        self.root_dir = Path(root_dir).resolve()
        if not self.root_dir.exists():
            self.root_dir.mkdir(parents=True)
        self.logger = logger

    def _safe_path(self, path):
        """Validates that a path is within the allowed root directory."""
        target_path = Path(self.root_dir / path).resolve()
        if not str(target_path).startswith(str(self.root_dir)):
            raise PermissionError(f"RESTRICTED: {path} is outside sandbox.")
        if target_path.is_symlink():
            link_target = target_path.readlink().resolve()
            if not str(link_target).startswith(str(self.root_dir)):
                raise PermissionError(f"RESTRICTED: Symlink {path} points outside sandbox.")
        return target_path

    def write(self, path: str, content: str) -> str:
        """Writes content to a file. Overwrites if exists."""
        try:
            target = self._safe_path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return f"SUCCESS: {path} written."
        except Exception as e:
            return f"ERROR: {str(e)}"

    def read(self, path: str, start_line: int = None, end_line: int = None) -> str:
        """Reads a file's content. Supports line-range chunking."""
        try:
            target = self._safe_path(path)
            if not target.exists(): return f"ERROR: {path} not found."
            
            lines = target.read_text(encoding="utf-8").splitlines()
            if start_line is not None and end_line is not None:
                start = max(0, int(start_line) - 1)
                end = min(len(lines), int(end_line))
                lines = lines[start:end]
            return "\n".join(lines)
        except Exception as e:
            return f"ERROR: {str(e)}"

    def glob(self, pattern: str) -> list[str]:
        """Finds files matching a glob pattern."""
        files = []
        for p in self.root_dir.rglob(pattern):
            if p.is_file() and ".git" not in p.parts:
                files.append(str(p.relative_to(self.root_dir)))
        return sorted(files)

    def grep(self, pattern: str, path: str = ".") -> str:
        """Searches for a regex pattern in files."""
        try:
            regex = re.compile(pattern)
            target = self._safe_path(path)
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
                except (UnicodeDecodeError, PermissionError):
                    continue 
        return "\n".join(results) if results else "No matches found."

    def replace(self, path: str, old_text: str, new_text: str) -> str:
        """Replaces exact text within a file."""
        try:
            target = self._safe_path(path)
            if not target.exists(): return f"ERROR: {path} not found."
            content = target.read_text(encoding="utf-8")
            if old_text not in content:
                return f"ERROR: 'old_text' not found in {path}."
            new_content = content.replace(old_text, new_text)
            target.write_text(new_content, encoding="utf-8")
            return f"SUCCESS: {path} updated."
        except Exception as e:
            return f"ERROR: {str(e)}"

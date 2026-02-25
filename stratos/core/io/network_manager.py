import subprocess
try:
    from duckduckgo_search import DDGS
    HAS_DDG = True
except ImportError:
    HAS_DDG = False

class NetworkManager:
    """Handles external network operations like web fetching and searching."""

    def __init__(self, logger=None):
        self.logger = logger

    def fetch(self, url: str) -> str:
        """Fetches the content of a URL."""
        cmd = f"curl -L -s '{url}'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return f"CODE_{result.returncode}\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"

    def search(self, query: str) -> str:
        """Searches the web for information using DuckDuckGo."""
        if not HAS_DDG:
            return "ERROR: 'duckduckgo-search' library missing."
        
        try:
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=5):
                    results.append(r)
            
            if not results: return "No results found."
                
            formatted = f"SEARCH RESULTS for '{query}':\n\n"
            for i, r in enumerate(results, 1):
                formatted += f"Result #{i}:\nTitle: {r.get('title')}\nURL: {r.get('href')}\nSnippet: {r.get('body')}\n---\n"
            
            return formatted
        except Exception as e:
            return f"ERROR: Search failed - {str(e)}"

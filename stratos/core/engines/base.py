from abc import ABC, abstractmethod
from typing import List, Dict, Any, Union, Optional

from .protocol import Message, MessagePart, ToolDefinition

class AIEngine(ABC):
    """Abstract base class for AI models (Gemini, Claude, GPT, etc.)."""
    
    def __init__(self, api_key: str, model_id: str):
        self.api_key = api_key
        self.model_id = model_id
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    @abstractmethod
    def generate_content(self, messages: List[Message], tools: List[ToolDefinition], turn_count: int, logger: Any) -> Union[List[MessagePart], str]:
        """Core method to generate model response and handle streaming/tool calls."""
        pass

    @abstractmethod
    def get_costs(self) -> float:
        """Returns the cost calculation for the current session."""
        pass

    @abstractmethod
    def list_models(self) -> List[str]:
        """Returns a list of available model IDs from the provider."""
        pass

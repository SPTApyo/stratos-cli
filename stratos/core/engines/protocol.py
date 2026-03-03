from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union

@dataclass
class ToolCall:
    """Generic representation of a model requesting a tool execution."""
    name: str
    args: Dict[str, Any]
    id: Optional[str] = None

@dataclass
class ToolResponse:
    """Generic representation of a tool execution result."""
    name: str
    result: Any
    id: Optional[str] = None

@dataclass
class MessagePart:
    """A single part of a message (text, call, or response)."""
    text: Optional[str] = None
    tool_call: Optional[ToolCall] = None
    tool_response: Optional[ToolResponse] = None

@dataclass
class Message:
    """A complete message exchanged between Agent and Engine."""
    role: str
    parts: List[MessagePart] = field(default_factory=list)

@dataclass
class ToolDefinition:
    """Generic definition of an available tool."""
    name: str
    description: str
    parameters: Dict[str, Any]

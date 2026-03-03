import time
from typing import List, Any, Union, Dict
from .base import AIEngine
from .protocol import Message, MessagePart, ToolCall, ToolResponse, ToolDefinition

class ClaudeEngine(AIEngine):
    """Implementation of Claude models via Anthropic SDK."""
    
    def __init__(self, api_key: str, model_id: str):
        super().__init__(api_key, model_id)
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key)
        except ImportError:
            self.client = None

    def generate_content(self, messages: List[Message], tools: List[ToolDefinition], turn_count: int, logger: Any) -> Union[List[MessagePart], str]:
        """Translates Protocol to Anthropic format and back with robust error handling."""
        if not self.client:
            return "ERROR: Anthropic SDK not found. Please run: pip install anthropic"
            
        claude_messages = self._convert_messages(messages)
        claude_tools = self._convert_tools(tools)
        
        retry_count = 0
        while retry_count < 3:
            try:
                logger.wait_if_paused()
                with self.client.messages.stream(
                    model=self.model_id,
                    max_tokens=4096,
                    messages=claude_messages,
                    tools=claude_tools if claude_tools else None,
                ) as stream:
                    full_text = ""
                    for event in stream:
                        if event.type == "content_block_delta":
                            if event.delta.type == "text_delta":
                                full_text += event.delta.text
                                logger.update_spinner(f"Claude Thinking (turn {turn_count})", thought=full_text)
                        elif event.type == "message_delta":
                            self.total_input_tokens += getattr(event.usage, 'input_tokens', 0)
                            self.total_output_tokens += getattr(event.usage, 'output_tokens', 0)

                    final_msg = stream.get_final_message()
                    
                    response_parts = []
                    if full_text:
                        response_parts.append(MessagePart(text=full_text))
                    
                    for block in final_msg.content:
                        if block.type == "tool_use":
                            response_parts.append(MessagePart(
                                tool_call=ToolCall(id=block.id, name=block.name, args=block.input)
                            ))
                    return response_parts

            except Exception as e:
                err_msg = str(e).lower()
                retry_count += 1
                
                if "429" in err_msg or "rate_limit" in err_msg or "overloaded" in err_msg:
                    logger.update_spinner(f"Claude Overloaded. Retrying ({retry_count}/3)...")
                    time.sleep(2 ** retry_count)
                    continue
                
                if "max_tokens" in err_msg or "context_length" in err_msg:
                    return f"ERROR (Claude): Context window exceeded for {self.model_id}."
                
                return f"ERROR (Claude): {str(e)}"
                
        return "ERROR (Claude): API_TIMEOUT after multiple retries."

    def _convert_messages(self, messages: List[Message]) -> List[Dict]:
        """Protocol Message -> Anthropic dict."""
        claude_msgs = []
        for m in messages:
            role = "user" if m.role == "user" else "assistant"
            content = []
            for p in m.parts:
                if p.text: 
                    content.append({"type": "text", "text": p.text})
                if p.tool_call: 
                    content.append({
                        "type": "tool_use", 
                        "id": p.tool_call.id, 
                        "name": p.tool_call.name, 
                        "input": p.tool_call.args
                    })
                if p.tool_response: 
                    content.append({
                        "type": "tool_result", 
                        "tool_use_id": p.tool_response.id, 
                        "content": str(p.tool_response.result)
                    })
            claude_msgs.append({"role": role, "content": content})
        return claude_msgs

    def _convert_tools(self, tools: List[ToolDefinition]) -> List[Dict]:
        """Protocol ToolDefinition -> Anthropic dict."""
        return [{"name": t.name, "description": t.description, "input_schema": t.parameters} for t in tools]

    def get_costs(self) -> float:
        return ((self.total_input_tokens / 1_000_000) * 3.0) + ((self.total_output_tokens / 1_000_000) * 15.0)

    def list_models(self) -> List[str]:
        return [
            "claude-3-7-sonnet-latest", "claude-3-5-sonnet-latest", 
            "claude-3-5-haiku-latest", "claude-3-opus-latest"
        ]

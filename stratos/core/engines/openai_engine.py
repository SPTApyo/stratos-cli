import time
import json
from typing import List, Any, Union, Dict
from .base import AIEngine
from .protocol import Message, MessagePart, ToolCall, ToolResponse, ToolDefinition

class OpenAIEngine(AIEngine):
    """Implementation of OpenAI models via OpenAI SDK."""
    
    def __init__(self, api_key: str, model_id: str):
        super().__init__(api_key, model_id)
        try:
            import openai
            self.client = openai.OpenAI(api_key=api_key)
        except ImportError:
            self.client = None

    def generate_content(self, messages: List[Message], tools: List[ToolDefinition], turn_count: int, logger: Any) -> Union[List[MessagePart], str]:
        """Translates Protocol to OpenAI format and back with robust error handling."""
        if not self.client:
            return "ERROR: OpenAI SDK not found. Please run: pip install openai"
            
        openai_messages = self._convert_messages(messages)
        openai_tools = self._convert_tools(tools)
        
        retry_count = 0
        while retry_count < 3:
            try:
                logger.wait_if_paused()
                stream = self.client.chat.completions.create(
                    model=self.model_id,
                    messages=openai_messages,
                    tools=openai_tools if openai_tools else None,
                    stream=True,
                    stream_options={"include_usage": True}
                )
                
                full_text = ""
                tool_calls_raw = {}
                
                for chunk in stream:
                    if not chunk.choices:
                        if hasattr(chunk, 'usage') and chunk.usage:
                            self.total_input_tokens += chunk.usage.prompt_tokens
                            self.total_output_tokens += chunk.usage.completion_tokens
                        continue
                    
                    delta = chunk.choices[0].delta
                    if delta.content:
                        full_text += delta.content
                        logger.update_spinner(f"OpenAI Thinking (turn {turn_count})", thought=full_text)
                    
                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            idx = tc.index
                            if idx not in tool_calls_raw:
                                tool_calls_raw[idx] = {"id": tc.id, "name": "", "args": ""}
                            if tc.id: tool_calls_raw[idx]["id"] = tc.id
                            if tc.function.name: tool_calls_raw[idx]["name"] = tc.function.name
                            if tc.function.arguments: tool_calls_raw[idx]["args"] += tc.function.arguments

                response_parts = []
                if full_text:
                    response_parts.append(MessagePart(text=full_text))
                
                for idx in sorted(tool_calls_raw.keys()):
                    tc = tool_calls_raw[idx]
                    try: args = json.loads(tc["args"]) if tc["args"] else {}
                    except: args = {}
                    response_parts.append(MessagePart(
                        tool_call=ToolCall(id=tc["id"], name=tc["name"], args=args)
                    ))
                return response_parts

            except Exception as e:
                err_msg = str(e).lower()
                retry_count += 1
                
                if "429" in err_msg or "rate_limit" in err_msg or "overloaded" in err_msg:
                    logger.update_spinner(f"OpenAI Rate Limited. Retrying ({retry_count}/3)...")
                    time.sleep(2 ** retry_count)
                    continue
                
                if "context_length_exceeded" in err_msg or "maximum context length" in err_msg:
                    return f"ERROR (OpenAI): Token limit reached for model {self.model_id}. Mission too large."
                
                return f"ERROR (OpenAI): {str(e)}"
                
        return "ERROR (OpenAI): API_TIMEOUT after multiple retries."

    def _convert_messages(self, messages: List[Message]) -> List[Dict]:
        """Protocol Message -> OpenAI dict."""
        openai_msgs = []
        for m in messages:
            role = "user" if m.role == "user" else "assistant"
            for p in m.parts:
                if p.text: openai_msgs.append({"role": role, "content": p.text})
                if p.tool_call:
                    openai_msgs.append({
                        "role": "assistant",
                        "tool_calls": [{
                            "id": p.tool_call.id,
                            "type": "function",
                            "function": {"name": p.tool_call.name, "arguments": json.dumps(p.tool_call.args)}
                        }]
                    })
                if p.tool_response:
                    openai_msgs.append({
                        "role": "tool",
                        "tool_call_id": p.tool_response.id,
                        "content": str(p.tool_response.result)
                    })
        return openai_msgs

    def _convert_tools(self, tools: List[ToolDefinition]) -> List[Dict]:
        """Protocol ToolDefinition -> OpenAI dict."""
        return [{"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.parameters}} for t in tools]

    def get_costs(self) -> float:
        return ((self.total_input_tokens / 1_000_000) * 2.50) + ((self.total_output_tokens / 1_000_000) * 10.0)

    def list_models(self) -> List[str]:
        return ["gpt-4o", "gpt-4o-mini", "o1", "o3-mini"]

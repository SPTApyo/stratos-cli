import time
from typing import List, Any, Union
from google import genai
from google.genai import types
from .base import AIEngine
from .protocol import Message, MessagePart, ToolCall, ToolResponse, ToolDefinition

class GeminiEngine(AIEngine):
    """Implementation of Gemini models via Google GenAI SDK."""
    
    def __init__(self, api_key: str, model_id: str):
        super().__init__(api_key, model_id)
        self.client = genai.Client(api_key=api_key)

    def generate_content(self, messages: List[Message], tools: List[ToolDefinition], turn_count: int, logger: Any) -> Union[List[MessagePart], str]:
        """Translates Protocol to Gemini and back."""
        gemini_messages = self._convert_messages(messages)
        gemini_tools = self._convert_tools(tools)
        
        retry_count = 0
        while retry_count < 3:
            try:
                logger.wait_if_paused()
                stream = self.client.models.generate_content_stream(
                    model=self.model_id, 
                    contents=gemini_messages, 
                    config=types.GenerateContentConfig(tools=[types.Tool(function_declarations=gemini_tools)])
                )
                
                accumulated_parts = []
                full_text = ""
                for chunk in stream:
                    if chunk.usage_metadata:
                        self.total_input_tokens += chunk.usage_metadata.prompt_token_count
                        self.total_output_tokens += chunk.usage_metadata.candidates_token_count
                    
                    if not chunk.candidates: continue
                    for part in chunk.candidates[0].content.parts:
                        if part.text:
                            full_text += part.text
                            logger.update_spinner(f"Thinking (turn {turn_count})", thought=full_text)
                        if part.function_call:
                            accumulated_parts.append(part)
                
                response_parts = []
                if full_text:
                    response_parts.append(MessagePart(text=full_text))
                
                for gp in accumulated_parts:
                    response_parts.append(MessagePart(
                        tool_call=ToolCall(name=gp.function_call.name, args=gp.function_call.args)
                    ))
                
                return response_parts
                
            except Exception as e:
                err_msg = str(e).lower()
                retry_count += 1
                
                if "429" in err_msg or "quota" in err_msg or "rate_limit" in err_msg:
                    logger.update_spinner(f"Gemini Rate Limited. Retrying ({retry_count}/3)...")
                    time.sleep(2 ** retry_count)
                    continue
                
                if "context" in err_msg or "token" in err_msg or "400" in err_msg:
                    return f"ERROR (Gemini): Context limit reached for {self.model_id}. Mission too large."
                
                return f"ERROR (Gemini): {str(e)}"
        return "ERROR: API_TIMEOUT"

    def _convert_messages(self, messages: List[Message]) -> List[types.Content]:
        """Protocol Message -> Google types.Content."""
        gemini_msgs = []
        for m in messages:
            parts = []
            for p in m.parts:
                if p.text: 
                    parts.append(types.Part(text=p.text))
                if p.tool_call: 
                    parts.append(types.Part(function_call=types.FunctionCall(name=p.tool_call.name, args=p.tool_call.args)))
                if p.tool_response: 
                    parts.append(types.Part(function_response=types.FunctionResponse(name=p.tool_response.name, response={"result": p.tool_response.result})))
            gemini_msgs.append(types.Content(role=m.role, parts=parts))
        return gemini_msgs

    def _convert_tools(self, tools: List[ToolDefinition]) -> List[types.FunctionDeclaration]:
        """Protocol ToolDefinition -> Google types.FunctionDeclaration."""
        return [types.FunctionDeclaration(name=t.name, description=t.description, parameters=t.parameters) for t in tools]

    def get_costs(self) -> float:
        return ((self.total_input_tokens / 1_000_000) * 0.10) + ((self.total_output_tokens / 1_000_000) * 0.40)

    def list_models(self) -> List[str]:
        models = self.client.models.list()
        blacklist = ["imagen", "veo", "speech", "tts", "stt", "whisper", "audio", "video", "image", "robotics", "compute", "aqa", "learnlm", "med-", "health"]
        return [m.name.replace("models/", "").lower() for m in models if "generateContent" in m.supported_actions and not any(term in m.name.lower() for term in blacklist)]

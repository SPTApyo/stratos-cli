from google import genai
from google.genai import types
import os
import time
from dotenv import load_dotenv

load_dotenv()

class AIAgent:
    """Refactored AI Agent following Clean Code principles: SRP and KISS."""
    
    def __init__(self, name, role, sandbox, logger, api_key, project_info, pool_callback=None, model_id='gemini-2.5-flash'):
        self.name = name
        self.role = role
        self.sandbox = sandbox
        self.logger = logger
        self.project_name = project_info['name']
        self.project_desc = project_info['desc']
        self.client = genai.Client(api_key=api_key)
        self.model_id = model_id
        self.pool_callback = pool_callback
        
        self.total_input_tokens = 0
        self.total_output_tokens = 0

        # Initialize tools
        self._setup_tool_map()
        self._setup_function_declarations()

    def _setup_tool_map(self):
        """Defines the core tool mapping with safety wrappers."""
        
        def ask_user_wrapper(question):
            self.logger.start_prompt(self.name, question)
            res = self.sandbox.ask_user(question)
            self.logger.stop_prompt()
            return res

        def confirm_wrapper(action):
            options = [{"label": "Yes", "value": "y"}, {"label": "No", "value": "n"}]
            self.logger.start_prompt(self.name, f"Confirm: {action}", details={"command": action}, options=options)
            res = self.sandbox.request_confirmation(action)
            self.logger.stop_prompt()
            return res

        def exec_wrapper(command):
            self.logger.debug(f"[REQUEST] {self.name}: {command}")
            options = [
                {"label": "Allow", "value": "y"},
                {"label": "Deny", "value": "n"},
                {"label": "Change", "value": "o", "require_text": True}
            ]
            self.logger.start_prompt(self.name, "Execute command?", details={"command": command}, options=options)
            allowed, result = self.sandbox.request_command_approval(self.name, command)
            self.logger.stop_prompt()
            
            if allowed: return self.sandbox.execute_command(command)
            return f"USER_DENIED: {result}"

        self.tool_map = {
            "write_file": self.sandbox.write_file,
            "read_file": self.sandbox.read_file,
            "smart_replace": self.sandbox.smart_replace,
            "glob_search": self.sandbox.glob_search,
            "grep_search": self.sandbox.grep_search,
            "execute_command": exec_wrapper,
            "search_web": self.sandbox.search_web,
            "web_fetch": self.sandbox.web_fetch,
            "ask_user": ask_user_wrapper,
            "request_confirmation": confirm_wrapper,
            "get_structure_tree": self.sandbox.get_structure_tree,
            "git_init": self.sandbox.git_init,
            "git_commit": self.sandbox.git_commit,
            "install_dependencies": self.sandbox.install_dependencies,
            "update_todo_list": self.sandbox.update_todo_list,
            "report_status": lambda m: self.logger.info(m) or "SUCCESS"
        }
        
        if self.pool_callback:
            self.tool_map["request_specialist"] = self.pool_callback

    def _setup_function_declarations(self):
        """Converts tool map to Gemini function declarations."""
        self.tools = []
        for tool_name in self.tool_map:
            self.tools.append(types.FunctionDeclaration(
                name=tool_name,
                description=self.tool_map[tool_name].__doc__ or "Execute action",
                parameters=self._get_tool_schema(tool_name)
            ))

    def _get_tool_schema(self, name):
        schemas = {
            "write_file": {"type": "OBJECT", "properties": {"path": {"type": "STRING"}, "content": {"type": "STRING"}}, "required": ["path", "content"]},
            "read_file": {"type": "OBJECT", "properties": {"path": {"type": "STRING"}, "start_line": {"type": "INTEGER"}, "end_line": {"type": "INTEGER"}}, "required": ["path"]},
            "smart_replace": {"type": "OBJECT", "properties": {"path": {"type": "STRING"}, "old_text": {"type": "STRING"}, "new_text": {"type": "STRING"}}, "required": ["path", "old_text", "new_text"]},
            "execute_command": {"type": "OBJECT", "properties": {"command": {"type": "STRING"}}, "required": ["command"]},
            "grep_search": {"type": "OBJECT", "properties": {"pattern": {"type": "STRING"}, "path": {"type": "STRING"}}, "required": ["pattern"]},
            "glob_search": {"type": "OBJECT", "properties": {"pattern": {"type": "STRING"}}, "required": ["pattern"]},
            "search_web": {"type": "OBJECT", "properties": {"query": {"type": "STRING"}}, "required": ["query"]},
            "web_fetch": {"type": "OBJECT", "properties": {"url": {"type": "STRING"}}, "required": ["url"]},
            "ask_user": {"type": "OBJECT", "properties": {"question": {"type": "STRING"}}, "required": ["question"]},
            "request_confirmation": {"type": "OBJECT", "properties": {"action": {"type": "STRING"}}, "required": ["action"]},
            "git_commit": {"type": "OBJECT", "properties": {"message": {"type": "STRING"}}, "required": ["message"]},
            "update_todo_list": {"type": "OBJECT", "properties": {"todo_content": {"type": "STRING"}}, "required": ["todo_content"]},
            "report_status": {"type": "OBJECT", "properties": {"message": {"type": "STRING"}}, "required": ["message"]},
            "request_specialist": {"type": "OBJECT", "properties": {"role_name": {"type": "STRING"}, "role_description": {"type": "STRING"}, "weight": {"type": "STRING", "enum": ["HEAVY", "MEDIUM", "LIGHT"]}}, "required": ["role_name", "role_description"]}
        }
        return schemas.get(name, {"type": "OBJECT", "properties": {}})

    def think_and_act(self, task, context=""):
        """Main execution loop for the agent."""
        self.logger.log(self.name, f"TASK: {task[:50]}...", style="agent")
        
        # 1. Prepare and Review Prompt
        full_prompt = self._prepare_prompt(task, context)
        full_prompt = self._review_prompt(full_prompt)
        if not full_prompt: return "TASK_ABORTED"

        messages = [types.Content(role="user", parts=[types.Part(text=full_prompt)])]
        
        # 2. Iterative reasoning loop
        turns = 0
        while turns < 25:
            self.logger.wait_if_paused()
            turns += 1
            
            # Call LLM
            response_parts = self._call_llm(messages, turns)
            if isinstance(response_parts, str): return response_parts # Error
            
            # Record response
            model_content = types.Content(role="model", parts=response_parts)
            messages.append(model_content)
            
            # Handle Text vs Tool calls
            function_calls = [p.function_call for p in response_parts if p.function_call]
            if not function_calls:
                text = "".join([p.text for p in response_parts if p.text])
                return text or "DONE"

            # Execute Tools
            tool_results = self._execute_tools(function_calls)
            messages.append(types.Content(role="user", parts=tool_results))
            
        return "ERROR: MAX_TURNS_REACHED"

    def _prepare_prompt(self, task, context):
        from stratos.assets import load_prompt
        global_p = load_prompt("global_mandate", project_name=self.project_name, project_desc=self.project_desc)
        perso_p = f"=== AGENT_PROFILE ===\nID: {self.name} | ROLE: {self.role}\n======================\n"
        return f"{global_p}\n{perso_p}\nSTATE:\n{context}\n\nTASK: {task}"

    def _review_prompt(self, prompt):
        """Allows human to review and edit the generated prompt."""
        options = [
            {"label": "Confirm & Send", "value": "y"},
            {"label": "Edit Prompt", "value": "e", "require_text": True},
            {"label": "Abort Task", "value": "n"}
        ]
        self.logger.start_prompt(self.name, "Reviewing system prompt...", details={"prompt_preview": prompt}, options=options)
        res = self.sandbox.ask_user("Reviewing prompt...")
        self.logger.stop_prompt()
        
        if res == "n": return None
        if res and res != "y": return res # Return modified prompt
        return prompt

    def _call_llm(self, messages, turn_count):
        """Handles the actual API communication with retry logic."""
        retry_count = 0
        while retry_count < 3:
            try:
                self.logger.wait_if_paused()
                stream = self.client.models.generate_content_stream(
                    model=self.model_id, 
                    contents=messages, 
                    config=types.GenerateContentConfig(tools=[types.Tool(function_declarations=self.tools)])
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
                            self.logger.update_spinner(f"Thinking (turn {turn_count})", thought=full_text)
                        if part.function_call:
                            accumulated_parts.append(part)
                
                if full_text and not accumulated_parts:
                    accumulated_parts.append(types.Part(text=full_text))
                return accumulated_parts
                
            except Exception as e:
                retry_count += 1
                if "429" in str(e) or "quota" in str(e).lower():
                    time.sleep(2 ** retry_count)
                else: return f"ERROR: {str(e)}"
        return "ERROR: API_TIMEOUT"

    def _execute_tools(self, function_calls):
        """Executes a list of function calls and returns formatted results."""
        results = []
        for fc in function_calls:
            args = fc.args or {}
            target = next(iter(args.values()), "") if args else ""
            self.logger.log(self.name, f"{fc.name} ({str(target)[:30]})", style="exec")
            
            try:
                if fc.name in self.tool_map:
                    res = self.tool_map[fc.name](**args)
                else:
                    res = "ERROR: Unknown tool"
            except Exception as e:
                res = f"ERROR: {str(e)}"
            
            if self.logger.state.show_results:
                self.logger.log(self.name, f"RESULT: {str(res)[:100]}", style="info")
            
            results.append(types.Part(function_response=types.FunctionResponse(name=fc.name, response={"result": res})))
        return results

    def get_costs(self):
        return ((self.total_input_tokens / 1_000_000) * 0.10) + ((self.total_output_tokens / 1_000_000) * 0.40)

from google import genai
from google.genai import types
import os
import platform
import datetime
import json
import time
from dotenv import load_dotenv

load_dotenv()

class AIAgent:
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

        # --- MANDATORY VALIDATION WRAPPERS ---
        
        def ask_user_wrapper(question):
            self.logger.start_prompt(self.name, question)
            res = self.sandbox.ask_user(question)
            self.logger.stop_prompt()
            return res

        def confirm_wrapper(action):
            options = [{"label": "Yes", "value": "y"}, {"label": "No", "value": "n"}]
            self.logger.start_prompt(self.name, f"Requesting confirmation for: {action}", details={"command": action}, options=options)
            res = self.sandbox.request_confirmation(action)
            self.logger.stop_prompt()
            return res

        def exec_wrapper(command):
            """Unified wrapper for ALL system commands to force human validation."""
            self.logger.debug(f"[AGENT-REQUEST] {self.name} wants to run: {command}")
            details = {"command": command, "dir": str(self.sandbox.root_dir)}
            options = [
                {"label": "Allow Execution", "value": "y"},
                {"label": "Deny Execution", "value": "n"},
                {"label": "Provide Specific Order", "value": "o", "require_text": True}
            ]
            self.logger.start_prompt(self.name, "Requesting command execution", details=details, options=options)
            allowed, result = self.sandbox.request_command_approval(self.name, command)
            self.logger.stop_prompt()
            
            if allowed:
                self.logger.debug(f"[USER-APPROVED] Command: {command}")
                return self.sandbox.execute_command(command)
            else:
                self.logger.debug(f"[USER-DENIED] Reason: {result}")
                return f"USER_DENIED: Execution blocked by human. Order/Reason: {result}"

        def git_init_wrapper():
            cmd = "git init"
            details = {"command": cmd, "dir": str(self.sandbox.root_dir)}
            options = [
                {"label": "Allow Git Init", "value": "y"},
                {"label": "Deny Git Init", "value": "n"},
                {"label": "Provide Specific Order", "value": "o", "require_text": True}
            ]
            self.logger.start_prompt(self.name, "Requesting git initialization", details=details, options=options)
            allowed, _ = self.sandbox.request_command_approval(self.name, cmd)
            self.logger.stop_prompt()
            if allowed: return self.sandbox.git_init()
            else: return "USER_DENIED: Git init cancelled."

        def install_deps_wrapper():
            cmd = "pip install -r requirements.txt"
            details = {"command": cmd, "dir": str(self.sandbox.root_dir)}
            options = [
                {"label": "Allow Installation", "value": "y"},
                {"label": "Deny Installation", "value": "n"},
                {"label": "Provide Specific Order", "value": "o", "require_text": True}
            ]
            self.logger.start_prompt(self.name, "Requesting dependency installation", details=details, options=options)
            allowed, _ = self.sandbox.request_command_approval(self.name, cmd)
            self.logger.stop_prompt()
            if allowed: return self.sandbox.install_dependencies()
            else: return "USER_DENIED: Installation cancelled."

        def report_status_wrapper(message):
            """Logs a status update to the mission dashboard."""
            self.logger.info(message)
            return "SUCCESS: Status logged."

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
            "git_init": git_init_wrapper,
            "git_commit": self.sandbox.git_commit,
            "install_dependencies": install_deps_wrapper,
            "update_todo_list": self.sandbox.update_todo_list,
            "report_status": report_status_wrapper
        }
        
        if self.pool_callback:
            self.tool_map["request_specialist"] = self.pool_callback

        self.tools = []
        for tool_name, func in self.tool_map.items():
            self.tools.append(types.FunctionDeclaration(
                name=tool_name,
                description=func.__doc__ or "Execute action",
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

    def _get_global_prompt(self):
        return (
            f"=== GLOBAL_SYSTEM_MANDATE ===\n"
            f"PROJECT: {self.project_name}\n"
            f"GOAL: {self.project_desc}\n"
            f"ROOT: You are ALREADY inside the specific project directory.\n\n"
            "IDENTITY & OPERATIONAL MODE:\n"
            "1. YOU ARE AN EXPERT: You write production-grade, cleaner, safer, and more idiomatic code than average. You handle edge cases.\n"
            "2. AUTONOMOUS & PROACTIVE: Do not wait for user input unless absolutely necessary (e.g. credentials). Fix your own errors. If a build fails, analyze the error and try a different approach.\n"
            "3. THINK FIRST: Before writing code, analyze the file structure and read existing files to maximize context.\n\n"
            "CRITICAL RULES:\n"
            "1. NO SUBDIRECTORIES FOR PROJECT: DO NOT create a new folder named after the project. You are already in the project folder. Create files directly in the current root or appropriate subfolders (src, data, etc.).\n"
            "2. FULL FUNCTIONALITY: The deliverable must be fully functional. No placeholders, no 'insert code here'. The app must run immediately after installation.\n"
            "3. BASH_COMMANDS: Every 'execute_command' call WILL REQUIRE human approval. No exceptions. Chain commands with '&&' sparingly; prefer sequential calls for better error handling.\n"
            "4. NO ECHO COMMANDS: DO NOT use `execute_command('echo ...')` to log progress. Use the dedicated tool `report_status('message')` instead. This prevents unnecessary security prompts.\n"
            "5. FILE EDITS: When using 'smart_replace', ensure unique context. Prefer 'write_file' for creating new files. Read a file before editing it to ensure you have the correct context.\n"
            "6. FILE SEARCHING: Use 'glob_search' to find files by pattern (e.g., '**/*.py') and 'grep_search' to find code content. Use 'get_structure_tree' to understand project layout.\n"
            "7. DEPENDENCIES: Use 'install_dependencies' to install packages from requirements.txt. Use 'web_fetch' to retrieve external documentation if needed. Use 'search_web' to find documentation or solutions to errors.\n\n"
            "TEAM_STUCTURE & SYNC:\n"
            "1. FOLLOW_THE_LEADER: Follow the PROJECT_MANAGER roadmap and the TODO_LIST.\n"
            "2. UPDATE_TODO: Use 'update_todo_list' when progress is made.\n\n"
            "DEVELOPMENT_PHILOSOPHY: EFFICIENCY_AND_SIMPLICITY\n"
            "1. MINIMAL_VIABLE_APPROACH: Prioritize single-file solutions if possible, but ensure completeness.\n"
            "2. ERROR RECOVERY: If a tool fails, DO NOT request the user to fix it. Attempt to debug it yourself using 'grep_search' or 'read_file'.\n"
            "3. NO_EXCESSIVE_TESTING: For simple projects/MVPs, manual verification or a single integration test is sufficient. Do not write extensive unit test suites unless specifically requested. Once the core feature works, STOP. Do not spend time on edge-case testing for prototypes.\n"
            "==============================\n"
        )

    def _get_personalized_prompt(self):
        return f"=== AGENT_PROFILE ===\nID: {self.name} | ROLE: {self.role}\n======================\n"

    def think_and_act(self, task, context=""):
        self.logger.log(self.name, f"TASK: {task[:50]}...", style="agent")
        messages = [types.Content(role="user", parts=[types.Part(text=f"{self._get_global_prompt()}\n{self._get_personalized_prompt()}\nSTATE:\n{context}\n\nTASK: {task}")])]
        
        turns = 0
        while turns < 25:
            self.logger.wait_if_paused() # CHECK BEFORE EACH TURN
            turns += 1
            full_response = None
            retry_count = 0
            while retry_count < 3:
                try:
                    self.logger.wait_if_paused() # CHECK BEFORE API CALL
                    stream = self.client.models.generate_content_stream(model=self.model_id, contents=messages, config=types.GenerateContentConfig(tools=[types.Tool(function_declarations=self.tools)]))
                    full_text = ""
                    accumulated_parts = []
                    last_usage = None
                    
                    for chunk in stream:
                        if hasattr(chunk, 'usage_metadata') and chunk.usage_metadata:
                            last_usage = chunk.usage_metadata
                            
                        if not chunk.candidates or not chunk.candidates[0].content or not chunk.candidates[0].content.parts: 
                            continue
                            
                        for part in chunk.candidates[0].content.parts:
                            if part.text:
                                full_text += part.text
                                self.logger.update_spinner(f"Thinking (turn {turns})", thought=full_text)
                            if part.function_call:
                                accumulated_parts.append(part)
                    
                    if full_text and not accumulated_parts:
                        accumulated_parts.append(types.Part(text=full_text))
                        
                    if last_usage:
                        self.total_input_tokens += last_usage.prompt_token_count
                        self.total_output_tokens += last_usage.candidates_token_count
                        
                    full_response = True
                    break
                except Exception as e:
                        retry_count += 1
                        if any(x in str(e).lower() for x in ["429", "quota", "overloaded"]):
                            backoff = 2 ** retry_count
                            self.logger.warning(f"API Rate limit hit. Retrying in {backoff}s...")
                            time.sleep(backoff)
                        else: return f"ERROR: {str(e)}"

            if not full_response: return "ERROR: API_UNAVAILABLE"
            
            model_content = types.Content(role="model", parts=accumulated_parts)
            messages.append(model_content)
            if not model_content.parts: return "DONE"
            
            function_calls = [part.function_call for part in model_content.parts if part.function_call]
            if not function_calls: return full_text or "DONE"

            tool_responses = []
            for fc in function_calls:
                args = fc.args or {}
                target = args.get("path") or args.get("command") or args.get("url") or ""
                if len(target) > 50: target = target[:47] + "..."
                self.logger.log(self.name, f"{fc.name} ({target})", style="exec")
                
                if fc.name in self.tool_map:
                    try: res = self.tool_map[fc.name](**args)
                    except Exception as e: res = f"ERROR: {str(e)}"
                else: res = "ERROR: Unknown tool"
                
                if self.logger.show_results:
                    res_preview = str(res)
                    if len(res_preview) > 100: res_preview = res_preview[:97] + "..."
                    self.logger.log(self.name, f"RESULT ({fc.name}) -> {res_preview}", style="info")
                
                tool_responses.append(types.Part(function_response=types.FunctionResponse(name=fc.name, response={"result": res})))
            messages.append(types.Content(role="user", parts=tool_responses))
        return "ERROR: MAX_TURNS_REACHED"

    def get_costs(self):
        return ((self.total_input_tokens / 1_000_000) * 0.10) + ((self.total_output_tokens / 1_000_000) * 0.40)

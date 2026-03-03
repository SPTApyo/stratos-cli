import os
import time
from typing import List
from dotenv import load_dotenv
from .engines.protocol import Message, MessagePart, ToolCall, ToolResponse, ToolDefinition

load_dotenv()

class AIAgent:
    """Refactored AI Agent: AI-model agnostic via AIEngine abstraction.
    Uses universal protocol.py for message exchange.
    """
    
    def __init__(self, name, role, sandbox, logger, ai_engine, project_info, mission_type="NEW_PROJECT", pool_callback=None):
        from stratos.core.roles import AgentRole
        if not AgentRole.is_valid_role(role):
            logger.error(f"FATAL: Unauthorized agent role '{role}'. Please use one of the roles defined in roles.json.")
            raise ValueError(f"Unauthorized role: {role}")
            
        self.name = name
        self.role = role.upper()
        self.mission_type = mission_type
        self.sandbox = sandbox
        self.logger = logger
        self.project_name = project_info['name']
        self.project_desc = project_info['desc']
        
        self.engine = ai_engine
        self.pool_callback = pool_callback
        
        from stratos.assets import load_tools
        self.tool_definitions = load_tools()
        
        self._setup_tool_map()
        self._setup_tools_list()

    def _setup_tool_map(self):
        """Dynamically maps tools from tools.json to Sandbox methods or local wrappers."""
        self.tool_map = {}
        wrappers = {
            "ask_user": self._ask_user_wrapper,
            "request_confirmation": self._confirm_wrapper,
            "execute_command": self._exec_wrapper,
            "report_status": lambda message: self.logger.info(message) or "SUCCESS"
        }
        for tool_name in self.tool_definitions:
            if tool_name == "request_specialist":
                if self.pool_callback: self.tool_map[tool_name] = self.pool_callback
                continue
            if tool_name in wrappers:
                self.tool_map[tool_name] = wrappers[tool_name]
                continue
            if hasattr(self.sandbox, tool_name):
                self.tool_map[tool_name] = getattr(self.sandbox, tool_name)
                continue
            self.logger.warning(f"INTEGRITY ALERT: Tool '{tool_name}' defined in tools.json but NOT implemented in AIAgent or Sandbox.")
        implemented_tools = set(self.tool_map.keys())
        defined_tools = set(self.tool_definitions.keys())
        if not defined_tools.issubset(implemented_tools):
            missing = defined_tools - implemented_tools
            self.logger.error(f"CRITICAL: Missing implementation for tools: {missing}")

    def _ask_user_wrapper(self, question):
        self.logger.start_prompt(self.name, question)
        res = self.sandbox.ask_user(question)
        self.logger.stop_prompt()
        return res

    def _confirm_wrapper(self, action):
        options = [{"label": "Yes", "value": "y"}, {"label": "No", "value": "n"}]
        self.logger.start_prompt(self.name, f"Confirm: {action}", details={"command": action}, options=options)
        res = self.sandbox.request_confirmation(action)
        self.logger.stop_prompt()
        return res

    def _exec_wrapper(self, command):
        self.logger.debug(f"[REQUEST] {self.name}: {command}")
        options = [{"label": "Allow", "value": "y"}, {"label": "Deny", "value": "n"}, {"label": "Change", "value": "o", "require_text": True}]
        self.logger.start_prompt(self.name, "Execute command?", details={"command": command}, options=options)
        allowed, result = self.sandbox.request_command_approval(self.name, command)
        self.logger.stop_prompt()
        if allowed: return self.sandbox.execute_command(command)
        return f"USER_DENIED: {result}"

    def _setup_tools_list(self):
        """Converts tool map to generic ToolDefinition list."""
        self.tools = []
        for tool_name in self.tool_map:
            if tool_name in self.tool_definitions:
                defn = self.tool_definitions[tool_name]
                self.tools.append(ToolDefinition(name=tool_name, description=defn["description"], parameters=defn["parameters"]))

    def think_and_act(self, task, context=""):
        """Main execution loop using generic Protocol."""
        self.logger.log(self.name, f"TASK: {task[:50]}...", style="agent")
        
        full_prompt = self._prepare_prompt(task, context)
        full_prompt = self._review_prompt(full_prompt)
        if not full_prompt: return "TASK_ABORTED"

        messages = [Message(role="user", parts=[MessagePart(text=full_prompt)])]
        turns = 0
        while turns < 25:
            self.logger.wait_if_paused()
            turns += 1
            response_parts = self.engine.generate_content(messages, self.tools, turns, self.logger)
            if isinstance(response_parts, str): return response_parts 
            assistant_msg = Message(role="assistant", parts=response_parts)
            messages.append(assistant_msg)
            tool_calls = [p.tool_call for p in response_parts if p.tool_call]
            if not tool_calls:
                text = "".join([p.text for p in response_parts if p.text])
                return text or "DONE"
            results_parts = self._execute_tools(tool_calls)
            messages.append(Message(role="user", parts=results_parts))
        return "ERROR: MAX_TURNS_REACHED"

    def _prepare_prompt(self, task, context):
        from stratos.assets import load_prompt
        from stratos.core.roles import AgentRole
        from stratos.core.missions import MissionType
        global_p = load_prompt("global_mandate", project_name=self.project_name, project_desc=self.project_desc)
        mission_key = MissionType.get_prompt_key(self.mission_type)
        mission_p = load_prompt(mission_key)
        if "ERROR" in mission_p: mission_p = ""
        prompt_key = AgentRole.get_prompt_key(self.role)
        strategy_p = load_prompt(prompt_key)
        if "ERROR" in strategy_p: strategy_p = ""
        perso_p = f"=== AGENT_PROFILE ===\nID: {self.name} | ROLE: {self.role.upper()} | MISSION_MODE: {self.mission_type}\n======================\n"
        return f"{global_p}\n{mission_p}\n{strategy_p}\n{perso_p}\nSTATE:\n{context}\n\nTASK: {task}"

    def _review_prompt(self, prompt):
        """Allows human to review and edit the generated prompt."""
        options = [{"label": "Confirm & Send", "value": "y"}, {"label": "Edit Prompt", "value": "e", "require_text": True}, {"label": "Abort Task", "value": "n"}]
        self.logger.start_prompt(self.name, "Reviewing system prompt...", details={"prompt_preview": prompt}, options=options)
        res = self.sandbox.ask_user("Reviewing prompt...")
        self.logger.stop_prompt()
        if res == "n": return None
        if res and res != "y": return res 
        return prompt

    def _execute_tools(self, tool_calls: List[ToolCall]) -> List[MessagePart]:
        """Executes generic tool calls and returns MessageParts with ToolResponses."""
        parts = []
        for tc in tool_calls:
            target = next(iter(tc.args.values()), "") if tc.args else ""
            self.logger.log(self.name, f"{tc.name} ({str(target)[:30]})", style="exec")
            try:
                if tc.name in self.tool_map: res = self.tool_map[tc.name](**tc.args)
                else: res = "ERROR: Unknown tool"
            except Exception as e: res = f"ERROR: {str(e)}"
            
            res_str = str(res)
            is_error = res_str.startswith("ERROR") or res_str.startswith("CRASH") or res_str.startswith("USER_DENIED")
            
            if self.logger.state.show_results:
                from rich.panel import Panel
                from rich.text import Text
                
                if len(res_str) > 250:
                    head = res_str[:200]
                    fade = res_str[200:240]
                    display_res = Text(head, style="white")
                    display_res.append(fade[:10], style="#BBBBBB")
                    display_res.append(fade[10:20], style="#888888")
                    display_res.append(fade[20:30], style="#555555")
                    display_res.append(fade[30:], style="#333333")
                    display_res.append("...", style="bold #333333")
                else:
                    display_res = Text(res_str, style="white")

                if "\n" in res_str or "{" in res_str or "/" in res_str:
                    display_res = Panel(display_res, border_style="dim cyan" if not is_error else "dim red", title=f"[dim]{'ERROR' if is_error else 'RESULT DATA'}[/]", expand=False)
                
                self.logger.log(self.name, display_res, style="info" if not is_error else "err")
            else:
                # Minimalist display: just Success/Fail
                if is_error:
                    self.logger.log(self.name, f"FAILED ({tc.name}) › {res_str[:50]}...", style="err")
                else:
                    self.logger.log(self.name, f"SUCCESS ({tc.name})", style="ok")
            
            parts.append(MessagePart(tool_response=ToolResponse(name=tc.name, result=res, id=tc.id)))
        return parts

    def get_costs(self):
        return self.engine.get_costs()

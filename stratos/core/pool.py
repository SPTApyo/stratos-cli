import datetime
import difflib

class Blackboard:
    def __init__(self, sandbox, logger):
        self.data = {
            "TODO_LIST": "1. INITIAL_ANALYSIS (Pending)",
            "MASTER_PLAN": "No plan defined yet."
        }
        self.team_log = []
        self.sandbox = sandbox
        self.logger = logger
        self.compressed_archive = ""
        self.last_snapshot = {}
        self.last_cycle_errors = ""

    def post(self, key, value):
        self.data[key] = value

    def post_discussion(self, agent_name, message):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        self.team_log.append(f"[{now}] [{agent_name}] {message}")

    def compute_diff(self, new_snapshot):
        self.logger.debug(f"COMPUTING_DIFF BETWEEN {len(self.last_snapshot)} AND {len(new_snapshot)} FILES")
        diff_report = []
        old_files = set(self.last_snapshot.keys())
        new_files = set(new_snapshot.keys())
        for f in new_files - old_files:
            diff_report.append(f"[NEW] {f}")
        for f in old_files - new_files:
            diff_report.append(f"[DEL] {f}")
        for f in old_files & new_files:
            if self.last_snapshot[f] != new_snapshot[f]:
                diff = difflib.unified_diff(
                    self.last_snapshot[f].splitlines(),
                    new_snapshot[f].splitlines(),
                    fromfile=f"a/{f}", tofile=f"b/{f}", lineterm=""
                )
                diff_report.append(f"[MOD] {f}:\n" + "\n".join(list(diff)))
        return "\n".join(diff_report) if diff_report else "NO_CHANGES"

    def get_all_context(self, current_diff=""):
        real_structure = self.sandbox.get_structure_tree()
        context = ""
        if self.compressed_archive:
            context += f"COMPRESSED_ARCHIVE:\n{self.compressed_archive}\n\n"
        if self.last_cycle_errors:
            context += f"POST_MORTEM_ANALYSIS:\n{self.last_cycle_errors}\n\n"
            
        # Avoid recursion by not calling get_all_context inside needs_compression
        # We'll just estimate the size based on the current components
        estimated_size = len(real_structure) + len(current_diff) + sum(len(str(v)) for v in self.data.values()) + sum(len(l) for l in self.team_log)
        
        if estimated_size > 60000:
            self.logger.warning("Context size high. Compressing context...")
            recent_logs = "\n".join(self.team_log[-3:])
            real_structure = real_structure[:2000] + "\n... [TRUNCATED]"
        else:
            recent_logs = "\n".join(self.team_log[-8:])
            
        context += f"REAL_FILESYSTEM_STATE:\n{real_structure}\n\n"
        if current_diff:
            context += f"RECENT_CHANGES (DIFF):\n{current_diff}\n\n"
        context += "ACTIVE_PROJECT_DATA (GLOBAL_BLACKBOARD):\n"
        for k, v in self.data.items():
            val = str(v)[:500] + "..." if len(str(v)) > 500 else v
            context += f"  - {k}: {val}\n"
        context += f"\nRECENT_TEAM_LOGS:\n{recent_logs}"
        return context

    def needs_compression(self, threshold=60000):
        # This method is now deprecated as we estimate size directly in get_all_context
        # to avoid infinite recursion.
        return False

class AIPool:
    def __init__(self, sandbox, logger, api_key, project_info):
        self.sandbox = sandbox
        self.logger = logger
        self.api_key = api_key
        self.project_info = project_info
        self.agents = {}
        self.specialists = {}
        self.blackboard = Blackboard(sandbox, logger)
        self.models = {
            "HEAVY": "gemini-3.1-pro-preview", 
            "MEDIUM": "gemini-2.5-pro",        
            "LIGHT": "gemini-2.5-flash"        
        }

    def request_specialist(self, **kwargs) -> str:
        role_name = kwargs.get('role_name')
        role_description = kwargs.get('role_description')
        weight = kwargs.get('weight', 'MEDIUM').upper()
        model_id = self.models.get(weight, self.models["MEDIUM"])

        if not role_name or not role_description:
            return "ERROR: Missing role_name or role_description"
        if role_name in self.agents or role_name in self.specialists:
            return f"INFO: {role_name} already exists."
        
        from .agent import AIAgent
        from google.genai import types
        self.logger.info(f"DYNAMIC_RECRUITMENT: {role_name}")
        
        new_agent = AIAgent(
            f"EXPERT_{role_name}", role_description, self.sandbox, self.logger, 
            self.api_key, self.project_info, pool_callback=self.request_specialist,
            model_id=model_id
        )
        
        # Specialist must use the same protected tools as standard agents
        def tool_update_todo(todo_content):
            self.blackboard.post("TODO_LIST", todo_content)
            self.logger.set_todo(todo_content)
            return f"SUCCESS: Global TODO_LIST updated."
            
        new_agent.tool_map["update_todo_list"] = tool_update_todo
        
        # Re-generate Function Declarations with the full (wrapped) tool_map
        from google.genai import types
        new_agent.tools = [types.FunctionDeclaration(
            name=n,
            description=f.__doc__ or "Execute action",
            parameters=new_agent._get_tool_schema(n)
        ) for n, f in new_agent.tool_map.items()]
        
        self.specialists[role_name] = new_agent
        self.blackboard.post_discussion("SYSTEM", f"New specialist joined: {role_name}")
        return f"SUCCESS: {role_name} is now available."

    def setup_default_pool(self):
        from .agent import AIAgent
        
        # Shared tool to update the TODO list on the blackboard
        def tool_update_todo(todo_content):
            self.blackboard.post("TODO_LIST", todo_content)
            self.logger.set_todo(todo_content)
            return f"SUCCESS: Global TODO_LIST updated."

        roles = {
            "MANAGER": {"desc": "PROJECT_LEADER: Define tech stack, roadmap, and maintain the TODO_LIST. You are the boss.", "model": self.models["HEAVY"]},
            "ARCHITECT": {"desc": "SYSTEM_DESIGNER: Create file structures and specifications based on PM roadmap.", "model": self.models["MEDIUM"]},
            "CODER": {"desc": "IMPLEMENTATION_ENGINEER: Write code and fix bugs following the TODO_LIST.", "model": self.models["LIGHT"]},
            "REVIEWER": {"desc": "QUALITY_ASSURANCE: Test code and verify functional requirements.", "model": self.models["MEDIUM"]},
            "DOCUMENTATION": {"desc": "TECHNICAL_WRITER: Update user manuals and README.", "model": self.models["LIGHT"]}
        }
        for role, data in roles.items():
            agent = AIAgent(
                f"AGENT_{role}", data["desc"], self.sandbox, self.logger, 
                self.api_key, self.project_info, pool_callback=self.request_specialist,
                model_id=data["model"]
            )
            # Override or manually inject the blackboard tool
            agent.tool_map["update_todo_list"] = tool_update_todo
            # Regenerate tool definitions for the model
            from google.genai import types
            agent.tools = [types.FunctionDeclaration(
                name=name,
                description=func.__doc__ or "Execute action",
                parameters=agent._get_tool_schema(name)
            ) for name, func in agent.tool_map.items()]
            
            self.agents[role] = agent
        self.sandbox.git_init()

    def _execute_agent_action(self, agent, task):
        self.logger.agent_takeover(agent.name, agent.role)
        self.logger.wait_if_paused() # CHECK BEFORE STARTING ACTION
        if not self.blackboard.last_snapshot:
            self.blackboard.last_snapshot = self.sandbox.get_snapshot()
        current_state = self.sandbox.get_snapshot()
        diff = self.blackboard.compute_diff(current_state)
        result = agent.think_and_act(
            task, 
            context=self.blackboard.get_all_context(current_diff=diff)
        )
        self.blackboard.last_snapshot = self.sandbox.get_snapshot()
        return result

    def _handle_interjection(self):
        """Internal check to handle user interjection if an instruction was provided."""
        # The engine signal_handler now handles the prompt logic. 
        # We just check if there's text left in the input buffer from an 'instruct' choice.
        if hasattr(self.logger, 'prompt_input') and self.logger.prompt_input.strip():
            order = self.logger.prompt_input.strip()
            self.blackboard.post_discussion("HUMAN", f"INTERJECTION: {order}")
            self.blackboard.post("USER_ORDER", order)
            self.logger.prompt_input = "" # Clear buffer

    def broadcast_task(self, task):
        self.logger.section("HIERARCHICAL_TEAM_WORKFLOW")
        max_iterations = 6
        iteration = 0
        is_ready = False

        while not is_ready and iteration < max_iterations:
            iteration += 1
            self.logger.start_cycle(iteration)
            
            # Update tokens metric on dashboard
            all_agents = list(self.agents.values()) + list(self.specialists.values())
            total_tokens = sum(a.total_input_tokens + a.total_output_tokens for a in all_agents)
            self.logger.update_tokens(total_tokens)
            
            # 1. PM Decision
            pm_instruction = (
                f"LEADERSHIP_PHASE: Analyze the goal '{task}' and current state. "
                "1. Choose the language and tech stack. "
                "2. Update the 'MASTER_PLAN' key on the blackboard. "
                "3. Update the 'TODO_LIST' key with clear, actionable steps. "
                "4. Assign specific focus for this cycle."
            )
            strategy = self._execute_agent_action(self.agents["MANAGER"], pm_instruction)
            self.blackboard.post("MASTER_PLAN", strategy)
            self._handle_interjection()

            # 2. Architect Design
            plan = self._execute_agent_action(self.agents["ARCHITECT"], "DESIGN_STRATEGY: Follow PM's roadmap. Define files and logic.")
            self.blackboard.post("DETAILED_SPECS", plan)
            self._handle_interjection()

            # 3. Execution
            for name, specialist in list(self.specialists.items()):
                self._execute_agent_action(specialist, f"EXPERT_CONTRIBUTION: {name}. Consult TODO_LIST.")
                self._handle_interjection()

            self._execute_agent_action(self.agents["CODER"], "IMPLEMENTATION: Execute current pending tasks in TODO_LIST.")
            self._handle_interjection()
            
            # 4. Verification
            self._execute_agent_action(self.agents["REVIEWER"], "QA_AND_TEST_RUN: Verify everything works.")
            self._handle_interjection()
            
            vote = self._execute_agent_action(self.agents["REVIEWER"], "FINAL_STATUS_CHECK")
            
            is_ready = "STATUS: READY" in vote.upper()
            if is_ready: break

        import threading
        doc_thread = threading.Thread(target=self._execute_agent_action, args=(self.agents["DOCUMENTATION"], "FINAL_DOCS"))
        doc_thread.start()
        doc_thread.join()
        return "SUCCESS"

import datetime
import difflib

class Blackboard:
    """Refactored Blackboard: holds state and handles context generation."""
    
    def __init__(self, sandbox, logger):
        self.data = {
            "TODO_LIST": "1. INITIAL_ANALYSIS (Pending)",
            "MASTER_PLAN": "No plan defined yet."
        }
        self.team_log = []
        self.sandbox = sandbox
        self.logger = logger
        self.last_snapshot = {}
        self.last_cycle_errors = ""

    def post(self, key, value):
        self.data[key] = value

    def post_discussion(self, agent_name, message):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        self.team_log.append(f"[{now}] [{agent_name}] {message}")

    def get_full_context(self, current_diff=""):
        """Generates a comprehensive context string for agents."""
        structure = self.sandbox.get_structure_tree()
        
        # Simple Truncation logic for context size management
        if len(structure) > 4000: structure = structure[:4000] + "\n... [TRUNCATED]"
        recent_logs = "\n".join(self.team_log[-8:])
        
        context = ""
        if self.last_cycle_errors:
            context += f"POST_MORTEM_ANALYSIS:\n{self.last_cycle_errors}\n\n"
            
        context += f"REAL_FILESYSTEM_STATE:\n{structure}\n\n"
        if current_diff:
            context += f"RECENT_CHANGES (DIFF):\n{current_diff}\n\n"
            
        context += "ACTIVE_PROJECT_DATA (GLOBAL_BLACKBOARD):\n"
        for k, v in self.data.items():
            val = str(v)[:500] + "..." if len(str(v)) > 500 else v
            context += f"  - {k}: {val}\n"
            
        context += f"\nRECENT_TEAM_LOGS:\n{recent_logs}"
        return context

    def compute_diff(self, new_snapshot):
        """Computes a unified diff between two file system snapshots."""
        diff_report = []
        old_files = set(self.last_snapshot.keys())
        new_files = set(new_snapshot.keys())
        
        for f in new_files - old_files: diff_report.append(f"[NEW] {f}")
        for f in old_files - new_files: diff_report.append(f"[DEL] {f}")
        for f in old_files & new_files:
            if self.last_snapshot[f] != new_snapshot[f]:
                diff = difflib.unified_diff(
                    self.last_snapshot[f].splitlines(),
                    new_snapshot[f].splitlines(),
                    fromfile=f"a/{f}", tofile=f"b/{f}", lineterm=""
                )
                diff_report.append(f"[MOD] {f}:\n" + "\n".join(list(diff)[:20])) # Limit diff size
                
        return "\n".join(diff_report) if diff_report else "NO_CHANGES"

class AIPool:
    """Refactored AIPool: manages agent lifecycle and mission orchestration."""
    
    MODELS = {
        "HEAVY": "gemini-3.1-pro-preview", 
        "MEDIUM": "gemini-2.5-pro",        
        "LIGHT": "gemini-2.5-flash"        
    }

    def __init__(self, sandbox, logger, api_key, project_info):
        self.sandbox = sandbox
        self.logger = logger
        self.api_key = api_key
        self.project_info = project_info
        self.agents = {}
        self.specialists = {}
        self.blackboard = Blackboard(sandbox, logger)

    def setup_default_pool(self):
        """Initializes the core team of agents."""
        roles = {
            "MANAGER": {"desc": "PROJECT_LEADER: Define tech stack, roadmap, and maintain the TODO_LIST.", "model": self.MODELS["HEAVY"]},
            "ARCHITECT": {"desc": "SYSTEM_DESIGNER: Create file structures and specifications.", "model": self.MODELS["MEDIUM"]},
            "CODER": {"desc": "IMPLEMENTATION_ENGINEER: Write code following the roadmap.", "model": self.MODELS["LIGHT"]},
            "REVIEWER": {"desc": "QUALITY_ASSURANCE: Test code and verify requirements.", "model": self.MODELS["MEDIUM"]},
            "DOCUMENTATION": {"desc": "TECHNICAL_WRITER: Update manuals and README.", "model": self.MODELS["LIGHT"]}
        }
        
        from .agent import AIAgent
        for role, data in roles.items():
            agent = AIAgent(f"AGENT_{role}", data["desc"], self.sandbox, self.logger, self.api_key, self.project_info, pool_callback=self.request_specialist, model_id=data["model"])
            # Standardize tool: update_todo_list
            agent.tool_map["update_todo_list"] = self._tool_update_todo
            self.agents[role] = agent
            
        self.sandbox.git_init()

    def _tool_update_todo(self, todo_content):
        self.blackboard.post("TODO_LIST", todo_content)
        self.logger.set_todo(todo_content)
        return "SUCCESS: Global TODO_LIST updated."

    def request_specialist(self, role_name, role_description, weight='MEDIUM') -> str:
        """Dynamic recruitment of expert agents."""
        weight = weight.upper()
        if role_name in self.agents or role_name in self.specialists: return f"INFO: {role_name} already exists."
        
        from .agent import AIAgent
        self.logger.info(f"DYNAMIC_RECRUITMENT: {role_name}")
        
        spec = AIAgent(f"EXPERT_{role_name}", role_description, self.sandbox, self.logger, self.api_key, self.project_info, pool_callback=self.request_specialist, model_id=self.MODELS.get(weight, self.MODELS["MEDIUM"]))
        spec.tool_map["update_todo_list"] = self._tool_update_todo
        self.specialists[role_name] = spec
        return f"SUCCESS: {role_name} joined."

    def broadcast_task(self, task):
        """High-level orchestration of the hierarchical workflow."""
        self.logger.section("MISSION_WORKFLOW_START")
        for iteration in range(1, 7):
            self.logger.start_cycle(iteration)
            self._sync_metrics()
            
            # --- PHASE 1: STRATEGY (MANAGER) ---
            from stratos.assets import load_prompt
            self._run_agent(self.agents["MANAGER"], load_prompt("pm_strategy", task=task))
            
            # --- PHASE 2: DESIGN (ARCHITECT) ---
            self._run_agent(self.agents["ARCHITECT"], "DESIGN_STRATEGY: Follow PM roadmap.")
            
            # --- PHASE 3: EXECUTION (SPECIALISTS & CODER) ---
            for spec in list(self.specialists.values()):
                self._run_agent(spec, "EXPERT_CONTRIBUTION: Follow TODO_LIST.")
            self._run_agent(self.agents["CODER"], "IMPLEMENTATION: Execute pending tasks.")
            
            # --- PHASE 4: VERIFICATION (REVIEWER) ---
            self._run_agent(self.agents["REVIEWER"], "QA_AND_TEST_RUN: Verify functional requirements.")
            vote = self._run_agent(self.agents["REVIEWER"], "FINAL_STATUS_CHECK: Reply with 'STATUS: READY' if finished.")
            
            if "STATUS: READY" in vote.upper(): break

        self._run_agent(self.agents["DOCUMENTATION"], "FINAL_DOCS: Complete the README and documentation.")
        return "SUCCESS"

    def _run_agent(self, agent, task):
        """Executes a single agent turn with state synchronization."""
        self.logger.agent_takeover(agent.name, agent.role)
        self.logger.wait_if_paused()
        
        # Pre-execution snapshot
        if not self.blackboard.last_snapshot: self.blackboard.last_snapshot = self.sandbox.get_snapshot()
        current_state = self.sandbox.get_snapshot()
        diff = self.blackboard.compute_diff(current_state)
        
        # Execution
        result = agent.think_and_act(task, context=self.blackboard.get_full_context(diff))
        
        # Post-execution cleanup
        self.blackboard.last_snapshot = self.sandbox.get_snapshot()
        self._handle_user_interjections()
        return result

    def _sync_metrics(self):
        all_agents = list(self.agents.values()) + list(self.specialists.values())
        total_tokens = sum(a.total_input_tokens + a.total_output_tokens for a in all_agents)
        self.logger.update_tokens(total_tokens)

    def _handle_user_interjections(self):
        state = self.logger.state
        if state.prompt_input.strip():
            order = state.prompt_input.strip()
            self.blackboard.post_discussion("HUMAN", f"INTERJECTION: {order}")
            self.blackboard.post("USER_ORDER", order)
            state.prompt_input = ""

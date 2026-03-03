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
        if len(structure) > 4000: structure = structure[:4000] + "\n... [TRUNCATED]"
        recent_logs = "\n".join(self.team_log[-8:])
        context = ""
        if self.last_cycle_errors: context += f"POST_MORTEM_ANALYSIS:\n{self.last_cycle_errors}\n\n"
        context += f"REAL_FILESYSTEM_STATE:\n{structure}\n\n"
        if current_diff: context += f"RECENT_CHANGES (DIFF):\n{current_diff}\n\n"
        context += "ACTIVE_PROJECT_DATA (GLOBAL_BLACKBOARD):\n"
        for k, v in self.data.items():
            val = str(v)[:500] + "..." if len(str(v)) > 500 else v
            context += f"  - {k}: {val}\n"
        context += f"\nRECENT_TEAM_LOGS:\n{recent_logs}"
        return context

    def compute_diff(self, new_snapshot):
        """Computes a unified diff between two file system snapshots."""
        self.logger.debug(f"COMPUTING_DIFF BETWEEN {len(self.last_snapshot)} AND {len(new_snapshot)} FILES")
        diff_report = []
        old_files = set(self.last_snapshot.keys())
        new_files = set(new_snapshot.keys())
        for f in new_files - old_files: diff_report.append(f"[NEW] {f}")
        for f in old_files - new_files: diff_report.append(f"[DEL] {f}")
        for f in old_files & new_files:
            if self.last_snapshot[f] != new_snapshot[f]:
                diff = difflib.unified_diff(self.last_snapshot[f].splitlines(), new_snapshot[f].splitlines(), fromfile=f"a/{f}", tofile=f"b/{f}", lineterm="")
                diff_report.append(f"[MOD] {f}:\n" + "\n".join(list(diff)[:20]))
        return "\n".join(diff_report) if diff_report else "NO_CHANGES"

class AIPool:
    """Refactored AIPool: manages agent lifecycle and mission orchestration."""
    
    def __init__(self, sandbox, logger, api_key, project_info, mission_type="NEW_PROJECT"):
        self.sandbox = sandbox
        self.logger = logger
        self.api_key = api_key
        self.project_info = project_info
        self.mission_type = mission_type
        self.agents = {}
        self.specialists = {}
        self.blackboard = Blackboard(sandbox, logger)
        from stratos.utils.config import load_config
        self.provider = load_config().get("active_engine")

    def setup_default_pool(self):
        """Initializes the core team of agents using the EngineFactory."""
        from stratos.core.roles import AgentRole
        from stratos.core.engines.factory import EngineFactory
        default_roles = AgentRole.get_default_roles()
        from .agent import AIAgent
        for role, data in default_roles.items():
            if not AgentRole.is_valid_role(role): continue
            tier = EngineFactory.get_tier_for_role(role)
            engine = EngineFactory.create_engine(self.provider, tier, self.api_key)
            agent = AIAgent(f"AGENT_{role}", role, self.sandbox, self.logger, engine, self.project_info, mission_type=self.mission_type, pool_callback=self.request_specialist)
            agent.tool_map["update_todo_list"] = self._tool_update_todo
            self.agents[role] = agent
        
        self.logger.debug("[GIT-INIT] Initializing repo...")
        self.sandbox.git_init()

    def _tool_update_todo(self, todo_content):
        self.blackboard.post("TODO_LIST", todo_content)
        self.logger.set_todo(todo_content)
        return "SUCCESS: Global TODO_LIST updated."

    def request_specialist(self, role_name, role_description, weight='MEDIUM') -> str:
        """Dynamic recruitment of expert agents, strictly restricted to roles.json."""
        from stratos.core.roles import AgentRole
        from stratos.core.engines.factory import EngineFactory
        role_name = role_name.upper()
        if not AgentRole.is_valid_role(role_name): return f"ERROR: Unauthorized role '{role_name}'. Recruitment denied."
        weight = weight.upper()
        if role_name in self.agents or role_name in self.specialists: return f"INFO: {role_name} already exists."
        from .agent import AIAgent
        self.logger.info(f"DYNAMIC_RECRUITMENT: {role_name}")
        engine = EngineFactory.create_engine(self.provider, weight, self.api_key)
        spec = AIAgent(f"EXPERT_{role_name}", role_name, self.sandbox, self.logger, engine, self.project_info, mission_type=self.mission_type, pool_callback=self.request_specialist)
        spec.tool_map["update_todo_list"] = self._tool_update_todo
        self.specialists[role_name] = spec
        return f"SUCCESS: {role_name} joined."

    def broadcast_task(self, task):
        """High-level orchestration of the hierarchical workflow."""
        self.logger.section("MISSION_WORKFLOW_START")
        for iteration in range(1, 7):
            self.logger.start_cycle(iteration)
            self._sync_metrics()
            
            from stratos.assets import load_prompt
            self._run_agent(self.agents["MANAGER"], f"LEADERSHIP_PHASE: Analyze the goal '{task[:30]}...' and update the TODO_LIST.\n\nSTRATEGY_GUIDE:\n{load_prompt('manager_strategy')}")
            
            self._run_agent(self.agents["ARCHITECT"], "DESIGN_STRATEGY: Follow PM roadmap. Define files and requirements.")
            
            for spec in list(self.specialists.values()):
                self._run_agent(spec, "EXPERT_CONTRIBUTION: Follow TODO_LIST. Execute your specific expertise.")
            self._run_agent(self.agents["CODER"], "IMPLEMENTATION: Execute pending tasks from the TODO_LIST.")
            
            self._run_agent(self.agents["REVIEWER"], "QA_AND_TEST_RUN: Verify functional requirements.")
            vote = self._run_agent(self.agents["REVIEWER"], "FINAL_STATUS_CHECK: Reply with 'STATUS: READY' if finished.")
            if "STATUS: READY" in vote.upper(): break

        if "DOCUMENTATION" in self.agents:
            self._run_agent(self.agents["DOCUMENTATION"], "FINAL_DOCS: Complete the README and documentation.")
        return "SUCCESS"

    def _run_agent(self, agent, task):
        """Executes a single agent turn with state synchronization."""
        self.logger.agent_takeover(agent.name, agent.role)
        self.logger.wait_if_paused()
        if not self.blackboard.last_snapshot: self.blackboard.last_snapshot = self.sandbox.get_snapshot()
        current_state = self.sandbox.get_snapshot()
        diff = self.blackboard.compute_diff(current_state)
        result = agent.think_and_act(task, context=self.blackboard.get_full_context(diff))
        self.blackboard.last_snapshot = self.sandbox.get_snapshot()
        self._handle_user_interjections()
        return result

    def _sync_metrics(self):
        all_agents = list(self.agents.values()) + list(self.specialists.values())
        total_tokens = sum(a.engine.total_input_tokens + a.engine.total_output_tokens for a in all_agents)
        self.logger.update_tokens(total_tokens)

    def _handle_user_interjections(self):
        state = self.logger.state
        if state.prompt_input.strip():
            order = state.prompt_input.strip()
            self.blackboard.post_discussion("HUMAN", f"INTERJECTION: {order}")
            self.blackboard.post("USER_ORDER", order)
            state.prompt_input = ""
            
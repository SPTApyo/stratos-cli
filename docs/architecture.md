# Stratos Architecture

Stratos is built on a modular, multi-agent architecture designed for terminal-based autonomous software development.

## Core Components

### 1. The Engine (`stratos.core.engine`)
The central orchestrator that manages the mission lifecycle, UI updates, and thread synchronization between the AI pool and the terminal dashboard.

### 2. The Sandbox (`stratos.core.sandbox`)
A protected execution layer. It intercepts all system calls and validates them against a safety policy before allowing them to reach the host shell. It also provides the agents with tools for file manipulation and web searching.

### 3. The AI Pool (`stratos.core.pool`)
Manages the team of specialized agents. It implements a hierarchical workflow:
- **Manager**: Roadmap and high-level strategy.
- **Architect**: System design and file specifications.
- **Coder**: Implementation and bug fixing.
- **Reviewer**: Quality assurance and verification.

### 4. The Blackboard
A shared memory space where agents post tasks, plans, and technical specifications. It ensures all team members stay synchronized with the current state of the project.

### 5. The TUI (`stratos.ui`)
Terminal user interface built with `rich`. It provides real-time monitoring of the agent's thought process and mission logs.

## Security Model
Stratos follows a "Human-in-the-Loop" security model. While the sandbox blocks destructive commands automatically, every critical action (like executing generated scripts) requires manual approval through the dashboard.

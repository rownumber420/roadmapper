# Roadmap Orchestrator (roadmapper)

An automated workflow for creating and refining project roadmaps using an iterative "Writer-Reviewer" agent loop. It leverages CLI-based AI agents, orchestrated via LangGraph.

## Project Overview

The project aims to automate the process of turning an initial idea into a detailed, atomic, and verified `roadmap.md` file. It uses:
- **Writer Agent:** Generates the initial roadmap. It is agent-agnostic and uses an `Agent` abstraction (e.g., `opencode`, `gemini`).
- **Reviewer Agent:** Critiques the roadmap and provides feedback. It is also agent-agnostic.
- **Orchestrator:** A LangGraph-based Python application that manages the loop between the Writer and Reviewer until a stable roadmap is achieved.
- **Persistence:** PostgreSQL is used for LangGraph state persistence (allowing runs to be resumed via `--task-id`) and custom iteration logging.
- **GUI:** A Streamlit-based dashboard to visualize the iteration logs and agent communication.

## Architecture

- **Dockerized Environment:** The entire stack (orchestrator, postgres, gui) is designed to run in Docker.
- **Subprocess Integration:** Agents are invoked as subprocesses within the orchestrator container.
- **Volume Mounts:**
    - `/codebase`: Read-only mount of the project being roadmapped.
    - `/output`: Read-write mount for the generated `roadmap.md` and feedback files.
    - `~/.gemini`: Read-write mount for Gemini CLI credentials and configuration.

## Key Files

- `Dockerfile` & `docker-compose.yml`: Infrastructure and environment definitions.
- `entrypoint.sh` & `run_roadmapper.sh`: Container entrypoint and config-driven wrapper script for executing the workflow.
- `requirements.txt`: Python dependencies (langgraph, psycopg-binary, streamlit, pydantic).
- `src/main.py`: CLI entry point for the orchestrator.
- `src/graph.py`: LangGraph state machine definition.
- `src/nodes/`: Implementation of Writer and Reviewer node logic.
- `src/agents/`: Agent factory and implementations (`base.py`, `opencode.py`, `gemini.py`).
- `gui/app.py`: Streamlit application for log visualization.

## Building and Running

### Prerequisites
- Docker and Docker Compose installed.
- Relevant agent credentials (e.g., Gemini CLI credentials in `~/.gemini`).

### Commands
- **Start Infrastructure (Postgres & GUI):**
  ```bash
  docker compose up -d postgres gui
  ```
- **Run Orchestration Workflow:**
  Use the wrapper script with a configuration file (`*.orch`):
  ```bash
  ./run_roadmapper.sh my-project.orch
  ```
- **Access GUI:** Open `http://localhost:8501` in your browser.

## Development Conventions

- **Atomic Tasks:** Roadmaps should consist of atomic, testable tasks with short code examples.
- **Iterative Refinement:** The workflow typically runs for a configured number of iterations (e.g., 6) until the Reviewer accepts the roadmap.
- **Subprocess Safety:** Output from agents (especially ANSI codes) is stripped before logging to the database.
- **Environment Isolation:** Agents run in a constrained container environment with specific read-only/read-write mounts for safety.

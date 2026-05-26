# Roadmap Orchestrator (roadmapper)

An automated workflow for creating and refining project roadmaps using an iterative "Writer-Reviewer" agent loop. It leverages Gemini CLI and OpenCode AI agents, orchestrated via LangGraph.

## Project Overview

The project aims to automate the process of turning an initial idea into a detailed, atomic, and verified `roadmap.md` file. It uses:
- **Writer Agent:** Uses `opencode` to generate the initial roadmap.
- **Reviewer Agent:** Uses `gemini` CLI to review and provide feedback on the roadmap.
- **Orchestrator:** A LangGraph-based Python application that manages the loop between the Writer and Reviewer until a stable roadmap is achieved.
- **Persistence:** PostgreSQL is used for LangGraph state persistence and custom iteration logging.
- **GUI:** A Streamlit-based dashboard to visualize the iteration logs and agent communication.

## Architecture

- **Dockerized Environment:** The entire stack (orchestrator, postgres, gui) is designed to run in Docker.
- **Subprocess Integration:** Agents are invoked as subprocesses within the orchestrator container.
- **Volume Mounts:**
    - `/codebase`: Read-only mount of the project being roadmapped.
    - `/output`: Read-write mount for the generated `roadmap.md`.
    - `~/.gemini`: Read-write mount for Gemini CLI credentials and configuration.

## Key Files (Planned/Implemented)

- `initial_idea.md`: The input file describing the project idea.
- `roadmap.md`: The output file generated and refined by the agents.
- `Dockerfile` & `docker-compose.yml`: Infrastructure and environment definitions.
- `requirements.txt`: Python dependencies (langgraph, psycopg2-binary, streamlit, pydantic).
- `src/main.py`: CLI entry point for the orchestrator.
- `src/graph.py`: LangGraph state machine definition.
- `src/nodes/`: Implementation of Writer and Reviewer node logic.
- `gui/app.py`: Streamlit application for log visualization.

## Building and Running

### Prerequisites
- Docker and Docker Compose installed.
- Gemini CLI credentials in `~/.gemini`.

### Commands
- **Start Infrastructure (Postgres & GUI):**
  ```bash
  docker compose up -d postgres gui
  ```
- **Run Orchestration Workflow:**
  ```bash
  docker compose run orchestrator --idea /codebase/initial_idea.md --project-dir /codebase
  ```
- **Access GUI:** Open `http://localhost:8501` in your browser.

## Development Conventions

- **Atomic Tasks:** Roadmaps should consist of atomic, testable tasks with short code examples.
- **Iterative Refinement:** The workflow typically runs for up to 6 iterations until the Reviewer accepts the roadmap.
- **Subprocess Safety:** Output from agents (especially ANSI codes) is stripped before logging to the database.
- **Environment Isolation:** Agents run in a constrained container environment with specific read-only/read-write mounts for safety.

# Roadmap Orchestrator — Implementation Plan

## Overview

Automate the Writer-Reviewer agent loop for creating and refining a `roadmap.md` from an `initial_idea.md`. Uses LangGraph for orchestration with PostgreSQL for state persistence, both agents (opencode + Gemini CLI) run as subprocesses with full tool access.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Docker Compose                                     │
│                                                     │
│  ┌─────────────────────────────────────────────┐    │
│  │  orchestrator (Python + LangGraph)          │    │
│  │                                             │    │
│  │  ┌──────────┐  Agent abstraction  ┌────────┐│    │
│  │  │ Writer   │ ──── get_agent() ──>│opencode││    │
│  │  │ Node     │<─── parse/write ────│ run    ││    │
│  │  └──────────┘   roadmap.md        └────────┘│    │
│  │        │                                    │    │
│  │  ┌──────────┐  Agent abstraction  ┌────────┐│    │
│  │  │ Reviewer │ ──── get_agent() ──>│ gemini ││    │
│  │  │ Node     │<─── parse_status ───│ cli    ││    │
│  │  └──────────┘   feedback          └────────┘│    │
│  │        │                                    │    │
│  │  ┌─────▼──────────────┐                     │    │
│  │  │ Checkpointer       │                     │    │
│  │  │ (PostgreSQL via    │                     │    │
│  │  │  LangGraph)        │                     │    │
│  │  └─────┬──────────────┘                     │    │
│  │        │ also writes to                     │    │
│  │  ┌─────▼──────────────┐                     │    │
│  │  │ iteration_logs     │                     │    │
│  │  │ (custom SQL table) │                     │    │
│  │  └────────────────────┘                     │    │
│  │                                             │    │
│  │  Mounts: ~/.gemini (rw)                     │    │
│  │  Target repo mounted at /codebase (ro)      │    │
│  │  Output mounted at /output (rw)             │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│  ┌─────────────────────┐  ┌──────────────────┐      │
│  │  PostgreSQL         │  │  Streamlit GUI   │      │
│  └─────────────────────┘  └──────────────────┘      │
└─────────────────────────────────────────────────────┘
```

## LangGraph Flow

```
START → writer_node → reviewer_node → should_continue()
                                         ├── True → writer_node (loop)
                                         └── False → END
```

`should_continue()` returns True if iteration < max_iterations AND reviewer did NOT mark as accepted.

## Files

```
roadmap-orchestrator/
├── docker-compose.yml          # postgres (always up) + gui + orchestrator (one-shot)
├── Dockerfile                  # python:3.12-slim + node (opencode npm) + gemini CLI
├── requirements.txt            # langgraph, psycopg2-binary, streamlit, pydantic, etc.
├── .env.example
├── src/
│   ├── __init__.py
│   ├── main.py                 # argparse CLI: --idea, --writer-agent, --writer-model, --reviewer-agent, --reviewer-model, etc.
│   ├── config.py               # pydantic-settings: agent types, model names, paths, timeouts, CLI overrides
│   ├── state.py                # RoadmapState TypedDict
│   ├── graph.py                # LangGraph StateGraph with builder
│   ├── db.py                   # iteration_logs table schema + insert/query helpers
│   ├── ansi.py                 # strip ANSI escape sequences from agent output
│   ├── agents/                 # Pluggable agent abstraction
│   │   ├── __init__.py         # Registry: register(), get_agent()
│   │   ├── base.py             # Agent ABC + AgentResult
│   │   ├── opencode.py         # OpenCodeAgent (writer)
│   │   └── gemini.py           # GeminiAgent (reviewer)
│   └── nodes/
│       ├── __init__.py
│       ├── writer.py           # Uses get_agent(settings.writer_agent)
│       └── reviewer.py         # Uses get_agent(settings.reviewer_agent)
└── gui/
    ├── __init__.py
    └── app.py                  # Streamlit: query iteration_logs directly
```

## State Schema

```python
class RoadmapState(TypedDict):
    run_id: str                 # UUID for this run
    project_path: str           # mounted codebase path
    iteration: int
    max_iterations: int         # default 6
    is_stable: bool
    # Full content stored only in iteration_logs table.
    # This state holds refs/ids to avoid duplicating large text in checkpointer.
```

## Custom Logging Table

In addition to LangGraph's checkpointer, each node writes to a dedicated SQL table for easy GUI querying:

```sql
CREATE TABLE iteration_logs (
    id SERIAL PRIMARY KEY,
    run_id UUID NOT NULL,
    iteration INT NOT NULL,
    node_type VARCHAR(20) NOT NULL,  -- 'writer' or 'reviewer'
    raw_output TEXT,                  -- ANSI-stripped stdout+stderr
    roadmap_content TEXT,
    feedback TEXT,
    prompt TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

The Streamlit GUI queries only `iteration_logs` — fully decoupled from LangGraph internals.

## Agent Abstraction

Agent-specific logic (CLI invocation, prompt passing, output parsing) is factored out into pluggable classes under `src/agents/`. Each node resolves its agent via `get_agent()` from the registry, keeping the node itself generic.

### Agent interface (`src/agents/base.py`)

```python
class AgentResult:
    stdout: str
    stderr: str

class Agent(ABC):
    name: str = ""  # set by subclasses, used as registry key

    def build_command(self, prompt: str, output_path: Path, model: str) -> list[str]
    def get_stdin_data(self, prompt: str) -> bytes | None
    def stdin_mode(self) -> int                    # subprocess.PIPE or DEVNULL
    def parse_status(self, stdout: str) -> bool    # extract ACCEPT/REVISE
```

### OpenCodeAgent (`src/agents/opencode.py`)

- Constructs `opencode run --model <model> --dangerously-skip-permissions [--file <path>] <prompt>`
- If prompt exceeds 100KB, writes prompt to `output_path /.writer_prompt.md` and uses `--file` to avoid ARG_MAX
- `stdin_mode = DEVNULL`, `get_stdin_data()` returns `None`
- `parse_status()` uses `STATUS:\s*(ACCEPT|REVISE)` regex (identical to GeminiAgent)

### GeminiAgent (`src/agents/gemini.py`)

- Constructs `gemini --model <model> --prompt - --skip-trust --approval-mode yolo --include-directories /codebase --include-directories /app/codebase --include-directories /output`
- `stdin_mode = PIPE`, `get_stdin_data()` returns `prompt.encode()`
- `parse_status()` regex-matches `STATUS: ACCEPT` or `STATUS: REVISE`
- Both agents are fully symmetric — any agent can serve as writer or reviewer

### Adding a new agent

```python
# src/agents/claude.py
class ClaudeAgent(Agent):
    name = "claude"
    def build_command(self, prompt, output_path, model):
        return ["claude", "--model", model, ...]

# Register it
from src.agents.claude import ClaudeAgent
register(ClaudeAgent)

# CLI: --writer-agent claude --writer-model claude-sonnet-4
```

### Writer Node

- Write `initial_idea.md` and any prior feedback as files to `/output/prompt_idea.md` and `/output/prior_feedback.md`
- Read file contents in Python and inject directly into the prompt string (avoids relying on `@filename` syntax)
- Resolve agent: `agent = get_agent(settings.writer_agent)`
- Delegate command building and I/O to the agent
- After subprocess completes, read `/output/roadmap.md` from disk
- Strip ANSI escape sequences from captured output (via `src/ansi.py`)
- Log all content to `iteration_logs` table
- Return updated state (iteration +1, no large text blobs)

### Reviewer Node

- Read both `initial_idea.md` and `roadmap.md`, construct review prompt
- Resolve agent: `agent = get_agent(settings.reviewer_agent)`
- Delegate command building, stdin data, and status parsing to the agent
- Write full reviewer stdout as `/output/prior_feedback.md` (after ANSI stripping)
- Log all content to `iteration_logs` table
- Return feedback and `is_stable` flag

## Docker Setup

### docker-compose.yml

Three services:
- `postgres`: standard postgres:16 with named volume for persistence
- `orchestrator`: one-shot service built from Dockerfile, depends on postgres
- `gui`: same image, runs `streamlit run gui/app.py`, port 8501

### Dockerfile notes

- Base: `python:3.12-slim`
- Install `curl` via `apt-get install -y curl` before Node setup (needed to download Node.js installer)
- Install Node.js via `apt-get` or the official Node setup script
- Install `opencode` via `npm install -g opencode-ai`
- Install `gemini` CLI — download binary with `curl` or `wget` (check distribution method)
- Set `ENV GEMINI_CLI_TRUST_WORKSPACE=true` in the Dockerfile for all commands globally

### Volume Mounts
- `~/.gemini/` → `/home/user/.gemini/` (Gemini OAuth credentials, **read-write** — token refresh requires write access)
- Target project dir → `/codebase` (read-only) — specified at runtime via `-v /path/to/target:/codebase:ro`
- Output dir → `/output` (writable for roadmap.md) — specified at runtime via `-v /path/to/output:/output`

### OpenCode auth
Appears to work without authentication so far. Before finalizing, verify by running `opencode run "hello"` inside the container during development. If an API key is needed, add it to `.env` and pass via environment variable or mount `~/.local/share/opencode/auth.json`.

## Usage

```bash
# 1. Start infra (postgres + optional GUI)
docker compose up -d postgres gui

# 2. Run the workflow (one-shot) — target codebase and output dir at runtime
docker compose run \
  -v /path/to/target-project:/codebase:ro \
  -v /path/to/output:/output \
  orchestrator \
  --idea /codebase/initial_idea.md \
  --project-dir /codebase \
  --output-dir /output \
  --max-iterations 6 \
  --writer-agent opencode \
  --writer-model opencode/deepseek-v4-flash-free \
  --reviewer-agent gemini \
  --reviewer-model gemini-2.0-flash

# 3. Browse logs at http://localhost:8501
```

## Subprocess TTY Handling

Both `opencode` and `gemini` CLI are designed for interactive terminals and may emit ANSI escape codes (spinners, colors, progress bars) or hang when run without a TTY.

Mitigations:

1. **PTY only for Writer**: `opencode run` may require a TTY. Use Python's `pty` module (or `ptyprocess`) for the Writer node subprocess.
2. **No PTY for Reviewer**: `gemini -` reads from stdin pipe — no TTY needed. It detects non-TTY stdin and disables interactive output automatically.
3. **ANSI stripping**: After capturing output, run it through a regex-based ANSI escape code stripper (`src/ansi.py`) before storing in state/DB.
4. **Non-interactive flags**: Pass `--no-color` if available. Verify via `opencode run --help`.
5. **Timeouts**: Every subprocess call has a hard timeout (default 300s, configurable) to catch hangs.

```python
# src/ansi.py
import re

_ansi_re = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def strip_ansi(text: str) -> str:
    return _ansi_re.sub('', text)
```

## GUI (Streamlit)

- Connect to the same PostgreSQL database
- Show all runs: ID, project, status, created_at
- Click a run to expand and see all iterations
- Each iteration shows: writer prompt/output, reviewer feedback, roadmap diff

## Edge Cases & Considerations

- **ARG_MAX limits**: Passing large prompts as CLI args can fail with "Argument list too long" (Linux: ~128KB per arg, ~2MB total). Writer: pass prompt as CLI positional if under 100KB; fall back to `--file` for larger prompts. Reviewer: pass prompt via `subprocess.communicate(input=...)` to stdin — no length limit.
- **PTY only for Writer**: `opencode run` may need a TTY. Reviewer (`gemini -`) reads stdin and auto-disables interactive mode — no PTY needed.
- **Dockerfile deps**: `python:3.12-slim` needs `curl` installed before Node.js setup script can run.
- **State redundancy**: `RoadmapState` stores only lightweight refs (run_id, iteration, flags). Full text content lives only in `iteration_logs` — avoids duplicating large blobs in LangGraph checkpointer.
- **Timeouts**: Each agent subprocess has a configurable timeout (default 300s) to prevent hangs with free models. Enforced via `subprocess.run(timeout=N)`.
- **Error recovery**: If an agent crashes or times out, the run is marked `failed` with preserved state for debugging. The `iteration_logs` table still retains all prior iterations.
- **Iteration limit**: Hard cap at 6 (configurable) to prevent infinite loops.
- **Structured review output**: Reviewer must output parseable STATUS. Wrap in markers like `---STATUS: ACCEPT---` or `---STATUS: REVISE---`.
- **Gemini OAuth token refresh**: Mount `~/.gemini/` as **read-write** (not read-only) so token refreshes don't crash the container.
- **OpenCode auth**: Verify during development. If API keys are needed, mount `~/.local/share/opencode/auth.json` or use env vars.
- **ANSI noise**: Strip ANSI escape codes from all captured agent output before storing to state or DB.
- **File safety**: Writer only has write access to `/output`; codebase must be mounted read-only by the user at runtime.
- **Gemini workspace**: Gemini CLI restricts file access to `/app` (its WORKDIR). The entrypoint creates a symlink `/app/codebase → /codebase` so gemini can access the codebase. opencode has no such restriction.
- **Shared filesystem**: Both agents share the same filesystem as the orchestrator via runtime mounts. Acceptable for a personal tool, but worth noting for security considerations.

## Implementation Tasks

Each task is atomic, independently testable, and builds on the previous one.

### Task 1 — Scaffold [DONE]
Create the project skeleton: `docker-compose.yml`, `Dockerfile`, `requirements.txt`, `.env.example`, and all directory stubs.

**Files**: `docker-compose.yml`, `Dockerfile`, `requirements.txt`, `.env.example`, `src/__init__.py`, `gui/__init__.py`, `src/nodes/__init__.py`

**Test**: `docker compose build` succeeds.

### Task 2 — Core utilities [DONE]
Implement `src/ansi.py` (ANSI escape stripping), `src/state.py` (RoadmapState TypedDict), `src/config.py` (Pydantic-settings with `WRITER_AGENT`, `WRITER_MODEL`, `REVIEWER_AGENT`, `REVIEWER_MODEL`, `WRITER_TIMEOUT`, `REVIEWER_TIMEOUT`, `MAX_ITERATIONS`, `PROJECT_PATH`, `OUTPUT_PATH` (default `/output`), `DATABASE_URL`). All settings read from env / `.env`, overridable by CLI args in main.py.

**Files**: `src/ansi.py`, `src/state.py`, `src/config.py`

**Test**: `python -c "from src.ansi import strip_ansi; assert strip_ansi('\x1b[31mhello\x1b[0m') == 'hello'"`

### Task 3 — Database layer [DONE]
Implement `src/db.py` with `iteration_logs` table creation (run via app start), insert helper, and query helper. Uses `psycopg2` connecting via `DATABASE_URL`.

**Files**: `src/db.py`

**Test**: Start postgres container, run a script that creates the table, inserts a row, queries it back.

### Task 4 — Writer node [DONE]
Implement `src/nodes/writer.py`. Reads `initial_idea.md` and prior feedback from `/output`, constructs prompt, runs `opencode run --model {model} {prompt}` as subprocess, captures output, strips ANSI, reads resulting `roadmap.md`, logs to DB.

**Files**: `src/nodes/writer.py`

**Test**: Place a test `initial_idea.md` in `/output`, run writer node standalone, verify `roadmap.md` is produced and DB has a row.

### Task 5 — Reviewer node [DONE]
Implement `src/nodes/reviewer.py`. Reads `initial_idea.md` (from `settings.idea_path`) and `roadmap.md` (from `settings.output_path`), constructs review prompt that includes both, passes it via `subprocess.Popen` with `stdin=subprocess.PIPE` + `communicate(input=prompt.encode())` to `gemini -`, parses response for `STATUS: ACCEPT` or `STATUS: REVISE`, logs to DB.

**Files**: `src/nodes/reviewer.py`

**Test**: Place a test `initial_idea.md` and `roadmap.md` in `/output`, run reviewer node standalone, verify it returns `is_stable=True/False` and DB has a row.

### Task 6 — Graph + CLI entry [DONE]
Implement `src/graph.py` (LangGraph StateGraph with writer→reviewer→conditional loop) and `src/main.py` (argparse CLI with `--idea`, `--project-dir`, `--output-dir`, `--max-iterations`, `--writer-agent`, `--writer-model`, `--reviewer-agent`, `--reviewer-model`). CLI args are written to config before graph execution.

**Files**: `src/graph.py`, `src/main.py`

**Test**: `docker compose run -v /path/to/target:/codebase:ro -v /path/to/output:/output orchestrator --idea /codebase/initial_idea.md --project-dir /codebase --output-dir /output --max-iterations 3 --writer-agent opencode --writer-model opencode/... --reviewer-agent gemini --reviewer-model gemini-2.0-flash` completes end-to-end.

### Task 7 — Streamlit GUI [IN PROGRESS]
Implement `gui/app.py`. Connects to PostgreSQL, lists runs, expands to show iterations (prompt, output, feedback, roadmap).

**Files**: `gui/app.py`

**Test**: `docker compose up gui`, open `http://localhost:8501`, see past runs.

### Task 8 — Agent abstraction layer [DONE]
Extract agent-specific subprocess logic into pluggable classes (`src/agents/`). Each agent (opencode, gemini) gets its own class with methods for command construction, stdin handling, and output parsing. Nodes use `get_agent(name)` to resolve the configured agent at runtime.

**Files**: `src/agents/__init__.py`, `src/agents/base.py`, `src/agents/opencode.py`, `src/agents/gemini.py`, `src/nodes/writer.py`, `src/nodes/reviewer.py`, `src/config.py`, `src/main.py`

**Test**: `python -c "from src.agents import get_agent; assert get_agent('opencode').name == 'opencode'; assert get_agent('gemini').name == 'gemini'"`

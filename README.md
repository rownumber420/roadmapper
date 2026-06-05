# Roadmapper

Automated project roadmaps via a Writer–Reviewer agent loop.

A LangGraph-based orchestrator that runs two AI agents in a feedback loop: a **Writer** generates a roadmap from an initial idea, and a **Reviewer** critiques it. The loop repeats until the roadmap is accepted or the iteration limit is reached.

## Prerequisites

- Docker + Docker Compose
- Authenticate in Gemini CLI on your host system first (run `gemini` and sign in); Docker copies `~/.gemini/` into the container.

## Quick start

### 1. Start infrastructure

```bash
docker compose up -d postgres gui
```

This starts PostgreSQL (state storage) and the Streamlit GUI (browse runs at `http://localhost:8501`).

### 2. Create a config file

A config file is a shell script that sets paths and parameters. Example (`my-project.orch`):

```bash
PROJECT_DIR=/home/user/my-project
IDEA_FILE=docs/initial_idea.md
OUTPUT_DIR=/home/user/my-project/output
MAX_ITERATIONS=10
WRITER_AGENT=opencode
WRITER_MODEL=opencode/deepseek-v4-flash-free
WRITER_TIMEOUT=300
REVIEWER_AGENT=gemini
REVIEWER_MODEL=gemini-3-flash-preview
REVIEWER_TIMEOUT=300
```

Paths can be absolute or relative to `PROJECT_DIR`.

### 3. Run the workflow

```bash
./run_roadmapper.sh my-project.orch
```

Preview the command without running:

```bash
./run_roadmapper.sh --dry-run my-project.orch
```

## Configuration

### Config file (`*.orch`) reference

| Variable | Default | Description |
|---|---|---|
| `PROJECT_DIR` | *(required)* | Host path to the project being roadmapped |
| `IDEA_FILE` | *(required)* | Path to the initial idea markdown file |
| `OUTPUT_DIR` | *(required)* | Host path where `roadmap.md` is written |
| `MAX_ITERATIONS` | `10` | Max Writer–Reviewer cycles |
| `WRITER_AGENT` | `opencode` | Agent to use for writing |
| `WRITER_MODEL` | `opencode/deepseek-v4-flash-free` | Model for the Writer |
| `WRITER_TIMEOUT` | `300` | Writer timeout (seconds) |
| `REVIEWER_AGENT` | `gemini` | Agent to use for reviewing |
| `REVIEWER_MODEL` | `gemini-3.1-flash-lite-preview` | Model for the Reviewer |
| `REVIEWER_TIMEOUT` | `300` | Reviewer timeout (seconds) |

### Environment variables (`.env`)

Same variables as above, read by `pydantic-settings` at runtime. Override with the config file or CLI flags.

## GUI

Open `http://localhost:8501` after starting the gui service. The dashboard shows all runs, their iterations, and a diff between consecutive revisions.

## Project structure

```
├── docker-compose.yml     # Infrastructure definition
├── Dockerfile              # Container image for orchestrator + gui
├── entrypoint.sh           # Container entrypoint (symlink, Gemini auth, dispatch)
├── run_roadmapper.sh       # Config-driven wrapper for docker compose run
├── fft.orch                # Example config file
├── .env.example            # Template for .env
├── GEMINI.md               # Gemini CLI setup guide
├── specs/archive/          # Example idea and output (project-specific)
├── gui/
│   └── app.py              # Streamlit run browser
└── src/
    ├── main.py             # CLI entry point
    ├── graph.py            # LangGraph state machine
    ├── config.py           # pydantic-settings config
    ├── db.py               # PostgreSQL iteration log CRUD
    ├── ansi.py             # ANSI escape code stripping
    ├── nodes/
    │   ├── writer.py       # Writer node (prompts opencode)
    │   └── reviewer.py     # Reviewer node (prompts gemini CLI)
    └── agents/
        ├── __init__.py     # Agent registry (register/get_agent)
        ├── base.py         # Agent ABC
        ├── opencode.py     # OpenCodeAgent — CLI arg prompt
        └── gemini.py       # GeminiAgent — stdin-piped prompt
```

## Common workflows

**Tune timeouts for large projects:**
```bash
WRITER_TIMEOUT=600 REVIEWER_TIMEOUT=600 ./run_roadmapper.sh my-project.orch
```

**Override agent/model per run:**
```bash
./run_roadmapper.sh my-project.orch --reviewer-model gemini-3-flash-preview
```

**Browse past runs:**
```bash
docker compose up -d gui
# → http://localhost:8501
```

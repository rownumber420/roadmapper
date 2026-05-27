# Project Memory

## Workflow Rules
- Never commit without explicit user approval.

## Architecture

Python 3.12 project that orchestrates a Writer–Reviewer agent loop using **LangGraph** to iteratively produce `roadmap.md` from `initial_idea.md`. Runs entirely in Docker (postgres + orchestrator + Streamlit GUI).

- **Writer**: subprocess → `opencode run --model <model> --dangerously-skip-permissions <prompt>`
- **Reviewer**: subprocess → `gemini --model <model> --prompt - --skip-trust --approval-mode yolo --include-directories /codebase` (prompt via stdin pipe)
- **State**: `RoadmapState` stores only lightweight refs (`run_id`, `iteration`, `is_stable`); full text lives in `iteration_logs` DB table
- **Persistence**: PostgreSQL via `/cockroach` psycopg2; LangGraph checkpointer + custom `iteration_logs` table

## Development

### Setup & Run (Docker only — no local Python env)
```bash
# Start infra
docker compose up -d postgres gui

# Run workflow
docker compose run \
  -v /path/to/target:/codebase:ro \
  -v /path/to/output:/output \
  orchestrator \
  --idea /codebase/initial_idea.md \
  --project-dir /codebase \
  --output-dir /output \
  --max-iterations 6 \
  --writer-model opencode/deepseek-v4-flash-free \
  --reviewer-model gemini-3.1-flash-lite-preview
```

### Key env vars (via `.env` or docker-compose environment)
`WRITER_MODEL`, `REVIEWER_MODEL`, `WRITER_TIMEOUT`, `REVIEWER_TIMEOUT`, `MAX_ITERATIONS`, `IDEA_PATH`, `OUTPUT_PATH`, `DATABASE_URL`

### Notable implementation details
- Entrypoint creates symlink `/app/codebase → /codebase` — Gemini CLI restricts file access to WORKDIR
- Writer prompt >100KB falls back from CLI arg to `--file` to avoid ARG_MAX
- ANSI escape codes stripped from all captured agent output via `src/ansi.py`
- `--dangerously-skip-permissions` required because opencode runs non-interactively (no TTY)
- Reviewer writes feedback to `/output/prior_feedback.md` so Writer can address it in the next iteration
- Reviewer parses response for `STATUS: ACCEPT` or `STATUS: REVISE` to set `is_stable`
- `gemini` OAuth token refresh needs `~/.gemini/` mounted **read-write**

### Files not yet implemented (as of this writing)
`src/main.py`, `src/graph.py`, `gui/app.py`

### Style
- `pydantic-settings` for config (reads env / `.env`, overridable by `configure()`)
- `psycopg2` (not async) for DB
- Errors: agent crashes/timeouts mark run as `failed` but preserve prior iterations in DB

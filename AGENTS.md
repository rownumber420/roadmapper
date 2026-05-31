# Project Memory

## Workflow Rules
- Never commit without explicit user approval.
- Never delete existing comments in the code.

## Architecture

Python 3.12 project that orchestrates a Writer–Reviewer agent loop using **LangGraph** to iteratively produce a project roadmap from an initial idea. Runs entirely in Docker (postgres + orchestrator + Streamlit GUI).

- **Writer**: subprocess → `opencode run --model <model> --dangerously-skip-permissions <prompt>`
- **Reviewer**: subprocess → `gemini --model <model> --prompt - --skip-trust --approval-mode yolo --include-directories /codebase` (prompt via stdin pipe)
- **State**: `RoadmapState` stores only lightweight refs (`run_id`, `iteration`, `is_stable`); full text lives in `iteration_logs` DB table
- **Persistence**: PostgreSQL via `/cockroach` psycopg2; LangGraph checkpointer + custom `iteration_logs` table

## Development

### Setup & Run (Docker only — no local Python env)

**Recommended** — use the wrapper script with a config file:
```bash
# Start infra
docker compose up -d postgres gui

# Run (see fft.orch for config format)
./run_roadmapper.sh my-project.orch
```

**Low-level** — raw `docker compose run`:
```bash
docker compose run \
  -v /path/to/target:/codebase:ro \
  -v /path/to/output:/output \
  orchestrator \
  --idea /codebase/specs/archive/initial_idea.md \
  --max-iterations 10 \
  --writer-agent opencode \
  --writer-model opencode/deepseek-v4-flash-free \
  --writer-timeout 300 \
  --reviewer-agent gemini \
  --reviewer-model gemini-3.1-flash-lite-preview \
  --reviewer-timeout 300
```

### Key env vars (via `.env` or docker-compose environment)
`WRITER_AGENT`, `WRITER_MODEL`, `WRITER_TIMEOUT`, `REVIEWER_AGENT`, `REVIEWER_MODEL`, `REVIEWER_TIMEOUT`, `MAX_ITERATIONS`, `IDEA_PATH`, `OUTPUT_PATH`, `DATABASE_URL`

### Notable implementation details
- Entrypoint creates symlink `/app/codebase → /codebase` — Gemini CLI restricts file access to WORKDIR
- Entrypoint uses `${1#-}` flag-detection to distinguish `orchestrator --flags` from `streamlit run gui/app.py`
- `run_roadmapper.sh` resolves host paths, translates them to container paths, and builds the `docker compose run` command; supports `--dry-run` for preview
- Config files (`*.orch`) are shell-sourced variables — absolute paths are stripped to a `PROJECT_DIR`-relative form for the `--idea` container path
- Writer prompt >100KB falls back from CLI arg to `--file` to avoid ARG_MAX
- ANSI escape codes stripped from all captured agent output via `src/ansi.py`
- `--dangerously-skip-permissions` required because opencode runs non-interactively (no TTY)
- Reviewer writes feedback to `/output/prior_feedback.md` so Writer can address it in the next iteration
- Reviewer parses response for `STATUS: ACCEPT` or `STATUS: REVISE` to set `is_stable`
- `gemini` OAuth token refresh needs `~/.gemini/` mounted **read-write**

### Style
- `pydantic-settings` for config (reads env / `.env`, overridable by `configure()`)
- `psycopg2` (not async) for DB
- Errors: agent crashes/timeouts mark run as `failed` but preserve prior iterations in DB

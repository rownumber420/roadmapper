#!/bin/bash
# run_roadmapper.sh — convenience wrapper around `docker compose run orchestrator`.
#
# Loads project settings from a config file (source-able shell variables),
# translates host paths to container paths, and runs the orchestrator.
#
# Usage:
#   ./run_roadmapper.sh [--dry-run] <config-file> [extra docker args...]

set -e  # exit immediately if any command fails

# ── Parse optional --dry-run flag ──────────────────────────────────────────
DRY_RUN=false
if [ "$1" = "--dry-run" ]; then
  DRY_RUN=true
  shift  # remove --dry-run from the argument list so $1 becomes the config path
fi

# ── Read config file ───────────────────────────────────────────────────────
# ${1:?...} means: use $1, but if it's unset/empty, print the error message and exit.
CONFIG="${1:?Usage: $0 [--dry-run] <config-file> [extra-opts...]}"
shift  # remove config path from args; remaining $@ will be passed to the container

# `source` reads the file as shell commands — the file must set variables like
# PROJECT_DIR, IDEA_FILE, etc. (see fft.orch for an example).
source "$CONFIG"

# ── Resolve host paths ─────────────────────────────────────────────────────
# realpath resolves symlinks, relative paths (".."), and trailing slashes,
# producing an absolute canonical path.  If PROJECT_DIR doesn't exist, it fails.
PROJECT_DIR="$(realpath "$PROJECT_DIR")"

# IDEA_FILE can be absolute (e.g. /home/user/project/idea.md) or relative
# (e.g. research/idea.md, meaning $PROJECT_DIR/research/idea.md).
# If absolute, strip the PROJECT_DIR prefix to get the relative part for the container.
if [[ "$IDEA_FILE" = /* ]]; then
  # ${VAR#PREFIX} removes the shortest leading PREFIX from the value of VAR.
  # Example: IDEA_FILE=/home/user/proj/research/idea.md, PROJECT_DIR=/home/user/proj
  #   → REL_IDEA = research/idea.md
  REL_IDEA="${IDEA_FILE#$PROJECT_DIR/}"
else
  REL_IDEA="$IDEA_FILE"
fi

# OUTPUT_DIR follows the same logic.
if [[ "$OUTPUT_DIR" = /* ]]; then
  OUTPUT_DIR="$OUTPUT_DIR"
else
  OUTPUT_DIR="$PROJECT_DIR/$OUTPUT_DIR"
fi

# ── Apply defaults for any setting not defined in the config ───────────────
# ${VAR:-default} means: use $VAR if set (even if empty), otherwise use "default".
TASK_ID="${TASK_ID:-}"
MAX_ITERATIONS="${MAX_ITERATIONS:-10}"
WRITER_AGENT="${WRITER_AGENT:-opencode}"
WRITER_MODEL="${WRITER_MODEL:-opencode/deepseek-v4-flash-free}"
WRITER_TIMEOUT="${WRITER_TIMEOUT:-300}"
REVIEWER_AGENT="${REVIEWER_AGENT:-gemini}"
REVIEWER_MODEL="${REVIEWER_MODEL:-gemini-3-flash-preview}"
REVIEWER_TIMEOUT="${REVIEWER_TIMEOUT:-300}"

# ── Build orchestrator args ─────────────────────────────────────────────────
ORCH_ARGS=(
  --idea "/app/codebase/$REL_IDEA"
  --max-iterations "$MAX_ITERATIONS"
  --writer-agent "$WRITER_AGENT"
  --writer-model "$WRITER_MODEL"
  --writer-timeout "$WRITER_TIMEOUT"
  --reviewer-agent "$REVIEWER_AGENT"
  --reviewer-model "$REVIEWER_MODEL"
  --reviewer-timeout "$REVIEWER_TIMEOUT"
)
[ -n "$TASK_ID" ] && ORCH_ARGS+=(--task-id "$TASK_ID")

# ── Build the docker compose command as an array ───────────────────────────
# Each element is one word ("$@" is expanded separately at the end), so paths
# with spaces stay intact.
CMD=(docker compose run --rm
  -v "$PROJECT_DIR:/codebase:ro"
  -v "$OUTPUT_DIR:/output"
  orchestrator
  "${ORCH_ARGS[@]}"
  "$@"
)

# ── Execute (or dry-run) ───────────────────────────────────────────────────
if [ "$DRY_RUN" = true ]; then
  # "${CMD[*]}" joins all array elements with a space — good for display.
  echo "${CMD[*]}"
else
  # exec replaces this shell process with the command (no extra subprocess).
  # "${CMD[@]}" expands each element as a separate word — safe for quoting.
  exec "${CMD[@]}"
fi

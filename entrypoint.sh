#!/bin/bash
# entrypoint.sh — container entrypoint for the roadmapper orchestrator image.
#
# Responsibilities:
#   1. Create /app/codebase → /codebase symlink (Gemini CLI restricts file
#      access to WORKDIR, so codebase files must be reachable under /app).
#   2. Copy Gemini OAuth credentials from a host mount if present.
#   3. Run the Python orchestrator (src.main) when CLI flags are passed,
#      otherwise execute whatever command was given (e.g. a shell for
#      debugging, or the Streamlit GUI server).

set -e  # exit immediately if any command fails

# ── Symlink /codebase into the app directory ───────────────────────────────
# The host mounts the target project at /codebase (read-only).
# The symlink at /app/codebase makes it appear under the WORKDIR so that
# the Gemini CLI, which only allows reading files within WORKDIR, can access it.
ln -sf /codebase /app/codebase

# ── Bootstrap Gemini OAuth credentials (first run only) ────────────────────
# -d FILE: true if FILE exists and is a directory.
# ! -f FILE: true if FILE does NOT exist.
# && chains: both conditions must be true.
# If the user mounted their host ~/.gemini/ at /mnt/host-gemini (read-write),
# copy the credentials into the appuser home so the Gemini CLI can authenticate.
if [ -d /mnt/host-gemini ] && [ ! -f /home/appuser/.gemini/oauth_creds.json ]; then
  echo "Initializing gemini config from host mount..."
  mkdir -p /home/appuser/.gemini
  cp -r /mnt/host-gemini/. /home/appuser/.gemini/
  chown -R appuser:appuser /home/appuser/.gemini/
fi

# ── Decide what to run ─────────────────────────────────────────────────────
# $# expands to the number of positional arguments.
# "${1#-}" strips a leading dash from $1. If the result differs from $1,
# then $1 starts with "-" (i.e. it's a flag like --idea), so assume we
# should run the Python orchestrator with all arguments.
#
# exec replaces this shell process with the given command — no extra
# subprocess remains.  gosu drops privileges from root to appuser before
# running the command (security best practice).
if [ $# -gt 0 ] && [ "${1#-}" != "$1" ]; then
  exec gosu appuser python -m src.main "$@"
fi

# No flags or no arguments at all → run whatever was passed as CMD
# (e.g. "streamlit run gui/app.py" or "/bin/bash").
exec gosu appuser "$@"

import re
import subprocess
from pathlib import Path

from src.ansi import strip_ansi
from src.config import get_settings
from src.db import insert_log


def build_review_prompt(initial_idea: str, roadmap_content: str) -> str:
    return f"""You are in /app. The target codebase is mounted at /codebase
and also accessible via /app/codebase (symlink). Explore /codebase
thoroughly before writing — understand the project structure, existing
code conventions, directory layout, package structure, and any existing
configuration files.

Look for context files in /codebase that document project conventions
(e.g. AGENTS.md, GEMINI.md, .opencode.json, CLAUDE.md, etc.).
Use them to align the roadmap with the project's actual setup.

Review this roadmap for correctness, bugs, and feasibility.
Check that:
- All requirements in the initial idea are addressed by the roadmap
- Each task is atomic (one deliverable each)
- Each task has a clear verification step
- Referenced file paths and modules actually exist
- Code examples match the project's real patterns and conventions
- Proposed tasks are compatible with the existing architecture
- Scope is proportional (no gold-plating, no omissions)

Output FEEDBACK: <issues> and STATUS: ACCEPT or REVISE. Be critical.

INITIAL IDEA:
{initial_idea}

ROADMAP:
{roadmap_content}
"""


def reviewer_node(state: dict) -> dict:
    settings = get_settings()

    idea_path = Path(settings.idea_path)
    output_path = Path(settings.output_path)
    roadmap_path = output_path / "roadmap.md"

    initial_idea = idea_path.read_text()
    roadmap_content = roadmap_path.read_text()

    prompt = build_review_prompt(initial_idea, roadmap_content)

    proc = subprocess.Popen(
        [
            "gemini",
            "--model", settings.reviewer_model,
            "--prompt", "-",
            "--skip-trust",
            "--approval-mode", "yolo",
            "--include-directories", "/codebase",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
    )
    stdout, stderr = proc.communicate(
        input=prompt.encode(), timeout=settings.reviewer_timeout
    )

    stdout_str = (
        stdout.decode(errors="replace") if isinstance(stdout, bytes) else ""
    )
    stderr_str = (
        stderr.decode(errors="replace") if isinstance(stderr, bytes) else ""
    )

    (output_path / "prior_feedback.md").write_text(stdout_str)

    status_match = re.search(
        r"STATUS:\s*(ACCEPT|REVISE)", stdout_str, re.IGNORECASE
    )
    is_stable = bool(status_match and status_match.group(1).upper() == "ACCEPT")

    run_id = state.get("run_id", "")
    iteration = state.get("iteration", 0)

    insert_log(
        run_id=run_id,
        iteration=iteration,
        node_type="reviewer",
        raw_output=strip_ansi(stdout_str + "\n" + stderr_str),
        feedback=stdout_str,
        roadmap_content=roadmap_content,
        prompt=prompt,
    )

    return {
        "run_id": run_id,
        "iteration": iteration,
        "is_stable": is_stable,
    }

import subprocess
from pathlib import Path

from src.agents import get_agent
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

THIS IS A ROADMAP REVIEW ONLY. DO NOT modify any files. DO NOT write code.
DO NOT create, edit, or delete any files. Read-only analysis.

Review this roadmap for correctness, bugs, and feasibility.
Check that:
- All requirements in the initial idea are addressed by the roadmap
- Each task is atomic (one deliverable each)
- Each task has a clear verification step
- Referenced file paths and modules actually exist
- Code examples match the project's real patterns and conventions
- Proposed tasks are compatible with the existing architecture
- Scope is proportional (no gold-plating, no omissions)

List all issues under FEEDBACK: <issues>. Then output STATUS: ACCEPT or REVISE.
Only use STATUS: ACCEPT if the roadmap has zero issues — no errors, no omissions,
no concerns at all. If you have even one actionable item under <issues>, use STATUS: REVISE.
Be critical.

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

    agent = get_agent(settings.reviewer_agent)
    cmd = agent.build_command(prompt, output_path, settings.reviewer_model)

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=agent.stdin_mode,
    )

    timed_out = False
    try:
        stdout, stderr = proc.communicate(
            input=agent.get_stdin_data(prompt), timeout=settings.reviewer_timeout
        )
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        timed_out = True

    stdout_str = (
        stdout.decode(errors="replace") if isinstance(stdout, bytes) else ""
    )
    stderr_str = (
        stderr.decode(errors="replace") if isinstance(stderr, bytes) else ""
    )

    (output_path / "prior_feedback.md").write_text(strip_ansi(stdout_str))

    is_stable = agent.parse_status(stdout_str)

    run_id = state.get("run_id", "")
    iteration = state.get("iteration", 0)

    insert_log(
        run_id=run_id,
        iteration=iteration,
        node_type="reviewer",
        raw_output=strip_ansi(stdout_str + "\n" + stderr_str),
        feedback=strip_ansi(stdout_str),
        roadmap_content=roadmap_content,
        prompt=prompt,
    )

    if timed_out:
        raise subprocess.TimeoutExpired(proc.args, settings.reviewer_timeout)

    return {
        "run_id": run_id,
        "iteration": iteration,
        "is_stable": is_stable,
    }

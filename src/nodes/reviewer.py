import re
import subprocess
from pathlib import Path

from src.agents import get_agent
from src.ansi import strip_ansi
from src.config import get_settings
from src.db import insert_log


def build_review_prompt(initial_idea: str, roadmap_content: str) -> str:
    return f"""You are reviewing a roadmap for the codebase at /app/codebase.

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

Read the specific files needed to verify roadmap claims.
Try not to glob or grep the entire codebase.

Your response must follow this structure:

FEEDBACK:
- <each issue on its own line>

STATUS: ACCEPT or STATUS: REVISE

Only use STATUS: ACCEPT if the roadmap has zero issues — no errors, no omissions,
no concerns at all. If you have even one actionable item, use STATUS: REVISE.
Be critical.

The very last line of your response MUST be exactly one of:
STATUS: ACCEPT
STATUS: REVISE

INITIAL IDEA:
{initial_idea}

ROADMAP:
{roadmap_content}
"""


def parse_status(stdout: str) -> bool:
    """Parse the agent's captured stdout to determine if the review passed."""
    match = re.search(
        r"STATUS:\s*(ACCEPT|REVISE)", stdout, re.IGNORECASE
    )
    return bool(match and match.group(1).upper() == "ACCEPT")


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

    full_text = strip_ansi(stdout_str)

    # strip out any conversational preamble the agent may produce before the structured FEEDBACK: section
    feedback_text = full_text
    if "FEEDBACK:" in full_text:
        feedback_text = "FEEDBACK:" + full_text.split("FEEDBACK:", 1)[1]

    (output_path / "prior_feedback.md").write_text(feedback_text)

    is_stable = parse_status(stdout_str)

    run_id = state.get("run_id", "")
    iteration = state.get("iteration", 0)

    insert_log(
        run_id=run_id,
        iteration=iteration,
        node_type="reviewer",
        raw_output=strip_ansi(stdout_str + "\n" + stderr_str),
        feedback=feedback_text,
        roadmap_content=roadmap_content,
        prompt=prompt,
    )

    if timed_out:
        raise subprocess.TimeoutExpired(proc.args, settings.reviewer_timeout)

    return {
        "iteration": iteration,
        "is_stable": is_stable,
    }

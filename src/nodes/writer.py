import subprocess
from pathlib import Path

from src.agents import get_agent
from src.ansi import strip_ansi
from src.config import get_settings
from src.db import insert_log


def build_prompt(initial_idea: str, prior_feedback: str = "") -> str:
    feedback_section = ""
    if prior_feedback:
        feedback_section = f"PREVIOUS FEEDBACK TO ADDRESS:\n{prior_feedback}\n"

    return f"""You are in /app. The target codebase is at /app/codebase.
Explore it thoroughly — understand the project structure, existing code
conventions, directory layout, package structure, and any existing
configuration files.

Look for context files in /app/codebase that document project conventions
(e.g. AGENTS.md, GEMINI.md, .opencode.json, CLAUDE.md, etc.).
Use them to align the roadmap with the project's actual setup.

Read the initial idea below and create a roadmap.md file at /output/roadmap.md.
Each task should:
- Be atomic (one deliverable each)
- Reference real file paths in /app/codebase
- Include a short code example or diff where applicable
- Have a clear verification step

Only create /output/roadmap.md. Do not modify anything in /app/codebase.

If the PREVIOUS FEEDBACK contains an item you believe is a false alarm
or based on a misunderstanding, you may note your reasoning in the roadmap
rather than making the requested change. Explain clearly why the feedback
does not apply.

{feedback_section}

INITIAL IDEA:
{initial_idea}
"""


def writer_node(state: dict) -> dict:
    settings = get_settings()

    idea_path = Path(settings.idea_path)
    output_path = Path(settings.output_path)

    initial_idea = idea_path.read_text()

    prior_feedback_path = output_path / "prior_feedback.md"
    prior_feedback = (
        prior_feedback_path.read_text() if prior_feedback_path.exists() else ""
    )

    prompt = build_prompt(initial_idea, prior_feedback)

    agent = get_agent(settings.writer_agent)
    cmd = agent.build_command(prompt, output_path, settings.writer_model)

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=agent.stdin_mode,
    )

    timed_out = False
    try:
        stdout, stderr = proc.communicate(
            input=agent.get_stdin_data(prompt), timeout=settings.writer_timeout
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

    roadmap_path = output_path / "roadmap.md"
    roadmap_content = roadmap_path.read_text() if roadmap_path.exists() else ""

    run_id = state.get("run_id", "")
    iteration = state.get("iteration", 0) + 1

    insert_log(
        run_id=run_id,
        iteration=iteration,
        node_type="writer",
        raw_output=strip_ansi(stdout_str + "\n" + stderr_str),
        roadmap_content=roadmap_content,
        prompt=prompt,
    )

    if timed_out:
        raise subprocess.TimeoutExpired(proc.args, settings.writer_timeout)

    return {
        "iteration": iteration,
    }

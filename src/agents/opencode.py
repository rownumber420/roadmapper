import subprocess
from pathlib import Path

from src.agents.base import Agent


class OpenCodeAgent(Agent):
    """Prompt goes as a CLI argument (or as a temp file reference when too long for ARG_MAX). Stdin is unused."""
    name = "opencode"

    def build_command(
        self, prompt: str, output_path: Path, model: str
    ) -> list[str]:
        prompt_bytes = prompt.encode()
        if len(prompt_bytes) > 100_000:
            prompt_path = output_path / ".writer_prompt.md"
            prompt_path.write_text(prompt)
            return [
                "opencode", "run",
                "--model", model,
                "--dangerously-skip-permissions",
                "--file", str(prompt_path),
                "Follow the instructions in the attached file.",
            ]
        return [
            "opencode", "run",
            "--model", model,
            "--dangerously-skip-permissions",
            prompt,
        ]

    @property
    def stdin_mode(self) -> int:
        return subprocess.DEVNULL  # agent doesn't read stdin, pipe is closed

import re
import subprocess
from pathlib import Path

from src.agents.base import Agent


class OpenCodeAgent(Agent):
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

    def parse_status(self, stdout: str) -> bool:
        match = re.search(
            r"STATUS:\s*(ACCEPT|REVISE)", stdout, re.IGNORECASE
        )
        return bool(match and match.group(1).upper() == "ACCEPT")

    @property
    def stdin_mode(self) -> int:
        return subprocess.DEVNULL

import re
import subprocess
from pathlib import Path

from src.agents.base import Agent


class GeminiAgent(Agent):
    name = "gemini"

    def build_command(
        self, prompt: str, output_path: Path, model: str
    ) -> list[str]:
        return [
            "gemini",
            "--model", model,
            "--prompt", "-",
            "--skip-trust",
            "--approval-mode", "yolo",
            "--include-directories", "/codebase",
            "--include-directories", "/app/codebase",
            "--include-directories", "/output",
        ]

    def get_stdin_data(self, prompt: str) -> bytes:
        return prompt.encode()

    @property
    def stdin_mode(self) -> int:
        return subprocess.PIPE

    def parse_status(self, stdout: str) -> bool:
        match = re.search(
            r"STATUS:\s*(ACCEPT|REVISE)", stdout, re.IGNORECASE
        )
        return bool(match and match.group(1).upper() == "ACCEPT")

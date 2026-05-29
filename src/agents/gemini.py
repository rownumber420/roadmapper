import subprocess
from pathlib import Path

from src.agents.base import Agent


class GeminiAgent(Agent):
    """Prompt goes through stdin pipe. The node opens a PIPE, writes encoded prompt bytes via proc.communicate(input=...)"""
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
            "--include-directories", "/output",
        ]

    def get_stdin_data(self, prompt: str) -> bytes:
        return prompt.encode()

    @property
    def stdin_mode(self) -> int:
        return subprocess.PIPE

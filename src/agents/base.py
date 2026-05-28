import subprocess
from abc import ABC, abstractmethod
from pathlib import Path


class AgentResult:
    def __init__(self, stdout: str, stderr: str):
        self.stdout = stdout
        self.stderr = stderr


class Agent(ABC):
    name: str = ""

    @abstractmethod
    def build_command(
        self, prompt: str, output_path: Path, model: str
    ) -> list[str]:
        ...

    def get_stdin_data(self, prompt: str) -> bytes | None:
        return None

    @property
    def stdin_mode(self) -> int:
        return subprocess.DEVNULL

    @abstractmethod
    def parse_status(self, stdout: str) -> bool:
        ...

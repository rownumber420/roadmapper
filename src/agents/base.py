import subprocess
from abc import ABC, abstractmethod
from pathlib import Path


class AgentResult:
    def __init__(self, stdout: str, stderr: str):
        self.stdout = stdout
        self.stderr = stderr


class Agent(ABC):
    """
    prompt delivery:
    cmd = agent.build_command(prompt, output_path, model)
    proc = subprocess.Popen(cmd, stdin=agent.stdin_mode)
    stdout, stderr = proc.communicate(input=agent.get_stdin_data(prompt)) 
    """
    name: str = ""

    @abstractmethod
    def build_command(
        self, prompt: str, output_path: Path, model: str
    ) -> list[str]:
        """Build the shell command to invoke the agent subprocess."""

    def get_stdin_data(self, prompt: str) -> bytes | None:
        """Return bytes to pipe to the agent's stdin, or None to send nothing."""

    @property
    def stdin_mode(self) -> int:
        """Return the stdin argument for subprocess.Popen: PIPE to send data, DEVNULL to close it."""

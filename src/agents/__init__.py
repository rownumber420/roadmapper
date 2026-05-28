from src.agents.base import Agent, AgentResult
from src.agents.gemini import GeminiAgent
from src.agents.opencode import OpenCodeAgent

_registry: dict[str, type[Agent]] = {}


def register(cls: type[Agent]) -> None:
    _registry[cls.name] = cls


def get_agent(name: str) -> Agent:
    cls = _registry.get(name)
    if cls is None:
        raise ValueError(
            f"Unknown agent: '{name}'. Available: {list(_registry.keys())}"
        )
    return cls()


register(OpenCodeAgent)
register(GeminiAgent)


__all__ = ["Agent", "AgentResult", "get_agent", "register"]

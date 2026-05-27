from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

_settings: Optional["Settings"] = None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    writer_model: str = "opencode/deepseek-v4-flash-free"
    reviewer_model: str = "gemini-3.1-flash-lite-preview"
    writer_timeout: int = 300
    reviewer_timeout: int = 300
    max_iterations: int = 6
    project_path: str = "/codebase"
    idea_path: str = "/codebase/initial_idea.md"
    output_path: str = "/output"
    database_url: str = (
        "postgresql://roadmapper:roadmapper@postgres:5432/roadmapper"
    )


def get_settings() -> "Settings":
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def configure(**overrides) -> "Settings":
    global _settings
    _settings = Settings(**overrides)
    return _settings

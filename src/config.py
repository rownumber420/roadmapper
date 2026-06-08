from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

# Singleton — lazily init'd by get_settings(), cached for subsequent calls
_settings: Optional["Settings"] = None


class Settings(BaseSettings):
    # pydantic-settings: resolves config from env vars, .env, and
    # explicit overrides in order of increasing priority
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    task_id: Optional[str] = None
    writer_agent: str = "opencode"
    writer_model: str = "opencode/deepseek-v4-flash-free"
    reviewer_agent: str = "gemini"
    reviewer_model: str = "gemini-3.1-flash-lite-preview"
    writer_timeout: int = 300
    reviewer_timeout: int = 300
    max_iterations: int = 6
    idea_path: str = "/app/codebase/initial_idea.md"
    output_path: str = "/output"
    database_url: str = (
        "postgresql://roadmapper:roadmapper@postgres:5432/roadmapper"
    )


# Singleton accessor — lazy-initialises the single Settings instance
# on first call and returns it on all subsequent calls.
def get_settings() -> "Settings":
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# Builder-style factory: reconstructs the Settings object from scratch
# with overrides merged on top of env/file defaults.
def configure(**overrides) -> "Settings":
    global _settings
    _settings = Settings(**overrides)
    return _settings

import logging
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> parents[2] == backend root (where .env lives)
BACKEND_ROOT: Path = Path(__file__).resolve().parents[2]
ENV_FILE_PATH: Path = BACKEND_ROOT / ".env"

_logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    app_name: str = Field(default="Candid API", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    api_prefix: str = Field(default="/api/v1", alias="API_PREFIX")
    frontend_origin: str = Field(default="http://localhost:5173", alias="FRONTEND_ORIGIN")

    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")
    claude_model: str = Field(default="claude-sonnet-4-20250514", alias="CLAUDE_MODEL")
    # Max new tokens per assistant message (tune via CLAUDE_MAX_OUTPUT_TOKENS; respect model limits).
    claude_max_output_tokens: int = Field(
        default=8192,
        ge=256,
        le=64000,
        alias="CLAUDE_MAX_OUTPUT_TOKENS",
    )

    chroma_persist_dir: str = Field(default="./data/chroma", alias="CHROMA_PERSIST_DIR")

    tiktok_headless: bool = Field(default=True, alias="TIKTOK_HEADLESS")
    tiktok_locale: str = Field(default="en-US", alias="TIKTOK_LOCALE")
    tiktok_timeout_seconds: int = Field(default=20, alias="TIKTOK_TIMEOUT_SECONDS")

    reddit_user_agent: str = Field(
        default="CandidBot/0.1 (+https://example.com)",
        alias="REDDIT_USER_AGENT",
    )
    reddit_timeout_seconds: int = Field(default=20, alias="REDDIT_TIMEOUT_SECONDS")

    enable_safety_filter: bool = Field(default=True, alias="ENABLE_SAFETY_FILTER")

    tiktok_user_agent: str = Field(default="", alias="TIKTOK_USER_AGENT")
    tiktok_session_cookie: str = Field(default="", alias="TIKTOK_SESSION_COOKIE")
    tiktok_proxy_url: str = Field(default="", alias="TIKTOK_PROXY_URL")
    tiktok_wait_ms: int = Field(default=2500, alias="TIKTOK_WAIT_MS")
    playwright_browsers_path: str = Field(default="", alias="PLAYWRIGHT_BROWSERS_PATH")

    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("anthropic_api_key", mode="after")
    @classmethod
    def anthropic_key_nonempty(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("ANTHROPIC_API_KEY is required and must be non-empty")
        return s

    def has_claude_key(self) -> bool:
        return bool(self.anthropic_api_key and self.anthropic_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


def log_env_debug_status() -> None:
    """Temporary safe startup hint: never logs secrets."""
    s = get_settings()
    _logger.info(
        "Config env: env_file=%s env_file_exists=%s anthropic_key_present=%s claude_model=%s",
        ENV_FILE_PATH,
        ENV_FILE_PATH.is_file(),
        s.has_claude_key(),
        s.claude_model,
    )

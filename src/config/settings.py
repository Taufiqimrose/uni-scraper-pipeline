from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # --- Required ---
    OPENAI_API_KEY: str
    DATABASE_URL: str
    API_KEY: str

    # --- Server ---
    ENVIRONMENT: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    # --- OpenAI ---
    OPENAI_MODEL: str = "gpt-4o"
    TOKEN_BUDGET: int = 2_000_000

    # --- Browser ---
    BROWSER_POOL_SIZE: int = 3
    RATE_LIMIT_DELAY: float = 2.0
    PAGE_TIMEOUT_MS: int = 30_000

    # --- Cache ---
    CACHE_TTL_HOURS: int = 24

    # --- Logging ---
    LOG_LEVEL: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


def get_settings() -> Settings:
    """Create and return a Settings instance."""
    return Settings()  # type: ignore[call-arg]

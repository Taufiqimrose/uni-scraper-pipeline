from pydantic import computed_field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # --- Required ---
    OPENAI_API_KEY: str
    DATABASE_URL: str
    API_KEY: str

    # --- Search ---
    SERP_API_KEY: str = ""

    # --- Server ---
    ENVIRONMENT: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse comma-separated ALLOWED_ORIGINS into a list."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    # --- OpenAI ---
    OPENAI_MODEL: str = "gpt-4o"
    TOKEN_BUDGET: int = 2_000_000
    # Max tokens for page content in extractor (reserve rest for system prompt + response).
    # Defaults by model: gpt-4o/4.1 ~100k, gpt-5.x ~350k. Override for custom models.
    MAX_CONTENT_TOKENS: int | None = None

    # --- Browser ---
    BROWSER_POOL_SIZE: int = 3
    RATE_LIMIT_DELAY: float = 2.0
    PAGE_TIMEOUT_MS: int = 30_000

    # --- Cache ---
    CACHE_TTL_HOURS: int = 24

    # --- Logging ---
    LOG_LEVEL: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    # Suggested max content tokens by model (context - system - response reserve)
    _MODEL_CONTEXT_HINTS: dict[str, int] = {
        "gpt-4o": 100_000,
        "gpt-4.1": 100_000,
        "gpt-4.1-mini": 100_000,
        "gpt-4.1-nano": 100_000,
        "gpt-5": 350_000,
        "gpt-5.1": 350_000,
        "gpt-5.2": 350_000,
        "gpt-5-mini": 350_000,
        "gpt-5-nano": 350_000,
    }

    def get_max_content_tokens(self) -> int:
        """Max tokens for extractor page content. Uses MAX_CONTENT_TOKENS or model hint."""
        if self.MAX_CONTENT_TOKENS is not None:
            return self.MAX_CONTENT_TOKENS
        model_lower = self.OPENAI_MODEL.lower()
        # Match longest prefix first (e.g. gpt-5.2 before gpt-5)
        for prefix in sorted(self._MODEL_CONTEXT_HINTS.keys(), key=len, reverse=True):
            if model_lower.startswith(prefix):
                return self._MODEL_CONTEXT_HINTS[prefix]
        return 100_000  # safe default for unknown models


def get_settings() -> Settings:
    """Create and return a Settings instance."""
    return Settings()  # type: ignore[call-arg]

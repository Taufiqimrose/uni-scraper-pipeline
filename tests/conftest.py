import pytest

from src.config.settings import Settings


@pytest.fixture
def settings() -> Settings:
    """Test settings."""
    return Settings(
        DATABASE_URL="postgresql://test:test@localhost:5432/uni_scraper_test",
        OPENAI_API_KEY="test-key",
        API_KEY="test-api-key",
        ENVIRONMENT="test",
        BROWSER_POOL_SIZE=1,
    )

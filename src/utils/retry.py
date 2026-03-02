import logging
import re

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

def parse_openai_retry_after(error: Exception) -> float | None:
    """Parse 'Please try again in X.XXs' from OpenAI rate limit errors. Returns seconds or None."""
    msg = str(error)
    m = re.search(r"try again in ([\d.]+)s", msg, re.IGNORECASE)
    return float(m.group(1)) if m else None


# Retry decorator for page fetching
fetch_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=5, min=5, max=60),
    retry=retry_if_exception_type((TimeoutError, ConnectionError, OSError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)

# Retry decorator for OpenAI API calls (includes rate limit)
try:
    from openai import RateLimitError
    _LLM_RETRY_EXCEPTIONS = (TimeoutError, ConnectionError, RateLimitError)
except ImportError:
    _LLM_RETRY_EXCEPTIONS = (TimeoutError, ConnectionError)

llm_retry = retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=3, min=10, max=90),
    retry=retry_if_exception_type(_LLM_RETRY_EXCEPTIONS),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)

# Retry decorator for database operations
db_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((ConnectionError, OSError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)

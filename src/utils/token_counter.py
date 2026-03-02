import tiktoken


# Cache encodings by model
_encodings: dict[str, tiktoken.Encoding] = {}
_DEFAULT_MODEL = "gpt-4o"


def _get_encoding(model: str | None = None) -> tiktoken.Encoding:
    """Get tiktoken encoding for a model. Falls back to cl100k_base for unknown models."""
    key = model or _DEFAULT_MODEL
    if key not in _encodings:
        try:
            _encodings[key] = tiktoken.encoding_for_model(key)
        except KeyError:
            _encodings[key] = tiktoken.get_encoding("cl100k_base")
    return _encodings[key]


def count_tokens(text: str, model: str | None = None) -> int:
    """Count the number of tokens in a text string."""
    return len(_get_encoding(model).encode(text))


def truncate_to_tokens(text: str, max_tokens: int, model: str | None = None) -> str:
    """Truncate text to a maximum number of tokens."""
    encoding = _get_encoding(model)
    tokens = encoding.encode(text)
    if len(tokens) <= max_tokens:
        return text
    truncated = encoding.decode(tokens[:max_tokens])
    return truncated + "\n\n[... truncated to fit token limit ...]"


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    """Estimate the cost of a GPT-4o API call in USD.

    Prices as of 2025: $2.50/1M input, $10/1M output.
    """
    input_cost = (input_tokens / 1_000_000) * 2.50
    output_cost = (output_tokens / 1_000_000) * 10.00
    return round(input_cost + output_cost, 4)

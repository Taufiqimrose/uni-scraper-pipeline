import tiktoken


# Cache the encoding to avoid re-creating it
_encoding: tiktoken.Encoding | None = None


def _get_encoding() -> tiktoken.Encoding:
    global _encoding
    if _encoding is None:
        _encoding = tiktoken.encoding_for_model("gpt-4o")
    return _encoding


def count_tokens(text: str) -> int:
    """Count the number of tokens in a text string for GPT-4o."""
    return len(_get_encoding().encode(text))


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate text to a maximum number of tokens."""
    encoding = _get_encoding()
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

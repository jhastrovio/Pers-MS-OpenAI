"""Utility functions for tokenization and chunking."""

from typing import List

# Optional tiktoken for accurate token counts
try:
    import tiktoken

    _encoding = tiktoken.get_encoding("cl100k_base")
    TIKTOKEN_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    _encoding = None
    TIKTOKEN_AVAILABLE = False

# Fallback simple token estimator
try:
    from tokeniser import estimate_tokens  # type: ignore
except Exception:  # pragma: no cover - fallback

    def estimate_tokens(text: str) -> int:
        return len(text.split())


def token_count(text: str) -> int:
    """Return the number of tokens in *text*.

    Uses tiktoken when available, otherwise falls back to a simple
    estimation via the ``tokeniser`` package.
    """
    if TIKTOKEN_AVAILABLE and _encoding:
        return len(_encoding.encode(text))
    return estimate_tokens(text)


def split_by_tokens(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Split ``text`` into chunks of approximately ``chunk_size`` tokens.

    Args:
        text: The text to split.
        chunk_size: Target size of each chunk in tokens.
        overlap: Number of overlapping tokens between chunks.
    """
    if not text:
        return []

    segments: List[str] = []
    if TIKTOKEN_AVAILABLE and _encoding:
        tokens = _encoding.encode(text)
        step = max(1, chunk_size - overlap)
        for i in range(0, len(tokens), step):
            seg_tokens = tokens[i : i + chunk_size]
            segments.append(_encoding.decode(seg_tokens))
    else:
        char_size = chunk_size * 4
        char_overlap = overlap * 4
        step = max(1, char_size - char_overlap)
        for i in range(0, len(text), step):
            segments.append(text[i : i + char_size])
    return segments

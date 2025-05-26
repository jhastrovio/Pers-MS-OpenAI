from core.utils.tokenization import token_count, split_by_tokens


def test_token_count_basic():
    text = "Hello world"
    assert token_count(text) >= 2


def test_split_by_tokens_overlap():
    text = "one two three four five six seven"
    chunks = split_by_tokens(text, chunk_size=3, overlap=1)
    assert len(chunks) >= 2
    assert chunks[0] != chunks[-1]

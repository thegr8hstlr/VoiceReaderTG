from app.services.tts import _split_text


def test_split_short_text():
    assert _split_text("Hello", 100) == ["Hello"]


def test_split_long_text():
    text = "First sentence. Second sentence. Third sentence. Fourth sentence."
    chunks = _split_text(text, 35)
    assert len(chunks) > 1
    assert all(len(c) <= 35 for c in chunks)


def test_split_no_sentence_boundary():
    text = "a" * 100
    chunks = _split_text(text, 40)
    assert len(chunks) == 3

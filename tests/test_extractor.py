from app.services.extractor import _truncate


def test_truncate_short_text():
    text = "Hello world"
    assert _truncate(text) == text


def test_truncate_long_text():
    text = "a" * 200_000
    result = _truncate(text)
    assert len(result) < 200_000
    assert result.endswith("[Content truncated]")

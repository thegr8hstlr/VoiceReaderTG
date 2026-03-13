from app.models.schemas import ReadingLink, SummaryResult


def test_summary_result_markdown():
    result = SummaryResult(
        summary="This is a test summary.",
        key_points=["Point 1", "Point 2"],
        relevance="Very relevant.",
        further_reading=[
            ReadingLink(
                title="Example", url="https://example.com", description="A link"
            )
        ],
        voice_text="This is a test.",
    )
    md = result.as_telegram_markdown()
    assert "**Summary**" in md
    assert "Point 1" in md
    assert "Example" in md

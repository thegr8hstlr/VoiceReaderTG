from __future__ import annotations

import json

from openai import OpenAI

from app.config import settings
from app.models.schemas import SummaryResult

SUMMARIZER_PROMPT = """\
You are a document summarizer. Analyze the provided document and produce a structured summary.

Respond with ONLY valid JSON matching this schema:
{
  "summary": "A clear, concise 2-3 paragraph summary of the document's main content and arguments.",
  "key_points": ["Point 1", "Point 2", ...],
  "relevance": "One paragraph explaining why this document matters and who would benefit from reading it.",
  "further_reading": [
    {"title": "Resource Name", "url": "https://...", "description": "Why this is relevant"}
  ],
  "voice_text": "A spoken-word version of the summary. No markdown, no bullet points. Use smooth transitions like 'First...', 'Additionally...', 'Finally...'. Keep under 4000 characters. Write as if speaking to a listener."
}

Guidelines:
- key_points: 4-6 bullet points capturing the most important takeaways
- further_reading: 2-4 links to related resources (use real, well-known URLs when possible)
- voice_text: Must sound natural when read aloud by TTS. Avoid abbreviations, special characters, or formatting.
"""

_client = OpenAI(api_key=settings.openai_api_key)


async def summarize_document(text: str, title: str = "Untitled") -> SummaryResult:
    response = _client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SUMMARIZER_PROMPT},
            {
                "role": "user",
                "content": f"Document title: {title}\n\n---\n\n{text[:50_000]}",
            },
        ],
        max_tokens=2048,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content
    data = json.loads(raw)
    return SummaryResult(**data)

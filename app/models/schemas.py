from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class ReadingLink(BaseModel):
    title: str
    url: str
    description: str


class SummaryResult(BaseModel):
    summary: str
    key_points: list[str]
    relevance: str
    further_reading: list[ReadingLink]
    voice_text: str

    def as_telegram_markdown(self) -> str:
        points = "\n".join(f"• {p}" for p in self.key_points)
        links = "\n".join(
            f"• [{r.title}]({r.url}) — {r.description}" for r in self.further_reading
        )
        sections = [
            f"**Summary**\n{self.summary}",
            f"\n**Key Points**\n{points}",
            f"\n**Relevance**\n{self.relevance}",
        ]
        if links:
            sections.append(f"\n**Further Reading**\n{links}")
        return "\n".join(sections)


class SessionData(BaseModel):
    session_id: str
    title: str
    full_text: str
    summary_result: SummaryResult
    vapi_assistant_id: Optional[str] = None
    vapi_tool_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

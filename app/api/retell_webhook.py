from __future__ import annotations

import io
import logging
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.services.retell_call import cleanup_knowledge_base
from app.services.session_store import delete_session, get_session

logger = logging.getLogger(__name__)

router = APIRouter()

TELEGRAM_API = f"https://api.telegram.org/bot{settings.telegram_bot_token}"


def _build_transcript_text(transcript: list[dict], title: str) -> str:
    """Build a plain-text transcript for the PDF."""
    lines = [
        f"Discussion Transcript",
        f"Document: {title}",
        f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "-" * 50,
        "",
    ]
    for entry in transcript:
        role = entry.get("role", "unknown")
        content = entry.get("content", "")
        speaker = "Agent" if role == "agent" else "You"
        lines.append(f"{speaker}: {content}")
        lines.append("")
    return "\n".join(lines)


async def _send_transcript_pdf(chat_id: int, transcript: list[dict], title: str) -> None:
    """Generate a text file transcript and send it to Telegram as a document."""
    text = _build_transcript_text(transcript, title)
    file_bytes = text.encode("utf-8")
    filename = f"transcript_{title[:30].replace(' ', '_')}.txt"

    async with httpx.AsyncClient() as client:
        await client.post(
            f"{TELEGRAM_API}/sendDocument",
            data={
                "chat_id": str(chat_id),
                "caption": f"📝 Discussion transcript: {title}",
            },
            files={"document": (filename, io.BytesIO(file_bytes), "text/plain")},
            timeout=15,
        )


@router.post("/webhook/retell")
async def retell_webhook(request: Request) -> JSONResponse:
    body = await request.json()
    event = body.get("event", "")
    call = body.get("call", {})
    logger.info("Retell webhook: event=%s call_id=%s", event, call.get("call_id"))

    if event in ("call_ended", "call_analyzed"):
        metadata = call.get("metadata", {})
        session_id = metadata.get("session_id", "")
        transcript = call.get("transcript_object", [])

        if session_id:
            session = get_session(session_id)
            if session:
                # Send transcript as file to Telegram
                if transcript and session.telegram_chat_id:
                    try:
                        await _send_transcript_pdf(
                            session.telegram_chat_id, transcript, session.title
                        )
                        logger.info("Sent transcript to chat %s", session.telegram_chat_id)
                    except Exception:
                        logger.exception("Failed to send transcript to Telegram")

                # Cleanup KB
                if session.retell_kb_id:
                    await cleanup_knowledge_base(session.retell_kb_id)

            if event == "call_ended":
                delete_session(session_id)
                logger.info("Cleaned up session %s after call ended", session_id)

    return JSONResponse(content={"ok": True})

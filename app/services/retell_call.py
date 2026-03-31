from __future__ import annotations

import logging

from retell import AsyncRetell

from app.config import settings
from app.services.session_store import get_session, update_session

logger = logging.getLogger(__name__)

_client = AsyncRetell(api_key=settings.retell_api_key)


async def create_knowledge_base(title: str, text: str) -> str:
    """Upload document text to a Retell Knowledge Base. Returns the KB id."""
    kb = await _client.knowledge_base.create(
        knowledge_base_name=f"doc-{title[:40]}",
        knowledge_base_texts=[{"title": title, "text": text}],
    )
    logger.info("Created Retell KB %s for '%s'", kb.knowledge_base_id, title)
    return kb.knowledge_base_id


async def create_web_call(session_id: str) -> dict:
    """Create a Retell web call with the session's KB attached.

    Returns ``{"access_token": ..., "call_id": ...}``.
    """
    session = get_session(session_id)
    if session is None:
        raise ValueError(f"Session {session_id} not found")

    key_points = "\n".join(f"- {p}" for p in session.summary_result.key_points)

    override_kwargs: dict = {
        "retell_llm": {
            "begin_message": (
                f'Hi! I\'ve read through "{session.title}" and I\'m ready '
                "to discuss it with you. What would you like to know?"
            ),
        },
    }
    if session.retell_kb_id:
        override_kwargs["retell_llm"]["knowledge_base_ids"] = [session.retell_kb_id]

    web_call = await _client.call.create_web_call(
        agent_id=settings.retell_agent_id,
        metadata={"session_id": session_id},
        retell_llm_dynamic_variables={
            "document_title": session.title,
            "document_summary": session.summary_result.summary,
            "key_points": key_points,
        },
        agent_override=override_kwargs,
    )

    update_session(session_id, retell_call_id=web_call.call_id)
    logger.info("Created Retell web call %s for session %s", web_call.call_id, session_id)
    return {"access_token": web_call.access_token, "call_id": web_call.call_id}


async def cleanup_knowledge_base(kb_id: str) -> None:
    """Delete a Retell Knowledge Base."""
    try:
        await _client.knowledge_base.delete(kb_id)
        logger.info("Deleted Retell KB %s", kb_id)
    except Exception:
        logger.exception("Failed to delete Retell KB %s", kb_id)

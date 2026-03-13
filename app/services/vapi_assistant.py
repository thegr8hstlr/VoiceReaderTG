from __future__ import annotations

import httpx

from app.config import settings
from app.services.session_store import get_session

VAPI_BASE = "https://api.vapi.ai"

ASSISTANT_SYSTEM_PROMPT = """\
You are a knowledgeable document discussion assistant. You have been given a document to discuss with the user.

**Document Title:** {title}

**Document Summary:**
{summary}

**Key Points:**
{key_points}

**Full Document Text (for reference):**
{full_text_truncated}

Your role:
- Answer questions about this document conversationally and accurately.
- When the user asks about specific topics, use the search_document tool to find relevant passages.
- When asked for key takeaways, use the get_key_points tool.
- When asked for related resources, use the get_further_reading tool.
- Be concise in voice responses — keep answers under 3 sentences unless the user asks for detail.
- If you don't know something that isn't in the document, say so honestly.
"""

FIRST_MESSAGE_TEMPLATE = (
    "Hi! I've read through \"{title}\" and I'm ready to discuss it with you. "
    "What would you like to know about it?"
)

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_document",
            "description": "Search the document for paragraphs related to a query",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The topic or question to search for in the document",
                    }
                },
                "required": ["query"],
            },
        },
        "server": {"url": "{webhook_url}"},
    },
    {
        "type": "function",
        "function": {
            "name": "get_key_points",
            "description": "Get the pre-generated key points from the document summary",
            "parameters": {"type": "object", "properties": {}},
        },
        "server": {"url": "{webhook_url}"},
    },
    {
        "type": "function",
        "function": {
            "name": "get_further_reading",
            "description": "Get suggested further reading links related to the document",
            "parameters": {"type": "object", "properties": {}},
        },
        "server": {"url": "{webhook_url}"},
    },
]


def _build_tools(webhook_url: str) -> list[dict]:
    import json
    tools_json = json.dumps(TOOL_DEFINITIONS)
    tools_json = tools_json.replace("{webhook_url}", webhook_url)
    return json.loads(tools_json)


async def create_document_assistant(session_id: str) -> str:
    session = get_session(session_id)
    if session is None:
        raise ValueError(f"Session {session_id} not found")

    webhook_url = f"{settings.base_url}/webhook/vapi"
    key_points_text = "\n".join(f"- {p}" for p in session.summary_result.key_points)
    full_text_truncated = session.full_text[:15_000]

    system_prompt = ASSISTANT_SYSTEM_PROMPT.format(
        title=session.title,
        summary=session.summary_result.summary,
        key_points=key_points_text,
        full_text_truncated=full_text_truncated,
    )
    first_message = FIRST_MESSAGE_TEMPLATE.format(title=session.title)

    payload = {
        "name": f"DocAssistant-{session_id[:8]}",
        "firstMessage": first_message,
        "model": {
            "provider": "anthropic",
            "model": "claude-sonnet-4-20250514",
            "messages": [{"role": "system", "content": system_prompt}],
        },
        "voice": {
            "provider": "11labs",
            "voiceId": "21m00Tcm4TlvDq8ikWAM",  # Rachel
        },
        "tools": _build_tools(webhook_url),
        "metadata": {"session_id": session_id},
        "serverUrl": webhook_url,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{VAPI_BASE}/assistant",
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.vapi_api_key}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

    assistant_id = data["id"]
    # Update session with assistant ID
    from app.services.session_store import update_session
    update_session(session_id, vapi_assistant_id=assistant_id)
    return assistant_id


async def delete_assistant(assistant_id: str) -> None:
    async with httpx.AsyncClient() as client:
        await client.delete(
            f"{VAPI_BASE}/assistant/{assistant_id}",
            headers={"Authorization": f"Bearer {settings.vapi_api_key}"},
            timeout=15,
        )

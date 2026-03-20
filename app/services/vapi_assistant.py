from __future__ import annotations

import logging

import httpx

from app.config import settings
from app.services.session_store import get_session, update_session

logger = logging.getLogger(__name__)

VAPI_BASE = "https://api.vapi.ai"
VAPI_HEADERS = {
    "Authorization": f"Bearer {settings.vapi_api_key}",
    "Content-Type": "application/json",
}

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
    'Hi! I\'ve read through "{title}" and I\'m ready to discuss it with you. '
    "What would you like to know about it?"
)

# Tool definitions to create via POST /tool
TOOL_SPECS = [
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
    },
    {
        "type": "function",
        "function": {
            "name": "get_key_points",
            "description": "Get the pre-generated key points from the document summary",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_further_reading",
            "description": "Get suggested further reading links related to the document",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


async def _create_tools(client: httpx.AsyncClient, webhook_url: str) -> list[str]:
    """Create tools via VAPI API and return their IDs."""
    tool_ids = []
    for spec in TOOL_SPECS:
        payload = {**spec, "server": {"url": webhook_url}}
        resp = await client.post(
            f"{VAPI_BASE}/tool",
            json=payload,
            headers=VAPI_HEADERS,
            timeout=15,
        )
        if resp.status_code >= 400:
            logger.error("VAPI tool creation failed: %s %s", resp.status_code, resp.text)
            resp.raise_for_status()
        data = resp.json()
        tool_ids.append(data["id"])
        logger.info("Created VAPI tool %s: %s", data["id"], spec["function"]["name"])
    return tool_ids


async def create_web_call(session_id: str) -> str:
    """Create a web call server-side using the private API key.

    This bypasses the public key entirely. Returns the webCallUrl
    that the browser joins via Daily.co.
    """
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

    # Inline tool definitions with server URLs
    tools = [{**spec, "server": {"url": webhook_url}} for spec in TOOL_SPECS]

    payload = {
        "type": "webCall",
        "assistant": {
            "name": f"DocAssistant-{session_id[:8]}",
            "firstMessage": first_message,
            "model": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "messages": [{"role": "system", "content": system_prompt}],
                "tools": tools,
            },
            "voice": {
                "provider": "vapi",
                "voiceId": "Elliot",
            },
            "transcriber": {
                "provider": "deepgram",
                "model": "nova-3",
                "language": "en",
            },
            "silenceTimeoutSeconds": 30,
            "responseDelaySeconds": 1.5,
            "startSpeakingPlan": {
                "waitSeconds": 1.8,
                "smartEndpointingEnabled": False,
            },
            "stopSpeakingPlan": {
                "numWords": 0,
                "voiceSeconds": 0.3,
                "backoffSeconds": 2.0,
            },
            "metadata": {"session_id": session_id},
            "serverUrl": webhook_url,
        },
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{VAPI_BASE}/call",
            json=payload,
            headers=VAPI_HEADERS,
            timeout=30,
        )
        if resp.status_code >= 400:
            logger.error("VAPI web call creation failed: %s %s", resp.status_code, resp.text)
            resp.raise_for_status()
        data = resp.json()
        logger.info("VAPI call response keys: %s", list(data.keys()))

    web_call_url = data.get("webCallUrl", "")
    call_id = data.get("id", "")
    logger.info("Created VAPI web call %s, url=%s", call_id, web_call_url)
    return web_call_url


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

    async with httpx.AsyncClient() as client:
        # Step 1: Create tools
        tool_ids = await _create_tools(client, webhook_url)

        # Step 2: Create assistant with tool references
        payload = {
            "name": f"DocAssistant-{session_id[:8]}",
            "firstMessage": first_message,
            "model": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "messages": [{"role": "system", "content": system_prompt}],
                "toolIds": tool_ids,
            },
            "voice": {
                "provider": "vapi",
                "voiceId": "Elliot",
            },
            "transcriber": {
                "provider": "deepgram",
                "model": "nova-3",
                "language": "en",
            },
            "silenceTimeoutSeconds": 30,
            "responseDelaySeconds": 1.5,
            "startSpeakingPlan": {
                "waitSeconds": 1.8,
                "smartEndpointingEnabled": False,
            },
            "stopSpeakingPlan": {
                "numWords": 0,
                "voiceSeconds": 0.3,
                "backoffSeconds": 2.0,
            },
            "metadata": {"session_id": session_id},
            "serverUrl": webhook_url,
        }

        resp = await client.post(
            f"{VAPI_BASE}/assistant",
            json=payload,
            headers=VAPI_HEADERS,
            timeout=30,
        )
        if resp.status_code >= 400:
            logger.error("VAPI assistant creation failed: %s %s", resp.status_code, resp.text)
            resp.raise_for_status()
        data = resp.json()

    assistant_id = data["id"]
    update_session(
        session_id,
        vapi_assistant_id=assistant_id,
        vapi_tool_ids=tool_ids,
    )
    logger.info("Created VAPI assistant %s with %d tools", assistant_id, len(tool_ids))
    return assistant_id


async def delete_assistant(assistant_id: str, tool_ids: list[str] | None = None) -> None:
    async with httpx.AsyncClient() as client:
        # Delete assistant
        try:
            await client.delete(
                f"{VAPI_BASE}/assistant/{assistant_id}",
                headers=VAPI_HEADERS,
                timeout=15,
            )
            logger.info("Deleted VAPI assistant %s", assistant_id)
        except Exception:
            logger.exception("Failed to delete assistant %s", assistant_id)

        # Delete tools
        if tool_ids:
            for tid in tool_ids:
                try:
                    await client.delete(
                        f"{VAPI_BASE}/tool/{tid}",
                        headers=VAPI_HEADERS,
                        timeout=15,
                    )
                    logger.info("Deleted VAPI tool %s", tid)
                except Exception:
                    logger.exception("Failed to delete tool %s", tid)

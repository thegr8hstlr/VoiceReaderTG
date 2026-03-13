from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.services.session_store import delete_session, get_session
from app.services.vapi_assistant import delete_assistant
from app.tools.document_tools import dispatch_tool

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/webhook/vapi")
async def vapi_webhook(request: Request) -> JSONResponse:
    body = await request.json()
    message = body.get("message", {})
    msg_type = message.get("type", "")
    logger.info("VAPI webhook: type=%s", msg_type)

    if msg_type == "tool-calls":
        return _handle_tool_calls(message)
    elif msg_type == "end-of-call-report":
        await _handle_end_of_call(message)
        return JSONResponse(content={"ok": True})
    elif msg_type == "status-update":
        logger.info("VAPI status: %s", message.get("status", "unknown"))
        return JSONResponse(content={"ok": True})
    else:
        logger.info("VAPI unhandled type: %s", msg_type)
        return JSONResponse(content={"ok": True})


def _handle_tool_calls(message: dict) -> JSONResponse:
    # VAPI sends toolCallList (per docs), not toolCalls
    tool_call_list = message.get("toolCallList", [])

    # Also try legacy format
    if not tool_call_list:
        tool_call_list = message.get("toolCalls", [])

    # Extract session_id from metadata
    call = message.get("call", {})
    assistant = message.get("assistant", {})
    metadata = (
        assistant.get("metadata", {})
        or call.get("assistant", {}).get("metadata", {})
        or call.get("metadata", {})
        or {}
    )
    session_id = metadata.get("session_id", "")

    logger.info(
        "Tool calls for session %s: %s",
        session_id,
        [tc.get("name") or tc.get("function", {}).get("name") for tc in tool_call_list],
    )

    results = []
    for tc in tool_call_list:
        # VAPI custom tools format: name and arguments at top level
        tool_name = tc.get("name") or tc.get("function", {}).get("name", "")
        tool_args = tc.get("arguments") or tc.get("function", {}).get("arguments", {})
        tool_call_id = tc.get("id", "")

        # Parse arguments if they're a string
        if isinstance(tool_args, str):
            import json
            try:
                tool_args = json.loads(tool_args)
            except (json.JSONDecodeError, TypeError):
                tool_args = {}

        result = dispatch_tool(tool_name, tool_args, session_id)
        results.append({"toolCallId": tool_call_id, "result": result})

    logger.info("Tool results: %d items", len(results))
    return JSONResponse(content={"results": results})


async def _handle_end_of_call(message: dict) -> None:
    call = message.get("call", {})
    assistant = message.get("assistant", {})
    metadata = (
        assistant.get("metadata", {})
        or call.get("assistant", {}).get("metadata", {})
        or call.get("metadata", {})
        or {}
    )
    session_id = metadata.get("session_id", "")
    assistant_id = call.get("assistantId", "")

    logger.info("Call ended: session=%s assistant=%s", session_id, assistant_id)

    # Get tool IDs from session before cleanup
    tool_ids = []
    if session_id:
        session = get_session(session_id)
        if session:
            tool_ids = session.vapi_tool_ids

    if assistant_id:
        await delete_assistant(assistant_id, tool_ids)

    if session_id:
        delete_session(session_id)

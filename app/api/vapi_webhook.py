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

    if msg_type == "tool-calls":
        return await _handle_tool_calls(message)
    elif msg_type == "end-of-call-report":
        await _handle_end_of_call(message)
        return JSONResponse(content={"ok": True})
    elif msg_type == "status-update":
        status = message.get("status", "unknown")
        logger.info("VAPI status update: %s", status)
        return JSONResponse(content={"ok": True})
    else:
        logger.debug("Unhandled VAPI webhook type: %s", msg_type)
        return JSONResponse(content={"ok": True})


async def _handle_tool_calls(message: dict) -> JSONResponse:
    tool_calls = message.get("toolCalls", [])
    results = []

    # Extract session_id from call metadata
    call = message.get("call", {})
    metadata = call.get("assistant", {}).get("metadata", {})
    session_id = metadata.get("session_id", "")

    for tc in tool_calls:
        tool_name = tc.get("function", {}).get("name", "")
        tool_args = tc.get("function", {}).get("arguments", {})
        tool_call_id = tc.get("id", "")

        result = dispatch_tool(tool_name, tool_args, session_id)
        results.append({"toolCallId": tool_call_id, "result": result})

    return JSONResponse(content={"results": results})


async def _handle_end_of_call(message: dict) -> None:
    call = message.get("call", {})
    metadata = call.get("assistant", {}).get("metadata", {})
    session_id = metadata.get("session_id", "")
    assistant_id = call.get("assistantId", "")

    logger.info("Call ended for session %s, assistant %s", session_id, assistant_id)

    # Clean up the VAPI assistant
    if assistant_id:
        try:
            await delete_assistant(assistant_id)
            logger.info("Deleted VAPI assistant %s", assistant_id)
        except Exception:
            logger.exception("Failed to delete assistant %s", assistant_id)

    # Clean up the session
    if session_id:
        delete_session(session_id)

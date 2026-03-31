from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.services.retell_call import create_web_call
from app.services.session_store import get_session

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/health")
async def health_check():
    return {"status": "ok"}


@router.get("/chat/{session_id}", response_class=HTMLResponse)
async def chat_page(request: Request, session_id: str):
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    return templates.TemplateResponse(
        "chat.html",
        {
            "request": request,
            "session_id": session_id,
            "title": session.title,
            "summary": session.summary_result.summary,
            "retell_agent_id": settings.retell_agent_id,
        },
    )


@router.post("/chat/{session_id}/start")
async def start_assistant(session_id: str):
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    try:
        result = await create_web_call(session_id)
        return JSONResponse(content=result)
    except Exception as e:
        logger.exception("Failed to create web call: %s", e)
        raise HTTPException(status_code=500, detail="Failed to create voice call")

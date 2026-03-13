from __future__ import annotations

import time
from typing import Optional

from app.models.schemas import SessionData

TTL_SECONDS = 3600  # 1 hour

_store: dict[str, tuple[float, SessionData]] = {}


def save_session(session: SessionData) -> None:
    _store[session.session_id] = (time.time(), session)
    _cleanup()


def get_session(session_id: str) -> Optional[SessionData]:
    entry = _store.get(session_id)
    if entry is None:
        return None
    created, session = entry
    if time.time() - created > TTL_SECONDS:
        _store.pop(session_id, None)
        return None
    return session


def delete_session(session_id: str) -> None:
    _store.pop(session_id, None)


def update_session(session_id: str, **kwargs) -> Optional[SessionData]:
    session = get_session(session_id)
    if session is None:
        return None
    updated = session.model_copy(update=kwargs)
    save_session(updated)
    return updated


def _cleanup() -> None:
    now = time.time()
    expired = [k for k, (t, _) in _store.items() if now - t > TTL_SECONDS]
    for k in expired:
        del _store[k]

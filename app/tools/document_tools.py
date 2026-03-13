from __future__ import annotations

from app.services.session_store import get_session


def search_document(query: str, session_id: str) -> str:
    session = get_session(session_id)
    if session is None:
        return "Session expired. Please generate a new summary."

    query_lower = query.lower()
    paragraphs = session.full_text.split("\n\n")
    scored = []
    for para in paragraphs:
        para = para.strip()
        if not para or len(para) < 30:
            continue
        # Simple keyword matching — count query word occurrences
        score = sum(1 for word in query_lower.split() if word in para.lower())
        if score > 0:
            scored.append((score, para))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:3]

    if not top:
        return f"No passages found matching '{query}' in the document."

    results = "\n\n---\n\n".join(para for _, para in top)
    return f"Found {len(top)} relevant passage(s):\n\n{results}"


def get_key_points(session_id: str) -> str:
    session = get_session(session_id)
    if session is None:
        return "Session expired. Please generate a new summary."
    points = "\n".join(f"• {p}" for p in session.summary_result.key_points)
    return f"Key points from the document:\n\n{points}"


def get_further_reading(session_id: str) -> str:
    session = get_session(session_id)
    if session is None:
        return "Session expired. Please generate a new summary."
    links = session.summary_result.further_reading
    if not links:
        return "No further reading suggestions available for this document."
    items = "\n".join(f"• {r.title} ({r.url}) — {r.description}" for r in links)
    return f"Suggested further reading:\n\n{items}"


def dispatch_tool(name: str, params: dict, session_id: str) -> str:
    handlers = {
        "search_document": lambda: search_document(params.get("query", ""), session_id),
        "get_key_points": lambda: get_key_points(session_id),
        "get_further_reading": lambda: get_further_reading(session_id),
    }
    handler = handlers.get(name)
    if handler is None:
        return f"Unknown tool: {name}"
    return handler()

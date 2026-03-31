# Architecture

## System Overview

VoiceReaderTG is a two-phase system: document summarization (Phase 1) and interactive voice discussion (Phase 2).

### Phase 1 — Document Summarization (Telegram Bot)

```
Telegram User
    |
    v
bot/handlers.py --> Detect file type (PDF/DOCX/MD/TXT/URL)
    |
    v
services/extractor.py --> Raw text extraction
    |                      - pdfplumber (PDF)
    |                      - python-docx (DOCX)
    |                      - plain decode (MD, TXT)
    |                      - trafilatura (URL)
    |
    v
services/summarizer.py --> OpenAI GPT-4o-mini (JSON mode)
    |
    +---> services/tts.py --> OpenAI TTS (tts-1, nova voice, OGG Opus)
    |
    +---> services/retell_call.py --> Upload document to Retell Knowledge Base
    |
    +---> services/session_store.py --> Save context (in-memory, 1hr TTL)
    |
    v
Telegram: voice note + text summary + "Discuss" button
```

### Phase 2 — Voice Discussion (Retell AI)

```
User clicks "Discuss This Document"
    |
    v
api/routes.py --> GET /chat/{session_id}
    |              Serves chat.html with Retell Web Client SDK
    |
    v
api/routes.py --> POST /chat/{session_id}/start
    |              Creates Retell web call with KB + dynamic variables
    |
    v
services/retell_call.py
    |   - Creates web call via Retell API
    |   - Attaches Knowledge Base (automatic RAG)
    |   - Injects document context via dynamic variables
    |   - Returns access_token for browser
    |
    v
chat.html --> Retell Web Client SDK (WebRTC)
    |          - Start/stop call
    |          - Live transcript display
    |
    v
Retell Cloud --> Agent processes voice
    |             - Knowledge Base for document search (automatic RAG)
    |             - web_search tool --> POST /webhook/retell/tool/web_search
    |                                   --> Tavily (primary) / DuckDuckGo (fallback)
    |
    v
api/retell_webhook.py --> call_ended event
    |   - Send transcript file to Telegram
    |   - Cleanup Knowledge Base
    |   - Delete session
```

## Component Responsibilities

| Module | Responsibility |
|--------|---------------|
| `app/main.py` | FastAPI app, bot lifecycle management |
| `app/config.py` | Environment variable loading via pydantic-settings |
| `app/bot/handlers.py` | Telegram message routing and processing pipeline |
| `app/bot/runner.py` | Bot initialization, polling start/stop |
| `app/services/extractor.py` | Text extraction from PDF, DOCX, MD, TXT, URLs |
| `app/services/summarizer.py` | GPT-4o-mini-powered document summarization |
| `app/services/tts.py` | OpenAI TTS voice note generation |
| `app/services/session_store.py` | In-memory session storage with TTL |
| `app/services/retell_call.py` | Retell AI web call + Knowledge Base management |
| `app/services/web_search.py` | Web search via Tavily + DuckDuckGo fallback |
| `app/api/routes.py` | HTTP routes (health, chat page, start call) |
| `app/api/retell_webhook.py` | Retell webhook handler (transcript, tool calls, cleanup) |
| `app/models/schemas.py` | Pydantic data models |
| `app/templates/chat.html` | Retell voice call web interface |

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI + Python 3.12 |
| Telegram Bot | python-telegram-bot v21 (async) |
| Summarization | OpenAI GPT-4o-mini (JSON mode) |
| Voice Notes | OpenAI TTS (tts-1, nova voice, OGG Opus) |
| Voice Discussion | Retell AI (Knowledge Base + Web Call SDK) |
| Voice Agent LLM | GPT-4.1-mini (via Retell) |
| Web Search | Tavily (primary) + DuckDuckGo (fallback) |
| PDF Extraction | pdfplumber |
| DOCX Extraction | python-docx |
| URL Extraction | trafilatura |
| Deployment | Docker + Caddy |

## Design Decisions

- **Retell Knowledge Base per document**: Each uploaded document gets its own KB, attached to the call via `agent_override`. Cleaned up after the call ends.
- **Dynamic variables over full-text prompts**: Summary and key points injected via Retell dynamic variables. Full document handled by KB (automatic RAG).
- **Tavily + DuckDuckGo fallback**: Tavily provides AI-optimized search results. DuckDuckGo requires no API key and serves as a free fallback.
- **In-memory session store**: Simple and sufficient for ephemeral sessions (1hr TTL). Swap to Redis for production scale.
- **Direct OGG Opus from OpenAI**: Telegram natively supports OGG Opus voice notes — no format conversion needed.
- **Docker + Caddy**: Simple production deployment with automatic HTTPS certificate management.

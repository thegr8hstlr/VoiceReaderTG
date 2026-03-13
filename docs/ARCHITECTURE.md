# Architecture

## System Overview

VoiceReaderTG is a two-phase system: document summarization (Phase 1) and interactive voice discussion (Phase 2).

### Phase 1 — Document Summarization (Telegram Bot)

```
Telegram User
    │
    ▼
bot/handlers.py ──► Detect file type (PDF/DOCX/URL)
    │
    ▼
services/extractor.py ──► Raw text extraction
    │                      • pdfplumber (PDF)
    │                      • python-docx (DOCX)
    │                      • trafilatura (URL)
    │
    ▼
services/summarizer.py ──► Claude API call
    │                       • Structured JSON output
    │                       • SummaryResult model
    │
    ├──► services/tts.py ──► OpenAI TTS
    │                         • OGG Opus format
    │                         • Text chunking for long content
    │
    ├──► services/session_store.py ──► Save context (1hr TTL)
    │
    └──► Telegram: voice note + text summary + "Discuss" button
```

### Phase 2 — Voice Discussion (VAPI)

```
User clicks "Discuss This Document"
    │
    ▼
api/routes.py ──► GET /chat/{session_id}
    │              Serves chat.html with VAPI Web SDK
    │
    ▼
api/routes.py ──► POST /chat/{session_id}/start
    │              Lazy assistant creation
    │
    ▼
services/vapi_assistant.py ──► POST to VAPI API
    │                           • System prompt with document context
    │                           • Tool definitions
    │                           • Claude as LLM, ElevenLabs as voice
    │                           • session_id in metadata
    │
    ▼
chat.html ──► VAPI Web SDK
    │          • Start/stop call
    │          • Live transcript
    │
    ▼
VAPI Cloud ──► Webhook: POST /webhook/vapi
    │
    ▼
api/vapi_webhook.py ──► Event routing
    │
    ├──► tool-calls ──► tools/document_tools.py
    │                    • search_document (fuzzy paragraph search)
    │                    • get_key_points (pre-generated)
    │                    • get_further_reading (pre-generated)
    │
    ├──► end-of-call-report ──► Cleanup
    │                            • Delete VAPI assistant
    │                            • Remove session data
    │
    └──► status-update ──► Logging
```

## Component Responsibilities

| Module | Responsibility |
|--------|---------------|
| `app/main.py` | FastAPI app, bot lifecycle management |
| `app/config.py` | Environment variable loading via pydantic-settings |
| `app/bot/handlers.py` | Telegram message routing and processing pipeline |
| `app/bot/runner.py` | Bot initialization, polling start/stop |
| `app/services/extractor.py` | Text extraction from PDF, DOCX, URLs |
| `app/services/summarizer.py` | Claude-powered document summarization |
| `app/services/tts.py` | OpenAI TTS voice note generation |
| `app/services/session_store.py` | In-memory session storage with TTL |
| `app/services/vapi_assistant.py` | VAPI assistant CRUD operations |
| `app/tools/document_tools.py` | VAPI tool implementations and dispatcher |
| `app/api/routes.py` | HTTP routes (health, chat page, assistant start) |
| `app/api/vapi_webhook.py` | VAPI webhook event handler |
| `app/models/schemas.py` | Pydantic data models |
| `app/templates/chat.html` | VAPI Web SDK voice chat interface |

## Design Decisions

- **In-memory session store**: Simplifies deployment; sessions are ephemeral by nature (1hr TTL). For production scale, swap to Redis.
- **Lazy assistant creation**: VAPI assistants are only created when the user opens the chat page, not when the summary is generated. This avoids creating unused assistants.
- **Synchronous Claude/OpenAI calls wrapped in async handlers**: The Anthropic and OpenAI SDKs use sync HTTP clients. Since these are I/O-bound and infrequent, the thread pool executor handles them without blocking the event loop.
- **Direct OGG Opus from OpenAI**: Telegram natively supports OGG Opus voice notes, so no format conversion is needed.
- **Tool dispatch via webhook**: VAPI calls our server URL for tool execution, keeping document context server-side rather than sending it to VAPI.

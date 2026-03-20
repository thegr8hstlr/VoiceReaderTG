# Architecture

## System Overview

VoiceReaderTG is a two-phase system: document summarization (Phase 1) and interactive voice discussion (Phase 2).

### Phase 1 — Document Summarization (Telegram Bot)

```
Telegram User
    │
    ▼
bot/handlers.py ──► Detect file type (PDF/DOCX/MD/TXT/URL)
    │
    ▼
services/extractor.py ──► Raw text extraction
    │                      • pdfplumber (PDF)
    │                      • python-docx (DOCX)
    │                      • plain decode (MD, TXT)
    │                      • trafilatura (URL)
    │
    ▼
services/summarizer.py ──► OpenAI GPT-4o-mini API call
    │                       • response_format: json_object (reliable JSON)
    │                       • SummaryResult model
    │
    ├──► services/tts.py ──► OpenAI TTS (tts-1, nova voice)
    │                         • OGG Opus format (no conversion needed)
    │                         • Text chunking for long content
    │
    ├──► services/session_store.py ──► Save context (in-memory, 1hr TTL)
    │
    └──► Telegram: voice note + text summary + "Discuss" button

Plain text messages:
    ▼
bot/handlers.py ──► OpenAI GPT-4o-mini chat response (no document needed)
```

### Phase 2 — Voice Discussion (VAPI)

```
User clicks "Discuss This Document"
    │
    ▼
api/routes.py ──► GET /chat/{session_id}
    │              Serves chat.html with VAPI HTML script-tag widget
    │
    ▼
api/routes.py ──► POST /chat/{session_id}/start
    │              Lazy assistant creation
    │
    ▼
services/vapi_assistant.py
    │   Step 1: POST /tool (×3) — create each tool separately, get tool IDs
    │   Step 2: POST /assistant — reference tools by ID in model.toolIds
    │              • System prompt with document context
    │              • OpenAI GPT-4o-mini as LLM
    │              • Vapi built-in voice "Elliot"
    │              • Deepgram Nova-3 transcriber
    │              • session_id in metadata
    │
    ▼
chat.html ──► VAPI HTML script-tag widget
    │          • Start/stop call
    │          • Live transcript
    │          [NOTE: Dynamic assistant auth is a known limitation — see below]
    │
    ▼
VAPI Cloud ──► Webhook: POST /webhook/vapi
    │
    ▼
api/vapi_webhook.py ──► Event routing
    │
    ├──► tool-calls (toolCallList) ──► tools/document_tools.py
    │                                   • search_document (fuzzy paragraph search)
    │                                   • get_key_points (pre-generated)
    │                                   • get_further_reading (pre-generated)
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
| `app/config.py` | Environment variable loading via pydantic-settings (extra="ignore") |
| `app/bot/handlers.py` | Telegram message routing and processing pipeline |
| `app/bot/runner.py` | Bot initialization, polling start/stop |
| `app/services/extractor.py` | Text extraction from PDF, DOCX, MD, TXT, URLs |
| `app/services/summarizer.py` | GPT-4o-mini-powered document summarization |
| `app/services/tts.py` | OpenAI TTS voice note generation |
| `app/services/session_store.py` | In-memory session storage with TTL |
| `app/services/vapi_assistant.py` | VAPI tool creation + assistant CRUD operations |
| `app/tools/document_tools.py` | VAPI tool implementations and dispatcher |
| `app/api/routes.py` | HTTP routes (health, chat page, assistant start) |
| `app/api/vapi_webhook.py` | VAPI webhook event handler |
| `app/models/schemas.py` | Pydantic data models |
| `app/templates/chat.html` | VAPI voice chat interface |

## Tech Stack (Actual)

| Component | Technology | Notes |
|-----------|-----------|-------|
| Backend | FastAPI + Python 3.11+ | |
| Telegram Bot | python-telegram-bot v21 async API | |
| Summarization | OpenAI GPT-4o-mini | Switched from Claude — see findings |
| TTS Voice Notes | OpenAI tts-1, nova voice, OGG Opus | |
| VAPI LLM | OpenAI GPT-4o-mini | |
| VAPI Voice | Vapi built-in "Elliot" | Switched from ElevenLabs — see findings |
| VAPI Transcriber | Deepgram Nova-3 | More responsive than gpt-4o-transcribe |
| PDF Extraction | pdfplumber | |
| DOCX Extraction | python-docx | |
| URL Extraction | trafilatura | |
| Plain text/MD | Built-in decode | |
| Chat (plain messages) | OpenAI GPT-4o-mini | |

## Design Decisions

- **In-memory session store**: Simplifies deployment; sessions are ephemeral by nature (1hr TTL). For production scale, swap to Redis.
- **Lazy assistant creation**: VAPI assistants are only created when the user opens the chat page, not when the summary is generated. This avoids creating unused assistants.
- **Tools created separately before assistant**: VAPI requires tools to be created via POST /tool first, then referenced by ID in `model.toolIds`. Inline `tools` on the assistant payload is rejected ("property tools should not exist").
- **Synchronous OpenAI calls wrapped in async handlers**: The OpenAI SDK uses sync HTTP clients. Since these are I/O-bound and infrequent, the thread pool executor handles them without blocking the event loop.
- **Direct OGG Opus from OpenAI**: Telegram natively supports OGG Opus voice notes, so no format conversion is needed.
- **Tool dispatch via webhook**: VAPI calls our server URL for tool execution, keeping document context server-side rather than sending it to VAPI.
- **OpenAI GPT-4o-mini with response_format: json_object**: Used for summarization instead of Claude because Claude occasionally wraps JSON in markdown code fences, requiring additional stripping logic. GPT-4o-mini with explicit json_object format is more reliable.

## Known Limitations

### Web Widget Auth (Phase 2)
The VAPI html-script-tag widget cannot connect to dynamically created assistants using the public key (returns 403 "Key doesn't allow assistantId"). Options explored:
- Public key: 403 on dynamic assistants
- Private key in client JS: insecure and not reliably supported by the widget
- Inline assistant config in widget: gets stuck at "Connecting..."

**Recommended fix (not yet implemented):** Use `POST /call/web` server-side to create a WebRTC call, then pass the resulting WebRTC URL to the browser directly — bypassing the widget auth issue.

### Voice discussion works from the VAPI dashboard (direct assistant ID), confirming the assistant creation logic is correct.

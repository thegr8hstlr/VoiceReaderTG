# VoiceReaderTG

Telegram bot that summarizes documents (PDF, DOCX, MD, TXT, URLs) with AI-generated voice notes and offers interactive voice discussions powered by VAPI.ai.

## Current Status

| Phase | Status |
|-------|--------|
| Phase 1 — Telegram bot (summarize + voice note) | Fully working |
| Phase 2 — Voice discussion via VAPI | Works from VAPI dashboard; web link integration pending (widget auth issue) |

## Architecture

```
User sends PDF / DOCX / MD / TXT / URL on Telegram
  → Extract text (pdfplumber / python-docx / trafilatura / plain decode)
  → Summarize with OpenAI GPT-4o-mini (JSON mode)
  → Generate voice note (OpenAI TTS, tts-1, nova voice, OGG Opus)
  → Send: voice note + text summary + "Discuss This Document" button

User sends a plain text message
  → LLM chat response via GPT-4o-mini

User clicks "Discuss This Document"
  → Opens web page with VAPI voice widget
  → VAPI tools created, then dynamic assistant created with document context
  → User asks follow-up questions via voice
  → VAPI tools: search_document, get_key_points, get_further_reading
  → On call end: assistant and tools cleaned up automatically
```

## Features

- PDF, DOCX, MD, TXT document processing
- URL / article content extraction via trafilatura
- AI-powered structured summaries (OpenAI GPT-4o-mini, JSON mode)
- Voice note generation (OpenAI TTS, OGG Opus — no conversion needed)
- Plain text messages get LLM chat responses
- Interactive voice discussions via VAPI.ai
- Dynamic VAPI assistant creation per document (tools created separately, then referenced by ID)
- Server-side tool calling for document search
- Webhook-based assistant lifecycle management
- In-memory session store with 1hr TTL

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI + Python 3.11+ |
| Telegram Bot | python-telegram-bot v21 (async) |
| Summarization | OpenAI GPT-4o-mini (response_format: json_object) |
| Chat (plain messages) | OpenAI GPT-4o-mini |
| Voice Notes | OpenAI TTS (tts-1, nova voice, OGG Opus) |
| Voice Discussion | VAPI.ai (REST API + HTML widget) |
| VAPI LLM | OpenAI GPT-4o-mini |
| VAPI Voice | Vapi built-in "Elliot" |
| VAPI Transcriber | Deepgram Nova-3 |
| PDF Extraction | pdfplumber |
| DOCX Extraction | python-docx |
| URL Extraction | trafilatura |
| Plain text / MD | Built-in decode |

## Quick Start

```bash
# Clone and enter project
git clone <repo-url> && cd VoiceReaderTG

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env — need TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, VAPI_API_KEY, VAPI_PUBLIC_KEY, BASE_URL

# Run
uv run uvicorn app.main:app --reload
```

For VAPI webhooks, you need a public URL. Use Cloudflare Tunnel (recommended — stable, free):
```bash
cloudflared tunnel --url http://localhost:8000
```
Then set `BASE_URL` in `.env` to the tunnel URL. See [Setup Guide](docs/SETUP.md) for details, including the required VAPI provider credential registration step.

## Known Limitations

- **VAPI web widget with dynamic assistants**: The public-key-based VAPI widget returns 403 when given a dynamically created assistant ID. Voice discussion currently only works via the VAPI dashboard. Fix requires server-side `POST /call/web` to create a WebRTC call and deliver the URL to the browser.
- **ngrok free tier**: Shows an interstitial page on first request, breaking VAPI webhook delivery. Use Cloudflare Tunnel instead.
- **In-memory sessions**: Sessions are lost on server restart. Acceptable for development; swap to Redis for production.

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — System design, data flow, and design decisions
- [Setup Guide](docs/SETUP.md) — Detailed setup including VAPI credential steps and tunnel options
- [VAPI Integration](docs/VAPI_INTEGRATION.md) — API usage details, webhook format, and implementation learnings
- [Prompts Registry](docs/PROMPTS.md) — All AI prompts documented with change log

## Project Structure

```
app/
├── main.py              # FastAPI entry point + bot lifecycle
├── config.py            # Environment configuration (pydantic-settings, extra="ignore")
├── bot/                 # Telegram bot handlers
├── services/            # Business logic (extraction, summarization, TTS, VAPI)
├── tools/               # VAPI tool handlers
├── api/                 # HTTP routes + VAPI webhooks
├── models/              # Pydantic data schemas
└── templates/           # Chat page HTML
```

## License

MIT

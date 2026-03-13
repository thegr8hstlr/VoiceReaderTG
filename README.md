# VoiceReaderTG

Telegram bot that summarizes documents (PDF, DOCX, URLs) with AI-generated voice notes and offers interactive voice discussions powered by VAPI.ai.

## Architecture

```
User sends PDF/URL on Telegram
  → Extract text (pdfplumber / trafilatura)
  → Summarize with Claude API
  → Generate voice note (OpenAI TTS)
  → Send: voice note + text summary + "Discuss This Document" button

User clicks "Discuss This Document"
  → Opens web page with VAPI Web SDK
  → Dynamic VAPI assistant created with document context
  → User asks follow-up questions via voice
  → VAPI tools: search_document, get_key_points, get_further_reading
  → On call end: assistant cleaned up automatically
```

## Features

- PDF and DOCX document processing
- URL/article content extraction
- AI-powered structured summaries (Claude)
- Voice note generation (OpenAI TTS, OGG Opus)
- Interactive voice discussions via VAPI.ai
- Dynamic VAPI assistant creation per document
- Server-side tool calling for document search
- Webhook-based assistant lifecycle management
- Minimal, clean Web SDK voice chat UI

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI + Python 3.11+ |
| Telegram Bot | python-telegram-bot v21 |
| Summarization | Claude API (claude-sonnet-4-20250514) |
| Voice Notes | OpenAI TTS (tts-1, nova voice) |
| Voice Discussion | VAPI.ai (REST API + Web SDK) |
| PDF Extraction | pdfplumber |
| DOCX Extraction | python-docx |
| URL Extraction | trafilatura |

## Quick Start

```bash
# Clone and enter project
git clone <repo-url> && cd VoiceReaderTG

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run
uv run uvicorn app.main:app --reload
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — System design and data flow
- [Setup Guide](docs/SETUP.md) — Detailed setup instructions
- [VAPI Integration](docs/VAPI_INTEGRATION.md) — Deep dive on VAPI patterns
- [Prompts Registry](docs/PROMPTS.md) — All AI prompts documented

## Project Structure

```
app/
├── main.py              # FastAPI entry point + bot lifecycle
├── config.py            # Environment configuration
├── bot/                 # Telegram bot handlers
├── services/            # Business logic (extraction, summarization, TTS, VAPI)
├── tools/               # VAPI tool handlers
├── api/                 # HTTP routes + VAPI webhooks
├── models/              # Pydantic data schemas
└── templates/           # Chat page HTML
```

## License

MIT

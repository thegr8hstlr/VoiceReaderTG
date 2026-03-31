# VoiceReaderTG

Telegram bot that summarizes documents (PDF, DOCX, MD, TXT, URLs) with AI-generated voice notes and offers interactive voice discussions powered by Retell AI.

## How It Works

```
User sends PDF / DOCX / URL / text on Telegram
  -> Extract text (pdfplumber / python-docx / trafilatura)
  -> Summarize with OpenAI GPT-4o-mini
  -> Generate voice note (OpenAI TTS)
  -> Upload document to Retell Knowledge Base
  -> Send: voice note + summary + "Discuss This Document" button

User clicks "Discuss This Document"
  -> Opens web page with voice call interface
  -> Retell AI agent discusses the document via voice
  -> Agent uses Knowledge Base (automatic RAG) for document questions
  -> Agent uses web search (Tavily/DuckDuckGo) for broader topics
  -> Transcript sent to Telegram after call ends
```

## Features

- PDF, DOCX, MD, TXT document processing
- URL / article content extraction
- AI-powered structured summaries with key points
- Voice note generation (OpenAI TTS, OGG Opus)
- Voice discussions via Retell AI with automatic document RAG
- Web search during voice calls (Tavily + DuckDuckGo fallback)
- Multilingual support (English, Hindi, and more)
- Discussion transcript sent to Telegram after call
- In-memory session store with 1hr TTL
- Docker deployment with Caddy reverse proxy

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI + Python 3.12 |
| Telegram Bot | python-telegram-bot v21 (async) |
| Summarization | OpenAI GPT-4o-mini |
| Voice Notes | OpenAI TTS (tts-1, nova voice) |
| Voice Discussion | Retell AI (Knowledge Base + Web Call SDK) |
| Web Search | Tavily (primary) + DuckDuckGo (fallback) |
| PDF Extraction | pdfplumber |
| DOCX Extraction | python-docx |
| URL Extraction | trafilatura |
| Deployment | Docker + Caddy |

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/thegr8hstlr/VoiceReaderTG.git
cd VoiceReaderTG
uv sync
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your API keys:
- `TELEGRAM_BOT_TOKEN` — from [@BotFather](https://t.me/BotFather)
- `OPENAI_API_KEY` — from [OpenAI](https://platform.openai.com/api-keys)
- `ANTHROPIC_API_KEY` — from [Anthropic](https://console.anthropic.com/)
- `RETELL_API_KEY` — from [Retell AI](https://www.retellai.com/)
- `RETELL_AGENT_ID` — create an agent on Retell dashboard (see below)
- `TAVILY_API_KEY` — (optional) from [Tavily](https://tavily.com/) for web search
- `BASE_URL` — your public HTTPS URL (required for Telegram buttons and Retell webhooks)

### 3. Set up Retell AI agent

1. Sign up at [retellai.com](https://www.retellai.com/)
2. Create a new agent with a Retell LLM
3. Set the system prompt with dynamic variable placeholders:

```
You are a female voice assistant discussing a specific document with the user.
You speak in the same language the user speaks.

Document Title: {{document_title}}
Summary: {{document_summary}}
Key Points: {{key_points}}
```

4. Set begin message: `Hi! I've read through "{{document_title}}" and I'm ready to discuss it. What would you like to know?`
5. Copy the Agent ID to your `.env`

### 4. Run locally

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

For the "Discuss" button to work, you need a public HTTPS URL. Use ngrok for local dev:

```bash
ngrok http 8000
```

Set `BASE_URL` in `.env` to the ngrok URL.

### 5. Deploy with Docker (production)

```bash
docker compose up -d --build
```

Use Caddy or nginx as a reverse proxy with HTTPS. Example Caddy config:

```
voice.yourdomain.com {
    reverse_proxy localhost:8000
    encode gzip
}
```

## Project Structure

```
app/
├── main.py              # FastAPI entry point + bot lifecycle
├── config.py            # Environment configuration
├── bot/
│   ├── runner.py        # Telegram bot setup and polling
│   └── handlers.py      # Message/document processing pipeline
├── services/
│   ├── extractor.py     # PDF, DOCX, URL, text extraction
│   ├── summarizer.py    # AI summarization (OpenAI)
│   ├── tts.py           # Voice note generation (OpenAI TTS)
│   ├── retell_call.py   # Retell AI web call + KB management
│   ├── session_store.py # In-memory session storage
│   └── web_search.py    # Tavily + DuckDuckGo web search
├── api/
│   ├── routes.py        # HTTP endpoints (health, chat page, start call)
│   └── retell_webhook.py # Retell event handler (transcript, cleanup)
├── models/
│   └── schemas.py       # Pydantic data models
└── templates/
    └── chat.html        # Voice call web interface (Retell SDK)
```

## License

MIT

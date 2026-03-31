# Setup Guide

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager

## API Keys Required

### 1. Telegram Bot Token
1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts
3. Copy the bot token

### 2. OpenAI API Key
1. Sign up at [platform.openai.com](https://platform.openai.com)
2. Go to API Keys -> Create new secret key
3. Used for: summarization (GPT-4o-mini), TTS (tts-1), and chat responses

### 3. Retell AI
1. Sign up at [retellai.com](https://www.retellai.com/)
2. Get your API key from the dashboard
3. Create an agent (see Agent Setup below)
4. Copy the Agent ID

### 4. Tavily (Optional)
1. Sign up at [tavily.com](https://tavily.com/)
2. Get your API key (1000 free searches/month)
3. If not configured, DuckDuckGo is used as fallback (no key needed)

## Retell Agent Setup

1. Create a new agent on the Retell dashboard
2. Choose a voice and set the LLM model
3. Set the system prompt with dynamic variable placeholders:

```
You are a female voice assistant discussing a specific document with the user.
You speak in the same language the user speaks.

Document Title: {{document_title}}
Summary: {{document_summary}}
Key Points: {{key_points}}
```

4. Set begin message: `Hi! I've read through "{{document_title}}" and I'm ready to discuss it. What would you like to know?`
5. Add a custom tool `web_search` pointing to `{YOUR_BASE_URL}/webhook/retell/tool/web_search`
6. Set webhook URL to `{YOUR_BASE_URL}/webhook/retell` with events: `call_ended`, `call_analyzed`

## Environment Setup

```bash
git clone https://github.com/thegr8hstlr/VoiceReaderTG.git
cd VoiceReaderTG
uv sync
cp .env.example .env
```

Edit `.env` with your API keys:

```env
TELEGRAM_BOT_TOKEN=your_telegram_token
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key
RETELL_API_KEY=your_retell_key
RETELL_AGENT_ID=your_retell_agent_id
TAVILY_API_KEY=your_tavily_key
BASE_URL=http://localhost:8000
```

## Running Locally

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The bot starts polling Telegram. The FastAPI server handles:
- `GET /health` — health check
- `GET /chat/{session_id}` — voice discussion page
- `POST /chat/{session_id}/start` — create Retell web call
- `POST /webhook/retell` — Retell webhook endpoint
- `POST /webhook/retell/tool/web_search` — web search tool endpoint

### Public URL for Voice Discussion

For the "Discuss" button and Retell webhooks to work, you need a public HTTPS URL:

```bash
ngrok http 8000
```

Set `BASE_URL` in `.env` to the ngrok URL and update your Retell agent's webhook URL accordingly.

## Docker Deployment (Production)

```bash
docker compose up -d --build
```

Use Caddy as a reverse proxy with automatic HTTPS:

```
voice.yourdomain.com {
    reverse_proxy localhost:8000
    encode gzip
}
```

Then set `BASE_URL=https://voice.yourdomain.com` in your `.env`.

## Running Tests

```bash
uv run pytest tests/ -v
```

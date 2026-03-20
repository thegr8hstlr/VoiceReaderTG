# Setup Guide

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager

## API Keys Required

### 1. Telegram Bot Token
1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts
3. Copy the bot token

### 2. OpenAI API Key
1. Sign up at [platform.openai.com](https://platform.openai.com)
2. Go to API Keys → Create new secret key
3. Copy the key
4. This key is used for: summarization (GPT-4o-mini), TTS (tts-1), and chat responses

### 3. VAPI Keys
1. Sign up at [vapi.ai](https://vapi.ai)
2. Go to Dashboard → Organization → API Keys
3. Copy both the **Private Key** (`VAPI_API_KEY`) and **Public Key** (`VAPI_PUBLIC_KEY`)

### 4. VAPI Provider Credentials (Required for voice calls)

VAPI needs your OpenAI API key registered in its system to make calls. Without this, calls silently fail to connect.

**Option A — Via VAPI Dashboard (recommended):**
1. Go to [dashboard.vapi.ai](https://dashboard.vapi.ai) → Provider Keys
2. Add your OpenAI API key under "OpenAI"
3. Add your Deepgram API key under "Deepgram" (for transcription)

**Option B — Via API:**
```bash
curl -X POST https://api.vapi.ai/credential \
  -H "Authorization: Bearer $VAPI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"provider": "openai", "apiKey": "sk-..."}'
```

## Environment Setup

```bash
# Clone the repository
git clone <repo-url>
cd VoiceReaderTG

# Install dependencies
uv sync

# Create environment file
cp .env.example .env
```

Edit `.env` with your API keys:

```env
TELEGRAM_BOT_TOKEN=your_telegram_token
OPENAI_API_KEY=sk-...
VAPI_API_KEY=your_vapi_private_key
VAPI_PUBLIC_KEY=your_vapi_public_key
BASE_URL=http://localhost:8000
```

Note: `ANTHROPIC_API_KEY` is no longer required. If your `.env` has extra variables, pydantic-settings is configured with `extra="ignore"` so they are safely ignored.

## Running Locally

```bash
# Start the server (runs both FastAPI and Telegram bot)
uv run uvicorn app.main:app --reload --port 8000
```

The bot will start polling Telegram for messages. The FastAPI server handles:
- `GET /health` — health check
- `GET /chat/{session_id}` — voice discussion page
- `POST /chat/{session_id}/start` — create VAPI assistant
- `POST /webhook/vapi` — VAPI webhook endpoint

## For Voice Discussion (VAPI Webhooks)

For VAPI webhooks to work, your server needs a public URL. VAPI calls your server for tool execution during voice calls.

### Option 1 — Cloudflare Tunnel (recommended for local dev)

```bash
cloudflared tunnel --url http://localhost:8000
```

Cloudflare Tunnel gives a **stable, free URL** that persists across restarts. This is important because:
- Your `BASE_URL` in `.env` needs to match the tool server URLs embedded in the VAPI assistant
- The "Discuss" button in Telegram messages contains the URL — a changed URL breaks existing links

### Option 2 — ngrok (use with caution)

```bash
ngrok http 8000
```

**Known issues with ngrok free tier:**
- Shows an interstitial HTML page on the first request — VAPI webhook calls hit this page and fail silently
- URL changes on every restart — existing Telegram "Discuss" buttons stop working
- If you use ngrok, set `NGROK_SKIP_BROWSER_WARNING=true` in your environment and test webhook delivery manually

### Option 3 — Cloud deployment

Deploy to any host with a stable public URL (Railway, Render, Fly.io). Update `BASE_URL` in your environment variables.

After getting a public URL, update `BASE_URL` in `.env`:

```env
BASE_URL=https://your-stable-url.trycloudflare.com
```

## Running Tests

```bash
uv run pytest tests/ -v
```

## Deploying to a Server

1. Set all environment variables on your host
2. Set `BASE_URL` to your public server URL
3. Run: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
4. For long-running deployments, use a process manager (systemd, supervisord, or Docker)
5. Note: The Telegram bot runs in polling mode. For high-traffic deployments, switch to webhook mode in `bot/runner.py`

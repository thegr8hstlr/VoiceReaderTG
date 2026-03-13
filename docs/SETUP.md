# Setup Guide

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- ffmpeg (for audio processing, if needed)

## API Keys Required

### 1. Telegram Bot Token
1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts
3. Copy the bot token

### 2. Anthropic API Key
1. Sign up at [console.anthropic.com](https://console.anthropic.com)
2. Go to API Keys → Create Key
3. Copy the key

### 3. OpenAI API Key
1. Sign up at [platform.openai.com](https://platform.openai.com)
2. Go to API Keys → Create new secret key
3. Copy the key

### 4. VAPI Keys
1. Sign up at [vapi.ai](https://vapi.ai)
2. Go to Dashboard → Organization → API Keys
3. Copy both the **Private Key** (`VAPI_API_KEY`) and **Public Key** (`VAPI_PUBLIC_KEY`)

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
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
VAPI_API_KEY=your_vapi_private_key
VAPI_PUBLIC_KEY=your_vapi_public_key
BASE_URL=http://localhost:8000
```

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

## For Voice Discussion (VAPI)

For VAPI webhooks to work, your server needs a public URL. Options:

1. **Vercel deployment** (recommended for production)
2. **ngrok** for local development: `ngrok http 8000`

Update `BASE_URL` in `.env` to your public URL.

## Running Tests

```bash
uv run pytest tests/ -v
```

## Deploying to Vercel

1. Install [Vercel CLI](https://vercel.com/docs/cli): `npm i -g vercel`
2. Add environment variables in Vercel dashboard
3. Deploy: `vercel --prod`
4. Update `BASE_URL` to your Vercel URL
5. Note: For Vercel, you'll need to switch the Telegram bot from polling to webhook mode

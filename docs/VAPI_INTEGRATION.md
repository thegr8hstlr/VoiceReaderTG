# VAPI Integration — Implementation Notes & Learnings

## Why VAPI

VAPI provides a managed voice AI pipeline: speech-to-text, LLM processing, text-to-speech, and WebRTC transport — all orchestrated as a single API. This project uses VAPI to add real-time voice conversations about documents, without managing audio streaming infrastructure.

---

## Actual API Usage (What Works)

### 1. Tools Must Be Created Separately

**Critical finding:** You cannot pass `tools` inline on the assistant creation payload. VAPI returns:

```
"property tools should not exist"
```

The correct flow is:

**Step 1 — Create each tool via POST /tool:**
```
POST https://api.vapi.ai/tool
{
  "type": "function",
  "function": {
    "name": "search_document",
    "description": "Search the document for relevant passages",
    "parameters": {
      "type": "object",
      "properties": {
        "query": { "type": "string" }
      },
      "required": ["query"]
    }
  },
  "server": { "url": "https://your-domain.com/webhook/vapi" }
}
```

This returns a tool object with an `id` field.

**Step 2 — Reference tool IDs in model.toolIds when creating the assistant:**
```
POST https://api.vapi.ai/assistant
{
  "name": "DocAssistant-{session_id}",
  "firstMessage": "Hi! I've read through '{title}'...",
  "model": {
    "provider": "openai",
    "model": "gpt-4o-mini",
    "toolIds": ["tool_id_1", "tool_id_2", "tool_id_3"],
    "messages": [{ "role": "system", "content": "..." }]
  },
  "voice": {
    "provider": "vapi",
    "voiceId": "Elliot"
  },
  "transcriber": {
    "provider": "deepgram",
    "model": "nova-3"
  },
  "metadata": { "session_id": "..." },
  "serverUrl": "https://your-domain.com/webhook/vapi"
}
```

### 2. Webhook Payload Format

The actual VAPI webhook payload differs from older docs. Key points:

- **Tool calls** arrive as `message.toolCallList` (not `message.toolCalls`)
- Each item in `toolCallList` has `name` and `arguments` at the **top level** (not nested under a `function` key)
- **Session metadata** is at `message.assistant.metadata` (not `message.metadata`)
- **Event type** is at `message.type`

Example tool-call payload structure:
```json
{
  "message": {
    "type": "tool-calls",
    "toolCallList": [
      {
        "id": "call_abc123",
        "name": "search_document",
        "arguments": { "query": "main conclusions" }
      }
    ],
    "assistant": {
      "metadata": {
        "session_id": "sess_xyz"
      }
    }
  }
}
```

Tool call response format:
```json
{
  "results": [
    {
      "toolCallId": "call_abc123",
      "result": "Found 3 relevant passages: ..."
    }
  ]
}
```

### 3. Voice Provider — Use Built-in Vapi Voices

ElevenLabs integration via VAPI requires your own ElevenLabs account credentials registered with VAPI. For simpler setup, use the built-in `vapi` provider:

```json
"voice": {
  "provider": "vapi",
  "voiceId": "Elliot"
}
```

Available built-in voices include Elliot, Kylie, Cole, and others listed in the VAPI dashboard.

### 4. Transcriber — Deepgram Nova-3

```json
"transcriber": {
  "provider": "deepgram",
  "model": "nova-3"
}
```

Deepgram Nova-3 provides low-latency real-time transcription. OpenAI `gpt-4o-transcribe` also works but is noticeably less responsive.

### 5. Conversation Tuning Parameters

These parameters significantly affect conversation quality:

```json
{
  "responseDelaySeconds": 1.5,
  "startSpeakingPlan": {
    "waitSeconds": 1.8,
    "smartEndpointingEnabled": false
  },
  "stopSpeakingPlan": {
    "backoffSeconds": 2.0
  }
}
```

- `responseDelaySeconds`: How long VAPI waits after the user finishes before the assistant responds
- `startSpeakingPlan.waitSeconds`: Silence threshold before the agent begins speaking
- `smartEndpointingEnabled: false`: Rely on actual silence detection rather than smart prediction (reduces false triggers)
- `stopSpeakingPlan.backoffSeconds`: How long to back off when the user interrupts

### 6. Provider Credentials in VAPI

VAPI cannot use your OpenAI key unless you explicitly register it in VAPI's system. Calls will silently fail to connect without this step.

Register via the VAPI Dashboard → Provider Keys, or via API:
```bash
POST https://api.vapi.ai/credential
{ "provider": "openai", "apiKey": "sk-..." }
```

Same for Deepgram if you are using it as your transcriber.

---

## Assistant Lifecycle

- **Create**: When user opens `/chat/{session_id}`, a `POST /chat/{session_id}/start` creates the tools and assistant
- **Identify**: `session_id` embedded in assistant metadata links webhook events to the right document session
- **Use**: VAPI connects the user to the assistant via WebRTC
- **Clean up**: On `end-of-call-report` webhook, assistant is deleted via `DELETE /assistant/{id}`

This prevents assistant accumulation in the VAPI dashboard.

---

## Tools

Three tools are defined per assistant:

| Tool | Purpose |
|------|---------|
| `search_document` | Fuzzy keyword search across document paragraphs |
| `get_key_points` | Return pre-generated key points from the summary |
| `get_further_reading` | Return suggested reading links |

VAPI sends tool call requests to our `serverUrl` webhook. We dispatch based on `name`, execute against the session store, and return results in the `results` array format above.

---

## Web Widget — Known Limitation

The VAPI html-script-tag widget (public-key-based) cannot connect to dynamically created assistants. It returns:

```
403: Key doesn't allow assistantId
```

What was tried:
- **Public key + assistantId**: 403 on dynamic assistants (public key only works with pre-created fixed assistants)
- **Private key in client JS**: Insecure; not reliably supported by the widget
- **Inline assistant config in widget**: Gets stuck at "Connecting..." — no call established

**Current status**: Voice discussion works correctly when called from the VAPI dashboard directly (confirming assistant creation is valid). The web link from Telegram is pending resolution.

**Recommended fix (not yet implemented)**: Use `POST /call/web` server-side to create a WebRTC call session, then deliver the resulting WebRTC URL to the browser. This bypasses the widget's public-key restriction entirely.

---

## Tunnel / Public URL Notes

VAPI webhooks require a publicly reachable URL. Key learnings:

- **ngrok free tier** shows an interstitial browser confirmation page on the first request — VAPI's webhook calls hit this page and fail silently. Also, the URL changes on every restart.
- **Cloudflare Tunnel** (`cloudflared tunnel --url http://localhost:8000`) provides a stable, free URL that persists across restarts. Strongly preferred for development.

---

## Architecture Diagram

```
Browser (chat.html)
    │
    │ VAPI Web SDK / widget (WebRTC)
    │  [auth limitation: see above]
    │
    ▼
VAPI Cloud
    │
    │ Webhook POST
    │
    ▼
FastAPI (/webhook/vapi)
    │
    ├── tool-calls (toolCallList) → document_tools.py → session_store
    ├── end-of-call-report → delete assistant + tools + session
    └── status-update → log
```

---

## Summary of Gotchas

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| `"property tools should not exist"` | Tools cannot be inline on assistant creation | Create tools via POST /tool, reference by ID in model.toolIds |
| Calls silently fail to connect | Missing provider credentials in VAPI | Register OpenAI/Deepgram keys via VAPI dashboard or POST /credential |
| 403 on widget with dynamic assistant | Public key restricted to pre-created assistants | Use POST /call/web server-side for dynamic call creation |
| ngrok webhook failures | Interstitial page on first request | Use Cloudflare Tunnel instead |
| `toolCalls` key not found in webhook | VAPI uses `toolCallList`, not `toolCalls` | Read from `message.toolCallList` |
| `metadata` not found in webhook | Metadata is at `message.assistant.metadata` | Adjust path in webhook handler |
| Conversation feels choppy | Default tuning too aggressive | Set responseDelaySeconds, waitSeconds, backoffSeconds |

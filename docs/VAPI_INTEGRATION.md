# VAPI Integration Deep Dive

## Why VAPI

VAPI provides a managed voice AI pipeline: speech-to-text, LLM processing, text-to-speech, and WebRTC transport — all orchestrated as a single API. This project uses VAPI to add real-time voice conversations about documents, without managing audio streaming infrastructure.

## VAPI Concepts Used

### 1. Dynamic Assistant Creation

Each document gets its own VAPI assistant with a custom system prompt containing the document's content. This is created via the VAPI REST API when the user opens the chat page.

```
POST https://api.vapi.ai/assistant
{
  "name": "DocAssistant-{session_id}",
  "firstMessage": "Hi! I've read through '{title}'...",
  "model": { "provider": "anthropic", "model": "claude-sonnet-4-20250514", ... },
  "voice": { "provider": "11labs", "voiceId": "..." },
  "tools": [...],
  "metadata": { "session_id": "..." },
  "serverUrl": "https://your-domain.com/webhook/vapi"
}
```

### 2. Assistant Lifecycle Management

- **Create**: When user opens `/chat/{session_id}`, a POST to `/chat/{session_id}/start` creates the assistant
- **Use**: VAPI Web SDK connects the user to the assistant via WebRTC
- **Delete**: On `end-of-call-report` webhook, the assistant is deleted via `DELETE /assistant/{id}`

This prevents assistant accumulation in the VAPI dashboard.

### 3. Server-Side Tool Calling

Three tools are defined on the assistant:

| Tool | Purpose |
|------|---------|
| `search_document` | Fuzzy keyword search across document paragraphs |
| `get_key_points` | Return pre-generated key points from the summary |
| `get_further_reading` | Return suggested reading links |

VAPI sends tool call requests to our `serverUrl` webhook. We dispatch based on function name, execute against the session store, and return results.

### 4. Webhook Event Handling

Our webhook endpoint (`POST /webhook/vapi`) handles three event types:

```
tool-calls        → Execute tool, return results
end-of-call-report → Delete assistant, clean up session
status-update     → Log for debugging
```

The webhook extracts `session_id` from the assistant's metadata to correlate requests with document sessions.

### 5. Web SDK Integration

The chat page loads the VAPI Web SDK from CDN and provides:
- One-click call start/stop
- Real-time transcript display
- Connection status indicators
- Lazy assistant initialization (created on first call)

### 6. Metadata for Session Correlation

`session_id` is embedded in the assistant's metadata at creation time. When VAPI sends webhook events, this metadata is included in the request body, allowing us to look up the correct document session without maintaining a separate mapping.

## Architecture Diagram

```
Browser (chat.html)
    │
    │ VAPI Web SDK (WebRTC)
    │
    ▼
VAPI Cloud
    │
    │ Webhook POST
    │
    ▼
FastAPI (/webhook/vapi)
    │
    ├── tool-calls → document_tools.py → session_store
    ├── end-of-call-report → delete assistant + session
    └── status-update → log
```

## Design Decisions

1. **One assistant per document, not per user**: Simplifies cleanup and keeps system prompts focused. If multiple users discuss the same document, they each get their own assistant.

2. **Document text in system prompt**: For documents under 15K chars, the full text is in the system prompt. For longer documents, it's truncated — but the `search_document` tool can search the full text stored in the session.

3. **No persistent assistant storage**: Assistants are ephemeral. They're created on demand and deleted after the call. The VAPI dashboard stays clean.

4. **Lazy creation**: The assistant is only created when the user actually opens the chat page and clicks "start call", not when the summary is generated. This avoids creating assistants that are never used.

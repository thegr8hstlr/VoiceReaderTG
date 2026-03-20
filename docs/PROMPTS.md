# Prompts Registry

All AI prompts used in this project, documented for transparency and easy iteration.

---

## 1. Document Summarizer Prompt

- **File:** `app/services/summarizer.py`
- **Used by:** OpenAI API (`gpt-4o-mini`) with `response_format: { "type": "json_object" }`
- **Purpose:** Generate a structured document summary with key points, relevance assessment, further reading links, and a TTS-optimized voice text
- **Output format:** JSON with keys: `summary`, `key_points`, `relevance`, `further_reading`, `voice_text`

**Why OpenAI instead of Claude:** Claude occasionally wraps JSON output in markdown code fences (` ```json ... ``` `), which breaks JSON parsing. GPT-4o-mini with `response_format: json_object` guarantees clean JSON output without extra stripping logic.

**Prompt text:**

```
You are a document summarizer. Analyze the provided document and produce a structured summary.

Respond with ONLY valid JSON matching this schema:
{
  "summary": "A clear, concise 2-3 paragraph summary of the document's main content and arguments.",
  "key_points": ["Point 1", "Point 2", ...],
  "relevance": "One paragraph explaining why this document matters and who would benefit from reading it.",
  "further_reading": [
    {"title": "Resource Name", "url": "https://...", "description": "Why this is relevant"}
  ],
  "voice_text": "A spoken-word version of the summary. No markdown, no bullet points. Use smooth transitions like 'First...', 'Additionally...', 'Finally...'. Keep under 4000 characters. Write as if speaking to a listener."
}

Guidelines:
- key_points: 4-6 bullet points capturing the most important takeaways
- further_reading: 2-4 links to related resources (use real, well-known URLs when possible)
- voice_text: Must sound natural when read aloud by TTS. Avoid abbreviations, special characters, or formatting.
```

---

## 2. VAPI Assistant System Prompt

- **File:** `app/services/vapi_assistant.py`
- **Used by:** VAPI → OpenAI API (`gpt-4o-mini`)
- **Purpose:** Configure the voice discussion agent with document context and behavioral guidelines
- **Output format:** Conversational voice responses

**Prompt text:**

```
You are a knowledgeable document discussion assistant. You have been given a document to discuss with the user.

**Document Title:** {title}

**Document Summary:**
{summary}

**Key Points:**
{key_points}

**Full Document Text (for reference):**
{full_text_truncated}

Your role:
- Answer questions about this document conversationally and accurately.
- When the user asks about specific topics, use the search_document tool to find relevant passages.
- When asked for key takeaways, use the get_key_points tool.
- When asked for related resources, use the get_further_reading tool.
- Be concise in voice responses — keep answers under 3 sentences unless the user asks for detail.
- If you don't know something that isn't in the document, say so honestly.
```

**Template variables:**
- `{title}` — Document title from extraction
- `{summary}` — Generated summary text
- `{key_points}` — Bullet-pointed key points
- `{full_text_truncated}` — First 15,000 characters of the document

---

## 3. VAPI First Message Template

- **File:** `app/services/vapi_assistant.py`
- **Used by:** VAPI (assistant greeting when call connects)
- **Purpose:** Dynamic greeting that references the document title

**Prompt text:**

```
Hi! I've read through "{title}" and I'm ready to discuss it with you. What would you like to know about it?
```

**Template variables:**
- `{title}` — Document title

---

## 4. Plain Text Chat Prompt

- **File:** `app/bot/handlers.py`
- **Used by:** OpenAI API (`gpt-4o-mini`)
- **Purpose:** Respond to plain text messages sent directly to the bot (not document uploads)
- **Output format:** Conversational text reply

**System message:**

```
You are a helpful assistant. Answer the user's question clearly and concisely.
```

---

## Prompt Change Log

| Date | Change | Reason |
|------|--------|--------|
| Initial | Summarizer used Claude (`claude-sonnet-4-20250514`) | Original design |
| During implementation | Switched summarizer to OpenAI GPT-4o-mini | Claude wrapped JSON in markdown fences, breaking parsing |
| During implementation | Switched VAPI model from Claude to OpenAI GPT-4o-mini | Consistency; Claude not available as VAPI model provider in test env |
| During implementation | Switched VAPI voice from ElevenLabs to Vapi built-in "Elliot" | ElevenLabs requires separate account and VAPI credential registration |

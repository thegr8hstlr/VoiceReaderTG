from __future__ import annotations

import io

from openai import OpenAI

from app.config import settings

_client = OpenAI(api_key=settings.openai_api_key)

MAX_TTS_CHARS = 4096


async def generate_voice_note(text: str) -> bytes:
    chunks = _split_text(text, MAX_TTS_CHARS)
    audio_parts: list[bytes] = []

    for chunk in chunks:
        response = _client.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=chunk,
            response_format="opus",
        )
        audio_parts.append(response.content)

    if len(audio_parts) == 1:
        return audio_parts[0]

    # For multiple chunks, concatenate the raw bytes
    # (works for OGG Opus streams)
    buffer = io.BytesIO()
    for part in audio_parts:
        buffer.write(part)
    return buffer.getvalue()


def _split_text(text: str, max_len: int) -> list[str]:
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break
        # Find the last sentence boundary within the limit
        cut = text[:max_len].rfind(". ")
        if cut == -1:
            cut = max_len
        else:
            cut += 1  # include the period
        chunks.append(text[:cut].strip())
        text = text[cut:].strip()
    return chunks

from __future__ import annotations

import logging
import re
import uuid

from openai import OpenAI
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.config import settings
from app.models.schemas import SessionData
from app.services.extractor import extract_docx, extract_pdf, extract_text_file, extract_url
from app.services.session_store import save_session
from app.services.summarizer import summarize_document
from app.services.tts import generate_voice_note

logger = logging.getLogger(__name__)

URL_PATTERN = re.compile(r"https?://\S+")

_openai_client = OpenAI(api_key=settings.openai_api_key)

TEXT_EXTENSIONS = {".md", ".txt", ".csv", ".json", ".xml", ".html", ".htm", ".rst"}


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Welcome to VoiceReaderTG!\n\n"
        "Send me a PDF, DOCX, MD, or URL and I'll:\n"
        "1. Summarize it with key points\n"
        "2. Generate a voice note summary\n"
        "3. Let you discuss the document with a voice AI\n\n"
        "Or just chat with me — I'm happy to talk!"
    )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    doc = update.message.document
    file_name = doc.file_name or "document"
    mime = doc.mime_type or ""
    ext = "." + file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""

    if "pdf" in mime or ext == ".pdf":
        extractor = extract_pdf
    elif "wordprocessingml" in mime or "msword" in mime or ext == ".docx":
        extractor = extract_docx
    elif ext in TEXT_EXTENSIONS or "text/" in mime:
        extractor = extract_text_file
    else:
        await update.message.reply_text(
            "Unsupported file type. Please send a PDF, DOCX, MD, or text file."
        )
        return

    status = await update.message.reply_text("Downloading file...")

    tg_file = await doc.get_file()
    data = await tg_file.download_as_bytearray()

    await status.edit_text("Extracting text...")
    try:
        text = extractor(bytes(data))
    except Exception:
        logger.exception("Extraction failed")
        await status.edit_text("Failed to extract text from the document.")
        return

    if not text.strip():
        await status.edit_text("The document appears to be empty.")
        return

    await _process_content(update, status, text, file_name)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text or ""

    # Check if it's a URL
    match = URL_PATTERN.search(text)
    if match:
        await _handle_url(update, match.group(0))
        return

    # Otherwise, chat with LLM
    await _handle_chat(update, text)


async def _handle_url(update: Update, url: str) -> None:
    status = await update.message.reply_text("Fetching article...")

    try:
        text = extract_url(url)
    except ValueError as e:
        await status.edit_text(str(e))
        return
    except Exception:
        logger.exception("URL extraction failed")
        await status.edit_text("Failed to extract content from the URL.")
        return

    title = url.split("/")[-1][:50] or "Web Article"
    await _process_content(update, status, text, title)


async def _handle_chat(update: Update, text: str) -> None:
    response = _openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are VoiceReader, a friendly Telegram assistant. "
                    "You can summarize documents (PDF, DOCX, MD) and URLs when users send them. "
                    "For general messages, be helpful, concise, and conversational."
                ),
            },
            {"role": "user", "content": text},
        ],
        max_tokens=512,
    )
    reply = response.choices[0].message.content
    await update.message.reply_text(reply)


async def _process_content(
    update: Update, status, text: str, title: str
) -> None:
    await status.edit_text("Summarizing with AI...")
    try:
        summary_result = await summarize_document(text, title)
    except Exception:
        logger.exception("Summarization failed")
        await status.edit_text("Failed to generate summary.")
        return

    await status.edit_text("Generating voice note...")
    try:
        audio_bytes = await generate_voice_note(summary_result.voice_text)
    except Exception:
        logger.exception("TTS failed")
        await status.edit_text("Failed to generate voice note.")
        return

    # Create session for voice discussion
    session_id = str(uuid.uuid4())
    session = SessionData(
        session_id=session_id,
        title=title,
        full_text=text,
        summary_result=summary_result,
    )
    save_session(session)

    chat_url = f"{settings.base_url}/chat/{session_id}"
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Discuss This Document", url=chat_url)]]
    )

    # Send voice note
    await update.message.reply_voice(
        voice=audio_bytes,
        caption=f"Voice summary of: {title}",
    )

    # Send text summary with discuss button
    await status.edit_text(
        summary_result.as_telegram_markdown(),
        parse_mode="Markdown",
        reply_markup=keyboard,
    )

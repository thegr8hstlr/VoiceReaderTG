from __future__ import annotations

import io

import pdfplumber
from docx import Document
from trafilatura import extract, fetch_url

MAX_CHARS = 100_000


def extract_pdf(data: bytes) -> str:
    text_parts: list[str] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return _truncate("\n\n".join(text_parts))


def extract_docx(data: bytes) -> str:
    doc = Document(io.BytesIO(data))
    text_parts = [p.text for p in doc.paragraphs if p.text.strip()]
    return _truncate("\n\n".join(text_parts))


def extract_url(url: str) -> str:
    downloaded = fetch_url(url)
    if not downloaded:
        raise ValueError(f"Could not download content from {url}")
    text = extract(downloaded, include_links=False, include_comments=False)
    if not text:
        raise ValueError(f"Could not extract text from {url}")
    return _truncate(text)


def extract_text_file(data: bytes) -> str:
    text = data.decode("utf-8", errors="replace")
    return _truncate(text)


def _truncate(text: str) -> str:
    if len(text) > MAX_CHARS:
        return text[:MAX_CHARS] + "\n\n[Content truncated]"
    return text

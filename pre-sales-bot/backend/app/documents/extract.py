from __future__ import annotations

from io import BytesIO
from pathlib import Path

from backend.app.core.guard import looks_like_jailbreak

UPLOAD_CHAR_LIMIT = 20000


class UnsafeUpload(Exception):
    """Visitor file looks like an attempt to override the assistant."""


def extract_text(filename: str, data: bytes, *, limit: int = UPLOAD_CHAR_LIMIT, sanitize: bool = True) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(data))
        text = "\n".join((page.extract_text() or "") for page in reader.pages[:25])
    elif suffix in {".docx", ".doc"}:
        import docx

        text = "\n".join(paragraph.text for paragraph in docx.Document(BytesIO(data)).paragraphs)
    elif suffix in {".txt", ".md"}:
        text = data.decode("utf-8", errors="replace")
    else:
        raise ValueError("Only PDF, DOCX, TXT, and Markdown files are accepted")
    text = text.strip()
    if sanitize and looks_like_jailbreak(text):
        raise UnsafeUpload()
    return text[:limit]

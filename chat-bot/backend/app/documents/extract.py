from io import BytesIO
from pathlib import Path

INJECTION_MARKERS = ("ignore previous", "ignore all instructions", "system prompt", "you are now", "disregard your rules")

UPLOAD_CHAR_LIMIT = 20000
UPLOAD_PAGE_LIMIT = 25


def extract_text(
    filename: str,
    data: bytes,
    *,
    limit: int = UPLOAD_CHAR_LIMIT,
    max_pages: int = UPLOAD_PAGE_LIMIT,
    sanitize: bool = True,
) -> str:
    """Decode a document to text.

    Defaults suit visitor uploads: capped and filtered because the text ends up in a
    model prompt. The content library passes a larger limit and `sanitize=False`,
    since those files are reviewed and committed, and a capability document is
    allowed to contain a phrase like "system prompt".
    """
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(data))
        text = "\n".join((page.extract_text() or "") for page in reader.pages[:max_pages])
    elif suffix in {".docx", ".doc"}:
        import docx

        text = "\n".join(p.text for p in docx.Document(BytesIO(data)).paragraphs)
    elif suffix in {".txt", ".md"}:
        text = data.decode("utf-8", errors="replace")
    else:
        raise ValueError("Only PDF, DOCX, and TXT files are accepted")
    if sanitize:
        return sanitize_untrusted(text, limit=limit)
    return (text or "").strip()[:limit]


def sanitize_untrusted(text: str, limit: int = UPLOAD_CHAR_LIMIT) -> str:
    cleaned = [line for line in (text or "").splitlines() if not any(m in line.lower() for m in INJECTION_MARKERS)]
    return "\n".join(cleaned).strip()[:limit]

from io import BytesIO
from pathlib import Path

INJECTION_MARKERS = ("ignore previous", "ignore all instructions", "system prompt", "you are now", "disregard your rules")


def extract_text(filename: str, data: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(data))
        text = "\n".join((page.extract_text() or "") for page in reader.pages[:25])
    elif suffix in {".docx", ".doc"}:
        import docx

        text = "\n".join(p.text for p in docx.Document(BytesIO(data)).paragraphs)
    elif suffix in {".txt", ".md"}:
        text = data.decode("utf-8", errors="replace")
    else:
        raise ValueError("Only PDF, DOCX, and TXT files are accepted")
    return sanitize_untrusted(text)


def sanitize_untrusted(text: str) -> str:
    cleaned = [line for line in (text or "").splitlines() if not any(m in line.lower() for m in INJECTION_MARKERS)]
    return "\n".join(cleaned).strip()[:20000]

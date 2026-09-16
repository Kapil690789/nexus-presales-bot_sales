from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from backend.app.documents.extract import extract_text
from backend.app.rag.chunker import chunk_text
from backend.app.rag.store import Document

CONTENT_SOURCE = "content"
TEXT_SUFFIXES = {".md", ".markdown", ".txt"}
BINARY_SUFFIXES = {".pdf", ".docx"}
SUPPORTED_SUFFIXES = TEXT_SUFFIXES | BINARY_SUFFIXES

# Content files are trusted, reviewed, and committed to git, so they are not run
# through the prompt-injection filter that visitor uploads are. A capability
# document is allowed to contain the words "system prompt".
MAX_DOC_CHARS = 200_000
SHORT_EXTRACTION_CHARS = 200
NOISY_CHUNK_COUNT = 30

# The folder a document lives in implies what it is, so `kind` rarely needs stating.
FOLDER_KINDS = {
    "case-studies": "case_study",
    "capabilities": "capability",
    "process": "process",
    "trust": "trust",
    "faq": "faq",
    "testimonials": "testimonial",
}

KNOWN_KEYS = {
    "title",
    "kind",
    "case_id",
    "service",
    "industry",
    "platforms",
    "stacks",
    "tags",
    "outcome",
    "summary",
    "url",
    "status",
    "nda_only",
    "updated",
}

KNOWN_STATUSES = {"published", "draft"}

FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
SECTION = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
TRAILING_SPACE = re.compile(r"[ \t]+$", re.MULTILINE)
BLANK_LINES = re.compile(r"\n{3,}")


@dataclass
class Finding:
    level: str  # error | warning | info
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.level.upper():7} {self.path}: {self.message}"


@dataclass
class ContentScan:
    documents: list[Document] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    files: int = 0
    indexed: int = 0
    skipped: int = 0

    @property
    def errors(self) -> list[Finding]:
        return [finding for finding in self.findings if finding.level == "error"]

    @property
    def warnings(self) -> list[Finding]:
        return [finding for finding in self.findings if finding.level == "warning"]


def content_documents(content_dir: Path, known_services: set[str] | None = None) -> list[Document]:
    return scan_content(content_dir, known_services).documents


def scan_content(content_dir: Path, known_services: set[str] | None = None) -> ContentScan:
    """Read the content library into documents, collecting validation findings.

    Findings are returned rather than raised so `--dry-run` can report every problem
    in one pass instead of stopping at the first bad file.
    """
    scan = ContentScan()
    if not content_dir.exists():
        scan.findings.append(Finding("warning", str(content_dir), "content directory does not exist"))
        return scan

    seen: dict[str, str] = {}
    for path in sorted(content_dir.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(content_dir)
        # `_template.md`, `README.md`, and anything under a `_` or `.` folder are
        # scaffolding for authors, not material for the bot.
        if any(part.startswith(("_", ".")) for part in relative.parts):
            continue
        if path.name.lower() in {"readme.md", "readme.txt"}:
            continue
        scan.files += 1
        suffix = path.suffix.lower()
        if suffix not in SUPPORTED_SUFFIXES:
            scan.skipped += 1
            scan.findings.append(
                Finding("warning", relative.as_posix(), f"unsupported file type {suffix or '(none)'}, skipped")
            )
            continue

        slug = relative.with_suffix("").as_posix()
        if slug in seen:
            scan.skipped += 1
            scan.findings.append(
                Finding("error", relative.as_posix(), f"document id collides with {seen[slug]}; rename one of them")
            )
            continue
        seen[slug] = relative.as_posix()

        documents = _read_file(path, relative, slug, scan, known_services)
        if documents:
            scan.indexed += 1
            scan.documents += documents
    return scan


def _read_file(
    path: Path,
    relative: Path,
    slug: str,
    scan: ContentScan,
    known_services: set[str] | None,
) -> list[Document]:
    label = relative.as_posix()
    suffix = path.suffix.lower()
    front: dict = {}
    if suffix in TEXT_SUFFIXES:
        raw = path.read_text(encoding="utf-8", errors="replace")
        parsed, body, had_block = _split_front_matter(raw, label, scan)
        if parsed is None:
            scan.skipped += 1
            return []
        front = parsed
        if not had_block:
            scan.findings.append(Finding("warning", label, "no front matter block; inferring title from the filename"))
    else:
        try:
            body = extract_text(path.name, path.read_bytes(), limit=MAX_DOC_CHARS, sanitize=False)
        except Exception as error:
            scan.skipped += 1
            scan.findings.append(Finding("error", label, f"could not read: {error}"))
            return []
        scan.findings.append(Finding("warning", label, "binary file has no front matter; inferring from folder and filename"))

    body = _normalize(body)
    if not body:
        scan.skipped += 1
        scan.findings.append(Finding("error", label, "no readable text extracted"))
        return []
    if suffix in BINARY_SUFFIXES and len(body) < SHORT_EXTRACTION_CHARS:
        scan.findings.append(
            Finding("warning", label, f"only {len(body)} characters extracted; consider rewriting as Markdown")
        )

    status = str(front.get("status") or "published").strip().lower()
    if status not in KNOWN_STATUSES:
        scan.findings.append(Finding("warning", label, f"unknown status '{status}'; treating as draft"))
    if status != "published":
        scan.skipped += 1
        scan.findings.append(Finding("info", label, f"status is '{status}', not indexed"))
        return []

    service = front.get("service")
    if service and known_services is not None and str(service) not in known_services:
        scan.findings.append(
            Finding("warning", label, f"service '{service}' is not a key in services.yaml")
        )

    title = str(front.get("title") or "").strip() or _title_from_filename(path)
    folder = relative.parts[0] if len(relative.parts) > 1 else ""
    kind = str(front.get("kind") or FOLDER_KINDS.get(folder, "document"))
    metadata = _metadata(front, folder=folder, kind=kind, filename=path.name)

    documents: list[Document] = []
    for index, (heading, chunk) in enumerate(_chunks(body)):
        documents.append(
            Document(
                doc_id=f"{CONTENT_SOURCE}:{slug}#{index}",
                title=f"{title} — {heading}" if heading else title,
                content=chunk,
                source=CONTENT_SOURCE,
                source_id=slug,
                metadata={**metadata, "chunk": index, "heading": heading, "doc_title": title},
            )
        )
    if len(documents) > NOISY_CHUNK_COUNT:
        scan.findings.append(
            Finding("warning", label, f"split into {len(documents)} chunks; consider splitting the file up")
        )
    return documents


def _split_front_matter(raw: str, label: str, scan: ContentScan) -> tuple[dict | None, str, bool]:
    """Returns None for the front matter when it could not be parsed at all.

    Unparseable front matter has to stop the document rather than fall back to
    defaults, because the defaults are `status: published` and `nda_only: false` —
    a typo in the block must not be what publishes a confidential case study.
    """
    match = FRONT_MATTER.match(raw)
    if not match:
        return {}, raw, False
    body = raw[match.end() :]
    try:
        parsed = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as error:
        detail = str(error).splitlines()[0]
        scan.findings.append(Finding("error", label, f"front matter is not valid YAML: {detail}"))
        return None, body, True
    if not isinstance(parsed, dict):
        scan.findings.append(Finding("error", label, "front matter must be a mapping"))
        return None, body, True
    if "title" not in parsed:
        scan.findings.append(Finding("error", label, "front matter is missing 'title'"))
    for key in parsed:
        if key not in KNOWN_KEYS:
            scan.findings.append(Finding("warning", label, f"unknown front matter key '{key}'"))
    return parsed, body, True


def _metadata(front: dict, *, folder: str, kind: str, filename: str) -> dict:
    metadata: dict = {"folder": folder, "kind": kind, "filename": filename}
    for key in ("case_id", "service", "industry", "outcome", "summary", "url"):
        value = front.get(key)
        if value not in (None, ""):
            metadata[key] = str(value)
    for key in ("platforms", "stacks", "tags"):
        value = front.get(key)
        if value:
            items = value if isinstance(value, list) else [value]
            metadata[key] = [str(item) for item in items]
    if front.get("updated"):
        metadata["updated"] = str(front["updated"])
    metadata["nda_only"] = bool(front.get("nda_only"))
    return metadata


def _chunks(body: str) -> list[tuple[str, str]]:
    """Split on level-2 headings first, then pack each section to the chunk limit.

    Section-aware splitting keeps one FAQ answer or one case-study section in a
    single chunk, and the heading rides along so a chunk still makes sense alone.
    """
    chunks: list[tuple[str, str]] = []
    for heading, section in _sections(body):
        for piece in chunk_text(section):
            chunks.append((heading, f"{heading}\n{piece}" if heading else piece))
    return chunks


def _sections(body: str) -> list[tuple[str, str]]:
    parts = SECTION.split(body)
    sections: list[tuple[str, str]] = []
    preamble = parts[0].strip()
    if preamble:
        sections.append(("", preamble))
    for index in range(1, len(parts) - 1, 2):
        text = parts[index + 1].strip()
        if text:
            sections.append((parts[index].strip(), text))
    return sections


def _normalize(text: str) -> str:
    cleaned = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    return BLANK_LINES.sub("\n\n", TRAILING_SPACE.sub("", cleaned)).strip()


def _title_from_filename(path: Path) -> str:
    return path.stem.replace("-", " ").replace("_", " ").strip().capitalize()

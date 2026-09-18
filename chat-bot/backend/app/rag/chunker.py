from __future__ import annotations

import html
import re
from pathlib import Path

from backend.app.config_loader.loader import AppConfig
from backend.app.rag.store import Document

MAX_CHUNK_CHARS = 1200
CHUNK_OVERLAP_CHARS = 160

_TAGS = re.compile(r"<[^>]+>")
_DROP_BLOCKS = re.compile(r"<(script|style|svg|noscript)\b.*?</\1>", re.IGNORECASE | re.DOTALL)
_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_WHITESPACE = re.compile(r"[ \t]+")
_BLANK_LINES = re.compile(r"\n{3,}")


def config_documents(config: AppConfig) -> list[Document]:
    """Approved facts from `config/`, one document per addressable thing."""
    return [
        *_portfolio(config),
        *_services(config),
        *_objections(config),
        *_pages(config),
        *_agency(config),
        *_pricing(config),
    ]


def _portfolio(config: AppConfig) -> list[Document]:
    documents = []
    for case in config.portfolio.cases:
        lines = [
            f"Case study: {case.title}",
            f"Industry: {case.industry}",
            f"Service: {case.service}",
            f"Platforms: {', '.join(case.platforms) or 'n/a'}",
            f"Stacks: {', '.join(case.stacks) or 'n/a'}",
            f"Themes: {', '.join(case.tags) or 'n/a'}",
            f"Outcome: {case.outcome.strip()}",
        ]
        documents.append(
            Document(
                doc_id=f"portfolio:{case.id}",
                title=case.title,
                content="\n".join(lines),
                source="portfolio",
                source_id=case.id,
                metadata={
                    "case_id": case.id,
                    "service": case.service,
                    "industry": case.industry,
                    "platforms": case.platforms,
                    "stacks": case.stacks,
                    "tags": case.tags,
                    "outcome": case.outcome.strip(),
                    "url": case.url,
                },
            )
        )
    return documents


def _services(config: AppConfig) -> list[Document]:
    documents = []
    for key, service in config.services.in_scope.items():
        lines = [
            f"Service: {service.label} ({key})",
            f"Summary: {service.summary}",
            f"Platforms: {', '.join(service.platforms) or 'n/a'}",
            f"Approved stacks: {', '.join(service.stacks) or 'n/a'}",
            f"Approved backend stacks: {', '.join(service.backend_stacks) or 'n/a'}",
        ]
        documents.append(
            Document(
                doc_id=f"services:{key}",
                title=service.label,
                content="\n".join(lines),
                source="services",
                source_id=key,
                metadata={"service": key, "platforms": service.platforms, "stacks": service.stacks},
            )
        )
    labels = [config.services.out_of_scope_labels.get(key, key) for key in config.services.out_of_scope]
    documents.append(
        Document(
            doc_id="services:out_of_scope",
            title="Work we do not take on",
            content="Out of scope: " + "; ".join(labels),
            source="services",
            source_id="out_of_scope",
            metadata={"kinds": config.services.out_of_scope},
        )
    )
    return documents


def _objections(config: AppConfig) -> list[Document]:
    documents = []
    for key, item in config.objections.items.items():
        documents.append(
            Document(
                doc_id=f"objections:{key}",
                title=f"Objection: {key.replace('_', ' ')}",
                content=f"Visitor concern: {', '.join(item.triggers)}\nApproved reply: {item.reply.strip()}",
                source="objections",
                source_id=key,
                metadata={"objection_id": key, "triggers": item.triggers, "reply": item.reply.strip()},
                # Matched on the concern, not the answer. The replies all share the same
                # consulting vocabulary, so including them made the four objections
                # confusable with each other.
                embed_text=f"{key.replace('_', ' ')}. Visitor says: {', '.join(item.triggers)}",
            )
        )
    return documents


def _pages(config: AppConfig) -> list[Document]:
    documents = []
    pages = [("default", config.pages.default), *((page.match, page) for page in config.pages.pages)]
    for key, page in pages:
        lines = [f"Page: {page.match}", f"Service track: {page.service or 'unspecified'}", f"Opening: {page.opening.strip()}"]
        if page.extra_questions:
            lines.append("Follow-up questions: " + "; ".join(page.extra_questions))
        documents.append(
            Document(
                doc_id=f"pages:{key}",
                title=f"Entry point {page.match}",
                content="\n".join(lines),
                source="pages",
                source_id=page.match,
                metadata={"match": page.match, "service": page.service},
            )
        )
    return documents


def _agency(config: AppConfig) -> list[Document]:
    agency = config.agency
    # `never_say` is deliberately not indexed: feeding banned phrases back into the
    # prompt as retrieved context is the fastest way to make the model emit them.
    overview = [
        f"Agency: {agency.name} ({agency.legal_name})",
        f"Tagline: {agency.tagline}",
        f"Tone: {agency.tone}",
        f"Markets: {', '.join(agency.markets)}",
        f"Languages: {', '.join(agency.languages)}",
        f"Website: {agency.website}",
        f"Pricing shown in: {agency.currency_display}",
    ]
    return [
        Document(
            doc_id="agency:overview",
            title=f"About {agency.name}",
            content="\n".join(overview),
            source="agency",
            source_id="overview",
            metadata={},
        ),
        Document(
            doc_id="agency:disclaimer",
            title="Estimate disclaimer",
            content=f"Estimate disclaimer: {agency.disclaimer.strip()}",
            source="agency",
            source_id="disclaimer",
            metadata={},
        ),
        Document(
            doc_id="agency:nda",
            title="Confidentiality",
            content=(
                f"Confidentiality version: {agency.nda.version}\n"
                f"Confidentiality title: {agency.nda.title}\n"
                f"Confidentiality checkbox: {agency.nda.checkbox_label}\n"
                f"Confidentiality terms: {agency.nda.body.strip()}\n"
                f"Required before document upload: {agency.nda.required_before_rfp}\n"
                f"Required before human handoff: {agency.nda.required_before_handoff}"
            ),
            source="agency",
            source_id="nda",
            metadata={},
        ),
        Document(
            doc_id="agency:out_of_scope_close",
            title="Closing an out-of-scope conversation",
            content=f"How to close politely when out of scope: {agency.out_of_scope_close.strip()}",
            source="agency",
            source_id="out_of_scope_close",
            metadata={},
        ),
    ]


def _pricing(config: AppConfig) -> list[Document]:
    """Only the commercial prose. Bases, multipliers, and weights stay server-side."""
    return [
        Document(
            doc_id="pricing:inclusions",
            title="What an engagement includes",
            content="Included in a scoped MVP engagement:\n" + "\n".join(f"- {item}" for item in config.pricing.inclusions),
            source="pricing",
            source_id="inclusions",
            metadata={},
        ),
        Document(
            doc_id="pricing:exclusions",
            title="What an engagement excludes",
            content="Not included in a scoped MVP engagement:\n" + "\n".join(f"- {item}" for item in config.pricing.exclusions),
            source="pricing",
            source_id="exclusions",
            metadata={},
        ),
    ]


def fixture_documents(fixtures_dir: Path) -> list[Document]:
    documents: list[Document] = []
    if not fixtures_dir.exists():
        return documents
    for path in sorted(fixtures_dir.glob("*")):
        if path.suffix.lower() not in {".txt", ".md"} or not path.is_file():
            continue
        body = _tidy(path.read_text(encoding="utf-8", errors="replace"))
        for index, chunk in enumerate(chunk_text(body)):
            documents.append(
                Document(
                    doc_id=f"fixture:{path.stem}#{index}",
                    title=f"Sample document: {path.stem}",
                    content=chunk,
                    source="fixtures",
                    source_id=path.stem,
                    metadata={"filename": path.name, "chunk": index},
                )
            )
    return documents


def website_documents(website_dir: Path) -> list[Document]:
    documents: list[Document] = []
    if not website_dir.exists():
        return documents
    for path in sorted(website_dir.glob("*.html")):
        raw = path.read_text(encoding="utf-8", errors="replace")
        title = _TITLE.search(raw)
        page_title = _tidy(html.unescape(_TAGS.sub(" ", title.group(1)))) if title else path.stem
        body = _strip_html(raw)
        for index, chunk in enumerate(chunk_text(body)):
            documents.append(
                Document(
                    doc_id=f"website:{path.stem}#{index}",
                    title=page_title,
                    content=chunk,
                    source="website",
                    source_id=path.stem,
                    metadata={"page": f"/{path.name}", "chunk": index},
                )
            )
    return documents


def chunk_text(body: str, max_chars: int = MAX_CHUNK_CHARS, overlap: int = CHUNK_OVERLAP_CHARS) -> list[str]:
    """Split on blank lines, packing paragraphs up to ``max_chars``."""
    text = (body or "").strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    current = ""
    for paragraph in re.split(r"\n\s*\n", text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        while len(paragraph) > max_chars:
            chunks.append(paragraph[:max_chars])
            paragraph = paragraph[max_chars - overlap :]
        if not current:
            current = paragraph
        elif len(current) + len(paragraph) + 2 <= max_chars:
            current = f"{current}\n\n{paragraph}"
        else:
            chunks.append(current)
            current = paragraph
    if current:
        chunks.append(current)
    return chunks


def _strip_html(raw: str) -> str:
    without_blocks = _DROP_BLOCKS.sub(" ", raw)
    text = _TAGS.sub("\n", without_blocks)
    return _tidy(html.unescape(text))


def _tidy(text: str) -> str:
    collapsed = _WHITESPACE.sub(" ", (text or "").replace("\r\n", "\n").replace("\r", "\n"))
    lines = [line.strip() for line in collapsed.split("\n")]
    return _BLANK_LINES.sub("\n\n", "\n".join(line for line in lines if line is not None)).strip()

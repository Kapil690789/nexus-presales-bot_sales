from __future__ import annotations

import re
from collections.abc import Callable

_HEADING = re.compile(r"^##\s+(.+)$", re.MULTILINE)
_SENTENCE = re.compile(r"(?<=[.!?])\s+")

EmbedFn = Callable[[list[str]], list[list[float]]]


def chunk_text(
    text: str,
    *,
    chunk_tokens: int = 500,
    overlap_tokens: int = 80,
    break_similarity: float | None = None,
    embed: EmbedFn | None = None,
) -> list[tuple[str, str]]:
    """Return (heading, chunk) pairs.

    Headings are hard breaks. Inside a section, a new chunk starts where
    neighboring sentences stop being about the same thing. ``chunk_tokens`` is
    a maximum word count, not a target size. Oversized pieces still use a
    word window; overlap is in words, which tracks tokens closely.
    """
    body = (text or "").strip()
    if not body:
        return []
    size = max(20, chunk_tokens)
    overlap = max(0, min(overlap_tokens, size // 2))
    chunks: list[tuple[str, str]] = []
    for heading, section in _sections(body):
        chunks.extend(_section_chunks(heading, section, size, overlap, break_similarity, embed))
    return chunks


def _sections(body: str) -> list[tuple[str, str]]:
    parts = _HEADING.split(body)
    sections: list[tuple[str, str]] = []
    if parts[0].strip():
        sections.append(("", parts[0].strip()))
    for index in range(1, len(parts), 2):
        heading = parts[index].strip()
        section = parts[index + 1].strip() if index + 1 < len(parts) else ""
        if section:
            sections.append((heading, section))
    return sections


def _section_chunks(
    heading: str,
    section: str,
    size: int,
    overlap: int,
    break_similarity: float | None,
    embed: EmbedFn | None,
) -> list[tuple[str, str]]:
    sentences = _sentences(section)
    if len(sentences) < 2:
        return _emit_piece(heading, section, size, overlap)
    try:
        vectors = (embed or _default_embed)(sentences)
        if len(vectors) != len(sentences):
            raise ValueError("embedding count did not match sentences")
        threshold = _threshold(break_similarity)
        groups = _semantic_groups(sentences, vectors, threshold)
    except Exception:
        return _pack_sentences(heading, sentences, size, overlap)
    chunks: list[tuple[str, str]] = []
    for group in groups:
        chunks.extend(_emit_piece(heading, " ".join(group), size, overlap))
    return chunks


def _sentences(section: str) -> list[str]:
    return [part.strip() for part in _SENTENCE.split(section) if part.strip()]


def _semantic_groups(
    sentences: list[str],
    vectors: list[list[float]],
    threshold: float,
) -> list[list[str]]:
    from backend.app.rag.embeddings import cosine

    groups: list[list[str]] = [[sentences[0]]]
    for index in range(1, len(sentences)):
        if cosine(vectors[index - 1], vectors[index]) < threshold:
            groups.append([sentences[index]])
        else:
            groups[-1].append(sentences[index])
    return groups


def _pack_sentences(heading: str, sentences: list[str], size: int, overlap: int) -> list[tuple[str, str]]:
    chunks: list[tuple[str, str]] = []
    current: list[str] = []
    count = 0
    for sentence in sentences:
        words = len(sentence.split())
        if words > size:
            if current:
                chunks.extend(_emit_piece(heading, " ".join(current), size, overlap))
                current, count = [], 0
            chunks.extend(_emit_piece(heading, sentence, size, overlap))
            continue
        if current and count + words > size:
            chunks.extend(_emit_piece(heading, " ".join(current), size, overlap))
            current, count = [], 0
        current.append(sentence)
        count += words
    if current:
        chunks.extend(_emit_piece(heading, " ".join(current), size, overlap))
    return chunks


def _emit_piece(heading: str, piece: str, size: int, overlap: int) -> list[tuple[str, str]]:
    words = piece.split()
    if not words:
        return []
    if len(words) <= size:
        return [(heading, _prefixed(heading, " ".join(words)))]
    chunks: list[tuple[str, str]] = []
    start = 0
    while start < len(words):
        end = min(len(words), start + size)
        chunks.append((heading, _prefixed(heading, " ".join(words[start:end]))))
        if end >= len(words):
            break
        start = end - overlap
    return chunks


def _prefixed(heading: str, piece: str) -> str:
    if heading:
        return f"{heading}\n{piece}"
    return piece


def _threshold(break_similarity: float | None) -> float:
    if break_similarity is not None:
        return break_similarity
    from backend.app.core.platform import get_platform

    return get_platform().semantic_break_similarity


def _default_embed(texts: list[str]) -> list[list[float]]:
    from backend.app.rag.embeddings import embed_texts

    return embed_texts(texts).vectors

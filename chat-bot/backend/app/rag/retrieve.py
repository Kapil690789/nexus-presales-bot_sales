from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.agents.brief import ProjectBrief, brief_query, brief_tags
from backend.app.config_loader.models import RagConfig
from backend.app.core.settings import get_settings
from backend.app.rag.embeddings import FALLBACK_MODEL, active_model
from backend.app.rag.store import Hit, get_store

SERVICE_BOOST = 0.15
PLATFORM_BOOST = 0.08
TAG_BOOST = 0.06


def rag_enabled() -> bool:
    return get_settings().rag_enabled


def retrieve_knowledge(
    db: Session | None,
    query: str,
    brief: ProjectBrief | None,
    rag: RagConfig,
    *,
    k: int | None = None,
    sources: list[str] | None = None,
    nda_accepted: bool = False,
) -> list[Hit]:
    """Approved facts most relevant to the current message and brief."""
    limit = k or rag.top_k
    text = " ".join(part for part in [query or "", brief_query(brief) if brief else ""] if part).strip()
    return _search(
        db, text, rag, kind="knowledge", k=limit, brief=brief, sources=sources, nda_accepted=nda_accepted
    )


def retrieve_solution(
    db: Session | None,
    brief: ProjectBrief | None,
    rag: RagConfig,
    *,
    query: str = "",
    k: int | None = None,
    nda_accepted: bool = False,
) -> list[Hit]:
    """Capability, process, and estimation material for a tailored recommendation."""
    limit = k or max(6, rag.top_k)
    text = " ".join(
        part
        for part in [brief_query(brief) if brief else "", "architecture MVP estimation stack", query or ""]
        if part
    ).strip()
    return _search(db, text, rag, kind="knowledge", k=limit, brief=brief, nda_accepted=nda_accepted)


def retrieve_lessons(
    db: Session | None,
    brief: ProjectBrief | None,
    stage: str,
    rag: RagConfig,
    *,
    k: int | None = None,
) -> list[Hit]:
    """Distilled guidance from past conversations that converted."""
    limit = k or rag.lesson_k
    text = " ".join(part for part in [brief_query(brief) if brief else "", stage or ""] if part).strip()
    return _search(db, text, rag, kind="lesson", k=limit, brief=brief)


def semantic_case_scores(db: Session | None, brief: ProjectBrief, rag: RagConfig, *, k: int = 12) -> dict[str, float]:
    """Raw similarity between the brief and each indexed case study, keyed by case id.

    Searches the narrative case studies in `content/` as well as the portfolio cards,
    which is what the `case_id` front matter field is for: a long write-up and its card
    score as one case. Best-matching chunk wins, so a case is not rewarded for length.

    Unboosted on purpose: the caller already scores metadata agreement itself, and
    counting it twice would drown out the semantic signal this is meant to add.
    """
    if db is None or not rag_enabled():
        return {}
    query = brief_query(brief)
    if not query:
        return {}
    try:
        hits = get_store().search(db, query, k=k, kind="knowledge", sources=["portfolio", "content"])
    except Exception:
        return {}
    scores: dict[str, float] = {}
    for hit in hits:
        case_id = (hit.metadata or {}).get("case_id") or hit.source_id
        if case_id:
            key = str(case_id)
            scores[key] = max(scores.get(key, 0.0), hit.score)
    return scores


def objection_hit(db: Session | None, text: str, rag: RagConfig) -> Hit | None:
    """Closest approved objection, or None when nothing is close enough.

    Scored on raw similarity with no brief boost: whether this is a known objection
    must not depend on what the visitor happens to be building.
    """
    if not text or not text.strip() or db is None or not rag_enabled():
        return None
    try:
        hits = get_store().search(db, text, k=1, kind="knowledge", sources=["objections"])
    except Exception:
        return None
    if not hits or hits[0].score < objection_floor(rag):
        return None
    return hits[0]


def objection_floor(rag: RagConfig) -> float:
    """Cosine values are not comparable across embedders, so the floor follows the model."""
    return rag.objection_min_score_local if active_model()[0] == FALLBACK_MODEL else rag.objection_min_score


def _search(
    db: Session | None,
    text: str,
    rag: RagConfig,
    *,
    kind: str,
    k: int,
    brief: ProjectBrief | None,
    sources: list[str] | None = None,
    nda_accepted: bool = False,
) -> list[Hit]:
    if db is None or not text or k <= 0 or not rag_enabled():
        return []
    try:
        # Over-fetch, then re-rank: metadata agreement often matters more than raw
        # cosine, especially under the local hashing embedder. The pool also has to
        # absorb whatever the NDA and per-document filters discard.
        candidates = get_store().search(db, text, k=max(k * 5, k + 8), kind=kind, sources=sources)
    except Exception:
        return []
    tags = brief_tags(brief) if brief else set()
    ranked = sorted(
        ((hit.score + _boost(hit, brief, tags), hit) for hit in candidates),
        key=lambda pair: pair[0],
        reverse=True,
    )
    hits: list[Hit] = []
    per_doc: dict[str, int] = {}
    cap = max(1, rag.max_chunks_per_doc)
    for score, hit in ranked:
        if score < rag.min_score:
            continue
        metadata = hit.metadata or {}
        if metadata.get("nda_only") and not nda_accepted:
            continue
        # Several chunks of one long document would otherwise crowd out the corpus.
        key = hit.source_id or hit.doc_id
        if per_doc.get(key, 0) >= cap:
            continue
        per_doc[key] = per_doc.get(key, 0) + 1
        hit.score = round(score, 4)
        hits.append(hit)
        if len(hits) >= k:
            break
    return hits


def _boost(hit: Hit, brief: ProjectBrief | None, tags: set[str]) -> float:
    if brief is None:
        return 0.0
    metadata = hit.metadata or {}
    boost = 0.0
    if brief.service and metadata.get("service") == brief.service:
        boost += SERVICE_BOOST
    platforms = {item.lower() for item in brief.platforms}
    if platforms and platforms.intersection({str(item).lower() for item in metadata.get("platforms") or []}):
        boost += PLATFORM_BOOST
    hit_tags = {str(item).lower() for item in metadata.get("tags") or []}
    if metadata.get("industry"):
        hit_tags.add(str(metadata["industry"]).lower())
    boost += TAG_BOOST * len(tags.intersection(hit_tags))
    return boost


def render_snippets(hits: list[Hit], max_chars: int) -> str:
    if not hits:
        return "(none)"
    lines = []
    for index, hit in enumerate(hits, start=1):
        body = hit.content.strip()
        if len(body) > max_chars:
            body = body[:max_chars].rstrip() + "…"
        lines.append(f"[{index}] {hit.title or hit.doc_id} (source: {hit.source})\n{body}")
    return "\n\n".join(lines)

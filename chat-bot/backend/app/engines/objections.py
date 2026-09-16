from backend.app.config_loader.models import ObjectionsConfig, RagConfig
from backend.app.rag.retrieve import objection_hit


def match_objection(
    text: str,
    objections: ObjectionsConfig,
    *,
    db=None,
    rag: RagConfig | None = None,
) -> dict | None:
    """Find the approved reply for a visitor concern.

    Trigger phrases win outright. When none hit, a semantic lookup catches concerns
    phrased in words nobody thought to list in `objections.yaml`. Either way the
    reply text comes from config, never from the index.
    """
    haystack = (text or "").lower()
    if not haystack:
        return None
    for key, item in objections.items.items():
        for trigger in item.triggers:
            if trigger.lower() in haystack:
                return {"id": key, "reply": item.reply.strip(), "match": "trigger"}
    if db is None or rag is None:
        return None
    hit = objection_hit(db, text, rag)
    if not hit:
        return None
    key = str((hit.metadata or {}).get("objection_id") or hit.source_id)
    item = objections.items.get(key)
    if not item:
        return None
    return {"id": key, "reply": item.reply.strip(), "match": "semantic", "score": hit.score}

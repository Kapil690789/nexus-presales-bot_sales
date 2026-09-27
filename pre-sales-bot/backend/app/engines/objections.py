from __future__ import annotations

from backend.app.tenants.schema import ObjectionsConfig


def match_objection(text: str, objections: ObjectionsConfig) -> dict | None:
    haystack = (text or "").lower()
    if not haystack:
        return None
    for key, item in objections.items.items():
        for trigger in item.triggers:
            if trigger.lower() in haystack:
                return {"id": key, "reply": " ".join(item.reply.split()), "match": "trigger"}
    return None

from backend.app.agents.brief import ProjectBrief
from backend.app.config_loader.models import ServicesConfig


def recommend_architecture(brief: ProjectBrief, services: ServicesConfig) -> dict:
    if not brief.service or brief.service not in services.in_scope:
        return {"service": None, "frontend": [], "backend": [], "notes": ["Confirm the product type before we lock an architecture."]}
    service = services.in_scope[brief.service]
    notes: list[str] = []
    frontend = list(service.stacks[:2])
    backend = list(service.backend_stacks[:2])
    platforms = {p.lower() for p in brief.platforms}
    haystack = " ".join([brief.industry or "", brief.goal or ""] + list(brief.constraints)).lower()
    if brief.service == "mobile_app":
        if platforms >= {"ios", "android"} or "both" in brief.platforms:
            frontend = ["Flutter"] if "Flutter" in service.stacks else service.stacks[:1]
            notes.append("Two platforms: a shared codebase keeps the first release honest.")
            if brief.budget_band in {"under_15k", "exploring"}:
                notes.append("A tight budget usually means one platform in v1 — the other waits.")
        elif "ios" in platforms:
            frontend = ["Swift + Kotlin"] if "Swift + Kotlin" in service.stacks else ["Flutter"]
            notes.append("Single platform first — we can add Android in phase two.")
        backend = ["Node.js + PostgreSQL"] if brief.integrations else (["Firebase"] if "Firebase" in service.backend_stacks else service.backend_stacks[:1])
    elif brief.service == "web_app":
        frontend = ["Next.js"] if "Next.js" in service.stacks else service.stacks[:1]
        backend = ["Node.js + PostgreSQL"] if brief.admin or brief.auth else service.backend_stacks[:1]
        if brief.admin:
            notes.append("An admin console should be a first-class module, not an afterthought.")
    elif brief.service == "ai_product":
        frontend = ["Next.js"] if "Next.js" in service.stacks else service.stacks[:1]
        backend = list(service.backend_stacks[:2]) or ["Python + FastAPI"]
        notes.append("Keep retrieval and tool-calling server-side; do not embed keys in the client.")
    elif brief.service == "ui_ux":
        frontend, backend = ["Figma"] if "Figma" in service.stacks else service.stacks[:1], []
        notes.append("We stop at a build-ready prototype unless you also want engineering.")
    elif brief.service == "staff_augmentation":
        notes.append("We match people to your current stack rather than imposing ours.")
    if brief.auth:
        notes.append("Plan for auth, roles, and a password-reset path in the MVP.")
    if brief.realtime:
        notes.append("Realtime features belong behind a managed pub/sub, not polling hacks.")
    if brief.industry == "health" or "hipaa" in haystack:
        notes.append("Treat privacy and access control as MVP constraints, not a later hardening pass.")
    if brief.marketplace:
        notes.append("Two-sided flows need a shared core, not two unrelated apps.")
    if brief.constraints:
        notes.append(f"Honor this constraint in v1: {brief.constraints[0][:120]}")
    return {
        "service": brief.service,
        "label": service.label,
        "frontend": frontend,
        "backend": backend,
        "notes": notes or [service.summary],
    }

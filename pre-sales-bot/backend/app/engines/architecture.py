from __future__ import annotations

from backend.app.agents.brief import ProjectBrief
from backend.app.tenants.schema import ServicesConfig


def recommend_architecture(brief: ProjectBrief, services: ServicesConfig) -> dict:
    if not brief.service or brief.service not in services.in_scope:
        return {"service": None, "frontend": [], "backend": [], "notes": ["Confirm the product type before we lock an architecture."]}
    service = services.in_scope[brief.service]
    notes: list[str] = []
    frontend = list(service.stacks[:2])
    backend = list(service.backend_stacks[:2])
    platforms = {item.lower() for item in brief.platforms}
    if brief.service == "mobile_app":
        if platforms >= {"ios", "android"}:
            frontend = ["Flutter"] if "Flutter" in service.stacks else frontend
            notes.append("Two platforms: a shared codebase keeps the first release honest.")
        backend = ["Node.js + PostgreSQL"] if brief.integrations else backend
    elif brief.service == "web_app":
        frontend = ["Next.js"] if "Next.js" in service.stacks else frontend
        if brief.admin:
            notes.append("An admin console should be a first-class module, not an afterthought.")
    elif brief.service == "ai_product":
        notes.append("Keep retrieval server-side; do not embed keys in the client.")
    elif brief.service == "ui_ux":
        frontend, backend = (["Figma"] if "Figma" in service.stacks else frontend), []
        notes.append("We stop at a build-ready prototype unless you also want engineering.")
    if brief.auth:
        notes.append("Plan for auth, roles, and a password-reset path in the MVP.")
    return {
        "service": brief.service,
        "label": service.label,
        "frontend": frontend,
        "backend": backend,
        "notes": notes or [service.summary],
    }

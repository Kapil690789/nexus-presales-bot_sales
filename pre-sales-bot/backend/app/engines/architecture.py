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

    from backend.app.engines.domains import detect_domain, get_domain_blueprint

    domain_id = detect_domain(brief=brief)
    bp = get_domain_blueprint(domain_id) if domain_id else None

    if bp and brief.service != "ui_ux":
        if bp.frontend_recommendations:
            has_mobile = bool(platforms & {"ios", "android", "mobile"})
            has_web = "web" in platforms

            if has_mobile and not has_web:
                mobile_recs = [r for r in bp.frontend_recommendations if any(k in r.lower() for k in ("flutter", "react native", "mobile", "app", "ble"))]
                frontend = mobile_recs[:2] if mobile_recs else bp.frontend_recommendations[:1]
            elif has_web and not has_mobile:
                web_recs = [r for r in bp.frontend_recommendations if any(k in r.lower() for k in ("next.js", "web", "portal", "dashboard", "storefront"))]
                frontend = web_recs[:2] if web_recs else bp.frontend_recommendations[:1]
            else:
                frontend = bp.frontend_recommendations[:2]

        if bp.backend_recommendations:
            backend = list(bp.backend_recommendations[:2])
    else:
        if brief.service == "mobile_app":
            if platforms >= {"ios", "android"}:
                frontend = ["Flutter"] if "Flutter" in service.stacks else frontend
                notes.append("Two platforms: a shared codebase keeps the first release honest.")
            backend = ["Node.js + PostgreSQL"] if brief.integrations else backend
        elif brief.service == "web_app":
            frontend = ["Next.js"] if "Next.js" in service.stacks else frontend
            if brief.admin:
                notes.append("An admin console should be a first-class module, not an afterthought.")

    if brief.service == "ai_product":
        notes.append("Keep retrieval server-side; do not embed keys in the client.")
    elif brief.service == "ui_ux":
        frontend, backend = (["Figma"] if "Figma" in service.stacks else frontend), []
        notes.append("We stop at a build-ready prototype unless you also want engineering.")

    if brief.auth and "Plan for auth, roles, and a password-reset path in the MVP." not in notes:
        notes.append("Plan for auth, roles, and a password-reset path in the MVP.")

    if brief.integrations:
        int_names = ", ".join(brief.integrations[:2])
        int_note = f"Design resilient webhook and async ingestion pipelines for {int_names}."
        if not any(int_names in n for n in notes):
            notes.append(int_note)

    if bp:
        for arch_note in bp.architecture_notes:
            if arch_note not in notes:
                notes.append(arch_note)

    return {
        "service": brief.service,
        "label": service.label,
        "frontend": frontend,
        "backend": backend,
        "notes": notes or [service.summary],
    }

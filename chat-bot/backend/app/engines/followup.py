from __future__ import annotations


def render_followup(
    *,
    email: str,
    intro: str,
    estimate: dict | None,
    portfolio: list[dict] | None,
    booking: dict | None,
    agency: str,
) -> dict:
    cases = portfolio or []
    case_lines = [f"- {item.get('title')}: {item.get('outcome')}" for item in cases[:2]]
    range_label = (estimate or {}).get("range_label") or "an indicative range after a strategist review"
    meeting = ""
    if booking and booking.get("label"):
        meeting = f"Consultation: {booking.get('label')} — {booking.get('meet_url')}"
    body = "\n".join(
        [
            intro.strip(),
            "",
            f"Indicative MVP range: {range_label}",
            "",
            "Relevant work:",
            *(case_lines or ["- We'll match case studies on the consultation."]),
            "",
            meeting or "Next step: a strategist will send live times if a slot was not picked.",
            "",
            f"— {agency} (dummy email — not actually sent)",
        ]
    )
    return {
        "to": email,
        "subject": "Your DevConsult discovery notes",
        "body": body,
        "preview": f"Recap queued to {email}" if email else "Recap queued",
    }

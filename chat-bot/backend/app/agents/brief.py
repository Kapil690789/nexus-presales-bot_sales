from typing import Any

from pydantic import BaseModel, Field

DISCOVERY_FIELDS = (
    "service",
    "goal",
    "platforms",
    "users",
    "integrations",
    "timeline",
    "budget_band",
    "decision_role",
)


class ProjectBrief(BaseModel):
    service: str | None = None
    goal: str | None = None
    users: str | None = None
    platforms: list[str] = Field(default_factory=list)
    integrations: list[str] = Field(default_factory=list)
    auth: bool | None = None
    admin: bool | None = None
    realtime: bool | None = None
    marketplace: bool | None = None
    ai_features: list[str] = Field(default_factory=list)
    timeline: str | None = None
    budget_band: str | None = None
    decision_role: str | None = None
    industry: str | None = None
    constraints: list[str] = Field(default_factory=list)
    company_size: str | None = None
    out_of_scope: str | None = None

    def apply_chip(self, field: str, value: Any) -> None:
        if not field or field in {"show_portfolio", "show_mvp", "continue_contact", "booking_window", "booking_slot", "nda", "download_ics"}:
            return
        if field in {"platforms", "integrations", "ai_features", "constraints"}:
            items = value if isinstance(value, list) else [value]
            current = list(getattr(self, field) or [])
            for item in items:
                text = str(item).strip()
                if text and text not in current:
                    current.append(text)
            setattr(self, field, current)
            return
        if field in {"auth", "admin", "realtime", "marketplace"}:
            setattr(self, field, value if isinstance(value, bool) else str(value).lower() in {"true", "yes", "1"})
            return
        if value in (None, "") or field not in self.model_fields:
            return
        setattr(self, field, value if not isinstance(value, list) else (value[0] if value else None))

    def missing_discovery(self) -> list[str]:
        return [field for field in DISCOVERY_FIELDS if getattr(self, field) in (None, "", [])]

    def completeness(self) -> float:
        return (len(DISCOVERY_FIELDS) - len(self.missing_discovery())) / len(DISCOVERY_FIELDS)


def brief_ready(brief: ProjectBrief) -> bool:
    required = ("service", "goal", "platforms", "timeline", "budget_band", "decision_role")
    return all(getattr(brief, name) not in (None, "", []) for name in required)

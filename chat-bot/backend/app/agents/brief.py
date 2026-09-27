from typing import Any

from pydantic import BaseModel, Field

DISCOVERY_FIELDS = (
    "service",
    "goal",
    "features",
    "platforms",
    "users",
    "integrations",
    "timeline",
    "budget_band",
    "decision_role",
)
# Engines will not estimate until these are present. Discovery may collect more.
ENGINE_FIELDS = (
    "service",
    "goal",
    "platforms",
    "timeline",
    "budget_band",
    "decision_role",
)
FLOW_SKIPPED = "not_specified"
FEATURE_SKIP_TOKENS = {"skipped", "__skip__", "not_sure", "unspecified"}


def is_features_skip(value: Any) -> bool:
    if value == []:
        return True
    if isinstance(value, str) and value.strip().lower() in FEATURE_SKIP_TOKENS:
        return True
    if isinstance(value, list) and len(value) == 1:
        return is_features_skip(value[0])
    return False


class ProjectBrief(BaseModel):
    service: str | None = None
    goal: str | None = None
    users: str | None = None
    platforms: list[str] = Field(default_factory=list)
    integrations: list[str] = Field(default_factory=list)
    features: list[str] | None = None
    user_flow: str | None = None
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
        if not field or field in {"show_portfolio", "show_mvp", "continue_contact", "booking_window", "booking_slot", "nda", "download_ics", "close_out"}:
            return
        if field == "features":
            if is_features_skip(value):
                if self.features is None:
                    self.features = []
                return
            items = value if isinstance(value, list) else [value]
            current = list(self.features or [])
            for item in items:
                text = str(item).strip()
                if text and text not in current and not is_features_skip(text):
                    current.append(text)
            self.features = current
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
        missing: list[str] = []
        for field in DISCOVERY_FIELDS:
            value = getattr(self, field)
            if field == "features":
                if value is None:
                    missing.append(field)
                continue
            if value in (None, "", []):
                missing.append(field)
        return missing

    def completeness(self) -> float:
        return (len(DISCOVERY_FIELDS) - len(self.missing_discovery())) / len(DISCOVERY_FIELDS)


def skip_optional_flow(style: dict | None) -> bool:
    style = style or {}
    return style.get("pace") == "terse" or style.get("mood") in {"impatient", "skeptical"}


def next_discovery_field(brief: ProjectBrief, style: dict | None = None) -> str | None:
    """Highest-leverage remaining ask. Features first after goal; flow is optional."""
    missing = brief.missing_discovery()
    head = missing[0] if missing else None
    if (
        brief.goal
        and brief.features is not None
        and brief.user_flow is None
        and not skip_optional_flow(style)
        and head not in {"service", "goal", "features"}
    ):
        return "user_flow"
    if missing:
        return missing[0]
    if not brief.company_size:
        return "company_size"
    return None


def engine_gaps(brief: ProjectBrief) -> list[str]:
    return [name for name in ENGINE_FIELDS if getattr(brief, name) in (None, "", [])]


def brief_ready(brief: ProjectBrief) -> bool:
    return not engine_gaps(brief)


GOAL_TAG_WORDS = ("marketplace", "saas", "health", "fintech", "onboarding")


def brief_tags(brief: ProjectBrief) -> set[str]:
    """Themes implied by the brief, used to match case studies and retrieved chunks."""
    tags: set[str] = set()
    if brief.industry:
        tags.add(brief.industry.lower())
    if brief.marketplace:
        tags.add("marketplace")
    if brief.ai_features or brief.service == "ai_product":
        tags.add("ai")
    goal = (brief.goal or "").lower()
    for word in GOAL_TAG_WORDS:
        if word in goal:
            tags.add(word)
    return tags


def brief_query(brief: ProjectBrief) -> str:
    """Flatten the brief into text worth embedding as a retrieval query."""
    parts = [brief.goal or "", brief.service or "", brief.industry or "", brief.users or "", brief.user_flow or ""]
    parts += brief.platforms + brief.integrations + brief.ai_features + brief.constraints + list(brief.features or [])
    parts += sorted(brief_tags(brief))
    return " ".join(part for part in parts if part and part != FLOW_SKIPPED).strip()

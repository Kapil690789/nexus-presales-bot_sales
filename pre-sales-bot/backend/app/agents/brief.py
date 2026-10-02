from __future__ import annotations

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
    features_confirmed: bool = False
    feature_detail: str | None = None
    user_flow: str | None = None
    auth: bool | None = None
    admin: bool | None = None
    realtime: bool | None = None
    marketplace: bool | None = None
    ai_features: list[str] = Field(default_factory=list)
    timeline: str | None = None
    budget_band: str | None = None
    decision_role: str | None = None
    role_unconfirmed: bool = False
    industry: str | None = None
    constraints: list[str] = Field(default_factory=list)
    company_size: str | None = None
    out_of_scope: str | None = None
    field_attempts: dict[str, int] = Field(default_factory=dict)

    def apply_chip(self, field: str, value: Any) -> None:
        if not field or field in {
            "show_portfolio",
            "continue_contact",
            "booking_window",
            "booking_slot",
            "nda",
            "close_out",
        }:
            return
        if field == "confirm_role":
            self.role_unconfirmed = False
            if value in ("study_or_practice", "intern_or_student"):
                self.decision_role = "intern_or_student"
            else:
                self.decision_role = "founder_or_exec"
            return
        if value in ("not_sure", "not_specified", "skipped") and field in {
            "timeline", "budget_band", "decision_role", "company_size", "users", "platforms"
        }:
            defaults = {
                "timeline": "flexible",
                "budget_band": "exploring",
                "decision_role": "founder_or_exec",
                "company_size": "startup",
                "users": "business",
                "platforms": ["web"],
            }
            if field in defaults and not getattr(self, field):
                setattr(self, field, defaults[field])
            return
        if field == "features_done":
            self.features_confirmed = True
            if self.features is None:
                self.features = []
            return
        if field == "features":
            if is_features_skip(value):
                self.features = []
                self.features_confirmed = True
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
                if not self.features_confirmed:
                    missing.append(field)
                continue
            if value in (None, "", []):
                missing.append(field)
        return missing

    def completeness(self) -> float:
        return (len(DISCOVERY_FIELDS) - len(self.missing_discovery())) / len(DISCOVERY_FIELDS)


def named_features(brief: ProjectBrief) -> list[str]:
    return [item.strip() for item in (brief.features or []) if item and str(item).strip()]


def needs_feature_detail(brief: ProjectBrief) -> bool:
    """Short labels need one explanation. A sentence, or no features, does not."""
    if not brief.features_confirmed or brief.feature_detail is not None:
        return False
    named = named_features(brief)
    if not named:
        return False
    return all(len(item.split()) < 8 for item in named)


def next_discovery_field(brief: ProjectBrief) -> str | None:
    missing = brief.missing_discovery()
    head = missing[0] if missing else None
    if head in {"service", "goal"}:
        return head
    if brief.goal and not brief.features_confirmed:
        return "features"
    if needs_feature_detail(brief):
        return "feature_detail"
    if (
        brief.goal
        and brief.features_confirmed
        and brief.user_flow is None
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

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
    budget_text: str | None = None
    decision_role: str | None = None
    role_unconfirmed: bool = False
    industry: str | None = None
    constraints: list[str] = Field(default_factory=list)
    company_size: str | None = None
    out_of_scope: str | None = None
    field_attempts: dict[str, int] = Field(default_factory=dict)
    recent_acks: list[str] = Field(default_factory=list)
    shape_shown: bool = False
    platform_service_clarified: bool = False
    service_source: str = "guess"  # "chip", "explicit", "guess"

    def apply_chip(self, field: str, value: Any) -> None:
        if not field or field in {
            "show_portfolio",
            "continue_contact",
            "booking_window",
            "booking_slot",
            "nda",
            "close_out",
            "view_mvp",
            "email_instead",
            "continue_discovery",
            "sharpen_estimate",
        }:
            return
        # Feature detail chip: "Standard functionality is fine" or "Skip detail & continue →"
        if field == "feature_detail":
            if value in ("not_specified", "not_sure", "skipped", "standard") or str(value).startswith("not_"):
                self.feature_detail = "not_specified"
            else:
                self.feature_detail = str(value).strip() if value else "not_specified"
            # Mark as fully attempted so needs_feature_detail() won't re-trigger
            self.field_attempts["feature_detail"] = 99
            return
        # User flow chip: "Standard flow is fine" or "Skip for now"
        if field == "user_flow":
            self.user_flow = "not_specified"
            self.field_attempts["user_flow"] = 99
            return

        if field == "confirm_role":
            self.role_unconfirmed = False
            if value in ("study_or_practice", "intern_or_student"):
                self.decision_role = "intern_or_student"
            else:
                self.decision_role = None
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
            features_text = " ".join(current).lower()
            if self.auth is None and any(w in features_text for w in ("auth", "login", "user account", "sign in", "signup", "sso")):
                self.auth = True
            if self.admin is None and any(w in features_text for w in ("admin", "dashboard", "backoffice", "analytics portal")):
                self.admin = True
            if self.realtime is None and any(w in features_text for w in ("realtime", "real-time", "live tracking", "websockets")):
                self.realtime = True
            if self.marketplace is None and any(w in features_text for w in ("marketplace", "multi-vendor", "vendor portal")):
                self.marketplace = True
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
        val_to_set = value if not isinstance(value, list) else (value[0] if value else None)
        if field == "goal" and isinstance(val_to_set, str):
            val_to_set = val_to_set.replace("_", " ").strip()
        setattr(self, field, val_to_set)
        if field == "service":
            self.service_source = "chip"
            if self.service == "mobile_app" and self.platforms == ["web"]:
                self.platforms = ["ios", "android"]
            elif self.service == "web_app" and self.platforms and all(p in ("ios", "android") for p in self.platforms):
                self.platforms = ["web"]

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
    """Short labels need one explanation. A sentence, or no features, does not.
    ai_product features (AI chat, Document processing) are self-explanatory — skip detail.
    ui_ux deliverables are also self-explanatory — skip detail."""
    if not brief.features_confirmed or brief.feature_detail is not None:
        return False
    # AI product features are industry-standard terms; no detail question needed
    if brief.service == "ai_product":
        return False
    # Skip for ui_ux — deliverables are self-explanatory
    if brief.service == "ui_ux":
        return False
    named = named_features(brief)
    if not named:
        return False
    # Commodity single-features like login / accounts are self-explanatory — skip detail
    if len(named) == 1 and named[0].lower().strip() in {
        "user authentication", "user accounts", "user login & profiles", "login & accounts",
    }:
        return False
    # If all feature names are longer than 3 words, they're already descriptive enough
    if all(len(item.split()) > 3 for item in named):
        return False
    return all(len(item.split()) < 8 for item in named)



FAST_FLOW_FIELDS = (
    "service",
    "goal",
    "platforms",
    "timeline",
    "budget_band",
)
SHARPEN_FIELDS = (
    "features",
    "integrations",
    "users",
    "decision_role",
    "company_size",
)


def fast_engine_gaps(brief: ProjectBrief) -> list[str]:
    gaps = []
    if not brief.service:
        gaps.append("service")
    if not brief.goal:
        gaps.append("goal")
    # ai_product integrates into an existing product — platform is not required
    if not brief.platforms and brief.service not in ("ui_ux", "ai_product"):
        gaps.append("platforms")
    if not brief.timeline:
        gaps.append("timeline")
    if not brief.budget_band:
        gaps.append("budget_band")
    return gaps


def next_sharpen_field(brief: ProjectBrief) -> str | None:
    if not brief.features_confirmed:
        return "features"
    if needs_feature_detail(brief):
        return "feature_detail"
    if not brief.integrations or brief.integrations == ["none"]:
        return "integrations"
    if not brief.users:
        return "users"
    if not brief.decision_role:
        return "decision_role"
    if not brief.company_size:
        return "company_size"
    return None


def next_discovery_field(brief: ProjectBrief, flow: str = "classic") -> str | None:
    if flow == "fast":
        gaps = fast_engine_gaps(brief)
        # Order: service, goal, platforms (unless ui_ux), timeline, budget_band
        # Never ask budget before goal and platforms
        return gaps[0] if gaps else None

    missing = brief.missing_discovery()
    head = missing[0] if missing else None
    if head == "service" and brief.goal and brief.field_attempts.get("service", 0) >= 1:
        if not brief.platforms:
            return "platforms"
        if not brief.features_confirmed:
            return "features"
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
        and brief.service != "ai_product"
        and head not in {"service", "goal", "features"}
    ):
        named = named_features(brief)
        is_commodity_single = bool(
            len(named) == 1 and named[0].lower().strip() in {
                "user authentication", "user accounts", "user login & profiles", "login & accounts",
            }
        )
        if (
            brief.feature_detail == "not_specified"
            or (brief.feature_detail and "standard" in brief.feature_detail.lower())
            or is_commodity_single
        ):
            brief.user_flow = "not_specified"
            if is_commodity_single and brief.feature_detail is None:
                brief.feature_detail = "not_specified"
        else:
            return "user_flow"
    if missing:
        # Never ask budget before goal and platforms
        if missing[0] == "budget_band" and (not brief.goal or (not brief.platforms and brief.service != "ui_ux")):
            if not brief.goal:
                return "goal"
            if not brief.platforms and brief.service != "ui_ux":
                return "platforms"
        return missing[0]
    return None


def engine_gaps(brief: ProjectBrief) -> list[str]:
    return [name for name in ENGINE_FIELDS if getattr(brief, name) in (None, "", [])]


def brief_ready(brief: ProjectBrief, flow: str = "classic") -> bool:
    if flow == "fast":
        return not fast_engine_gaps(brief)
    return not engine_gaps(brief)

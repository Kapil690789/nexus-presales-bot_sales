from __future__ import annotations

import re
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Starter(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str = Field(..., max_length=32)
    text: str = Field(..., max_length=120)


class PageHint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    match: str
    service: str = ""
    question: str = ""

    @field_validator("match")
    @classmethod
    def validate_match(cls, v: str) -> str:
        if not v or not v.startswith("/"):
            raise ValueError("PageHint match must start with '/'")
        return v

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        if v and len(v.split()) > 25:
            raise ValueError(f"PageHint question must be at most 25 words (got {len(v.split())})")
        return v


def _default_starters() -> list[Starter]:
    return [
        Starter(label="I have an app idea", text="I have an app idea"),
        Starter(label="I need a web platform", text="I need a web platform"),
        Starter(label="Add AI to my product", text="I want to add AI to my product"),
        Starter(label="Just exploring costs", text="I'm just exploring costs"),
    ]


class BrandConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = "Advisor"
    slug: str = "demo"
    logo_text: str = "Advisor"
    primary: str = "#1A2B4C"
    accent: str = "#1A2B4C"
    background: str = "#FFFFFF"
    surface: str = "#FFFFFF"
    text: str = "#1A2B4C"
    muted: str = "#5C6670"
    radius_px: int = 16
    launcher_text: str = "Talk to an advisor"
    launcher_subtitle: str = "Scope, estimate, and next steps"
    widget_title: str = "Advisor"
    widget_subtitle: str = "Online"
    placeholder: str = "Type your message..."
    position: str = "bottom-right"
    disclaimer: str = "Indicative range only, not a fixed quote."
    nda_text: str = "Some project stories are confidential."
    nda_version: str = "2026-01"
    currency: str = "USD"
    timezone: str = "Asia/Kolkata"

    # E1 fields
    advisor_name: str = "Alex"
    advisor_title: str = "AI project advisor"
    advisor_avatar: str = ""
    human_label: str = "Talk to a human"
    starters: list[Starter] = Field(default_factory=_default_starters)
    opening_variants: list[str] = Field(default_factory=list)
    page_hints: list[PageHint] = Field(default_factory=list)
    booking_handoff_text: str = "The team will see this whole conversation, so you won't need to repeat anything."

    @field_validator("advisor_name")
    @classmethod
    def validate_advisor_name(cls, v: str) -> str:
        v = (v or "").strip()
        if not (1 <= len(v) <= 30) or not re.match(r"^[a-zA-Z\s\-'.]+$", v):
            raise ValueError("advisor_name must be 1-30 characters (letters, spaces, hyphen, apostrophe, period)")
        return v

    @field_validator("advisor_title")
    @classmethod
    def validate_advisor_title(cls, v: str) -> str:
        v = (v or "").strip()
        if not re.search(r"\bAI\b", v):
            raise ValueError("advisor_title must contain the standalone word 'AI'")
        return v

    @field_validator("advisor_avatar")
    @classmethod
    def validate_advisor_avatar(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            return ""
        if not v.startswith("https://") or len(v) > 300:
            raise ValueError("advisor_avatar must be empty or an https:// URL up to 300 characters")
        return v

    @field_validator("human_label")
    @classmethod
    def validate_human_label(cls, v: str) -> str:
        v = (v or "").strip()
        if not (1 <= len(v) <= 32):
            raise ValueError("human_label must be 1-32 characters")
        return v

    @field_validator("starters")
    @classmethod
    def validate_starters(cls, v: list[Starter]) -> list[Starter]:
        if len(v) > 5:
            raise ValueError(f"starters must contain at most 5 items (got {len(v)})")
        return v

    @field_validator("opening_variants")
    @classmethod
    def validate_opening_variants(cls, v: list[str]) -> list[str]:
        for item in v:
            words = item.split()
            if len(words) > 25:
                raise ValueError(f"opening_variant must be up to 25 words (got {len(words)})")
            low = item.lower()
            if any(sym in low for sym in ["$", "€", "eur", "₹", "rupee", "%"]):
                raise ValueError("opening_variant must not contain $, EUR, rupee or percent signs")
            emoji_count = len(re.findall(r"[\U00010000-\U0010ffff]", item))
            if emoji_count > 1:
                raise ValueError("opening_variant must contain at most one emoji")
        return v


class FaqItem(BaseModel):
    id: str
    question: str
    answer: str
    topic: str = ""
    tags: list[str] = Field(default_factory=list)


class ServiceItem(BaseModel):
    label: str
    summary: str = ""
    platforms: list[str] = Field(default_factory=list)
    stacks: list[str] = Field(default_factory=list)
    backend_stacks: list[str] = Field(default_factory=list)


class ServicesConfig(BaseModel):
    in_scope: dict[str, ServiceItem] = Field(default_factory=dict)
    out_of_scope: list[str] = Field(default_factory=list)


class PricingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    currency: str = "USD"
    low_side_factor: float = 0.8
    range_factor: float = 1.25
    bases: dict[str, float] = Field(default_factory=dict)
    multipliers: dict[str, dict] = Field(default_factory=dict)
    timeline_weeks: dict[str, int] = Field(default_factory=lambda: {"simple": 8, "medium": 14, "complex": 22})
    complexity_thresholds: dict[str, float] = Field(default_factory=lambda: {"medium": 1.25, "complex": 1.55})
    team_mix: dict[str, list[str]] = Field(default_factory=dict)
    inclusions: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)

    @field_validator("low_side_factor")
    @classmethod
    def validate_low_side(cls, v: float) -> float:
        if v <= 0 or v > 1.0:
            raise ValueError(f"low_side_factor must be between 0 and 1.0 (got {v})")
        return v

    @field_validator("range_factor")
    @classmethod
    def validate_range_factor(cls, v: float) -> float:
        if v < 1.0:
            raise ValueError(f"range_factor must be >= 1.0 (got {v})")
        return v

    @field_validator("bases")
    @classmethod
    def validate_bases(cls, v: dict[str, float]) -> dict[str, float]:
        for k, val in v.items():
            if val <= 0:
                raise ValueError(f"Base price for '{k}' must be > 0 (got {val})")
        return v

    @field_validator("multipliers")
    @classmethod
    def validate_multipliers(cls, v: dict[str, dict]) -> dict[str, dict]:
        for group, items in v.items():
            if isinstance(items, dict):
                for item_k, factor in items.items():
                    if float(factor) <= 0:
                        raise ValueError(f"Multiplier '{group}.{item_k}' must be > 0 (got {factor})")
        return v

    @model_validator(mode="after")
    def validate_service_consistency(self) -> PricingConfig:
        if self.bases and self.team_mix:
            base_services = set(self.bases.keys())
            team_services = set(self.team_mix.keys())
            missing_team = base_services - team_services
            if missing_team:
                raise ValueError(f"Services defined in bases but missing team_mix: {missing_team}")
        return self


class QualificationConfig(BaseModel):
    budget_floor_usd: int = 8000
    book_threshold: int = 70
    warm_threshold: int = 50
    cold_threshold: int = 30
    weights: dict[str, int] = Field(default_factory=dict)
    budget_bands: dict[str, int] = Field(default_factory=dict)
    timeline_scores: dict[str, int] = Field(default_factory=dict)
    decision_role_scores: dict[str, int] = Field(default_factory=dict)
    company_size_scores: dict[str, int] = Field(default_factory=dict)
    disqualify_if: list[str] = Field(default_factory=list)
    book_requires: dict[str, object] = Field(default_factory=dict)
    budget_band_ranges_usd: dict[str, list[int | float | None] | None] = Field(default_factory=dict)


class PortfolioCase(BaseModel):
    id: str
    title: str
    industry: str = ""
    service: str = ""
    platforms: list[str] = Field(default_factory=list)
    stacks: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    outcome: str = ""
    url: str = ""


class PortfolioConfig(BaseModel):
    cases: list[PortfolioCase] = Field(default_factory=list)


class ObjectionItem(BaseModel):
    triggers: list[str] = Field(default_factory=list)
    reply: str = ""
    topic: str = ""


class ObjectionsConfig(BaseModel):
    items: dict[str, ObjectionItem] = Field(default_factory=dict)


VALID_ACK_PLACEHOLDERS = {"service_label", "goal_short", "platforms", "features_list", "timeline_label"}


class VoiceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    questions: dict[str, list[str]] = Field(default_factory=dict)
    acks: dict[str, list[str]] = Field(default_factory=dict)
    scope_coach: str = "That's a rich list. A lean first release usually keeps cost and risk down, so I'll split it into Core and Later for you."
    banned_phrases: list[str] = Field(default_factory=list)
    emoji_max: int = 1
    max_chars: int = 320

    @field_validator("questions")
    @classmethod
    def validate_questions(cls, v: dict[str, list[str]]) -> dict[str, list[str]]:
        for field, variants in v.items():
            if not isinstance(variants, list) or len(variants) < 2 or len(variants) > 3:
                raise ValueError(
                    f"field '{field}' questions must have 2 to 3 variants (got {len(variants) if isinstance(variants, list) else type(variants)})"
                )
            for variant in variants:
                words = variant.split()
                if len(words) > 30:
                    raise ValueError(f"question variant '{variant}' must be up to 30 words (got {len(words)})")
                if any(sym in variant for sym in ["$", "€", "£", "₹"]):
                    raise ValueError(f"question variant '{variant}' contains currency symbols")
                if re.search(r"\b\d+\s*(weeks?|months?|minutes?|hours?)\b", variant, re.IGNORECASE):
                    raise ValueError(f"question variant '{variant}' contains digits followed by weeks/months/minutes/hours")
        return v

    @field_validator("acks")
    @classmethod
    def validate_acks(cls, v: dict[str, list[str]]) -> dict[str, list[str]]:
        for field, templates in v.items():
            if not isinstance(templates, list):
                raise ValueError(f"acks for '{field}' must be a list of templates")
            for template in templates:
                placeholders = re.findall(r"\{([a-zA-Z0-9_]+)\}", template)
                for ph in placeholders:
                    if ph not in VALID_ACK_PLACEHOLDERS:
                        raise ValueError(f"Unknown placeholder '{{{ph}}}' in ack template '{template}'. Allowed: {sorted(VALID_ACK_PLACEHOLDERS)}")
        return v


class TenantConfig(BaseModel):
    brand: BrandConfig
    faqs: list[FaqItem] = Field(default_factory=list)
    services: ServicesConfig = Field(default_factory=ServicesConfig)
    pricing: PricingConfig = Field(default_factory=PricingConfig)
    qualification: QualificationConfig = Field(default_factory=QualificationConfig)
    portfolio: PortfolioConfig = Field(default_factory=PortfolioConfig)
    objections: ObjectionsConfig = Field(default_factory=ObjectionsConfig)
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    semantic_chunking: bool = False

    @model_validator(mode="after")
    def validate_page_hints_service(self) -> TenantConfig:
        if self.brand and self.brand.page_hints and self.services:
            valid_services = set(self.services.in_scope.keys())
            for hint in self.brand.page_hints:
                if hint.service and hint.service not in valid_services:
                    raise ValueError(
                        f"PageHint service '{hint.service}' is not in tenant in_scope services: {sorted(valid_services)}"
                    )
        return self

    @property
    def slug(self) -> str:
        return self.brand.slug


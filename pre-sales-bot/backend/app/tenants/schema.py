from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class BrandConfig(BaseModel):
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


class TenantConfig(BaseModel):
    brand: BrandConfig
    faqs: list[FaqItem] = Field(default_factory=list)
    services: ServicesConfig = Field(default_factory=ServicesConfig)
    pricing: PricingConfig = Field(default_factory=PricingConfig)
    qualification: QualificationConfig = Field(default_factory=QualificationConfig)
    portfolio: PortfolioConfig = Field(default_factory=PortfolioConfig)
    objections: ObjectionsConfig = Field(default_factory=ObjectionsConfig)
    semantic_chunking: bool = False

    @property
    def slug(self) -> str:
        return self.brand.slug

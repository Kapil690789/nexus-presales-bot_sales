from typing import Any

from pydantic import BaseModel, Field


class AgencyNda(BaseModel):
    required_before_rfp: bool = True
    required_before_handoff: bool = True
    version: str
    title: str = "Mutual confidentiality notice"
    checkbox_label: str
    body: str


class AgencyConfig(BaseModel):
    name: str
    legal_name: str
    tagline: str
    website: str
    tone: str
    languages: list[str]
    markets: list[str]
    currency_display: str = "USD"
    ask_email: str = "after_estimate"
    ask_phone: str = "optional"
    disclaimer: str
    nda: AgencyNda
    never_say: list[str] = Field(default_factory=list)
    out_of_scope_close: str
    out_of_scope_thanks: str = ""


class BrandConfig(BaseModel):
    primary: str
    accent: str
    background: str
    surface: str
    text: str
    muted: str
    success: str
    danger: str
    radius_px: int = 16
    logo_text: str
    launcher_text: str
    launcher_subtitle: str
    position: str = "bottom-right"
    widget_title: str
    widget_subtitle: str
    placeholder: str
    empty_state: str


class ServiceDef(BaseModel):
    label: str
    summary: str
    platforms: list[str] = Field(default_factory=list)
    stacks: list[str] = Field(default_factory=list)
    backend_stacks: list[str] = Field(default_factory=list)


class ServicesConfig(BaseModel):
    in_scope: dict[str, ServiceDef]
    out_of_scope: list[str]
    out_of_scope_labels: dict[str, str] = Field(default_factory=dict)


class PageDef(BaseModel):
    match: str = "/"
    service: str | None = None
    opening: str
    extra_questions: list[str] = Field(default_factory=list)


class PagesConfig(BaseModel):
    default: PageDef
    pages: list[PageDef]


class QualificationConfig(BaseModel):
    budget_floor_usd: int
    book_threshold: int
    warm_threshold: int
    cold_threshold: int
    weights: dict[str, int]
    budget_bands: dict[str, int]
    timeline_scores: dict[str, int]
    decision_role_scores: dict[str, int]
    company_size_scores: dict[str, int]
    disqualify_if: list[str]
    book_requires: dict[str, Any]


class PricingConfig(BaseModel):
    currency: str
    low_side_factor: float
    range_factor: float
    bases: dict[str, int]
    multipliers: dict[str, Any]
    timeline_weeks: dict[str, int]
    complexity_thresholds: dict[str, float]
    team_mix: dict[str, list[str]]
    inclusions: list[str]
    exclusions: list[str]


class CaseStudy(BaseModel):
    id: str
    title: str
    industry: str
    service: str
    platforms: list[str] = Field(default_factory=list)
    stacks: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    outcome: str
    url: str


class PortfolioConfig(BaseModel):
    cases: list[CaseStudy]


class ObjectionItem(BaseModel):
    triggers: list[str]
    reply: str


class ObjectionsConfig(BaseModel):
    items: dict[str, ObjectionItem]


class EnrichmentConfig(BaseModel):
    domains: dict[str, dict[str, str]] = Field(default_factory=dict)
    defaults: dict[str, str] = Field(default_factory=dict)


class HandoffNotify(BaseModel):
    email: dict[str, Any] = Field(default_factory=dict)
    slack: dict[str, Any] = Field(default_factory=dict)
    crm: dict[str, Any] = Field(default_factory=dict)
    calendar: dict[str, Any] = Field(default_factory=dict)


class HandoffConfig(BaseModel):
    notify: HandoffNotify
    summary_sections: list[str]
    follow_up: dict[str, str] = Field(default_factory=dict)


class CalendarConfig(BaseModel):
    timezone: str = "Asia/Kolkata"
    calendar_id: str = "primary"
    duration_minutes: int = 45
    weekdays: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4])
    open_hour: int = 10
    open_minute: int = 0
    close_hour: int = 17
    close_minute: int = 0
    title: str = "DevConsult consultation"


class PromptsConfig(BaseModel):
    persona: str
    rules: list[str]
    stage_goals: dict[str, str]
    json_contract: str
    lesson_contract: str = ""
    solution_contract: str = ""


class RagSources(BaseModel):
    config: bool = True
    content: bool = True
    fixtures: bool = True
    website: bool = False
    website_dir: str = "../website"


class RagRedaction(BaseModel):
    emails: bool = True
    phones: bool = True
    urls: bool = True
    proper_nouns: bool = True


class RagLearning(BaseModel):
    enabled: bool = True
    min_score: int | None = None
    outcome_boost: float = 2.0
    outcome_prior: int = 3


class RagConfig(BaseModel):
    top_k: int = 4
    lesson_k: int = 2
    min_score: float = 0.20
    max_snippet_chars: int = 480
    max_chunks_per_doc: int = 2
    objection_min_score: float = 0.55
    objection_min_score_local: float = 0.16
    sources: RagSources = Field(default_factory=RagSources)
    redaction: RagRedaction = Field(default_factory=RagRedaction)
    learning: RagLearning = Field(default_factory=RagLearning)

from functools import lru_cache
from pathlib import Path

import yaml

from backend.app.config_loader.models import (
    AgencyConfig,
    BrandConfig,
    HandoffConfig,
    ObjectionsConfig,
    PagesConfig,
    PortfolioConfig,
    PricingConfig,
    PromptsConfig,
    QualificationConfig,
    RagConfig,
    ServicesConfig,
    EnrichmentConfig,
)
from backend.app.core.settings import get_settings


class AppConfig:
    def __init__(
        self,
        agency: AgencyConfig,
        brand: BrandConfig,
        services: ServicesConfig,
        pages: PagesConfig,
        qualification: QualificationConfig,
        pricing: PricingConfig,
        portfolio: PortfolioConfig,
        objections: ObjectionsConfig,
        handoff: HandoffConfig,
        prompts: PromptsConfig,
        enrichment: EnrichmentConfig,
        rag: RagConfig,
    ) -> None:
        self.agency = agency
        self.brand = brand
        self.services = services
        self.pages = pages
        self.qualification = qualification
        self.pricing = pricing
        self.portfolio = portfolio
        self.objections = objections
        self.handoff = handoff
        self.prompts = prompts
        self.enrichment = enrichment
        self.rag = rag

    def page_for(self, path: str) -> tuple[str | None, str, list[str]]:
        normalized = (path or "/").split("?")[0].rstrip("/") or "/"
        if normalized.endswith(".html"):
            normalized = normalized[: -len(".html")]
        if normalized.endswith("/index"):
            normalized = normalized[: -len("/index")] or "/"
        for page in self.pages.pages:
            match = page.match.rstrip("/") or "/"
            if match != "/" and (normalized == match or normalized.endswith(match)):
                return page.service, page.opening.strip(), page.extra_questions
        default = self.pages.default
        return default.service, default.opening.strip(), default.extra_questions


def _read_yaml(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing config file: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config {path} must be a mapping")
    return data


def load_config(config_dir: Path | None = None) -> AppConfig:
    directory = Path(config_dir or get_settings().config_dir)
    return AppConfig(
        agency=AgencyConfig.model_validate(_read_yaml(directory / "agency.yaml")),
        brand=BrandConfig.model_validate(_read_yaml(directory / "brand.yaml")),
        services=ServicesConfig.model_validate(_read_yaml(directory / "services.yaml")),
        pages=PagesConfig.model_validate(_read_yaml(directory / "pages.yaml")),
        qualification=QualificationConfig.model_validate(_read_yaml(directory / "qualification.yaml")),
        pricing=PricingConfig.model_validate(_read_yaml(directory / "pricing.yaml")),
        portfolio=PortfolioConfig.model_validate(_read_yaml(directory / "portfolio.yaml")),
        objections=ObjectionsConfig.model_validate(_read_yaml(directory / "objections.yaml")),
        handoff=HandoffConfig.model_validate(_read_yaml(directory / "handoff.yaml")),
        prompts=PromptsConfig.model_validate(_read_yaml(directory / "prompts.yaml")),
        enrichment=EnrichmentConfig.model_validate(_read_yaml(directory / "enrichment.yaml")),
        rag=RagConfig.model_validate(_read_yaml(directory / "rag.yaml")),
    )


@lru_cache
def get_config() -> AppConfig:
    return load_config()

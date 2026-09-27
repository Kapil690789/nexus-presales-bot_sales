from __future__ import annotations

import json
import re
import shutil
from functools import lru_cache
from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.settings import ROOT
from backend.app.models.entities import TenantRow
from backend.app.tenants.schema import (
    BrandConfig,
    FaqItem,
    ObjectionsConfig,
    PortfolioConfig,
    PricingConfig,
    QualificationConfig,
    ServicesConfig,
    TenantConfig,
)

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")


class TenantNotFound(LookupError):
    pass


def tenants_root() -> Path:
    return ROOT / "tenants"


def tenant_dir(slug: str) -> Path:
    if not SLUG_RE.match(slug or ""):
        raise TenantNotFound(slug)
    return tenants_root() / slug


def _read_yaml(path: Path) -> dict:
    if not path.is_file():
        return {}
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return loaded if isinstance(loaded, dict) else {}


@lru_cache
def load_tenant(slug: str) -> TenantConfig:
    folder = tenant_dir(slug)
    if not folder.is_dir():
        raise TenantNotFound(slug)
    brand_raw = _read_yaml(folder / "brand.yaml")
    brand_raw.setdefault("slug", slug)
    brand = BrandConfig.model_validate(brand_raw)
    faqs_raw = _read_yaml(folder / "faqs.yaml").get("items") or []
    faqs = [FaqItem.model_validate(item) for item in faqs_raw if isinstance(item, dict)]
    return TenantConfig(
        brand=brand,
        faqs=faqs,
        services=ServicesConfig.model_validate(_read_yaml(folder / "services.yaml") or {"in_scope": {}}),
        pricing=PricingConfig.model_validate(_read_yaml(folder / "pricing.yaml") or {"bases": {}}),
        qualification=QualificationConfig.model_validate(_read_yaml(folder / "qualification.yaml") or {}),
        portfolio=PortfolioConfig.model_validate(_read_yaml(folder / "portfolio.yaml") or {}),
        objections=ObjectionsConfig.model_validate(_read_yaml(folder / "objections.yaml") or {}),
    )


def clear_tenant_cache() -> None:
    load_tenant.cache_clear()


def list_tenant_slugs() -> list[str]:
    root = tenants_root()
    if not root.is_dir():
        return []
    return sorted(path.name for path in root.iterdir() if path.is_dir() and (path / "brand.yaml").is_file())


def ensure_tenant_row(db: Session, slug: str) -> TenantRow:
    config = load_tenant(slug)
    row = db.scalar(select(TenantRow).where(TenantRow.slug == slug))
    brand_json = config.brand.model_dump_json()
    if row is None:
        row = TenantRow(
            slug=slug,
            name=config.brand.name,
            collection=slug,
            brand_json=brand_json,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    row.name = config.brand.name
    row.collection = row.collection or slug
    row.brand_json = brand_json
    db.commit()
    return row


def sync_tenant_rows(db: Session) -> list[TenantRow]:
    return [ensure_tenant_row(db, slug) for slug in list_tenant_slugs()]


def create_tenant_folder(slug: str, name: str, logo_text: str, primary: str) -> TenantConfig:
    if not SLUG_RE.match(slug):
        raise ValueError("Slug must be lowercase letters, numbers, and hyphens.")
    dest = tenant_dir(slug)
    if dest.exists():
        raise ValueError("That client already exists.")
    demo = tenant_dir("demo")
    dest.mkdir(parents=True)
    for filename in ("pricing.yaml", "qualification.yaml", "services.yaml", "objections.yaml"):
        source = demo / filename
        if source.is_file():
            shutil.copy(source, dest / filename)
    (dest / "portfolio.yaml").write_text("cases: []\n", encoding="utf-8")
    (dest / "faqs.yaml").write_text("items: []\n", encoding="utf-8")
    (dest / "content").mkdir()
    brand = {
        "name": name,
        "slug": slug,
        "logo_text": logo_text or name,
        "primary": primary or "#1A2B4C",
        "accent": primary or "#1A2B4C",
        "widget_title": f"{name} Advisor",
        "launcher_text": "Talk to an advisor",
        "disclaimer": "Indicative range only, not a fixed quote.",
        "nda_text": "Some project stories are confidential. Accept to see them in this chat.",
        "nda_version": "2026-01",
    }
    (dest / "brand.yaml").write_text(yaml.safe_dump(brand, sort_keys=False), encoding="utf-8")
    clear_tenant_cache()
    return load_tenant(slug)


def public_brand(config: TenantConfig) -> dict:
    brand = config.brand
    return json.loads(brand.model_dump_json())

from __future__ import annotations

import logging
import threading
from contextvars import ContextVar, Token
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.settings import ROOT, get_settings

log = logging.getLogger(__name__)

# Currency conversion default (as-of 2026-10, configurable via USD_TO_INR env var)
USD_TO_INR = 95.0

# Thread-safe in-memory cache for fast lookups and fallback tracking
_lock = threading.Lock()
_in_memory_records: list[dict[str, Any]] = []

# ContextVar for session binding across concurrent requests
_active_session_id: ContextVar[str | None] = ContextVar("active_session_id", default=None)


def set_active_session(session_id: str | None) -> Token:
    return _active_session_id.set(session_id)


def reset_active_session(token: Token) -> None:
    _active_session_id.reset(token)


def get_active_session() -> str:
    session_id = _active_session_id.get()
    if session_id:
        return session_id
    try:
        from backend.app.core.security import _llm_actor

        actor = _llm_actor.get()
        if actor:
            return actor[0]
    except Exception:
        pass
    return ""


def _load_model_rates() -> dict[str, Any]:
    rates_path = ROOT / "config" / "model_rates.yaml"
    if not rates_path.is_file():
        return {}
    try:
        import yaml

        with open(rates_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            return data.get("models", {})
    except Exception as exc:
        log.warning("Failed to load model rates from yaml: %s", type(exc).__name__)
        return {}


def get_model_rate(model: str, as_of_date: str | datetime | date | None = None) -> dict[str, Any] | None:
    """Look up the active rate tier for an exact model id as of a specific date."""
    if not model:
        return None
    clean = model.strip().lower()
    if clean.startswith("models/"):
        clean = clean[7:]
    rates_data = _load_model_rates()
    tiers = rates_data.get(clean)
    if not tiers or not isinstance(tiers, list):
        return None

    if as_of_date is None:
        target_date = datetime.now(timezone.utc).date()
    elif isinstance(as_of_date, datetime):
        target_date = as_of_date.date()
    elif isinstance(as_of_date, date):
        target_date = as_of_date
    elif isinstance(as_of_date, str):
        try:
            target_date = datetime.fromisoformat(as_of_date[:10]).date()
        except Exception:
            target_date = datetime.now(timezone.utc).date()
    else:
        target_date = datetime.now(timezone.utc).date()

    best_tier = None
    best_eff = None
    for tier in tiers:
        eff_str = str(tier.get("effective_from", "1970-01-01"))
        try:
            eff_date = datetime.fromisoformat(eff_str).date()
        except Exception:
            continue
        if eff_date <= target_date:
            if best_eff is None or eff_date >= best_eff:
                best_eff = eff_date
                best_tier = tier
    return best_tier


def calculate_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    call_type: str = "llm",
    as_of_date: str | datetime | date | None = None,
) -> tuple[float | None, float | None]:
    """Calculate USD and INR costs based on model token rates.

    Returns (cost_usd, cost_inr) or (None, None) if rate is unknown.
    Never falls back silently to another model's rate.
    """
    tier = get_model_rate(model, as_of_date=as_of_date)
    if not tier:
        return None, None

    in_rate = float(tier["input_per_1m"])
    out_rate = float(tier["output_per_1m"]) if call_type != "embedding" else 0.0

    cost_usd = (prompt_tokens / 1_000_000.0 * in_rate) + (completion_tokens / 1_000_000.0 * out_rate)
    usd_rate = getattr(get_settings(), "usd_to_inr", USD_TO_INR)
    cost_inr = cost_usd * usd_rate
    return cost_usd, cost_inr


def record_usage(
    provider: str,
    model: str,
    call_type: str,
    prompt_tokens: int,
    completion_tokens: int,
    session_id: str = "",
    tenant_id: str = "",
    estimated: bool = False,
    as_of_date: str | datetime | date | None = None,
) -> None:
    """Record LLM or embedding token usage into database and in-memory cache."""
    if not session_id:
        session_id = get_active_session()

    cost_usd, cost_inr = calculate_cost(model, prompt_tokens, completion_tokens, call_type, as_of_date=as_of_date)
    total_tokens = prompt_tokens + completion_tokens

    record_dict = {
        "provider": provider,
        "model": model,
        "call_type": call_type,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "cost_usd": cost_usd,
        "cost_inr": cost_inr,
        "estimated": estimated,
        "session_id": session_id,
        "tenant_id": tenant_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    with _lock:
        _in_memory_records.append(record_dict)

    # Persist into DB safely without risking caller flow
    try:
        from backend.app.models.db import SessionLocal
        from backend.app.models.entities import SessionRow, TokenUsageRow

        with SessionLocal() as db:
            row = TokenUsageRow(
                session_id=session_id,
                tenant_id=tenant_id,
                provider=provider,
                model=model,
                call_type=call_type,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_usd=cost_usd,
                cost_inr=cost_inr,
                estimated=estimated,
            )
            db.add(row)

            if session_id:
                srow = db.get(SessionRow, session_id)
                if srow is not None:
                    srow.llm_calls_used = (srow.llm_calls_used or 0) + 1
            db.commit()
    except Exception as exc:
        log.warning("Token usage DB write failed: %s", type(exc).__name__)


def get_usage_summary(db: Session | None = None, initial_budget_inr: float | None = None) -> dict[str, Any]:
    """Compile token usage, INR cost, and projections for admin view."""
    settings = get_settings()
    if initial_budget_inr is None:
        initial_budget_inr = settings.usage_budget_inr

    total_calls = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_tokens = 0
    total_cost_usd = 0.0
    total_cost_inr = 0.0
    sample_size = 0
    total_session_cost_inr = 0.0
    by_model: dict[str, dict[str, Any]] = {}
    recent_calls: list[dict[str, Any]] = []

    db_queried = False
    if db is not None:
        try:
            from backend.app.models.entities import TokenUsageRow

            count = db.scalar(select(func.count()).select_from(TokenUsageRow)) or 0
            if count > 0:
                total_calls = count
                total_prompt_tokens = db.scalar(select(func.sum(TokenUsageRow.prompt_tokens))) or 0
                total_completion_tokens = db.scalar(select(func.sum(TokenUsageRow.completion_tokens))) or 0
                total_tokens = db.scalar(select(func.sum(TokenUsageRow.total_tokens))) or 0
                total_cost_usd = float(
                    db.scalar(select(func.sum(TokenUsageRow.cost_usd)).where(TokenUsageRow.cost_usd.is_not(None))) or 0.0
                )
                total_cost_inr = float(
                    db.scalar(select(func.sum(TokenUsageRow.cost_inr)).where(TokenUsageRow.cost_inr.is_not(None))) or 0.0
                )

                sample_size = (
                    db.scalar(
                        select(func.count(func.distinct(TokenUsageRow.session_id))).where(TokenUsageRow.session_id != "")
                    )
                    or 0
                )

                total_session_cost_inr = float(
                    db.scalar(
                        select(func.sum(TokenUsageRow.cost_inr)).where(
                            TokenUsageRow.session_id != "", TokenUsageRow.cost_inr.is_not(None)
                        )
                    )
                    or 0.0
                )

                # Recent 15 calls
                recent_rows = db.scalars(
                    select(TokenUsageRow).order_by(TokenUsageRow.created_at.desc()).limit(15)
                ).all()
                for r in recent_rows:
                    recent_calls.append({
                        "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "",
                        "model": r.model,
                        "call_type": r.call_type,
                        "tokens": r.total_tokens,
                        "cost_inr": f"₹{r.cost_inr:.4f}" if r.cost_inr is not None else "rate unknown",
                        "cost_usd": f"${r.cost_usd:.5f}" if r.cost_usd is not None else "rate unknown",
                        "estimated": bool(r.estimated),
                        "session_id": r.session_id[:8] if r.session_id else "-",
                    })

                # Breakdown by model
                model_groups = db.execute(
                    select(
                        TokenUsageRow.model,
                        func.count().label("calls"),
                        func.sum(TokenUsageRow.total_tokens).label("tokens"),
                        func.sum(TokenUsageRow.cost_inr).label("inr"),
                    ).group_by(TokenUsageRow.model)
                ).all()
                for mg in model_groups:
                    m_name = mg.model or "unknown"
                    has_cost = mg.inr is not None
                    by_model[m_name] = {
                        "calls": mg.calls,
                        "tokens": mg.tokens or 0,
                        "cost_inr": round(float(mg.inr), 3) if has_cost else None,
                        "rate_status": "known" if has_cost else "unknown",
                    }
                db_queried = True
        except Exception as exc:
            log.debug("Database usage aggregation failed (%s): %s", type(exc).__name__, exc)

    if not db_queried or total_calls == 0:
        with _lock:
            total_calls = len(_in_memory_records)
            sessions_seen: set[str] = set()
            for r in _in_memory_records:
                total_prompt_tokens += r["prompt_tokens"]
                total_completion_tokens += r["completion_tokens"]
                total_tokens += r["total_tokens"]
                if r["cost_usd"] is not None:
                    total_cost_usd += r["cost_usd"]
                if r["cost_inr"] is not None:
                    total_cost_inr += r["cost_inr"]
                    if r["session_id"]:
                        total_session_cost_inr += r["cost_inr"]
                if r["session_id"]:
                    sessions_seen.add(r["session_id"])

                m = r["model"] or "unknown"
                if m not in by_model:
                    by_model[m] = {"calls": 0, "tokens": 0, "cost_inr": None, "rate_status": "unknown"}
                by_model[m]["calls"] += 1
                by_model[m]["tokens"] += r["total_tokens"]
                if r["cost_inr"] is not None:
                    curr = by_model[m]["cost_inr"] or 0.0
                    by_model[m]["cost_inr"] = round(curr + r["cost_inr"], 3)
                    by_model[m]["rate_status"] = "known"

                recent_calls.insert(0, {
                    "created_at": r["created_at"][:19].replace("T", " "),
                    "model": r["model"],
                    "call_type": r["call_type"],
                    "tokens": r["total_tokens"],
                    "cost_inr": f"₹{r['cost_inr']:.4f}" if r["cost_inr"] is not None else "rate unknown",
                    "cost_usd": f"${r['cost_usd']:.5f}" if r["cost_usd"] is not None else "rate unknown",
                    "estimated": bool(r.get("estimated", False)),
                    "session_id": r["session_id"][:8] if r["session_id"] else "-",
                })
            sample_size = len(sessions_seen)
            recent_calls = recent_calls[:15]

    # Projections: strictly measured per-session averages with sample size n >= 20
    projections_available = sample_size >= 20
    if projections_available and sample_size > 0:
        avg_session_cost_inr = total_session_cost_inr / sample_size
        if initial_budget_inr is not None and avg_session_cost_inr > 0:
            balance = max(0.0, initial_budget_inr - total_cost_inr)
            sessions_remaining = int(balance / avg_session_cost_inr)
            days_remaining = round(sessions_remaining / 30, 1)
        else:
            sessions_remaining = None
            days_remaining = None
    else:
        sessions_remaining = None
        days_remaining = None

    if initial_budget_inr is not None:
        balance_remaining_inr = max(0.0, initial_budget_inr - total_cost_inr)
        percentage_used = round((total_cost_inr / initial_budget_inr) * 100, 2) if initial_budget_inr > 0 else 0.0
        initial_budget_str = f"{initial_budget_inr:.2f}"
        balance_remaining_str = f"{balance_remaining_inr:.2f}"
        percentage_used_str = f"{percentage_used:.2f}"
    else:
        balance_remaining_inr = None
        percentage_used = None
        initial_budget_str = None
        balance_remaining_str = None
        percentage_used_str = None

    return {
        "total_calls": total_calls,
        "prompt_tokens": total_prompt_tokens,
        "completion_tokens": total_completion_tokens,
        "total_tokens": total_tokens,
        "prompt_tokens_formatted": f"{total_prompt_tokens:,}",
        "completion_tokens_formatted": f"{total_completion_tokens:,}",
        "total_tokens_formatted": f"{total_tokens:,}",
        "cost_usd": f"{total_cost_usd:.4f}",
        "cost_inr": f"{total_cost_inr:.2f}",
        "initial_budget_inr": initial_budget_str,
        "balance_remaining_inr": balance_remaining_str,
        "percentage_used": percentage_used_str,
        "sample_size": sample_size,
        "projections_available": projections_available,
        "sessions_remaining": f"{sessions_remaining:,}" if sessions_remaining is not None else None,
        "estimated_days_remaining": str(days_remaining) if days_remaining is not None else None,
        "by_model": by_model,
        "recent_calls": recent_calls,
    }


def reset_usage_for_tests() -> None:
    """Helper for testing: reset in-memory accumulator."""
    with _lock:
        _in_memory_records.clear()

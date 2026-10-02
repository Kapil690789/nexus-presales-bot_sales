from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

# Currency conversion: 1 USD = 95.0 INR (latest market rate)
USD_TO_INR = 95.0

# Model pricing table (per 1,000,000 tokens in USD)
# Format: (input_cost_per_1m, output_cost_per_1m)
_MODEL_RATES: dict[str, tuple[float, float]] = {
    # Gemini models
    "gemini-2.5-flash": (0.075, 0.30),
    "gemini-1.5-flash": (0.075, 0.30),
    "gemini-2.0-flash": (0.075, 0.30),
    "gemini-1.5-pro": (1.25, 5.00),
    "gemini-pro": (1.25, 5.00),
    "gemini-embedding-001": (0.02, 0.0),
    "text-embedding-004": (0.02, 0.0),
    # OpenAI models
    "gpt-4.1-mini": (0.15, 0.60),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    # Anthropic models
    "claude-sonnet-4-20250514": (3.00, 15.00),
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-3-5-haiku": (0.80, 4.00),
}
_DEFAULT_RATE = (0.075, 0.30)

# Thread-safe in-memory cache for fast lookups and fallback tracking
_lock = threading.Lock()
_in_memory_records: list[dict[str, Any]] = []


def calculate_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    call_type: str = "llm",
) -> tuple[float, float]:
    """Calculate USD and INR costs based on model token rates.

    Returns (cost_usd, cost_inr).
    """
    cleaned_model = (model or "").strip().lower()
    rates = _DEFAULT_RATE
    for key, rate in _MODEL_RATES.items():
        if key in cleaned_model:
            rates = rate
            break

    in_rate, out_rate = rates
    if call_type == "embedding":
        out_rate = 0.0

    cost_usd = (prompt_tokens / 1_000_000.0 * in_rate) + (completion_tokens / 1_000_000.0 * out_rate)
    cost_inr = cost_usd * USD_TO_INR
    return cost_usd, cost_inr


def record_usage(
    provider: str,
    model: str,
    call_type: str,
    prompt_tokens: int,
    completion_tokens: int,
    session_id: str = "",
    tenant_id: str = "",
) -> None:
    """Record LLM or embedding token usage into database and in-memory cache."""
    # Automatically resolve session_id from request context if not explicitly provided
    if not session_id:
        try:
            from backend.app.core.security import _llm_actor

            actor = _llm_actor.get()
            if actor:
                session_id = actor[0]
        except Exception:
            pass

    cost_usd, cost_inr = calculate_cost(model, prompt_tokens, completion_tokens, call_type)
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
        "session_id": session_id,
        "tenant_id": tenant_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    with _lock:
        _in_memory_records.append(record_dict)

    # Persist into DB asynchronously/safely without risking caller flow
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
            )
            db.add(row)

            # Also increment session llm_calls_used counter if active session
            if session_id:
                srow = db.get(SessionRow, session_id)
                if srow is not None:
                    srow.llm_calls_used = (srow.llm_calls_used or 0) + 1
            db.commit()
    except Exception as exc:
        log.debug("Token usage DB write skipped (%s): %s", type(exc).__name__, exc)


def get_usage_summary(db: Session | None = None, initial_budget_inr: float = 500.0) -> dict[str, Any]:
    """Compile token usage, INR cost, and 3-month forecast for admin view."""
    total_calls = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_tokens = 0
    total_cost_usd = 0.0
    total_cost_inr = 0.0
    by_model: dict[str, dict[str, Any]] = {}
    recent_calls: list[dict[str, Any]] = []

    # Attempt query from database
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
                total_cost_usd = float(db.scalar(select(func.sum(TokenUsageRow.cost_usd))) or 0.0)
                total_cost_inr = float(db.scalar(select(func.sum(TokenUsageRow.cost_inr))) or 0.0)

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
                        "cost_inr": f"₹{r.cost_inr:.4f}",
                        "cost_usd": f"${r.cost_usd:.5f}",
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
                    by_model[mg.model or "unknown"] = {
                        "calls": mg.calls,
                        "tokens": mg.tokens or 0,
                        "cost_inr": round(float(mg.inr or 0.0), 3),
                    }
                db_queried = True
        except Exception as exc:
            log.debug("Database usage aggregation failed (%s): %s", type(exc).__name__, exc)

    # Fallback / augment with in-memory records if DB empty
    if not db_queried or total_calls == 0:
        with _lock:
            total_calls = len(_in_memory_records)
            for r in _in_memory_records:
                total_prompt_tokens += r["prompt_tokens"]
                total_completion_tokens += r["completion_tokens"]
                total_tokens += r["total_tokens"]
                total_cost_usd += r["cost_usd"]
                total_cost_inr += r["cost_inr"]

                m = r["model"] or "unknown"
                if m not in by_model:
                    by_model[m] = {"calls": 0, "tokens": 0, "cost_inr": 0.0}
                by_model[m]["calls"] += 1
                by_model[m]["tokens"] += r["total_tokens"]
                by_model[m]["cost_inr"] = round(by_model[m]["cost_inr"] + r["cost_inr"], 3)

                recent_calls.insert(0, {
                    "created_at": r["created_at"][:19].replace("T", " "),
                    "model": r["model"],
                    "call_type": r["call_type"],
                    "tokens": r["total_tokens"],
                    "cost_inr": f"₹{r['cost_inr']:.4f}",
                    "cost_usd": f"${r['cost_usd']:.5f}",
                    "session_id": r["session_id"][:8] if r["session_id"] else "-",
                })
            recent_calls = recent_calls[:15]

    balance_remaining_inr = max(0.0, initial_budget_inr - total_cost_inr)
    percentage_used = round((total_cost_inr / initial_budget_inr) * 100, 2) if initial_budget_inr > 0 else 0.0

    # Capacity calculation:
    # Typical customer consultation session consumes ~5,000 tokens ≈ ₹0.05
    avg_session_cost_inr = 0.05
    sessions_remaining = int(balance_remaining_inr / avg_session_cost_inr) if avg_session_cost_inr > 0 else 0
    # Estimated days remaining assuming 30 client sessions/day
    days_remaining = round(sessions_remaining / 30, 1)

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
        "initial_budget_inr": f"{initial_budget_inr:.2f}",
        "balance_remaining_inr": f"{balance_remaining_inr:.2f}",
        "percentage_used": f"{percentage_used:.2f}",
        "sessions_remaining": f"{sessions_remaining:,}",
        "estimated_days_remaining": f"{days_remaining}",
        "by_model": by_model,
        "recent_calls": recent_calls,
    }


def reset_usage_for_tests() -> None:
    """Helper for testing: reset in-memory accumulator."""
    with _lock:
        _in_memory_records.clear()

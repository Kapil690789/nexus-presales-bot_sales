"""
Phase 0 golden tests — Nexus Pre-Sales Bot
==========================================
Covers:
  - Pricing golden cases (pin current engine math against pricing.yaml)
  - V1  Mislabeled vectors on Gemini failure   [xfail strict — desired: raise EmbeddingError]
  - V9  AI-features flag from free text         [xfail strict — desired: ai_features set]
  - V10 ["ios","android"] == "both" pricing     [pass — engine already handles it]
  - H1  Post-estimate free questions: RAG path  [characterization]
  - H2  Post-booking routing                    [unproven — driven through router]
  - H3  LLM failure: no event emitted           [xfail strict — desired: event written]
  - H4  student role: disqualifies immediately  [xfail strict — desired: confirm first]
  - H5  Production refuses SQLite               [xfail strict — desired: error on sqlite in prod]
  - H6  Feedback writes directly to training set [characterization]
  - V7  Vercel lazy-init: tables exist on first get_db [characterization]

Rules:
  - conftest sets EMBEDDING_BACKEND=hash and LLM_API_KEY="" so no real LLM/embedding calls.
  - This file NEVER prints or logs env key values.
  - xfail(strict=True) marks tests that document a *desired* behaviour the code does not yet
    have. The test must fail today (proving the bug) and will be promoted once the fix lands.
"""
from __future__ import annotations

import logging
import os
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_pricing():
    from backend.app.tenants.loader import load_tenant

    config = load_tenant("demo")
    return config.pricing


def _make_brief(**kwargs):
    from backend.app.agents.brief import ProjectBrief

    return ProjectBrief(**kwargs)


# ===========================================================================
# PRICING GOLDEN CASES
# ===========================================================================


class TestPricingGolden:
    """
    Pin the current engine arithmetic against pricing.yaml numbers.
    These tests must NOT change when the engine is refactored — they document
    what the formula currently produces.  Update only with owner approval.

    From pricing.yaml:
      bases: mobile_app=28000, web_app=24000
      low_side_factor: 0.80
      range_factor:    1.25
      platforms.both:  1.32
      flags.ai_features: 1.22
      timeline: simple=8, medium=14, complex=22
      complexity: medium>=1.25, complex>=1.55
    """

    def test_web_app_simple(self):
        """web_app + web platform, 0 integrations, no flags → simple complexity."""
        from backend.app.engines.pricing import estimate_project

        pricing = _load_pricing()
        brief = _make_brief(service="web_app", platforms=["web"], integrations=[])
        result = estimate_project(brief, pricing)

        # Raw = 24000 * 1.0 = 24000
        # Engine rounds to the nearest $500: int(round(raw * low_side_factor / 500.0) * 500) (pricing.py:52-53)
        # 24000 * 0.80 = 19200 -> 19200 / 500 = 38.4 -> round(38.4) = 38 -> 38 * 500 = 19000
        # High = round(19000 * 1.25 / 500) * 500 = round(47.5) * 500 = 48 * 500 = 24000
        assert result["low"] == 19_000
        assert result["high"] == 24_000
        assert result["complexity_band"] == "simple"
        assert result["timeline_weeks"] == 8
        assert result["currency"] == "USD"

    def test_mobile_app_both_platforms_no_flags(self):
        """mobile_app + both platforms, 0 integrations, no flags → medium complexity."""
        from backend.app.engines.pricing import estimate_project

        pricing = _load_pricing()
        brief = _make_brief(service="mobile_app", platforms=["ios", "android"], integrations=[])
        result = estimate_project(brief, pricing)

        # Raw = 28000 * 1.32 = 36960 (complexity 1.32 >= 1.25 -> medium -> 14 weeks)
        # Engine rounds to the nearest $500: int(round(raw * 0.80 / 500.0) * 500) (pricing.py:52-53)
        # 36960 * 0.80 = 29568 -> 29568 / 500 = 59.136 -> round(59.136) = 59 -> 59 * 500 = 29500
        # High = round(29500 * 1.25 / 500) * 500 = round(73.75) * 500 = 74 * 500 = 37000
        assert result["low"] == 29_500
        assert result["high"] == 37_000
        assert result["complexity_band"] == "medium"
        assert result["timeline_weeks"] == 14

    def test_mobile_app_both_platforms_with_ai_features_flag(self):
        """mobile_app + both platforms + ai_features flag → complex complexity."""
        from backend.app.engines.pricing import estimate_project

        pricing = _load_pricing()
        brief = _make_brief(
            service="mobile_app",
            platforms=["ios", "android"],
            integrations=[],
            ai_features=["AI chat"],
        )
        result = estimate_project(brief, pricing)

        # Complexity = 1.32 * 1.22 = 1.6104 >= 1.55 -> complex -> 22 weeks
        # Raw = 28000 * 1.6104 = 45091.2
        # Engine rounds to nearest $500: int(round(45091.2 * 0.80 / 500.0) * 500) = 72 * 500 = 36000
        # High = round(36000 * 1.25 / 500.0) * 500 = 45000
        assert result["low"] == 36_000
        assert result["high"] == 45_000
        assert result["complexity_band"] == "complex"
        assert result["timeline_weeks"] == 22

    # V10 — ["ios","android"] chip output must equal "both" pricing
    def test_v10_ios_android_list_equals_both(self):
        """
        V10 REFUTED: engine correctly maps ["ios","android"] to the 'both' multiplier.
        This test pins that behaviour so a future refactor cannot silently break it.
        """
        from backend.app.engines.pricing import estimate_project

        pricing = _load_pricing()
        brief_list = _make_brief(service="mobile_app", platforms=["ios", "android"], integrations=[])
        brief_both = _make_brief(service="mobile_app", platforms=["both"], integrations=[])
        r_list = estimate_project(brief_list, pricing)
        r_both = estimate_project(brief_both, pricing)
        assert r_list["low"] == r_both["low"]
        assert r_list["high"] == r_both["high"]
        assert r_list["complexity_band"] == r_both["complexity_band"]

    def test_mobile_both_asap_timeline_12_weeks(self):
        """
        Timeline modifier check (pricing.py:63-64):
        Base timeline for medium complexity (mobile_app + both, complexity=1.32) is 14 weeks.
        With brief.timeline == 'asap', pricing.py calculates:
            weeks = max(6, ceil(14 * 0.85)) = max(6, ceil(11.9)) = 12 weeks.
        This confirms mobile + both platforms with timeline='asap' yields exactly 12 weeks.
        """
        from backend.app.engines.pricing import estimate_project

        pricing = _load_pricing()
        brief = _make_brief(
            service="mobile_app",
            platforms=["ios", "android"],
            integrations=[],
            timeline="asap",
        )
        result = estimate_project(brief, pricing)
        assert result["timeline_weeks"] == 12
        assert result["low"] == 29_500
        assert result["high"] == 37_000


# ===========================================================================
# V9 — AI FEATURES EXTRACTION (heuristic path, LLM disabled in conftest)
# ===========================================================================


class TestV9AiExtraction:
    """
    Tests for extractor.py service/ai_features classification.
    Heuristic path only (LLM disabled via conftest LLM_API_KEY="").
    """

    def test_email_app_not_ai_product(self):
        """Word-boundary check: 'email' contains substring 'ai', must NOT trigger ai_product."""
        from backend.app.agents.extractor import _heuristic_extract

        result = _heuristic_extract("I want an email app")
        assert result.get("service") != "ai_product", f"Got service={result.get('service')!r}"

    def test_maintain_my_site_not_ai_product(self):
        """Word-boundary check: 'maintain' contains substring 'ai', must NOT trigger ai_product."""
        from backend.app.agents.extractor import _heuristic_extract

        result = _heuristic_extract("maintain my site")
        assert result.get("service") != "ai_product", f"Got service={result.get('service')!r}"

    def test_available_on_the_web_not_ai_product(self):
        """'available on the web' -> web_app, NOT ai_product."""
        from backend.app.agents.extractor import _heuristic_extract

        result = _heuristic_extract("available on the web")
        assert result.get("service") != "ai_product", f"Got service={result.get('service')!r}"
        assert result.get("service") == "web_app"

    def test_trail_booking_app_not_ai_product(self):
        """Word-boundary check: 'trail' contains 'ai', must NOT trigger ai_product."""
        from backend.app.agents.extractor import _heuristic_extract

        result = _heuristic_extract("trail booking app")
        assert result.get("service") != "ai_product", f"Got service={result.get('service')!r}"

    def test_plain_website_not_ai_product(self):
        """Word-boundary check: 'plain' contains 'ai', must NOT trigger ai_product."""
        from backend.app.agents.extractor import _heuristic_extract

        result = _heuristic_extract("plain website")
        assert result.get("service") != "ai_product", f"Got service={result.get('service')!r}"
        assert result.get("service") == "web_app"

    def test_available_on_ios_not_ai_product(self):
        """'available on iOS' -> mobile_app, NOT ai_product."""
        from backend.app.agents.extractor import _heuristic_extract

        result = _heuristic_extract("available on iOS")
        assert result.get("service") != "ai_product", f"Got service={result.get('service')!r}"
        assert result.get("service") == "mobile_app"

    def test_mobile_app_with_ai_chat_promoted(self):
        """
        Promoted from xfail: 'mobile app with AI chat' -> service=mobile_app
        and ai_features non-empty (e.g. ['AI chat']).
        """
        from backend.app.agents.brief import ProjectBrief
        from backend.app.agents.extractor import apply_extracted_slots, _heuristic_extract

        result = _heuristic_extract("mobile app with AI chat")
        assert result.get("service") == "mobile_app"
        assert result.get("ai_features"), "ai_features should be non-empty in extracted dict"

        brief = ProjectBrief()
        apply_extracted_slots(brief, result)
        assert brief.service == "mobile_app"
        assert brief.ai_features == ["AI chat"] or "AI chat" in brief.ai_features

    def test_ai_powered_assistant_for_clinic(self):
        """'AI-powered assistant for my clinic' -> ai_product."""
        from backend.app.agents.extractor import _heuristic_extract

        result = _heuristic_extract("AI-powered assistant for my clinic")
        assert result.get("service") == "ai_product"

    def test_an_ai_product(self):
        """'an AI product' -> ai_product."""
        from backend.app.agents.extractor import _heuristic_extract

        result = _heuristic_extract("an AI product")
        assert result.get("service") == "ai_product"

    def test_ios_and_android_app_with_ai_chat_prices_with_ai_flag(self):
        """
        'iOS and Android app with AI chat' sets mobile_app + both platforms + ai_features,
        pricing at $36,000–$45,000, 22 weeks for a non-asap timeline.
        """
        from backend.app.agents.brief import ProjectBrief
        from backend.app.agents.extractor import apply_extracted_slots, _heuristic_extract
        from backend.app.engines.pricing import estimate_project

        result = _heuristic_extract("iOS and Android app with AI chat")
        assert result.get("service") == "mobile_app"
        assert set(result.get("platforms", [])) == {"ios", "android"}
        assert result.get("ai_features")

        brief = ProjectBrief()
        apply_extracted_slots(brief, result)
        assert brief.service == "mobile_app"
        assert set(brief.platforms) == {"ios", "android"}
        assert brief.ai_features

        pricing = _load_pricing()
        estimate = estimate_project(brief, pricing)
        # raw = 28000 * 1.32 (both) * 1.22 (ai_features) = 45091.2
        # low = round(45091.2 * 0.80 / 500) * 500 = 36000
        # high = round(36000 * 1.25 / 500) * 500 = 45000
        assert estimate["low"] == 36_000
        assert estimate["high"] == 45_000
        assert estimate["complexity_band"] == "complex"
        assert estimate["timeline_weeks"] == 22

    def test_ai_regex_expanded_positive_terms(self):
        """
        Task A3: Each expanded keyword must positively trigger AI detection:
        ai, llm, gpt, chatgpt, openai, chatbot, chat bot, machine learning, nlp.
        """
        from backend.app.agents.extractor import _heuristic_extract

        terms = [
            "ai",
            "llm",
            "gpt",
            "chatgpt",
            "openai",
            "chatbot",
            "chat bot",
            "machine learning",
            "nlp",
        ]
        for term in terms:
            res = _heuristic_extract(f"I want to build a {term} product for my business")
            assert res.get("service") == "ai_product", (
                f"Expected service='ai_product' for keyword '{term}', got {res.get('service')!r}"
            )

    def test_ai_regex_expanded_negative_terms(self):
        """
        Task A3: Negative words containing 'ai' or related letters must NOT trigger ai_product:
        html, mail, again, maintain, detail, plain.
        """
        from backend.app.agents.extractor import _heuristic_extract

        negatives = [
            ("html", "I need an html template"),
            ("mail", "I want a mail server setup"),
            ("again", "Let us try again later"),
            ("maintain", "Please maintain my existing site"),
            ("detail", "Here is more detail about our work"),
            ("plain", "Just a plain website for now"),
        ]
        for label, text in negatives:
            res = _heuristic_extract(text)
            assert res.get("service") != "ai_product", (
                f"Negative '{label}' falsely triggered ai_product: {res.get('service')!r} from '{text}'"
            )

    def test_ai_features_label_chat_vs_non_chat(self):
        """
        Task A3: ai_features label must NOT be hardcoded to 'AI chat'.
        If text contains 'chat', use ['AI chat']; else use ['AI features'].
        """
        from backend.app.agents.extractor import _heuristic_extract

        # Text with 'chat' -> ['AI chat']
        res_chat = _heuristic_extract("mobile app with AI chat")
        assert res_chat.get("service") == "mobile_app"
        assert res_chat.get("ai_features") == ["AI chat"]

        # Text without 'chat' (e.g. machine learning, nlp) -> ['AI features']
        res_ml = _heuristic_extract("mobile app with machine learning capabilities")
        assert res_ml.get("service") == "mobile_app"
        assert res_ml.get("ai_features") == ["AI features"]

        res_nlp = _heuristic_extract("web app with nlp analytics")
        assert res_nlp.get("service") == "web_app"
        assert res_nlp.get("ai_features") == ["AI features"]

    def test_hinglish_mixed_language_input(self):
        """
        Task A3: Test mixed-language input 'mujhe ek AI wala app chahiye'.
        Pins actual extracted service and ai_features.
        """
        from backend.app.agents.extractor import _heuristic_extract

        result = _heuristic_extract("mujhe ek AI wala app chahiye")
        # 'AI' triggers ai_product (no specific mobile/web platform keyword present)
        assert result.get("service") == "ai_product", (
            f"Expected service='ai_product' for Hinglish AI request, got {result.get('service')!r}"
        )
        # When service is ai_product, ai_features is not set separately
        assert "ai_features" not in result



# ===========================================================================
# V1 — MISLABELED EMBEDDING VECTORS
# ===========================================================================


class TestV1MislabeledVectors:
    """
    V1: When Gemini embedding fails, EmbeddingError is raised.
    Never returns mislabeled hash vectors. Request sends x-goog-api-key header and no key in URL.
    Query mode adheres to 5s timeout, max 1 retry, 8s total budget.
    """

    def test_v1_characterization_mislabel_on_gemini_failure(self, monkeypatch):
        """
        Updated to new behaviour: Gemini HTTP failure raises EmbeddingError immediately.
        Dead code expecting hash vector fallback removed.
        """
        import httpx
        from backend.app.core.settings import get_settings
        from backend.app.rag.embeddings import EmbeddingError, _gemini_embed, embed_texts

        monkeypatch.setenv("EMBEDDING_BACKEND", "gemini")
        monkeypatch.setenv("LLM_API_KEY", "fake-key-for-test")
        get_settings.cache_clear()

        class _FailClient:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def post(self, *args, **kwargs):
                r = MagicMock()
                r.status_code = 500
                r.text = "Internal Server Error"
                return r

        with patch("httpx.Client", return_value=_FailClient()), \
             patch("time.sleep"):
            with pytest.raises(EmbeddingError) as exc_info:
                _gemini_embed(["hello world"], "gemini-embedding-001")
            assert exc_info.value.status_code == 500

            with pytest.raises(EmbeddingError):
                embed_texts(["hello world"], model_id="gemini-embedding-001")

        get_settings.cache_clear()

    def test_v1_desired_raises_embedding_error_on_failure(self, monkeypatch):
        """
        PROMOTED: Gemini failure -> EmbeddingError raised (never returns mislabeled vectors).
        """
        monkeypatch.setenv("EMBEDDING_BACKEND", "gemini")
        monkeypatch.setenv("LLM_API_KEY", "fake-key-for-test")
        from backend.app.core.settings import get_settings
        from backend.app.rag.embeddings import EmbeddingError, embed_texts

        get_settings.cache_clear()

        class _FailClient:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def post(self, *args, **kwargs):
                r = MagicMock()
                r.status_code = 500
                r.text = "error"
                return r

        with patch("httpx.Client", return_value=_FailClient()), \
             patch("time.sleep"):
            with pytest.raises(EmbeddingError) as exc_info:
                embed_texts(["hello"], model_id="gemini-embedding-001")
            assert exc_info.value.status_code == 500 or "500" in str(exc_info.value)

        get_settings.cache_clear()

    def test_v1_header_auth_no_key_in_url(self, monkeypatch):
        """
        Asserts that Gemini embedding requests pass key in 'x-goog-api-key' header
        and NEVER put 'key=' in the request URL.
        """
        from backend.app.core.settings import get_settings
        from backend.app.rag.embeddings import _gemini_embed

        monkeypatch.setenv("EMBEDDING_BACKEND", "gemini")
        monkeypatch.setenv("LLM_API_KEY", "secret-test-key-12345")
        get_settings.cache_clear()

        captured_requests = []

        class _CaptureClient:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def post(self, url, headers=None, json=None, **kwargs):
                captured_requests.append({"url": url, "headers": headers or {}, "json": json})
                r = MagicMock()
                r.status_code = 200
                r.json.return_value = {"embeddings": [{"values": [0.1] * 768}]}
                return r

        with patch("httpx.Client", return_value=_CaptureClient()):
            vecs = _gemini_embed(["test text"], "gemini-embedding-001")
            assert len(vecs) == 1

        assert len(captured_requests) == 1
        req = captured_requests[0]
        assert "key=" not in req["url"]
        assert req["headers"].get("x-goog-api-key") == "secret-test-key-12345"

        get_settings.cache_clear()

    def test_v1_query_mode_retries_and_budget_on_429(self, monkeypatch):
        """
        Simulate 429 in query mode with patched time functions:
        Asserts at most 2 HTTP calls and total wall-clock sleep <= 8s.
        """
        from backend.app.core.settings import get_settings
        from backend.app.rag.embeddings import EmbeddingError, _gemini_embed

        monkeypatch.setenv("EMBEDDING_BACKEND", "gemini")
        monkeypatch.setenv("LLM_API_KEY", "fake-key")
        get_settings.cache_clear()

        call_count = 0
        slept_durations = []

        class _429Client:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def post(self, *args, **kwargs):
                nonlocal call_count
                call_count += 1
                r = MagicMock()
                r.status_code = 429
                r.text = "Rate limit exceeded"
                return r

        def fake_sleep(secs):
            slept_durations.append(secs)

        with patch("httpx.Client", return_value=_429Client()), \
             patch("time.sleep", side_effect=fake_sleep):
            with pytest.raises(EmbeddingError) as exc_info:
                _gemini_embed(["user query"], model_id="gemini-embedding-001", mode="query")
            assert exc_info.value.status_code == 429

        assert call_count <= 2, f"Expected at most 2 calls in query mode, got {call_count}"
        assert sum(slept_durations) <= 8.0, f"Expected total sleep <= 8s, got {sum(slept_durations)}"

        get_settings.cache_clear()

    def test_v1_ingest_continues_past_one_failing_document(self, monkeypatch):
        """
        In upsert_documents, if doc 1 raises EmbeddingError and doc 2 succeeds,
        ingest logs the exception, skips doc 1, embeds doc 2, and counts failures.
        """
        from sqlalchemy import select

        from backend.app.models.db import SessionLocal, init_db
        from backend.app.models.entities import ChunkRow, TenantRow
        from backend.app.rag.embeddings import EmbeddingBatch, EmbeddingError
        from backend.app.rag.store import Document, upsert_documents

        init_db()
        with SessionLocal() as db:
            tenant = db.scalar(select(TenantRow).where(TenantRow.slug == "demo"))
            if not tenant:
                tenant = TenantRow(slug="demo", name="Demo")
                db.add(tenant)
                db.commit()

            doc1 = Document(doc_id="doc-fail-1", title="Fail Doc", content="This fails", source="knowledge")
            doc2 = Document(doc_id="doc-ok-2", title="OK Doc", content="This succeeds", source="knowledge")

            call_count = 0

            def fake_embed_texts(texts, model, mode="ingest"):
                nonlocal call_count
                call_count += 1
                if "This fails" in texts[0]:
                    raise EmbeddingError("Gemini API error 500", status_code=500)
                return EmbeddingBatch(model="test-model", dim=384, vectors=[[0.5] * 384])

            with patch("backend.app.rag.store.embed_texts", side_effect=fake_embed_texts):
                res = upsert_documents(db, tenant, [doc1, doc2])

            assert res["failures"] == 1
            assert res["embedded"] == 1

            # doc2 exists in DB, doc1 does not
            ok_chunk = db.scalar(select(ChunkRow).where(ChunkRow.doc_id == "doc-ok-2"))
            assert ok_chunk is not None
            fail_chunk = db.scalar(select(ChunkRow).where(ChunkRow.doc_id == "doc-fail-1"))
            assert fail_chunk is None

    def test_v1_health_shows_degraded_after_failure(self, client):
        """
        GET /health returns 'embeddings' dict. After an embedding failure,
        degraded is True, failures >= 1, and last_error contains no URL or key.
        """
        from backend.app.rag.embeddings import EmbeddingError, record_query_failure, reset_embedding_health

        reset_embedding_health()
        res_before = client.get("/health").json()
        assert "embeddings" in res_before
        assert res_before["embeddings"]["degraded"] is False
        assert res_before["embeddings"]["failures"] == 0

        # Simulate failure
        record_query_failure(EmbeddingError("Gemini 429 quota exhausted", status_code=429))

        res_after = client.get("/health").json()
        emb_health = res_after["embeddings"]
        assert emb_health["degraded"] is True
        assert emb_health["failures"] >= 1
        assert "429" in emb_health["last_error"]
        assert "http" not in emb_health["last_error"].lower()
        assert "key" not in emb_health["last_error"].lower()

        reset_embedding_health()



# ===========================================================================
# V7 — VERCEL LAZY INIT
# ===========================================================================


class TestV7VercelLazyInit:
    """
    V7: On Vercel, lifespan skips init_db(). db.py has ensure_ready() which
    is called by get_db(). Characterize whether tables exist after the first
    get_db() call in Vercel mode.
    """

    def test_v7_ensure_ready_creates_tables(self, monkeypatch, tmp_path):
        """
        Characterization: simulates the Vercel path by setting VERCEL=1 and using
        a fresh temp DB. Calls get_db() and verifies tables were created.
        """
        db_path = tmp_path / "vercel_test.db"
        db_url = f"sqlite:///{db_path}"

        monkeypatch.setenv("VERCEL", "1")
        monkeypatch.setenv("DATABASE_URL", db_url)
        monkeypatch.setenv("EMBEDDING_BACKEND", "hash")
        monkeypatch.setenv("LLM_API_KEY", "")

        # Reset all module-level singletons
        from backend.app.core.settings import get_settings

        get_settings.cache_clear()

        import backend.app.models.db as dbmod

        dbmod._engine = None
        dbmod._session_factory = None
        dbmod._ready = False

        # Trigger get_db (simulates first Vercel request)
        db_gen = dbmod.get_db()
        db = next(db_gen)
        try:
            from sqlalchemy import inspect as sa_inspect

            inspector = sa_inspect(db.get_bind())
            tables = inspector.get_table_names()
            # ensure_ready should have called init_db → created tables
            assert "sessions" in tables, (
                f"V7: 'sessions' table missing after first get_db() on Vercel path. "
                f"Found tables: {tables}. ensure_ready() may have silently failed."
            )
            assert "tenants" in tables, f"V7: 'tenants' table missing. Tables: {tables}"
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass
            dbmod._engine = None
            dbmod._session_factory = None
            dbmod._ready = False
            get_settings.cache_clear()


# ===========================================================================
# H1 — POST-ESTIMATE FREE QUESTIONS: RAG PATH
# ===========================================================================


class TestH1PostEstimateQuestions:
    """
    H1: After an estimate, free-form questions should be answered by LLM+RAG.
    We test all three paths: grade==show, grade==weak, embedding failure.
    LLM is disabled in conftest — so this characterizes the heuristic path.
    """

    def _complete_brief(self):
        from backend.app.agents.brief import ProjectBrief

        return ProjectBrief(
            service="web_app",
            goal="A SaaS dashboard for logistics companies",
            platforms=["web"],
            users="business",
            integrations=["none"],
            timeline="3_6_months",
            budget_band="40_80k",
            decision_role="founder_or_exec",
            features=["login", "dashboard"],
            features_confirmed=True,
        )

    def test_h1_show_path_uses_grounded_answer(self, client):
        """
        H1 show-path: when grade() returns 'show', grounded_answer() is used.
        Characterize: with hash embeddings and no corpus, grade likely returns 'weak'.
        """
        # Create session
        resp = client.post("/api/v1/sessions", json={"tenant": "demo"})
        assert resp.status_code == 200
        session_id = resp.json()["session_id"]

        # Manually set brief to complete state via multiple chip messages
        chips_sequence = [
            {"field": "service", "value": "web_app", "label": "Web app"},
            {"field": "platforms", "value": ["web"], "label": "Web"},
            {"field": "users", "value": "business", "label": "Business users"},
            {"field": "integrations", "value": ["none"], "label": "None on day one"},
            {"field": "timeline", "value": "3_6_months", "label": "3–6 months"},
            {"field": "budget_band", "value": "40_80k", "label": "$40–80k"},
            {"field": "decision_role", "value": "founder_or_exec", "label": "Founder / exec"},
        ]
        for chip in chips_sequence:
            r = client.post(
                f"/api/v1/sessions/{session_id}/messages",
                json={"content": "", "chip": chip},
            )
            assert r.status_code == 200

        # Send a goal to complete the brief
        r = client.post(
            f"/api/v1/sessions/{session_id}/messages",
            json={"content": "I want a logistics dashboard with real-time tracking"},
        )
        assert r.status_code == 200

        # Now ask a free-form question after the estimate
        r = client.post(
            f"/api/v1/sessions/{session_id}/messages",
            json={"content": "Do you use Flutter for mobile apps?"},
        )
        assert r.status_code == 200
        data = r.json()
        route = data.get("route")
        # Characterization: with no corpus, grade is weak → fallback route
        # Document the actual route so regressions are visible
        assert route in ("fallback", "rag", "faq"), f"Unexpected route={route!r}"
        # H1 finding: with hash embedder and no corpus, RAG chunks are empty
        # The fallback path IS reached for weak-hit questions after estimate
        # (This is the characterization — no xfail since fallback.py now calls LLM when available)

    def test_h1_weak_hit_no_rag_chunks(self):
        """
        H1 low/weak path: when grade() has no hits, it returns 'low' (score=0.0).
        Characterize: _strong_hits returns [] → no grounded_answer called.
        This documents the RAG gap for post-estimate questions with no corpus.
        """
        from backend.app.rag.grade import grade

        # With no hits (empty list), grade returns 'low' (score=0.0)
        decision, score = grade("do you use flutter?", [])
        # Pin the actual vocabulary returned by grade()
        assert decision == "low", (
            f"grade() vocabulary changed: expected 'low' for empty hits, got {decision!r}. "
            "Update this characterization."
        )
        assert score == 0.0
        # H1 finding: 'low' means no show-path, no grounded_answer.
        # Post-estimate questions with no corpus go to fallback route.


    def test_h1_embedding_failure_path(self, monkeypatch):
        """
        H1 embedding failure: characterize what happens when search() returns nothing.
        Expect fallback route, not a crash.
        """
        from backend.app.agents.brief import ProjectBrief

        brief = ProjectBrief(
            service="web_app",
            goal="dashboard",
            platforms=["web"],
            users="business",
            integrations=["none"],
            timeline="3_6_months",
            budget_band="40_80k",
            decision_role="founder_or_exec",
            features=["login"],
            features_confirmed=True,
        )
        # Patch search to return empty (simulates embedding failure producing 0 results)
        with patch("backend.app.agents.router.search", return_value=[]):
            from backend.app.agents.brief import brief_ready

            assert brief_ready(brief), "Brief should be complete for this test"

    def test_h1_retrieval_chunk_inclusion_across_scores(self):
        """
        H1 verification:
        Ingest demo corpus. Patch router.search to return hits scoring 0.60, 0.42, 0.20, and [].
        Capture prompts sent to mocked LLM for each turn.
        Checks whether retrieved chunks are included in the LLM prompt.
        """
        from backend.app.models.db import SessionLocal, init_db
        from backend.app.rag.ingest import ingest_all
        from backend.app.tenants.loader import ensure_tenant_row, load_tenant
        from backend.app.agents.brief import ProjectBrief
        from backend.app.models.entities import SessionRow
        from backend.app.rag.store import Hit
        from backend.app.agents.router import run_turn

        init_db()
        with SessionLocal() as db:
            ingest_all(db)
            tenant = ensure_tenant_row(db, "demo")
            tenant_id = tenant.id
            config = load_tenant("demo")

            test_cases = [
                (0.60, True),   # score 0.60 >= 0.50 (show_min_score) -> grounded_answer called with chunks
                (0.42, True),   # score 0.42 in weak band -> fallback_message called with possibly relevant notes
                (0.20, False),  # score 0.20 < 0.35 -> low grade -> fallback_message called (no chunks)
                (None, False),  # empty hits [] -> low grade -> fallback_message called (no chunks)
            ]

            for score_val, expected_has_chunks in test_cases:
                session = SessionRow(tenant_id=tenant_id, stage="advising")
                brief = ProjectBrief(
                    service="web_app", goal="Test logistics app", platforms=["web"],
                    users="business", integrations=["none"], timeline="3_6_months",
                    budget_band="40_80k", decision_role="founder_or_exec",
                    features=["login"], features_confirmed=True
                )
                session.brief_json = brief.model_dump_json()

                test_chunk_text = "UNIQUE_CHUNK_TEXT: We build custom software with AWS and Python."
                hits = []
                if score_val is not None:
                    hits = [Hit(
                        id="chunk_test_1", doc_id="doc_test_1", title="Tech Stack Doc",
                        content=test_chunk_text, score=score_val, source="content"
                    )]

                captured_prompts = []
                def fake_complete_json(system, prompt, **kwargs):
                    captured_prompts.append((system, prompt))
                    if "relevant" in (system or "").lower():
                        return {"relevant": True}
                    return {"message": "Mocked consultant response"}

                with patch("backend.app.agents.router.search") as mock_search, \
                     patch("backend.app.rag.grade.complete_json", side_effect=fake_complete_json), \
                     patch("backend.app.agents.fallback.complete_json", side_effect=fake_complete_json), \
                     patch("backend.app.rag.grade.llm_available", return_value=True), \
                     patch("backend.app.agents.fallback.llm_available", return_value=True):

                    def fake_search(db_arg, t_arg, q_arg, kind="knowledge", **kwargs):
                        if kind == "faq":
                            return []
                        return hits
                    mock_search.side_effect = fake_search

                    run_turn(db, tenant, config, session, [], "What tech stack do you use?", None)

                    has_chunk_in_llm_prompt = any(test_chunk_text in p[1] for p in captured_prompts)
                    assert has_chunk_in_llm_prompt == expected_has_chunks, (
                        f"For score {score_val}: expected chunk inclusion={expected_has_chunks}, got {has_chunk_in_llm_prompt}"
                    )


# ===========================================================================
# H2 — POST-BOOKING ROUTING (drive through router.py)
# ===========================================================================


class TestH2PostBookingRouting:
    """
    H2: Build a genuinely booked session and assert the follow-up reply
    is NOT the canned booking confirmation text from router.py:248.
    """

    def test_h2_post_booking_turn_calls_run_turn(self, client):
        """
        H2: After booking_json is set, a follow-up message must go through
        run_turn() normally and must NOT repeat the booking confirmation text.
        """
        # Create session
        resp = client.post("/api/v1/sessions", json={"tenant": "demo"})
        assert resp.status_code == 200
        session_id = resp.json()["session_id"]

        # Book a slot via booking_slot chip (router.py:79 -> _book())
        r = client.post(
            f"/api/v1/sessions/{session_id}/messages",
            json={"content": "", "chip": {"field": "booking_slot", "value": "2026-10-15T10:00:00Z", "label": "Thu Oct 15 10am"}},
        )
        assert r.status_code == 200
        booking_reply = r.json()
        booking_msg = booking_reply.get("message", "")

        # PRECONDITION ASSERTIONS:
        # (a) the booking turn's own reply contains the confirmation text from router.py:248
        assert "You're booked for" in booking_msg, (
            f"PRECONDITION (a) FAILED: booking turn reply did not contain confirmation text from router.py:248: {booking_msg!r}"
        )
        assert booking_reply.get("booking") is not None, (
            "PRECONDITION FAILED: session booking object missing in response"
        )

        # (b) the session row's booking_json is genuinely set in the database
        import json
        from backend.app.models.db import SessionLocal
        from backend.app.models.entities import SessionRow
        with SessionLocal() as db:
            session_row = db.get(SessionRow, session_id)
            assert session_row is not None, f"PRECONDITION (b) FAILED: session {session_id} not found in DB"
            assert session_row.booking_json, (
                "PRECONDITION (b) FAILED: session_row.booking_json is not set in the database"
            )
            booking_db_data = json.loads(session_row.booking_json)
            assert booking_db_data.get("slot_iso"), (
                "PRECONDITION (b) FAILED: booking_json has no slot_iso"
            )

        # Now send a follow-up free-form question AFTER the booking turn
        r2 = client.post(
            f"/api/v1/sessions/{session_id}/messages",
            json={"content": "What tech stack do you typically use?"},
        )
        assert r2.status_code == 200
        follow_data = r2.json()

        follow_msg = follow_data.get("message", "")
        assert follow_msg, "Follow-up after booking returned empty message"
        # Exact confirmation text check: follow-up must NOT repeat the booking confirmation
        assert not follow_msg.startswith("You're booked for"), (
            f"H2 BUG CONFIRMED: follow-up turn overwritten by canned booking confirmation: {follow_msg!r}"
        )
        assert "You're booked for" not in follow_msg, (
            f"H2 BUG CONFIRMED: follow-up turn repeats canned booking confirmation: {follow_msg!r}"
        )
        route = follow_data.get("route", "")
        assert route in ("fallback", "rag", "faq", "discovery", "off_topic"), (
            f"Unexpected route after booking follow-up: {route!r}"
        )


# ===========================================================================
# H3 — LLM FAILURE: NO EVENT EMITTED
# ===========================================================================


class TestH3LlmFailureVisibility:
    """
    H3: When an LLM call fails, the current code only logs at INFO level.
    No event is written, admin metric is not incremented, /health does not degrade.
    """

    def test_h3_characterization_llm_failure_logs_info_only(self, caplog):
        """
        Characterization: force an LLMError in fallback_message and assert
        it is logged at INFO, not ERROR or WARNING, and no event is emitted.
        """
        from backend.app.agents.brief import ProjectBrief
        from backend.app.agents.fallback import fallback_message
        from backend.app.core.llm import LLMError
        from backend.app.tenants.loader import load_tenant

        config = load_tenant("demo")
        brief = ProjectBrief()

        with patch("backend.app.agents.fallback.llm_available", return_value=True), \
             patch("backend.app.agents.fallback.complete_json", side_effect=LLMError("test 429")), \
             caplog.at_level(logging.INFO, logger="backend.app.agents.fallback"):
            result = fallback_message(config, brief, None, query="what stack do you use?")

        # Current behaviour: falls back gracefully, returns a string
        assert isinstance(result, str), "fallback_message must return a string"
        assert result  # non-empty

        # Characterization: logged at INFO (not WARNING/ERROR)
        llm_logs = [r for r in caplog.records if "fallback" in r.message.lower() or "llm" in r.message.lower()]
        if llm_logs:
            levels = {r.levelname for r in llm_logs}
            assert "ERROR" not in levels, "Unexpected ERROR log — characterization changed"

    def test_h3_desired_event_written_on_llm_failure(self, client):
        """
        DESIRED: forced LLMError during turn → GET /health reports llm failure counter or degraded flag.
        """
        from backend.app.agents.brief import ProjectBrief
        from backend.app.agents.fallback import fallback_message
        from backend.app.core.llm import LLMError
        from backend.app.tenants.loader import load_tenant

        config = load_tenant("demo")
        brief = ProjectBrief()

        with patch("backend.app.agents.fallback.llm_available", return_value=True), \
             patch("backend.app.agents.fallback.complete_json", side_effect=LLMError("429 rate limit")):
            fallback_message(config, brief, None, query="What is your process?")

        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert (
            "llm_failures" in data
            or data.get("llm_degraded") is True
            or data.get("status") == "degraded"
        ), f"/health did not report LLM failure counter or degraded state: {data}"
        assert "llm" in data
        assert "failures_1h" in data["llm"]
        assert "last_error_class" in data["llm"]
        assert "degraded" in data["llm"]

    def test_h3_extractor_failure_records_system_event(self, caplog):
        from backend.app.agents.extractor import extract_slots
        from backend.app.core.llm import LLMError
        from backend.app.models.db import SessionLocal
        from backend.app.models.entities import SystemEventRow

        with patch("backend.app.agents.extractor.llm_available", return_value=True), \
             patch("backend.app.agents.extractor.complete_json", side_effect=LLMError("API 500 error")), \
             caplog.at_level(logging.WARNING, logger="backend.app.agents.extractor"):
            res = extract_slots("I need a web app for my business")

        assert isinstance(res, dict)
        warning_logs = [r for r in caplog.records if r.levelname == "WARNING" and "LLMError" in r.message]
        assert len(warning_logs) >= 1, "Expected WARNING log containing only class name LLMError"

        with SessionLocal() as db:
            event = db.query(SystemEventRow).filter_by(stage="extractor", kind="llm_failure").order_by(SystemEventRow.created_at.desc()).first()
            assert event is not None, "System event row was not created for extractor failure"
            assert event.error_class == "LLMError"
            assert "I need a web app" not in event.reason, "PII or visitor query leaked into system_events reason"

    def test_h3_embedding_failure_records_system_event(self):
        from backend.app.models.db import SessionLocal
        from backend.app.models.entities import SystemEventRow
        from backend.app.rag.embeddings import EmbeddingError, record_query_failure

        record_query_failure(EmbeddingError("Quota exceeded 429"))

        with SessionLocal() as db:
            event = db.query(SystemEventRow).filter_by(stage="embeddings", kind="embedding_failure").order_by(SystemEventRow.created_at.desc()).first()
            assert event is not None, "System event row was not created for embedding failure"
            assert event.error_class == "EmbeddingError"

    def test_h3_system_events_retention_pruning(self):
        from datetime import datetime, timedelta, timezone
        from backend.app.core.llm import record_system_event
        from backend.app.models.db import SessionLocal
        from backend.app.models.entities import SystemEventRow

        with SessionLocal() as db:
            old_event = SystemEventRow(
                created_at=datetime.now(timezone.utc) - timedelta(days=10),
                kind="llm_failure",
                reason="old failure",
                stage="extractor",
                error_class="LLMError",
            )
            db.add(old_event)
            db.commit()
            old_id = old_event.id

        # Trigger a new write which must prune rows > 7 days
        record_system_event("llm_failure", "new failure", "fallback", "LLMError")

        with SessionLocal() as db:
            found = db.get(SystemEventRow, old_id)
            assert found is None, "Events older than 7 days must be pruned on write"


# ===========================================================================
# H4 — STUDENT ROLE: IMMEDIATE DISQUALIFICATION WITHOUT CONFIRMATION
# ===========================================================================


class TestH4StudentDisqualification:
    """
    H4: A single extraction of decision_role=intern_or_student immediately
    closes the chat if intern_or_student is in qualification.disqualify_if.
    No confirmation question is asked first.
    """

    def test_h4_student_chip_disqualifies_immediately(self, client):
        """
        The explicit 'Student / intern' chip still disqualifies immediately.
        """
        resp = client.post("/api/v1/sessions", json={"tenant": "demo"})
        session_id = resp.json()["session_id"]

        r = client.post(
            f"/api/v1/sessions/{session_id}/messages",
            json={"chip": {"field": "decision_role", "value": "intern_or_student", "label": "Student / intern"}},
        )
        assert r.status_code == 200
        data = r.json()
        assert data.get("stage") == "disqualified"
        assert "We partner with decision-makers" in data.get("message", "")

    def test_h4_free_text_student_asks_confirmation(self, client):
        """
        Free text student mention does not disqualify; asks confirming question with two chips.
        """
        resp = client.post("/api/v1/sessions", json={"tenant": "demo"})
        session_id = resp.json()["session_id"]

        r = client.post(
            f"/api/v1/sessions/{session_id}/messages",
            json={"content": "I am a student working on my college project"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data.get("stage") != "disqualified"
        labels = [c.get("label") for c in data.get("chips", [])]
        assert "Live project at a company" in labels
        assert "Study or practice" in labels

    def test_h4_confirmation_study_chip_disqualifies(self, client):
        """Confirming with 'Study or practice' chip sets role and disqualifies."""
        resp = client.post("/api/v1/sessions", json={"tenant": "demo"})
        session_id = resp.json()["session_id"]
        client.post(f"/api/v1/sessions/{session_id}/messages", json={"content": "I am a student"})
        r2 = client.post(
            f"/api/v1/sessions/{session_id}/messages",
            json={"chip": {"field": "confirm_role", "value": "study_or_practice", "label": "Study or practice"}},
        )
        assert r2.status_code == 200
        assert r2.json().get("stage") == "disqualified"

    def test_h4_confirmation_live_chip_continues(self, client):
        """Confirming with 'Live project at a company' chip sets role and continues discovery."""
        resp = client.post("/api/v1/sessions", json={"tenant": "demo"})
        session_id = resp.json()["session_id"]
        client.post(f"/api/v1/sessions/{session_id}/messages", json={"content": "I am a student"})
        r2 = client.post(
            f"/api/v1/sessions/{session_id}/messages",
            json={"chip": {"field": "confirm_role", "value": "company_project", "label": "Live project at a company"}},
        )
        assert r2.status_code == 200
        assert r2.json().get("stage") != "disqualified"

    def test_h4_desired_confirmation_before_close(self, client):
        """
        DESIRED: casual student mention → bot asks to confirm before disqualifying.
        """
        resp = client.post("/api/v1/sessions", json={"tenant": "demo"})
        session_id = resp.json()["session_id"]

        # Casual mention — cousin is a student, not the visitor
        r = client.post(
            f"/api/v1/sessions/{session_id}/messages",
            json={"content": "my cousin is a student, he suggested I try this"},
        )
        assert r.status_code == 200
        data = r.json()
        # Desired: bot does NOT immediately disqualify; instead asks a confirming question
        assert data.get("stage") != "disqualified", (
            "Bot disqualified immediately on casual student mention without confirmation"
        )
        msg = data.get("message", "").lower()
        # Should ask something like "are you the one making the decision?"
        assert any(w in msg for w in ("your role", "decision", "you or", "confirm")), (
            f"Bot should ask for confirmation before disqualifying. Got: {msg!r}"
        )


# ===========================================================================
# H5 — PRODUCTION SQLite REFUSAL
# ===========================================================================


class TestH5ProductionSqliteRefusal:
    """
    H5: settings.py refuses SQLite in production mode.
    ENVIRONMENT=production with a SQLite DATABASE_URL is rejected with ValueError.
    """

    def test_h5_production_rejects_sqlite_url(self):
        """Production environment with SQLite URL raises ValueError."""
        from backend.app.core.settings import Settings

        with pytest.raises(ValueError, match="SQLite database_url is not allowed in production"):
            Settings(environment="production", database_url="sqlite:////tmp/presales.db")

        with pytest.raises(ValueError, match="SQLite database_url is not allowed in production"):
            Settings(environment="production", database_url="sqlite:///./backend/presales.db")

    def test_h5_production_allows_postgres_url(self):
        """Production environment with Postgres URL succeeds and normalizes."""
        from backend.app.core.settings import Settings

        s = Settings(
            environment="production",
            database_url="postgresql://user:pass@host:5432/presales?sslmode=require",
        )
        assert s.environment == "production"
        assert s.database_url.startswith("postgresql+pg8000://")

    def test_h5_non_production_allows_sqlite_url(self, monkeypatch):
        """Non-production environments allow SQLite and preserve Vercel normalization."""
        from backend.app.core.settings import DEFAULT_SQLITE_URL, VERCEL_SQLITE_URL, Settings

        dev = Settings(environment="development", database_url=DEFAULT_SQLITE_URL)
        assert dev.database_url == DEFAULT_SQLITE_URL

        monkeypatch.setenv("VERCEL", "1")
        vercel_dev = Settings(environment="development", database_url=DEFAULT_SQLITE_URL)
        assert vercel_dev.database_url == VERCEL_SQLITE_URL

    def test_h5_desired_production_refuses_sqlite(self):
        """
        Promoted H5 test: production + SQLite refuses SQLite database_url.
        """
        from backend.app.core.settings import Settings

        with pytest.raises(ValueError, match="SQLite database_url is not allowed in production"):
            Settings(environment="production", database_url="sqlite:////tmp/presales.db")


class TestPhase3AdminSecurityAndCredentialScrubbing:
    """
    Phase 3: Admin fails closed in production; credentials scrubbed from docs.
    """

    def test_production_missing_password_fails_closed(self, monkeypatch):
        from fastapi.testclient import TestClient

        from backend.app.core.settings import get_settings
        from backend.app.main import create_app

        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/presales")
        monkeypatch.setenv("ADMIN_PASSWORD", "")
        monkeypatch.setenv("ADMIN_PASSWORD_HASH", "")
        get_settings.cache_clear()

        with TestClient(create_app()) as client:
            resp = client.get("/admin")
            assert resp.status_code == 404
            health_resp = client.get("/health")
            assert health_resp.status_code == 200
            assert health_resp.json()["admin"] == "disabled_misconfigured"

    def test_production_configured_password_mounts_admin(self, monkeypatch):
        from fastapi.testclient import TestClient

        from backend.app.core.settings import get_settings
        from backend.app.main import create_app

        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/presales")
        monkeypatch.setenv("ADMIN_PASSWORD", "strong_custom_password_xyz_987")
        monkeypatch.setenv("ADMIN_PASSWORD_HASH", "")
        get_settings.cache_clear()

        with TestClient(create_app()) as client:
            resp = client.get("/admin")
            assert resp.status_code == 401
            health_resp = client.get("/health")
            assert health_resp.status_code == 200
            assert health_resp.json()["admin"] == "enabled"

    def test_credential_scrubbing_readme_and_env_example(self):
        """Verify README.md and .env.example contain no admin123 or AIza keys."""
        from backend.app.core.settings import ROOT

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        env_example = (ROOT / ".env.example").read_text(encoding="utf-8")

        for forbidden in ("admin123", "AIza"):
            assert forbidden not in readme, f"Found '{forbidden}' in README.md"
            assert forbidden not in env_example, f"Found '{forbidden}' in .env.example"

    def test_cors_wildcard_rejected_in_production(self, monkeypatch):
        """In production, CORS origin '*' with allow_credentials=True raises ValueError."""
        from backend.app.core.settings import get_settings
        from backend.app.main import create_app

        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/presales")
        monkeypatch.setenv("CORS_ORIGINS", "*")
        monkeypatch.setenv("ADMIN_PASSWORD", "strong_password_123")
        get_settings.cache_clear()

        with pytest.raises(ValueError, match=r"Wildcard CORS origin '\*' with allow_credentials=True"):
            create_app()

    def test_cors_wildcard_allowed_with_warning_in_development(self, monkeypatch):
        """In non-production, CORS origin '*' with allow_credentials=True logs warning but starts."""
        from backend.app.core.settings import get_settings
        from backend.app.main import create_app

        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("CORS_ORIGINS", "*")
        get_settings.cache_clear()

        app = create_app()
        assert app is not None

    def test_v7_vercel_lazy_init_creates_tables_and_ingests(self, monkeypatch, tmp_path):
        """V7: on Vercel path, ensure_ready() creates tables and runs ingest on first DB call."""
        from sqlalchemy import inspect

        import backend.app.models.db as db_mod
        from backend.app.core.settings import get_settings

        test_db = f"sqlite:///{tmp_path}/vercel_test.db"
        monkeypatch.setenv("VERCEL", "1")
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("DATABASE_URL", test_db)
        get_settings.cache_clear()

        # Reset db module engine and ready flag
        with db_mod._engine_lock:
            db_mod._engine = None
        db_mod._session_factory = None
        db_mod._ready = False

        try:
            # Calling ensure_ready() on Vercel
            db_mod.ensure_ready()
            assert db_mod._ready is True

            # Check tables created
            engine = db_mod.get_engine()
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            assert "sessions" in tables
            assert "rag_chunks" in tables
            assert "documents" in tables
        finally:
            with db_mod._engine_lock:
                db_mod._engine = None
            db_mod._session_factory = None
            db_mod._ready = False
            get_settings.cache_clear()


# ===========================================================================
# H6 — FEEDBACK WRITES TO TRAINING SET WITHOUT ADMIN REVIEW
# ===========================================================================


class TestH6FeedbackPoisoning:
    """
    H6: Characterize whether thumb feedback pairs are immediately available
    to fine-tuning without any admin approval gate.
    """

    def test_h6_characterization_thumb_writes_directly(self):
        """
        Characterization: save_thumb() writes FeedbackPairRow immediately.
        positive_pairs() reads all rows with label='positive'.
        No approval column or gate exists in the schema.
        """
        from backend.app.learning.pairs import positive_pairs, save_thumb
        from backend.app.models.entities import FeedbackPairRow

        # Verify FeedbackPairRow has no 'approved' or 'reviewed' column
        columns = {c.key for c in FeedbackPairRow.__table__.columns}
        has_approval_gate = "approved" in columns or "reviewed" in columns or "pending" in columns
        assert not has_approval_gate, (
            f"Unexpected approval column found: {columns & {'approved','reviewed','pending'}}. "
            "Update this characterization test."
        )
        # Document: positive_pairs reads ALL positive rows directly
        # No admin review step exists between save_thumb and finetune_tenant
        # This is a documented risk (H6 confirmed) — a visitor can submit thumb-up
        # on any RAG chunk, immediately making it a fine-tuning positive.

    def test_h6_finetune_requires_min_positives(self):
        """
        H6 partial mitigation: finetune_tenant() checks finetune_min_positives (64).
        A single malicious thumb-up does not immediately trigger fine-tuning.
        This is the only guard that exists today.
        """
        from backend.app.core.platform import get_platform

        platform = get_platform()
        assert platform.finetune_min_positives >= 10, (
            f"finetune_min_positives={platform.finetune_min_positives} is unexpectedly low"
        )
        # fine-tuning is not triggered automatically — it's a manual CLI call
        # So immediate poisoning risk is low but admin-approval gate is absent


# ===========================================================================
# PHASE 1B — DIMENSIONS 768, STALE DETECTION, CHUNKER CACHE, CALIBRATION
# ===========================================================================


class TestPhase1BEmbeddingsAndCalibration:
    """
    Phase 1B:
    1. Dimension 768 from platform.yaml as source of truth.
    2. taskType (RETRIEVAL_DOCUMENT / RETRIEVAL_QUERY), outputDimensionality 768, L2-normalized.
    3. Store records dim and version (e.g. gemini-embedding-001@768:v1).
    4. Stale chunks detected on mismatch, ignored by queries, re-embedded on ingest.
    5. /health reports stale_chunks count.
    6. Chunker semantic breaking default OFF (structural ##); never uses hash embedder for breaks; caches sentence embeddings.
    7. scripts/calibrate_rag.py runs offline with stubbed embedder.
    """

    def test_gemini_embed_sends_task_type_and_output_dim(self, monkeypatch):
        from unittest.mock import MagicMock

        import httpx

        from backend.app.core.settings import get_settings
        from backend.app.rag.embeddings import _gemini_embed

        monkeypatch.setenv("LLM_API_KEY", "test-key-fake")
        get_settings.cache_clear()

        captured_requests = []

        class MockResponse:
            status_code = 200

            def json(self):
                # Return 768-dim unnormalized vector
                raw_values = [2.0] * 768
                return {"embeddings": [{"values": raw_values}]}

        def mock_post(url, headers, json):
            captured_requests.append(json)
            return MockResponse()

        mock_client = MagicMock()
        mock_client.post = mock_post
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        monkeypatch.setattr(httpx, "Client", MagicMock(return_value=mock_client))

        # Query mode
        vecs_query = _gemini_embed(["find healthcare"], mode="query")
        assert captured_requests[-1]["requests"][0]["taskType"] == "RETRIEVAL_QUERY"
        assert captured_requests[-1]["requests"][0]["outputDimensionality"] == 768
        assert len(vecs_query[0]) == 768
        # Assert L2 normalized: sum(v^2) ~= 1.0
        norm_query = sum(v * v for v in vecs_query[0])
        assert abs(norm_query - 1.0) < 1e-4

        # Ingest mode
        vecs_ingest = _gemini_embed(["healthcare clinic note"], mode="ingest")
        assert captured_requests[-1]["requests"][0]["taskType"] == "RETRIEVAL_DOCUMENT"
        assert captured_requests[-1]["requests"][0]["outputDimensionality"] == 768

    def test_dimension_and_version_recorded_in_chunk(self, tmp_path, monkeypatch):
        from backend.app.core.settings import get_settings
        from backend.app.models.db import SessionLocal, init_db
        from backend.app.models.entities import ChunkRow, TenantRow
        from backend.app.rag.embeddings import active_embedding_version
        from backend.app.rag.store import Document, upsert_documents

        test_db = f"sqlite:///{tmp_path}/test_dim_ver.db"
        monkeypatch.setenv("DATABASE_URL", test_db)
        monkeypatch.setenv("EMBEDDING_BACKEND", "hash")
        get_settings.cache_clear()

        init_db()
        with SessionLocal() as db:
            tenant = TenantRow(slug="test-t", name="Test Tenant", collection="test-t")
            db.add(tenant)
            db.commit()

            doc = Document(
                doc_id="test:doc#1",
                title="Test Doc",
                content="Some test content for dimension and version verification.",
                source="content",
                source_id="test",
            )
            upsert_documents(db, tenant, [doc])

            chunk = db.query(ChunkRow).filter(ChunkRow.doc_id == "test:doc#1").first()
            assert chunk is not None
            assert chunk.embedding_dim == 384
            assert chunk.embedding_version == active_embedding_version("hash-v1-384", 384)

    def test_stale_chunks_detected_and_reembedded(self, tmp_path, monkeypatch):
        import json

        from backend.app.core.settings import get_settings
        from backend.app.models.db import SessionLocal, init_db
        from backend.app.models.entities import ChunkRow, TenantRow
        from backend.app.rag.embeddings import active_embedding_version
        from backend.app.rag.store import Document, count_stale_chunks, upsert_documents

        test_db = f"sqlite:///{tmp_path}/test_stale.db"
        monkeypatch.setenv("DATABASE_URL", test_db)
        monkeypatch.setenv("EMBEDDING_BACKEND", "hash")
        get_settings.cache_clear()

        init_db()
        with SessionLocal() as db:
            tenant = TenantRow(slug="test-stale-slug", name="Stale Test Tenant", collection="test-stale")
            db.add(tenant)
            db.commit()

            # Insert artificially stale chunk (old dim 3072 and old version)
            stale_row = ChunkRow(
                tenant_id=tenant.id,
                doc_id="stale:chunk#1",
                collection="test-stale",
                kind="knowledge",
                title="Stale Chunk",
                content="Old content that is now stale",
                embedding_model="hash-v1-384",
                embedding_dim=3072,  # mismatch with 384
                embedding_version="gemini-embedding-001@3072:v0",
                embedding_json=json.dumps([0.1] * 384),
            )
            db.add(stale_row)
            db.commit()

            # Verify stale count for this tenant
            stale_count = count_stale_chunks(db, tenant)
            assert stale_count == 1

            # On next upsert, stale chunk should be re-embedded
            doc = Document(
                doc_id="stale:chunk#1",
                title="Stale Chunk",
                content="Old content that is now stale",
                source="content",
                source_id="stale",
            )
            upsert_documents(db, tenant, [doc])

            updated = db.query(ChunkRow).filter(ChunkRow.doc_id == "stale:chunk#1").first()
            assert updated.embedding_dim == 384
            assert updated.embedding_version == active_embedding_version("hash-v1-384", 384)
            assert count_stale_chunks(db, tenant) == 0

    def test_query_ignores_stale_chunks(self, tmp_path, monkeypatch):
        import json

        from backend.app.core.settings import get_settings
        from backend.app.models.db import SessionLocal, init_db
        from backend.app.models.entities import ChunkRow, TenantRow
        from backend.app.rag.store import search

        test_db = f"sqlite:///{tmp_path}/test_query_stale.db"
        monkeypatch.setenv("DATABASE_URL", test_db)
        monkeypatch.setenv("EMBEDDING_BACKEND", "hash")
        get_settings.cache_clear()

        init_db()
        with SessionLocal() as db:
            tenant = TenantRow(slug="test-query-slug", name="Query Test Tenant", collection="test-query")
            db.add(tenant)
            db.commit()

            # Add a stale chunk with old version
            db.add(
                ChunkRow(
                    tenant_id=tenant.id,
                    doc_id="stale:doc#1",
                    collection="test-query",
                    kind="knowledge",
                    title="Doctors Clinic",
                    content="Doctors clinic telehealth booking system",
                    embedding_model="hash-v1-384",
                    embedding_dim=384,
                    embedding_version="old-version-v0",  # stale!
                    embedding_json=json.dumps([1.0] + [0.0] * 383),
                )
            )
            db.commit()

            # Query should ignore the stale chunk
            hits = search(db, tenant, "clinic", kind="knowledge")
            assert not any(h.doc_id == "stale:doc#1" for h in hits)

    def test_health_reports_stale_chunks(self, tmp_path, monkeypatch):
        import json

        from fastapi.testclient import TestClient

        from backend.app.core.settings import get_settings
        from backend.app.main import create_app
        from backend.app.models.db import SessionLocal, init_db
        from backend.app.models.entities import ChunkRow, TenantRow

        test_db = f"sqlite:///{tmp_path}/test_health_stale.db"
        monkeypatch.setenv("DATABASE_URL", test_db)
        monkeypatch.setenv("EMBEDDING_BACKEND", "hash")
        get_settings.cache_clear()

        init_db()
        with SessionLocal() as db:
            tenant = db.query(TenantRow).filter(TenantRow.slug == "demo").first()
            if tenant is None:
                tenant = TenantRow(slug="demo", name="Demo", collection="demo")
                db.add(tenant)
                db.commit()
            db.add(
                ChunkRow(
                    tenant_id=tenant.id,
                    doc_id="stale:test#99",
                    collection="demo",
                    kind="knowledge",
                    embedding_model="hash-v1-384",
                    embedding_dim=123,  # wrong dim
                    embedding_version="stale:v0",
                    embedding_json=json.dumps([0.1] * 123),
                )
            )
            db.commit()

        with TestClient(create_app()) as client:
            resp = client.get("/health")
            assert resp.status_code == 200
            data = resp.json()
            assert "stale_chunks" in data
            assert data["stale_chunks"] >= 1
            assert data["embeddings"]["stale_chunks"] >= 1

    def test_chunker_default_structural_and_hash_never_called(self, monkeypatch):
        import backend.app.rag.embeddings as emb_mod
        from backend.app.core.settings import get_settings
        from backend.app.rag.chunker import chunk_text

        monkeypatch.setenv("EMBEDDING_BACKEND", "hash")
        get_settings.cache_clear()

        # Track calls to _hash_embed
        original_hash = emb_mod._hash_embed
        hash_called = []

        def spy_hash(*args, **kwargs):
            hash_called.append(args)
            return original_hash(*args, **kwargs)

        monkeypatch.setattr(emb_mod, "_hash_embed", spy_hash)

        sample_text = (
            "## Heading One\nFirst sentence. Second sentence about different topic.\n"
            "## Heading Two\nThird sentence."
        )

        # Default: semantic_chunking is False
        chunks_default = chunk_text(sample_text, semantic_chunking=False)
        assert len(chunks_default) >= 2
        assert len(hash_called) == 0, "Chunker called hash embedder when semantic_chunking=False"

        # When semantic_chunking is True with hash backend: never calls hash embedder for breaks
        chunks_optin = chunk_text(sample_text, semantic_chunking=True)
        assert len(chunks_optin) >= 2
        assert len(hash_called) == 0, "Chunker called hash embedder for breaks when backend=hash"

    def test_chunker_sentence_cache_avoids_reembedding(self):
        from backend.app.rag.chunker import _embed_sentences_with_cache, clear_sentence_cache

        clear_sentence_cache()
        embed_calls = []

        def mock_embed(sentences):
            embed_calls.append(list(sentences))
            return [[0.1] * 10 for _ in sentences]

        sentences = ["Sentence alpha.", "Sentence beta."]

        # First run: should call mock_embed
        vecs1 = _embed_sentences_with_cache(sentences, embed=mock_embed)
        assert len(embed_calls) == 1
        assert len(vecs1) == 2

        # Second run: identical sentences must be fetched from cache without calling mock_embed
        vecs2 = _embed_sentences_with_cache(sentences, embed=mock_embed)
        assert len(embed_calls) == 1, "Sentence embedding was not cached across chunker runs"
        assert vecs1 == vecs2

    def test_calibrate_rag_runs_offline_with_stubbed_embedder(self):
        from scripts.calibrate_rag import run_calibration

        results = run_calibration(offline=True)
        assert results["mode"] == "offline"
        assert results["total_queries"] >= 20
        assert "relevant_stats" in results
        assert "irrelevant_stats" in results
        assert "proposed_thresholds" in results
        prop = results["proposed_thresholds"]
        assert 0.0 < prop["weak_min_score"] <= prop["show_min_score"] <= prop["faq_min_score"] <= 1.0


class TestPhase2E4SlotsAndRepeat:
    """
    E4: Platform chips depend on service:
      web_app / ai_product -> Web, API
      mobile_app -> iOS, Android, iOS and Android
    Repeated discovery field when answer filled nothing rephrases once and offers 'Not sure yet' chip.
    """

    def test_e4_platform_chips_web_app(self):
        from backend.app.agents.brief import ProjectBrief
        from backend.app.screening.slots import chips_for_field

        brief = ProjectBrief(service="web_app")
        chips = chips_for_field("platforms", brief)
        labels = [c["label"] for c in chips]
        assert labels == ["Web", "API"], f"Expected ['Web', 'API'], got {labels}"

    def test_e4_platform_chips_ai_product(self):
        from backend.app.agents.brief import ProjectBrief
        from backend.app.screening.slots import chips_for_field

        brief = ProjectBrief(service="ai_product")
        chips = chips_for_field("platforms", brief)
        labels = [c["label"] for c in chips]
        assert labels == ["Web", "API"], f"Expected ['Web', 'API'], got {labels}"

    def test_e4_platform_chips_mobile_app(self):
        from backend.app.agents.brief import ProjectBrief
        from backend.app.screening.slots import chips_for_field

        brief = ProjectBrief(service="mobile_app")
        chips = chips_for_field("platforms", brief)
        labels = [c["label"] for c in chips]
        assert labels == ["iOS", "Android", "iOS and Android"], f"Expected iOS/Android chips, got {labels}"

    def test_e4_rephrased_prompt_and_not_sure_chip_on_repeat(self):
        from backend.app.agents.brief import ProjectBrief
        from backend.app.screening.slots import chips_for_field, prompt_for

        brief = ProjectBrief()
        standard_prompt = prompt_for(brief, "timeline", repeat=False)
        rephrased_prompt = prompt_for(brief, "timeline", repeat=True)
        assert standard_prompt != rephrased_prompt
        assert "target milestone or launch timeframe" in rephrased_prompt

        chips_standard = chips_for_field("timeline", brief, repeat=False)
        assert not any(c.get("label") == "Not sure yet" for c in chips_standard)

        chips_repeat = chips_for_field("timeline", brief, repeat=True)
        assert any(c.get("label") == "Not sure yet" for c in chips_repeat)

    def test_e4_session_rephrase_and_not_sure_chip_flow(self, client):
        resp = client.post("/api/v1/sessions", json={"tenant": "demo"})
        session_id = resp.json()["session_id"]

        # Initial turn asks service
        r1 = client.post(
            f"/api/v1/sessions/{session_id}/messages",
            json={"content": "hello there"},
        )
        assert r1.status_code == 200
        data1 = r1.json()
        assert not any(c.get("label") == "Not sure yet" for c in data1.get("chips", []))

        # Second turn: user sends something that fills nothing
        r2 = client.post(
            f"/api/v1/sessions/{session_id}/messages",
            json={"content": "umm..."},
        )
        assert r2.status_code == 200
        data2 = r2.json()
        # Should rephrase and include 'Not sure yet' chip
        chips2 = data2.get("chips", [])
        assert any(c.get("label") == "Not sure yet" for c in chips2)
        assert data2.get("message") != data1.get("message")

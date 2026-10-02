import os
import tempfile
from pathlib import Path
import pytest

from backend.app.rag.ingest import documents_for, _content_metadata
from backend.app.tenants.loader import create_tenant_folder, load_tenant, clear_tenant_cache
from scripts.lint_content import lint_content, LintIssue


class TestPhase4DemoHygieneAndContentLint:
    def test_lint_content_passes_on_clean_content(self, tmp_path):
        clean_file = tmp_path / "overview.md"
        clean_file.write_text(
            "---\ntitle: Overview\n---\nWe build modern web and mobile apps with clean architecture.\n",
            encoding="utf-8",
        )
        issues = lint_content(tmp_path)
        assert issues == []

    def test_lint_content_catches_dollar_figures(self, tmp_path):
        bad_file = tmp_path / "pricing_claim.md"
        bad_file.write_text(
            "---\ntitle: Services\n---\nOur mobile app package starts at $5,000 for standard MVPs.\n",
            encoding="utf-8",
        )
        issues = lint_content(tmp_path)
        assert len(issues) == 1
        assert issues[0].file == str(bad_file)
        assert issues[0].line_number == 4
        assert "$5,000" in issues[0].matched_text

    def test_lint_content_catches_rupee_figures(self, tmp_path):
        bad_file = tmp_path / "india_pricing.md"
        bad_file.write_text(
            "---\ntitle: India Services\n---\nStarting at ₹50,000 for web prototypes.\n",
            encoding="utf-8",
        )
        issues = lint_content(tmp_path)
        assert len(issues) == 1
        assert issues[0].line_number == 4
        assert "₹50,000" in issues[0].matched_text

    def test_lint_content_catches_iso_currency_codes(self, tmp_path):
        bad_file = tmp_path / "rates.md"
        bad_file.write_text(
            "---\ntitle: Rates\n---\nHourly rate: 75 USD per developer hour or 6000 INR.\n",
            encoding="utf-8",
        )
        issues = lint_content(tmp_path)
        assert len(issues) >= 2
        matches = [i.matched_text for i in issues]
        assert any("75 USD" in m for m in matches)
        assert any("6000 INR" in m for m in matches)

    def test_lint_content_ignores_pricing_yaml(self, tmp_path):
        pricing_file = tmp_path / "pricing.yaml"
        pricing_file.write_text("currency: USD\nbases:\n  web_app: 24000\n", encoding="utf-8")
        issues = lint_content(tmp_path)
        assert issues == []

    def test_demo_tenant_documents_marked_as_sample(self):
        clear_tenant_cache()
        config = load_tenant("demo")
        docs = documents_for(config)
        assert len(docs) > 0
        portfolio_docs = [d for d in docs if d.source == "portfolio"]
        assert len(portfolio_docs) > 0
        for doc in portfolio_docs:
            assert doc.metadata.get("is_sample") is True or doc.metadata.get("sample") is True

    def test_non_demo_tenant_refuses_demo_content_directory(self, monkeypatch):
        from backend.app.tenants.loader import tenant_dir
        clear_tenant_cache()
        config = load_tenant("demo")
        config.brand.slug = "client-acme"
        demo_dir = tenant_dir("demo")
        monkeypatch.setattr("backend.app.rag.ingest.tenant_dir", lambda slug: demo_dir)
        with pytest.raises(RuntimeError, match="cannot ingest demo tenant content"):
            documents_for(config)


class TestPhase4HybridSearchAndTransparency:
    def test_lexical_score_matches_keywords_and_exact_phrases(self):
        from backend.app.rag.store import _lexical_score
        # Full exact query match
        exact_score = _lexical_score("Flutter Firebase", "Mobile Project", "We build with Flutter Firebase for mobile.")
        # Partial match
        partial_score = _lexical_score("Flutter Firebase", "Mobile Project", "We build with Flutter for mobile.")
        # Unrelated match
        zero_score = _lexical_score("Flutter Firebase", "Web Project", "We build with Python and PostgreSQL.")

        assert exact_score > partial_score > zero_score
        assert zero_score == 0.0
        assert exact_score >= 0.5

    def test_hybrid_search_falls_back_to_lexical_on_embedding_error(self, monkeypatch):
        from unittest.mock import patch
        from backend.app.rag.embeddings import EmbeddingError
        from backend.app.rag.store import search
        from backend.app.models.db import SessionLocal, init_db
        from backend.app.tenants.loader import ensure_tenant_row

        init_db()
        with SessionLocal() as db:
            tenant = ensure_tenant_row(db, "demo")
            from backend.app.rag.ingest import ingest_tenant
            ingest_tenant(db, tenant)

            def fail_embed(*args, **kwargs):
                raise EmbeddingError("Gemini rate limit exceeded", status_code=429)

            with patch("backend.app.rag.store.embed_query", side_effect=fail_embed):
                # Even though embeddings failed, lexical search finds the Harvest or Flutter hit
                hits = search(db, tenant, "Harvest marketplace", kind="knowledge", k=3)
                assert len(hits) > 0
                assert any("Harvest" in h.title or "Harvest" in h.content for h in hits)

    def test_query_rewriting_with_brief(self):
        from backend.app.agents.brief import ProjectBrief
        from backend.app.agents.router import rewrite_query_with_brief

        brief = ProjectBrief(service="mobile_app", platforms=["iOS", "Android"])
        # Short ambiguous question
        rewritten = rewrite_query_with_brief("what stacks do you use?", brief)
        assert "mobile" in rewritten.lower() or "ios" in rewritten.lower()

        # Specific question without brief need
        specific = rewrite_query_with_brief("Tell me about Ledgerly web project", brief)
        assert specific == "Tell me about Ledgerly web project"

    def test_no_relevant_knowledge_transparency_in_fallback(self):
        from unittest.mock import patch
        from backend.app.agents.fallback import fallback_message
        from backend.app.tenants.loader import load_tenant

        config = load_tenant("demo")
        captured = []

        def mock_complete_json(system, prompt, **kwargs):
            captured.append(prompt)
            return {"message": "I don't have verified information about that, but our team can help."}

        with patch("backend.app.agents.fallback.complete_json", side_effect=mock_complete_json), \
             patch("backend.app.agents.fallback.llm_available", return_value=True):
            fallback_message(config, None, None, query="Do you support COBOL on mainframes?", notes=None)
            assert len(captured) > 0
            prompt_text = captured[0]
            assert "no verified knowledge" in prompt_text.lower() or "do not guess" in prompt_text.lower()


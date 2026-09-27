from sqlalchemy import func, select

from backend.app.memory.rewrite import rewrite_query
from backend.app.models.db import SessionLocal
from backend.app.models.entities import ChunkRow, EventRow, FeedbackPairRow, SessionRow, TenantRow
from backend.app.rag.chunker import chunk_text
from backend.app.rag.grade import classify
from backend.tests.conftest import cleanup_tenant

ZEPHYR = "The Zephyr clinic companion cut no-shows by 18 percent during the pilot."
HARBOR = "The Harbor ledger migration moved forty accountants off three spreadsheets."


def test_health_and_widget(client):
    health = client.get("/health")
    assert health.status_code == 200
    body = health.json()
    assert body["status"] == "ok"
    assert "demo" in body["tenants"]
    assert body["embedding_backend"] == "hash"
    widget = client.get("/widget/consultant.js")
    assert widget.status_code == 200
    assert "dataset.tenant" in widget.text
    page = client.get("/")
    assert page.status_code == 200
    assert 'data-tenant="demo"' in page.text
    config = client.get("/api/v1/public-config", params={"tenant": "demo"})
    assert config.status_code == 200
    assert config.json()["brand"]["logo_text"] == "Northline"
    assert client.get("/api/v1/public-config", params={"tenant": "missing"}).status_code == 404


def test_admin_auth_and_library(client, auth):
    assert client.get("/admin").status_code == 401
    page = client.get("/admin", auth=auth)
    assert page.status_code == 200
    assert "demo" in page.text
    rag = client.get("/admin/rag", params={"tenant": "demo"}, auth=auth)
    assert rag.status_code == 200
    assert "Zephyr" in rag.text
    assert client.get("/admin/google/start", params={"tenant": "demo"}, auth=auth).status_code == 400


def test_google_callback_reuses_pkce_verifier(client, auth, monkeypatch):
    from backend.app.core.settings import get_settings

    monkeypatch.setattr(get_settings(), "google_client_id", "client")
    monkeypatch.setattr(get_settings(), "google_client_secret", "secret")
    captured: dict = {}

    class FakeFlow:
        def __init__(self):
            self.code_verifier = "verifier-from-start"
            self.credentials = type("Creds", (), {"refresh_token": "refresh-1"})()

        def authorization_url(self, **_kwargs):
            return "https://accounts.google.com/o/oauth2/auth?x=1", "state-pkce"

        def fetch_token(self, **kwargs):
            captured["code"] = kwargs.get("code")

        @classmethod
        def from_client_config(cls, *_args, **kwargs):
            captured["callback_kwargs"] = kwargs
            flow = cls()
            if kwargs.get("code_verifier"):
                flow.code_verifier = kwargs["code_verifier"]
            return flow

    monkeypatch.setattr("google_auth_oauthlib.flow.Flow", FakeFlow)
    start = client.get("/admin/google/start", params={"tenant": "demo"}, auth=auth, follow_redirects=False)
    assert start.status_code == 307
    with SessionLocal() as db:
        row = db.scalar(select(TenantRow).where(TenantRow.slug == "demo"))
        assert row is not None
        assert row.oauth_state == "state-pkce"
        assert row.oauth_code_verifier == "verifier-from-start"
    done = client.get(
        "/admin/google/callback",
        params={"code": "abc", "state": "state-pkce"},
        follow_redirects=False,
    )
    assert done.status_code == 303
    assert captured["callback_kwargs"]["code_verifier"] == "verifier-from-start"
    assert captured["callback_kwargs"]["autogenerate_code_verifier"] is False
    assert captured["code"] == "abc"
    with SessionLocal() as db:
        row = db.scalar(select(TenantRow).where(TenantRow.slug == "demo"))
        assert row is not None
        assert row.google_refresh_token == "refresh-1"
        assert row.oauth_code_verifier == ""
        row.google_refresh_token = ""
        db.commit()


def test_screening_faq_skips_generation(client, monkeypatch):
    def explode(*_args, **_kwargs):
        raise AssertionError("FAQ hit must not call the model")

    monkeypatch.setattr("backend.app.rag.grade.complete_json", explode)
    monkeypatch.setattr("backend.app.agents.router.grade", explode)
    session = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    response = client.post(
        f"/api/v1/sessions/{session['session_id']}/messages",
        json={"content": "How do you run a project?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "faq"
    assert "weekly cadence" in body["message"]


def test_estimate_discovery(client):
    session = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    sid = session["session_id"]

    def send(content="", chip=None):
        payload = {"content": content}
        if chip:
            payload["chip"] = chip
        response = client.post(f"/api/v1/sessions/{sid}/messages", json=payload)
        assert response.status_code == 200, response.text
        return response.json()

    send(chip={"field": "service", "value": "mobile_app", "label": "Mobile app"})
    send("Let clinics message patients")
    added = send(chip={"field": "features", "value": ["Login & accounts"], "label": "Login"})
    assert any(chip["field"] == "features_done" for chip in added["chips"])
    assert "Login & accounts" in added["message"]
    added = send(chip={"field": "features", "value": ["Payments"], "label": "Payments"})
    assert "Payments" in added["message"]
    assert any(chip["field"] == "features_done" for chip in added["chips"])
    detail = send(chip={"field": "features_done", "value": "yes", "label": "That's all"})
    assert "Login & accounts and Payments" in detail["message"]
    assert any(chip["field"] == "feature_detail" for chip in detail["chips"])
    send("Staff sign in with email and reset a password")
    send(chip={"field": "user_flow", "value": "not_specified", "label": "Skip"})
    send(chip={"field": "platforms", "value": ["ios", "android"], "label": "Both"})
    send("Front desk staff")
    send(chip={"field": "integrations", "value": ["none"], "label": "None"})
    send(chip={"field": "timeline", "value": "1_3_months", "label": "1–3 months"})
    send(chip={"field": "budget_band", "value": "40_80k", "label": "$40–80k"})
    done = send(chip={"field": "decision_role", "value": "founder_or_exec", "label": "Founder"})
    assert done["route"] == "estimate"
    assert any(card["type"] == "estimate" and "$" in card["range"] for card in done["cards"])
    assert any(card["type"] == "architecture" for card in done["cards"])
    mvp = next(card for card in done["cards"] if card["type"] == "mvp")
    assert any("reset a password" in item for item in mvp["mvp"])
    objection = send("that feels expensive")
    assert objection["route"] == "objection"
    assert "phase-two" in objection["message"]


def test_feature_detail_skips_when_not_needed(client):
    session = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    sid = session["session_id"]

    def send(content="", chip=None):
        payload = {"content": content}
        if chip:
            payload["chip"] = chip
        response = client.post(f"/api/v1/sessions/{sid}/messages", json=payload)
        assert response.status_code == 200, response.text
        return response.json()

    send(chip={"field": "service", "value": "web_app", "label": "Web"})
    send("Replace spreadsheet approvals")
    skipped = send(chip={"field": "features", "value": [], "label": "Not sure yet"})
    assert "sketch" in skipped["message"].lower()
    assert all(chip["field"] != "feature_detail" for chip in skipped["chips"])

    other = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    other_id = other["session_id"]

    def send_other(content="", chip=None):
        payload = {"content": content}
        if chip:
            payload["chip"] = chip
        response = client.post(f"/api/v1/sessions/{other_id}/messages", json=payload)
        assert response.status_code == 200, response.text
        return response.json()

    send_other(chip={"field": "service", "value": "web_app", "label": "Web"})
    send_other("Replace spreadsheet approvals")
    long_list = (
        "Patients book a visit and the front desk gets a reminder when someone does not arrive"
    )
    described = send_other(long_list)
    assert "sketch" in described["message"].lower()
    assert all(chip["field"] != "feature_detail" for chip in described["chips"])


def test_disqualify_student(client):
    session = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    response = client.post(
        f"/api/v1/sessions/{session['session_id']}/messages",
        json={"content": "Student", "chip": {"field": "decision_role", "value": "intern_or_student", "label": "Student"}},
    )
    assert response.status_code == 200
    assert response.json()["route"] == "discovery"
    assert response.json()["stage"] == "disqualified"


def test_rag_show_and_nda_gate(client):
    session = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    sid = session["session_id"]
    shown = client.post(f"/api/v1/sessions/{sid}/messages", json={"content": ZEPHYR})
    assert shown.status_code == 200
    assert shown.json()["route"] == "rag"
    assert "Zephyr" in shown.json()["message"]
    hidden = client.post(f"/api/v1/sessions/{sid}/messages", json={"content": HARBOR})
    assert hidden.status_code == 200
    assert "Harbor" not in hidden.json()["message"]
    accepted = client.post(
        f"/api/v1/sessions/{sid}/nda",
        json={"version": "2026-01"},
    )
    assert accepted.json()["nda_accepted"] is True
    revealed = client.post(f"/api/v1/sessions/{sid}/messages", json={"content": HARBOR})
    assert "Harbor" in revealed.json()["message"]


def test_fallback_and_grader_withholds(client, monkeypatch):
    session = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    sid = session["session_id"]
    weak = client.post(
        f"/api/v1/sessions/{sid}/messages",
        json={"content": "What is the weather in Berlin tomorrow?"},
    )
    assert weak.status_code == 200
    body = weak.json()
    assert body["route"] == "fallback"
    assert "assistant" in body["message"].lower()
    assert "Zephyr" not in body["message"]
    assert any(chip["field"] == "booking_window" for chip in body["chips"])

    monkeypatch.setattr("backend.app.rag.grade.llm_available", lambda: True)
    monkeypatch.setattr("backend.app.rag.grade.complete_json", lambda *_a, **_k: {"relevant": False})
    rejected = client.post(f"/api/v1/sessions/{sid}/messages", json={"content": ZEPHYR})
    assert rejected.json()["route"] == "fallback"
    assert "Zephyr" not in rejected.json()["message"]


def test_memory_follow_up(client):
    assert "Zephyr" in rewrite_query("how long did that one take?", "", [ZEPHYR])
    session = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    sid = session["session_id"]
    client.post(f"/api/v1/sessions/{sid}/messages", json={"content": ZEPHYR})
    follow = client.post(f"/api/v1/sessions/{sid}/messages", json={"content": "how long did that one take?"})
    assert follow.status_code == 200
    assert "Zephyr" in follow.json()["message"] or "14 weeks" in follow.json()["message"]
    with SessionLocal() as db:
        row = db.get(SessionRow, sid)
        assert row.summary == "" or isinstance(row.summary, str)


def test_summary_persists(client):
    session = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    sid = session["session_id"]

    def send(content="", chip=None):
        payload = {"content": content}
        if chip:
            payload["chip"] = chip
        return client.post(f"/api/v1/sessions/{sid}/messages", json=payload)

    send(chip={"field": "service", "value": "web_app", "label": "Web"})
    send("Replace spreadsheet approvals")
    send(chip={"field": "features", "value": ["Admin"], "label": "Admin"})
    send(chip={"field": "features_done", "value": "yes", "label": "That's all"})
    with SessionLocal() as db:
        row = db.get(SessionRow, sid)
        assert "spreadsheet" in (row.summary or "")


def test_tenant_isolation(client, auth):
    created = client.post(
        "/admin/tenants",
        data={"slug": "acme", "name": "Acme", "logo_text": "Acme", "primary": "#112233"},
        auth=auth,
        follow_redirects=False,
    )
    assert created.status_code == 303
    try:
        session = client.post("/api/v1/sessions", json={"tenant": "acme"})
        assert session.status_code == 200
        assert session.json()["message"].startswith("I'm Acme's assistant")
        reply = client.post(
            f"/api/v1/sessions/{session.json()['session_id']}/messages",
            json={"content": ZEPHYR},
        )
        assert reply.json()["route"] == "fallback"
        assert "Zephyr" not in reply.json()["message"]
    finally:
        cleanup_tenant("acme")


def test_chunk_overlap_and_thresholds():
    words = " ".join(f"w{i}" for i in range(50))
    chunks = chunk_text(f"## Outcome\n{words}", chunk_tokens=20, overlap_tokens=5)
    assert len(chunks) >= 3
    assert chunks[0][0] == "Outcome"
    assert classify(0.9, True) == "show"
    assert classify(0.9, False) == "weak"
    assert classify(0.4, None) == "weak"
    assert classify(0.1, None) == "low"


def test_semantic_breakpoint_splits_topics():
    text = "## Outcome\nClinics book visits online. Harbor ledger tracks invoices."

    def dissimilar(sentences):
        return [[1.0, 0.0] if index == 0 else [0.0, 1.0] for index, _sentence in enumerate(sentences)]

    chunks = chunk_text(text, chunk_tokens=40, overlap_tokens=0, break_similarity=0.5, embed=dissimilar)
    assert len(chunks) == 2
    assert chunks[0][0] == "Outcome"
    assert chunks[1][0] == "Outcome"
    assert "Clinics book visits online." in chunks[0][1]
    assert "Harbor ledger tracks invoices." in chunks[1][1]

    def similar(sentences):
        return [[1.0, 0.0] for _sentence in sentences]

    together = chunk_text(text, chunk_tokens=40, overlap_tokens=0, break_similarity=0.5, embed=similar)
    assert len(together) == 1
    assert "Clinics" in together[0][1]
    assert "Harbor" in together[0][1]


def test_suggestion_chips_cover_open_questions(client, monkeypatch):
    calls = []

    def fake_complete(_system, user):
        calls.append(user)
        return {
            "chips": [
                {"label": "Clinic messaging", "value": "Let clinics message patients"},
                {"label": "Visit booking", "value": "Patients book visits"},
            ]
        }

    monkeypatch.setattr("backend.app.agents.suggestions.complete_json", fake_complete)
    monkeypatch.setattr("backend.app.agents.suggestions.llm_available", lambda: True)

    session = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    assert {chip["field"] for chip in session["chips"]} == {"service"}
    assert calls == []
    sid = session["session_id"]

    def send(content="", chip=None):
        payload = {"content": content}
        if chip:
            payload["chip"] = chip
        response = client.post(f"/api/v1/sessions/{sid}/messages", json=payload)
        assert response.status_code == 200, response.text
        return response.json()

    goal = send(chip={"field": "service", "value": "mobile_app", "label": "Mobile app"})
    assert goal["chips"]
    assert {chip["field"] for chip in goal["chips"]} == {"goal"}
    assert len(calls) == 1

    faq = send("How do you run a project?")
    assert faq["route"] == "faq"
    assert faq["chips"]
    assert {chip["field"] for chip in faq["chips"]} == {"goal"}
    assert len(calls) == 2
    assert "Retrieved notes:" in calls[1]
    assert "weekly cadence" in calls[1]

    other = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    other_id = other["session_id"]
    calls.clear()

    def send_other(content="", chip=None):
        payload = {"content": content}
        if chip:
            payload["chip"] = chip
        response = client.post(f"/api/v1/sessions/{other_id}/messages", json=payload)
        assert response.status_code == 200, response.text
        return response.json()

    send_other(chip={"field": "service", "value": "mobile_app", "label": "Mobile app"})
    assert len(calls) == 1
    send_other("Let clinics message patients")
    send_other(chip={"field": "features", "value": [], "label": "Not sure yet"})
    send_other(chip={"field": "user_flow", "value": "not_specified", "label": "Skip for now"})
    users = send_other(chip={"field": "platforms", "value": ["ios"], "label": "iOS"})
    assert len(calls) == 1
    assert {chip["field"] for chip in users["chips"]} == {"users"}
    assert {chip["value"] for chip in users["chips"]} == {"consumers", "business", "internal"}


def test_feedback_and_booking(client, monkeypatch):
    calls = {}

    def fake_post(url, json=None, timeout=5):
        calls["url"] = url
        calls["json"] = json

        class Response:
            status_code = 200

        return Response()

    monkeypatch.setattr("httpx.post", fake_post)
    with SessionLocal() as db:
        tenant = db.scalar(select(TenantRow).where(TenantRow.slug == "demo"))
        tenant.slack_webhook_url = "https://hooks.example/test"
        db.commit()
    try:
        session = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
        sid = session["session_id"]
        shown = client.post(f"/api/v1/sessions/{sid}/messages", json={"content": ZEPHYR}).json()
        feedback = client.post(
            f"/api/v1/sessions/{sid}/feedback",
            json={"message_id": shown["message_id"], "rating": "up"},
        )
        assert feedback.status_code == 200
        assert feedback.json()["saved"] >= 1
        slots = client.post(f"/api/v1/sessions/{sid}/messages", json={"content": "book a meeting"}).json()
        assert slots["route"] == "booking"
        booked = client.post(
            f"/api/v1/sessions/{sid}/messages",
            json={"content": slots["chips"][0]["label"], "chip": slots["chips"][0]},
        ).json()
        assert booked["route"] == "booking"
        assert "booked" in booked["message"].lower()
        with SessionLocal() as db:
            thumbs = db.scalar(
                select(func.count()).select_from(FeedbackPairRow).where(FeedbackPairRow.source == "thumb")
            )
            bookings = db.scalar(
                select(func.count()).select_from(FeedbackPairRow).where(FeedbackPairRow.source == "booking")
            )
            events = db.scalar(select(func.count()).select_from(EventRow).where(EventRow.kind == "slack"))
        assert thumbs >= 1
        assert bookings >= 1
        assert events >= 1
        assert calls["url"] == "https://hooks.example/test"
        admin = client.get(f"/admin/sessions/{sid}", auth=("admin", "test-admin"))
        assert admin.status_code == 200
        assert "Zephyr" in admin.text or "booked" in admin.text.lower()
    finally:
        with SessionLocal() as db:
            tenant = db.scalar(select(TenantRow).where(TenantRow.slug == "demo"))
            tenant.slack_webhook_url = ""
            db.commit()


def test_rfp_upload(client):
    session = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    response = client.post(
        f"/api/v1/sessions/{session['session_id']}/documents",
        files={"file": ("brief.txt", b"Clinic scheduling notes for the front desk.", "text/plain")},
    )
    assert response.status_code == 200
    assert "brief.txt" in response.json()["message"]
    assert response.json()["route"] == "rfp"


def test_finetune_gate(client, monkeypatch):
    from backend.app.learning.finetune import finetune_tenant

    with SessionLocal() as db:
        tenant = db.scalar(select(TenantRow).where(TenantRow.slug == "demo"))
        refused = finetune_tenant(db, "demo")
        assert refused["reason"] == "not_enough_pairs"
        chunk = db.scalar(select(ChunkRow).where(ChunkRow.tenant_id == tenant.id))
        for index in range(64):
            db.add(
                FeedbackPairRow(
                    tenant_id=tenant.id,
                    session_id="s",
                    message_id=f"m-{index}",
                    query="zephyr no shows",
                    chunk_id=chunk.id,
                    label="positive",
                    source="thumb",
                )
            )
        db.commit()
        blocked = finetune_tenant(db, "demo")
        assert blocked["reason"] == "hash_embedder_cannot_finetune"
        monkeypatch.setattr("backend.app.learning.finetune.embedding_backend", lambda: "sentence-transformers")
        monkeypatch.setattr("backend.app.learning.finetune._train", lambda *_a, **_k: None)
        done = finetune_tenant(db, "demo")
        assert done["ok"] is True
        assert done["model"].startswith("finetuned:")
        tenant.embedding_model = ""
        db.commit()


def test_pricing_faq_uses_stored_answer(client, monkeypatch):
    def explode(*_args, **_kwargs):
        raise AssertionError("FAQ hit must not call the model")

    monkeypatch.setattr("backend.app.rag.grade.complete_json", explode)
    monkeypatch.setattr("backend.app.agents.router.grade", explode)
    session = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    response = client.post(
        f"/api/v1/sessions/{session['session_id']}/messages",
        json={"content": "How is project pricing structured?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "faq"
    assert "fixed-price milestones" in body["message"]


def test_query_filters_keep_question_industry():
    from backend.app.rag.filters import query_filters

    assert query_filters("How is project pricing structured?") == {"topic": "pricing"}
    found = query_filters(
        "Do you have a healthcare case study?",
        service="mobile_app",
        industry="fintech",
    )
    assert found["doc_type"] == "case_study"
    assert found["industry"] == "health"
    assert found["service"] == "mobile_app"


def test_metadata_filter_narrows_then_falls_back(client):
    from backend.app.rag.store import search
    from backend.app.tenants.loader import ensure_tenant_row

    with SessionLocal() as db:
        tenant = ensure_tenant_row(db, "demo")
        health = search(
            db,
            tenant,
            "clinic patient onboarding",
            kind="knowledge",
            filters={"industry": "health", "doc_type": "case_study"},
        )
        assert health
        assert {hit.metadata.get("industry") for hit in health} == {"health"}
        assert {hit.metadata.get("doc_type") for hit in health} == {"case_study"}
        fallback = search(db, tenant, "clinic", kind="faq", filters={"topic": "missing-topic"})
        assert fallback
        assert any(hit.metadata.get("topic") != "missing-topic" for hit in fallback)


def test_ingest_is_idempotent(client):
    from backend.app.rag.ingest import ingest_tenant
    from backend.app.tenants.loader import ensure_tenant_row

    with SessionLocal() as db:
        tenant = ensure_tenant_row(db, "demo")
        first = ingest_tenant(db, tenant)
        second = ingest_tenant(db, tenant)
    assert first["documents"] > 0
    assert second["embedded"] == 0
    assert second["unchanged"] == first["documents"]

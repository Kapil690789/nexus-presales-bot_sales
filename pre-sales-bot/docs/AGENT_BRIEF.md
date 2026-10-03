# AGENT BRIEF v2 — Harden the Nexus Pre-Sales Bot (`pre-sales-bot/`)

You are a senior AI/ML + backend engineer. Read `MASTER_CONTEXT.md` first. Work through the phases **in order** and **stop for owner approval after every phase**.

> v1 of this brief was written from the legacy `chat-bot/` tree. Everything below is re-based on `pre-sales-bot/`. Items that were observed in `chat-bot/` but not yet seen in `pre-sales-bot/` are listed as **hypotheses (H)**, not bugs. Prove or disprove each one with a test before changing code.

---

## 0. Working rules

1. **NO `git commit`, `git push`, or remote changes.** The owner commits manually. After each phase leave changes uncommitted and list the files changed.
2. Work only in `/Volumes/Untitled 2/chatbot/Dummy-chat-bot/pre-sales-bot/`. Do not edit or run `chat-bot/`.
3. Read every file before editing it. If this brief contradicts the code, trust the code and report it.
4. **Invariants:** the LLM never produces or alters prices/ranges/durations; do not change pricing numbers or scoring weights without approval; sync `widget/consultant.js` to `public/widget/consultant.js` after widget edits; no secrets in code, docs, tests, logs, or URLs; never print `.env` values.
5. `.venv/bin/pytest backend/tests` passes after every change. Report the real test count (docs say both 46 and 103).
6. Verify external APIs (Gemini REST fields, model IDs, dimensions) against current Google docs before coding.
7. Keep each change small and covered by a test that fails before the fix.

---

## 1. Findings

### A. Verified in the code reviewed

| ID | Finding | File | Sev |
|---|---|---|---|
| V1 | **Failures are mislabeled.** On any Gemini failure `_gemini_embed` returns 384-dim hash vectors, but `embed_texts` still returns `EmbeddingBatch(model="gemini-embedding-001", dim=len(vectors[0]))`. Documents embedded during an outage are stored as "Gemini" vectors of length 384; queries are 3072. `cosine()` returns 0.0 on a length mismatch, so those documents silently never match (or, if the query embedding fails, nothing matches). No log reaches the admin, and "stored models" cannot reveal it. | `rag/embeddings.py` | P0 |
| V2 | **API key in the URL query string** (`...:batchEmbedContents?key=...`). URLs end up in proxy/platform logs and some exception messages. Gemini REST accepts the key in an `x-goog-api-key` header. | `rag/embeddings.py` | P0 |
| V3 | **Query-time retry budget is far too long.** Up to 5 attempts with sleeps 3+6+12+20+30 s (about 71 s) on 429, using blocking `time.sleep`. A single visitor question can hang past a serverless timeout. Ingest and query share the same policy. | `rag/embeddings.py` | P0 |
| V4 | **Admin fails open.** `assert_admin_configured` errors are caught and only logged ("The app will still serve"). With a missing/default password the admin dashboard is reachable. Docs also advertise `admin / admin123`. | `main.py`, README | P0 |
| V5 | No `taskType` (RETRIEVAL_DOCUMENT / RETRIEVAL_QUERY) and no `outputDimensionality`, so vectors are 3072-dim. Not normalized after any truncation (none today). | `rag/embeddings.py`, `platform.yaml` | P1 |
| V6 | **Semantic chunker depends on the embedder.** It embeds every sentence at ingest (many API calls, 1.2 s sleep per 40) and splits where cosine < 0.5. If the embedder silently falls back to hash vectors, the 0.5 threshold over-splits into one-sentence chunks. The threshold is not calibrated per model. | `rag/chunker.py`, `platform.yaml` | P1 |
| V7 | Vercel branch skips `init_db()` and ingest; the comment says the first DB request does them. Unverified. If untrue, a fresh Vercel DB has no tables/index. | `main.py` | P1 |
| V8 | **Docs contradict each other:** model (3.8 vs 2.5), tests (103 vs 46), batch size (15 vs 40), memory (3 vs 8 turns), a dead model named (`text-embedding-004`, shut down 2026-01-14), unmeasured "<500 ms". | README | P1 |
| V9 | **Pricing sample is not reproducible.** README says the "AI chat" mobile prompt returns $29.5k–$37k, 12 weeks. From `pricing.yaml` that range equals mobile + both platforms *without* the AI flag, and no config value gives 12 weeks (8/14/22). Possible under-quote if the AI flag is not being extracted. | README, `pricing.py`, extractor | P1 |
| V10 | Platform chip "iOS and Android" emits `["ios","android"]` while the pricing key is `both` (×1.32). If the engine does not map the pair to `both`, the quote is too low. Platform chips are also not service-aware (web projects see iOS/Android). | `agents/chips.py`, `pricing.py` | P1 |
| V11 | Config schema has no `extra="forbid"` or value validation: a typo like `low_side_factr` is silently ignored; a negative multiplier is accepted. Calendar timezone sits in `platform.yaml` (global), not per tenant. | `tenants/schema.py`, `platform.yaml` | P2 |
| V12 | Pricing math: multipliers compound (everything on ≈ 3.8× base), the price band is low = 0.8 x raw and high = raw (width 25% of low, 0% above raw) regardless of how complete the brief is, currency is USD-only, budget chips are USD. | `pricing.yaml`, `chips.py` | P2 |
| V13 | Demo case studies are **fictional with concrete outcome claims** ("no-shows down 18 percent"). A real client tenant must never show them as the client's work. README claims "50+" studies; `portfolio.yaml` has 5. | `tenants/demo/*` | P2 |

### B. Hypotheses to verify (observed in legacy `chat-bot/`; unknown here)

| ID | Hypothesis | How to test |
|---|---|---|
| H1 | After an estimate exists, a free-form question ("do you use Flutter?") is answered by a scripted fallback, not by Gemini + RAG. | Drive a session to an estimate, send 3 free-form questions, assert the LLM+retrieval path ran (mock the LLM and count calls). |
| H2 | After a slot is booked, every later turn is overwritten by a canned "Booked…" message. | Book a slot, then send a normal question; assert the reply answers it. |
| H3 | LLM/JSON failures fall back silently with no event, metric, or admin visibility. | Force a 429 and a bad-JSON response; assert an event/log with reason exists. |
| H4 | One weak LLM-extracted `decision_role=student` or `out_of_scope` closes the chat. | Feed a casual line ("my cousin is a student, he suggested this"); assert the bot confirms before closing. |
| H5 | Sessions are stored in ephemeral SQLite `/tmp` on Vercel and are lost across instances. | Inspect production `DATABASE_URL` handling; assert prod refuses SQLite. |
| H6 | `feedback_pairs` feed embedding fine-tuning (`finetune_min_positives`) without review, so a visitor can poison it. | Read the feedback + finetune code path; list who/what can write pairs. |

---

## PHASE 0 — Audit, golden tests, eval harness  (STOP after this phase)

1. Run `pytest`; record the real count and any failures.
2. Prove or disprove **H1–H6** with failing tests. Report a table: hypothesis → confirmed / refuted → evidence (file:line).
3. Pricing golden tests (pin current YAML math; do not edit YAML). Expected values from `pricing.yaml`, assuming `Low = round(Raw × 0.80)`, `High = round(Low × 1.25)`, and complexity = product of multipliers vs thresholds. If the engine disagrees, **report it; do not bend the test to match the engine.**

   | Case | Raw | Low–High | Complexity → weeks |
   |---|---|---|---|
   | web_app, web, 0 integrations, no flags | 24,000 | 19,200–24,000 | 1.00 → 8 |
   | mobile_app, both platforms | 36,960 | 29,568–36,960 | 1.32 → 14 |
   | mobile_app, both + ai_features | 45,091.2 | 36,073–45,091 | 1.6104 → 22 |

   Also test: `["ios","android"]` (chip output) is priced identically to `"both"` (V10); "AI chat" in free text sets the AI flag (V9).
4. Build `backend/tests/eval/` with 30+ scripted scenarios (clear brief, vague answers, topic switch, objection, Hinglish, student visitor, out-of-scope, RFP upload, booking, post-estimate question, post-booking question, simulated 429, simulated bad JSON). Metrics: `llm_fallback_rate`, `repeated_question_rate`, `post_estimate_llm_rate`, `post_booking_canned_rate`, `price_leak_count`, `slot_accuracy`, `retrieval_hit_rate`. Works offline with a stub LLM; uses the real LLM only if `LLM_API_KEY` is set.
5. Save baseline numbers in `docs/EVAL.md`.

**Done when:** hypothesis table, golden tests, and baseline exist. Report and wait.

---

## PHASE 1 — Embeddings correctness (V1, V2, V3, V5, V6)

Files: `rag/embeddings.py`, `rag/chunker.py`, `config/platform.yaml`, `core/settings.py`, store/ingest as needed.

1. Introduce `class EmbeddingError(RuntimeError)`. `_gemini_embed` raises it on failure. **Never return hash vectors under a Gemini label.** `EmbeddingBatch.model` and `.dim` must always describe the vectors actually returned.
2. Auth in a header, not the URL:
   ```python
   headers = {"x-goog-api-key": key}
   url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:batchEmbedContents"
   # per request (verify field names in current docs):
   {"model": f"models/{model}",
    "content": {"parts": [{"text": t}]},
    "taskType": task,                      # RETRIEVAL_DOCUMENT or RETRIEVAL_QUERY
    "outputDimensionality": settings.embedding_dim}   # default 768
   ```
   Normalize after truncation. Keep `platform.yaml: embedding_dim` and the code in sync (one source of truth).
3. Two retry policies:
   - **Ingest:** patient (current backoff is fine), runs off the request path.
   - **Query time:** hard budget of about 6–8 s total, 1 retry, async-safe (no long blocking sleeps). On failure fall back to **keyword/BM25 retrieval**, mark the turn `retrieval_mode="lexical"`, log with `log.exception`, write an event, and show degraded state in `/health` and admin.
4. Ingest must be atomic per document: if embedding fails, keep the old vectors and mark the document `stale`; do not write mislabeled vectors.
5. `embed_query()` uses `RETRIEVAL_QUERY`; documents use `RETRIEVAL_DOCUMENT`.
6. Chunker: make semantic breaking opt-in per tenant (default structural/heading chunking). If kept, record which embedder produced the breaks, never use hash vectors for break detection, calibrate `semantic_break_similarity` per model, and cache sentence embeddings so re-ingest does not re-pay.
7. Re-ingest after the dimension change (stored vectors with a different dim must be detected and rebuilt, not compared).
8. Calibration script `scripts/calibrate_rag.py`: 20+ labelled queries (relevant doc ids + clearly irrelevant ones). Print score distributions and propose values for `faq_min_score`, `show_min_score`, `weak_min_score`. Update `platform.yaml` only with owner approval.

**Done when:** a bad key or forced failure produces a loud, visible degraded state and zero mislabeled vectors; tests cover V1–V3.

---

## PHASE 2 — Conversation flow (only the hypotheses confirmed in Phase 0)

Files: `agents/router.py`, `agents/fallback.py`, `agents/extractor.py`, `engines/*`, `api/sessions.py`.

- **If H1:** route real questions through LLM + RAG at every stage after the estimate; append the deterministic next-step prompt (email, slots) afterwards so the flow stays controlled by code.
  ```python
  def is_free_question(text, chip, just_got_email):
      if chip or just_got_email or not (text or "").strip():
          return False
      return "?" in text or len(text.split()) >= 4
  ```
- **If H2:** build the booking confirmation/summary only on the turn the booking happened (compare booking state before vs after the turn). Later turns use the normal path. Make sure persistence does not overwrite a stored handoff summary with `None`.
- **If H3:** replace broad `except Exception: pass/warn` with specific handling; write an event per fallback (`stage`, `reason`, `error_type`); show fallback rate in admin. Use Gemini structured output where supported to reduce JSON failures.
- **If H4:** when `student` / `out_of_scope` comes from LLM extraction (not an explicit chip), ask one confirming question before closing.
- Budget chips and prompts: make platform chips depend on the selected service (V10).

**Done when:** the Phase 0 failing tests pass and the eval table improves on the baseline.

---

## PHASE 3 — Security and infra (V4, V7, H5, H6)

1. **Fail closed.** In `ENVIRONMENT=production`, if the admin password is missing or a known default, disable all `/admin*` routes (or refuse to start). Remove `admin123` and any real-looking credentials from every doc and `.env.example`.
2. Production requires a hosted Postgres `DATABASE_URL`; refuse ephemeral SQLite there (clear error).
3. Verify the Vercel lazy-init path (V7): confirm tables and ingest are created on the first DB request, with a test; if absent, add it with a lock so concurrent cold starts do not race.
4. Treat RFP text, retrieved chunks, and feedback data as untrusted in every prompt; add injection tests (instructions inside an uploaded RFP, inside a case study, inside feedback).
5. If H6 is true: feedback pairs need admin approval before they can influence fine-tuning, with per-session caps.
6. CORS: explicit origins in production; never combine `*` with credentials.
7. Model names via env with a configured fallback model (3.8 Flash is described by Google as short-term availability; 2.5 models have restricted access for new users).

---

## PHASE 4 — RAG quality and content

1. Hybrid retrieval: keyword + vector with reciprocal rank fusion; filter by service when known; rewrite the query with the current brief.
2. A "no relevant knowledge" signal so the model says it does not know rather than guessing.
3. Content lint (`make`/script): warn on currency figures (`$`, `USD`, `INR`, `₹`) in `content/` so prose cannot contradict the pricing engine.
4. Demo data hygiene (V13): mark demo case studies as sample; add a check that a non-demo tenant never loads `tenants/demo` content; replace counts in docs with real numbers.

---

## PHASE 5 — Pricing and config (needs owner approval for anything beyond tests)

- Allowed without approval: golden tests, schema hardening.
- Schema: `model_config = ConfigDict(extra="forbid")`; validators (factors > 0, `range_factor ≥ 1`, `low_side_factor ≤ 1`, every service in `bases` and `team_mix`, every flag/platform key known). Fail at load with a clear message.
- Move calendar timezone and currency to the tenant config.
- **Propose (do not merge):** optional cap on compounded flag multipliers; wider band when critical slots are missing or the visitor chose "not sure"; currency display config (USD/INR) driven by YAML, never by the LLM.
- Output guard: any currency figure in a reply that the engine did not produce is blocked or regenerated; add tests.

---

## PHASE 6 — Features (ask the owner which to build)

What-if pricing (toggle features, live band, engine only), three packages, shareable read-only proposal link with expiry + server-side PDF, streaming replies (SSE), real CRM adapter, admin funnel analytics, Hinglish prompts and tests. Reading the legacy `chat-bot/` for ideas is allowed (content front matter `status`/`nda_only`, `ingest-dry` validator, learning loop, Slack booking alerts); port nothing without approval.

---

## PHASE 7 — Docs reconciliation

Fix, using measured values only: model name (one env source), real test count, batch size, memory turns, remove `text-embedding-004`, remove unmeasured latency claims, real case-study count, `admin123` and similar credentials, and the pricing sample prompt (either correct the numbers or fix the engine). Update the tags in `MASTER_CONTEXT.md`.

---

## Definition of done

- Phase 0 tests exist and pass after their fixes; all tests pass; real count reported.
- Eval table beats baseline for `llm_fallback_rate`, `post_estimate_llm_rate`, `post_booking_canned_rate`, `retrieval_hit_rate`; `price_leak_count` is 0.
- Embedding failures are loud and never mislabeled; no secret appears in a URL, log, or doc.
- Admin is unreachable in production without a unique password.
- Final report: what changed, what was skipped and why, what disagreed with these docs. No commits were made by the agent.

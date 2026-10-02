# AGENT BRIEF — Harden the Nexus Pre-Sales AI Consultant

You are a senior AI/ML + backend engineer. Work through the phases **in order**. Do not start a phase until the previous one is green (`pytest` passes, new tests included).

---

## 0. Working rules

1. **Read before you edit.** Open every file you will touch. If this brief contradicts the code, trust the code and report the difference at the end.
2. **Resolve the codebase first (STEP 0).** Two trees are mentioned in the docs: `chat-bot/` and `pre-sales-bot/`. This brief was written from `chat-bot/` (it has `backend/app/agents/orchestrator.py`, `agents/extract.py`, `agents/style.py`, `rag/embeddings.py`, `rag/learn.py`). The architecture doc also names files such as `extractor.py`, `discovery_synth.py`, `tenants/demo/`, `public/studio.html`. If both trees exist, **stop and ask the owner which is canonical**. Do not port code between trees silently.
3. **Invariants (never break):**
   - Prices, ranges, timelines come only from `engines/pricing.py` + `config/pricing.yaml`. The LLM never invents or changes a number.
   - `config/` is the source of truth for anything a number depends on; `content/` is prose only.
   - `pricing.bases`, `pricing.multipliers`, and `agency.never_say` are never indexed into RAG.
   - NDA gating (`nda_only`, `required_before_handoff`) keeps working.
   - No secrets in the repo, docs, logs, or tests. If you see one, tell the owner to rotate it.
4. **Small commits, one concern each.** After each phase, run the full suite and the eval harness (Phase 0) and paste the score table in your report.
5. **Do not change pricing numbers or scoring weights.** Structural changes to the pricing engine (Phase 5) need owner approval before merging.
6. **Verify external APIs against current docs** before coding against them (Gemini model IDs, SDK method names, embedding dimensions). Do not rely on memory.

---

## 1. Evidence-backed problem list (from code review)

| # | Problem | Where | Severity |
|---|---|---|---|
| E1 | Default Gemini embedding model is `text-embedding-004`, which Google shut down on 2026-01-14. `embed_texts` swallows the failure (`except Exception: pass`) and silently falls back to the local hash embedder. Admin shows the *intended* model, not the one actually used. | `rag/embeddings.py` | P0 |
| E2 | After an estimate exists, a free-form visitor question lands in stage `capture`; `advise` is only true for `estimation/solutioning/portfolio`, and `consult_data` is skipped once the brief is ready, so the reply comes from scripted `fallback_reply`, not Gemini + RAG. | `agents/orchestrator.py` (`run_turn`) | P0 |
| E3 | After booking, `can_handoff` stays true every turn, so every later reply is overwritten by the "Booked…" block or `_dedupe_message`'s canned "Got it. What would you like to do next?". The visitor-facing text also contains "(dummy — not actually sent)". | `agents/orchestrator.py` | P0 |
| E4 | LLM failures are caught by `except (LLMError, Exception)` and only `log.warning`'d; the visitor silently gets a different, scripted tone. No metric. | `agents/orchestrator.py` | P0 |
| E5 | A single LLM-extracted `decision_role == "intern_or_student"` immediately disqualifies and closes the chat. | `_hint_stage`, `run_turn` | P1 |
| E6 | `max_snippet_chars: 480` but chunks are up to 1200 chars, so the model sees roughly half of each chunk. Similarity floors (`min_score 0.20`, `objection_min_score 0.55`, `_local 0.12`) were tuned for the hash embedder. | `config/rag.yaml` | P1 |
| E7 | `pages:*` and several `agency:*` documents are retrievable and add noise to `top_k=4`. | `rag/chunker.py` | P1 |
| E8 | `ingest_on_startup()` runs synchronously inside the async lifespan on every boot. On serverless with ephemeral SQLite this means a full re-embed per cold start (one API call per text). Errors are returned in a dict, never logged. | `main.py`, `rag/ingest.py`, `rag/embeddings.py::_gemini` | P1 |
| E9 | Lessons are injected into other visitors' prompts. `_distill_heuristic` copies visitor-controlled `brief.goal` into lesson text. Possible persistent prompt injection / RAG poisoning. | `rag/learn.py` | P1 |
| E10 | Win rate `handoffs/(sessions+prior)` favours frequently shown case studies even at equal true conversion; conversions are confounded by visitor fit. | `rag/learn.py::win_rates` | P2 |
| E11 | Pricing multipliers compound (all flags on is about 3.8x base); range is always +/-25% regardless of how incomplete the brief is; currency is USD-only. | `config/pricing.yaml`, `engines/pricing.py` | P2 |
| E12 | Prose in `content/faq/pricing-faq.md` may quote dollar figures that disagree with the engine. | `content/` | P2 |
| E13 | `allow_credentials=True` with `allow_origins=["*"]` is invalid in browsers. | `main.py` | P2 |
| E14 | `google-generativeai` is the old SDK. | `pyproject.toml` | P2 |

---

## PHASE 0 — Baseline, regression tests, eval harness

**Goal:** make the problems measurable before fixing them.

1. Create `backend/tests/eval/` with at least 30 scripted scenarios (YAML or JSON): clear brief, vague answers, topic switch mid-discovery, objection ("too expensive"), Hinglish messages, student visitor, out-of-scope service, RFP upload, booking flow, post-estimate question, post-booking question, simulated Gemini 429, simulated JSON parse failure.
2. Build a runner that executes scenarios against `run_turn` with (a) a stub LLM and (b) the real LLM when `LLM_API_KEY` is set. Metrics per run:
   - `llm_fallback_rate` (turns where the LLM path was expected but the scripted fallback replied)
   - `repeated_question_rate` (a filled slot asked again)
   - `post_estimate_llm_rate` (share of free-form questions after the estimate answered by the LLM)
   - `post_booking_canned_rate`
   - `price_leak_count` (currency figures in replies that are not in the engine output)
   - `slot_accuracy` against the scenario's expected brief
3. Write failing regression tests now (they must fail before Phases 1-2 and pass after):
   - `test_post_estimate_question_goes_to_llm_with_rag`
   - `test_post_booking_question_not_overwritten`
   - `test_llm_failure_is_recorded_as_event`
   - `test_embedding_failure_is_not_silent` (production mode)
   - `test_reply_never_contains_unapproved_price`
4. Save baseline numbers in `docs/EVAL.md`.

**Done when:** harness runs in under 2 minutes with the stub LLM and the baseline table exists.

---

## PHASE 1 — Embeddings (fixes E1, E8 partly, E14)

Files: `rag/embeddings.py`, `core/settings.py`, `pyproject.toml`, `rag/store.py` (read-only unless needed), `admin/templates/rag.html`.

1. Verify on Google's current docs: embedding model IDs, deprecation status, and supported `output_dimensionality` values. As of this brief, `gemini-embedding-001` is GA (default 3072 dims, truncatable via MRL to 768/1536) and Google lists `gemini-embedding-2` as the recommended replacement. Pick one, ask the owner if unsure, and record the choice in `docs/`.
2. Replace `google-generativeai` with `google-genai`. Sketch (verify against current SDK docs):
   ```python
   from google import genai
   from google.genai import types

   def _gemini(model: str, texts: list[str], task: str) -> list[list[float]]:
       client = genai.Client(api_key=get_settings().llm_api_key)
       res = client.models.embed_content(
           model=model,
           contents=texts,  # batch, not one call per text
           config=types.EmbedContentConfig(
               task_type=task,  # RETRIEVAL_DOCUMENT or RETRIEVAL_QUERY
               output_dimensionality=get_settings().embedding_dim,  # 768 default
           ),
       )
       return [list(e.values) for e in res.embeddings]
   ```
3. `embed_texts(texts, task="RETRIEVAL_DOCUMENT")` and `embed_query()` uses `RETRIEVAL_QUERY`. Always `_normalize` after truncation (already done; keep it).
4. Update `PROVIDER_MODELS["gemini"]` and `KNOWN_DIMS`. Add `EMBEDDING_DIM` to settings (default 768).
5. **No silent degradation.** Add setting `EMBEDDING_STRICT` (default true when `ENVIRONMENT=production`). When strict and the remote call fails: log with `log.exception`, raise, and make `/health` report `embeddings: degraded`. When not strict: fall back but log a warning once per process and record an `events` row.
6. Remove the failure-poisoning cache: `active_model()` must not cache a fallback result after a transient probe failure.
7. Store and report the **actual** model used per chunk. In `rag.html` show counts by stored model, not just `stats.embedding_model`.
8. Re-ingest (`make ingest`), then run the eval harness and confirm retrieval hits improved.

**Done when:** with a bad API key in production mode the app reports degraded embeddings loudly; with a good key all chunks carry the real model name; tests pass.

---

## PHASE 2 — Orchestrator (fixes E2, E3, E4, E5)

File: `backend/app/agents/orchestrator.py`. Keep behaviour for every existing passing test.

### 2a. Post-estimate Q&A goes through the LLM + RAG (E2)
Add a path: if `use_llm`, an estimate exists, the visitor typed a real question (not just an email, not a chip, not a slot pick), then call the solution/consult prompt even when the stage is `capture`, `booking`, or `handoff`. After the LLM answer, append the deterministic call-to-action for the current stage (ask for work email, show slots, etc.) instead of letting the LLM decide the flow.
```python
def _is_free_question(user_text, chip_field, just_got_email) -> bool:
    if chip_field or just_got_email or not (user_text or "").strip():
        return False
    return "?" in user_text or len(user_text.split()) >= 4

ANSWERABLE_STAGES = {"estimation", "solutioning", "portfolio", "capture", "booking", "handoff"}
advise = use_llm and bool(estimate) and (
    stage in {"estimation", "solutioning", "portfolio"}
    or (stage in ANSWERABLE_STAGES and _is_free_question(user_text, chip_field, just_got_email))
)
```
Keep `_ensure_range` and `sanitize_reply` in the pipeline for every LLM answer.

### 2b. Booking confirmation only once (E3)
- Save `prior_booking = dict(booking or {})` at the top of `run_turn`, before `confirm_slot`.
- `just_booked = _is_booked(booking) and not _is_booked(prior_booking)`.
- Build `summary`, `follow_up`, and the "Booked…" message **only when `just_booked`**. On later turns stage is `handoff` but the reply comes from the normal path (2a).
- Confirm `services/sessions.py::persist_turn` does not overwrite a stored `handoff_summary` with `None` on later turns. Add a test.
- Put the "(dummy — not actually sent)" text behind a config flag (e.g. `handoff.yaml: stub_notice: true`); default it to off for visitor-facing text and keep it in admin only.

### 2c. Failures are visible (E4)
- Replace `except (LLMError, Exception)` with specific handling: `LLMError` (quota, timeout), `json.JSONDecodeError`/validation errors, and a last-resort `Exception` that uses `log.exception`.
- On every fallback, write an `events` row: kind `llm_fallback`, payload `{stage, reason, error_type}`. Show a fallback rate on the admin dashboard.
- Prefer Gemini structured output (`response_schema`) for `complete_json` to reduce parse failures. Verify SDK usage in current docs.
- On 429, retry with backoff (already in `core/llm.py`), then fall back and tell the visitor nothing technical.

### 2d. Do not disqualify on one weak signal (E5)
If `decision_role == "intern_or_student"` or `out_of_scope` came from an LLM `brief_updates` (not an explicit chip), do not close. Ask one short confirming question first ("Just to check, is this for a real project or exploring for a class?"). Only close after a chip or an explicit confirmation.

### 2e. Optional refactor
Only after all tests are green: split `run_turn` into pure helpers (`apply_inputs`, `choose_stage`, `generate_reply`, `finalize`). No behaviour change. Snapshot-test them.

**Done when:** the three regression tests from Phase 0 pass; `post_estimate_llm_rate` approaches 1.0; `post_booking_canned_rate` is 0.

---

## PHASE 3 — RAG quality (fixes E6, E7, E12)

Files: `config/rag.yaml`, `rag/chunker.py`, `rag/content.py`, `rag/retrieve.py`, `rag/grade.py`.

1. Raise `max_snippet_chars` to roughly 900-1200 (match chunk size) and re-check prompt length.
2. Prepend the document title and service to the text that is embedded (`embed_text`) so chunks like "Outcome: ..." keep their context.
3. Exclude `pages:*` and `agency:out_of_scope_close` from `retrieve_knowledge` (keep them indexed only if another feature needs them).
4. Add hybrid retrieval: keyword/BM25 score fused with vector score using reciprocal rank fusion; metadata filter by `service` when the brief has one; rewrite the query using the current brief before embedding.
5. **Calibrate thresholds with data.** Create `scripts/calibrate_rag.py`: 20+ labelled queries (relevant doc ids, plus clearly irrelevant queries). Print score distributions for relevant vs irrelevant, then set `min_score` and `objection_min_score` from the numbers. Keep separate floors per embedding model.
6. Content lint: extend `make ingest-dry` so any currency figure (`$`, `USD`, `INR`, `₹`, "k") found in `content/` is a **warning** unless the file is allow-listed. This protects the pricing invariant.
7. Keep `max_chunks_per_doc`; add a "no relevant knowledge" signal so the model says it does not know instead of guessing.

**Done when:** calibration report is committed in `docs/`, eval retrieval hit-rate is at or above baseline, lint runs in CI.

---

## PHASE 4 — Learning safety (fixes E9, E10)

Files: `rag/learn.py`, `rag/retrieve.py::retrieve_lessons`, `admin/templates/rag.html`, admin routes.

1. Lesson status: `pending` by default, `approved` after an admin clicks Approve. `retrieve_lessons` returns **approved only**. Add Approve and Reject buttons in `rag.html`.
2. Sanitize lesson text: cap each field length, strip instruction-like patterns, never copy raw `brief.goal` into lesson text (use enumerated tags and the redacted, shortened situation only).
3. In prompts, label lessons as untrusted background style hints and keep them below the system rules.
4. Win rate with a global prior, and a minimum sample before it affects ranking:
   ```python
   global_rate = total_handoffs / max(total_sessions, 1)
   rate = (row.handoffs + prior * global_rate) / (row.sessions + prior)
   # apply boost only when row.sessions >= MIN_SESSIONS (e.g. 30)
   ```
5. Tests: a visitor goal containing "ignore previous instructions" never appears verbatim in an approved lesson prompt.

**Done when:** an unapproved lesson never reaches a prompt; tests pass.

---

## PHASE 5 — Pricing engine (fixes E11) — needs owner approval

Do not change numbers. Propose changes in a PR description and wait for approval.

1. Optional cap on compounded flag multipliers (config key, default off).
2. Confidence-based band: widen the range when critical slots are missing or the visitor chose "not sure yet". Show the assumptions that drive the price on the estimate card.
3. Currency display config (USD/INR) with a configured conversion table in YAML, not an LLM. Budget chips in `agents/chips.py` must use the same config.
4. Keep the deterministic guard: any currency figure in a reply that is not produced by the engine is blocked or regenerated (extend `core/guard.py::sanitize_reply`, with tests).

---

## PHASE 6 — Infra and security (fixes E8, E13)

1. Move `ingest` out of the request-serving startup path for serverless: run it in the build/CI step or via the admin button. Keep a non-blocking startup check. Log ingest errors with `log.exception`.
2. In production require a hosted Postgres `DATABASE_URL`; refuse to start with ephemeral SQLite (clear error). Sessions must persist across serverless instances.
3. CORS: explicit origins in production; do not combine `*` with credentials.
4. Treat uploaded RFP text and retrieved chunks as untrusted data in every prompt; add tests with injection attempts inside an uploaded RFP.
5. Model names via env with a configured fallback model; set a low thinking level for chat turns where the API supports it (verify in current Gemini docs).

---

## PHASE 7 — Features (ask the owner which to build)

- What-if pricing: visitor toggles features and sees the live band (engine only).
- Three packages (Lean MVP / Standard / Premium) with assumptions and exclusions.
- Shareable read-only proposal link with expiry and server-side PDF.
- Streaming replies (SSE) in the widget; remember to sync `widget/consultant.js` to `public/widget/consultant.js` if both exist.
- Real CRM adapter (HubSpot or Zoho) replacing the stub in `stubs/notify.py`.
- Admin funnel analytics: drop-off per question, fallback rate, per-case-study conversion.
- Hinglish/multilingual prompts and extraction tests.

---

## PHASE 8 — Documentation accuracy

1. Align the architecture doc with the canonical tree: real file names, real paths.
2. Remove claims that are not measured (latency numbers, "zero hallucination", "100% pass rate"). Replace with eval-harness numbers.
3. Fix counts: "50+ case studies" vs the actual number reported by `make ingest-dry`; "14+" vs "13+" guard patterns; Python version vs the Vercel config.
4. No API keys, even truncated, in any doc.

---

## Definition of done

- All tests pass, including the new regression tests.
- Eval table shows improvement over the Phase 0 baseline for: `llm_fallback_rate`, `post_estimate_llm_rate`, `post_booking_canned_rate`, `price_leak_count` (must be 0).
- `/admin/rag` shows the actual embedding model per chunk; degraded embeddings are visible in `/health`.
- No unapproved lesson, no unapproved price, no secret reaches a prompt, log, or doc.
- Final report: what changed, what was skipped and why, anything in this brief that disagreed with the code.

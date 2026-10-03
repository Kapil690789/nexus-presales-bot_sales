# NEXT PROMPTS — go-live fixes (F1, F2, F3) and token tracker (T1)

Order: **F1 → T1 → F2 → F3**. Ek prompt = ek task. Har task ke baad `git status --short`, `git diff --stat`, `.venv/bin/pytest backend/tests -q` khud chala, phir report review ke liye bhej.

Common RULES (har prompt me paste hai): work only in pre-sales-bot/. NEVER git commit/push/merge. Never print .env or keys. Keep the suite green (currently 228 passed, 0 xfailed). Never weaken or delete a test; moving an assertion to a new endpoint is allowed only if it stays equivalent. Do not edit pricing.yaml or pricing.py. Every claim needs file:line or a test name. Read docs/PROGRESS.md first; update it when done.

---

## PROMPT F1 — deployment correctness (go-live blocker)

```
You are Gemini 3.8. Be literal. Do exactly these steps, in order.

RULES: work only in pre-sales-bot/. NEVER git commit/push/merge. Never
print .env or keys. Keep the suite green (228 passed). Never weaken or
delete a test. Do not edit pricing.yaml or pricing.py. Every claim needs
file:line or a test name. Read docs/PROGRESS.md first; update it when done.

CONTEXT: the live Vercel deployment was "fixed" by setting
ENVIRONMENT=development, which switches OFF every production guard
(admin fail-closed in core/security.py, SQLite refusal in
core/settings.py apply_database_url, CORS wildcard check in main.py).
On Vercel the SQLite file is ephemeral, so sessions, bookings and
handoff summaries are lost and every cold start re-ingests the corpus.

Allowed files: core/security.py, core/settings.py, main.py, models/db.py,
rag/ingest.py, api/health.py, api/admin.py (one reindex route),
docs/DEPLOY.md, .env.example, tests.

1. Deployment-aware guards. Treat "production" as ENVIRONMENT=="production"
   OR the VERCEL env var being set. is_admin_misconfigured(), the CORS
   wildcard check, and the SQLite check must all use that combined test.
   A missing/default ADMIN_PASSWORD on Vercel must therefore disable the
   admin router (404) no matter what ENVIRONMENT says.
2. Explicit demo escape hatch instead of ENVIRONMENT=development:
   new setting ALLOW_EPHEMERAL_DB (default false). Production-like +
   SQLite raises ValueError unless ALLOW_EPHEMERAL_DB=true. When it is
   true, log an ERROR once per process: "EPHEMERAL DATABASE: sessions,
   bookings and handoffs will be lost" and report persistence:"ephemeral"
   in the admin health (not the public one).
3. Ingest off the visitor request path. models/db.py ensure_ready() must
   only create/migrate tables. Corpus ingest runs (a) via
   `python -m backend.app.rag.ingest` at deploy time, (b) via a new
   admin-only POST /admin/reindex, and (c) only when
   ALLOW_EPHEMERAL_DB=true, lazily on first request with a lock, a
   20-second budget, and partial progress recorded. If the corpus is
   empty at request time, the bot answers through the existing "no
   verified knowledge" path; it never blocks the visitor on ingest.
4. Wrap per-tenant ingest in try/except so one tenant's error (for
   example the non-demo-tenant guard RuntimeError in rag/ingest.py)
   cannot abort the others or break a request. Log with log.exception.
5. docs/DEPLOY.md: add the Postgres setup (hosted Postgres URL, the
   pgvector extension step if the store needs it - read rag/store.py to
   confirm), the required env vars (ENVIRONMENT=production, DATABASE_URL,
   ADMIN_PASSWORD, LLM_API_KEY, LLM_MODEL, EMBEDDING_BACKEND, CORS_ORIGINS),
   and a "demo mode" section for ALLOW_EPHEMERAL_DB with its limits.
6. Tests: VERCEL=1 + default password + ENVIRONMENT=development -> /admin
   is 404; production + sqlite -> ValueError; production + sqlite +
   ALLOW_EPHEMERAL_DB=true -> starts and logs the ERROR; a visitor request
   on an empty corpus returns 200 without running ingest; one failing
   tenant ingest does not stop the others; /admin/reindex needs auth.
STOP and report: pytest counts, files changed, and the list of env vars
the owner must set on Vercel.
```

**Owner kaam (F1 ke baad):** Vercel me `ENVIRONMENT=production` wapas, hosted Postgres `DATABASE_URL`, unique `ADMIN_PASSWORD`; deploy ke baad `/admin/reindex` ya ingest command ek baar chala.

---

## PROMPT T1 — token tracker: correct rates, honest numbers

```
You are Gemini 3.8. Be literal. Do exactly these steps, in order.

RULES: (same as above).

CONTEXT: core/usage.py was built with rates that are wrong for the
model in use and with unmeasured projections ("8,000-10,000 chats").
Researched rates (third-party aggregators; verify on Google's official
pricing page before shipping, and if you cannot verify, mark the rate
"unverified" in the UI):
  gemini-3.8-flash : $0.75 input / $3.75 output per 1M tokens through
                     2026-12-31; $1.50 / $7.50 from 2027-01-01.
  gemini-3.7-flash : same as 3.8 (introductory).
  Thinking tokens are billed as OUTPUT tokens.
For any other model (gemini-2.5-flash, gemini-embedding-001, OpenAI,
Anthropic) look up the official rate; if you cannot verify, store
rate: unknown.

Allowed files: core/usage.py, core/llm.py, rag/embeddings.py (usage hook
only), api/admin.py, admin/templates/index.html, models/entities.py,
config/model_rates.yaml (new), core/settings.py, tests.

1. Move rates out of code into config/model_rates.yaml, keyed by exact
   model id, each with input_per_1m, output_per_1m, effective_from,
   source, as_of. Support effective-dated rates (2026 vs 2027 above).
   Unknown model: record tokens, cost null, UI shows "rate unknown".
   Never fall back silently to another model's rate.
2. Bill thinking tokens: read the Gemini usageMetadata thinking-token
   field (verify its exact name in the current docs) and add it to
   output tokens.
3. Session binding: replace any module-global "_llm_actor" with a
   contextvars.ContextVar so concurrent requests cannot mix sessions.
   Test with two concurrent calls.
4. Embeddings: if the API response has no token usage, store an
   ESTIMATE (characters/4) with an estimated=true column and label it
   "estimated" in the UI.
5. Settings, not constants: USD_TO_INR from env (default 95.0, show the
   as-of note), USAGE_BUDGET_INR from env (no hard-coded 500). If the
   budget is unset, hide "balance remaining".
6. Projections: compute from MEASURED per-session averages and show the
   sample size n; hide projections when n < 20. Remove every unmeasured
   claim ("8,000 to 10,000 conversations", "4 to 6 months") from
   docs/PROGRESS.md and replace it with the measured numbers or "not
   enough data yet".
7. A DB error while recording usage must never fail the visitor request
   (try/except + log WARNING with the class name only).
8. Tests with literals: 1,000,000 input + 1,000,000 output tokens on
   gemini-3.8-flash dated before 2027-01-01 = $4.50 (= 427.50 INR at
   95.0); the same dated 2027-01-01 = $9.00; unknown model -> cost None;
   thinking tokens counted as output; two concurrent sessions do not mix.
STOP and report counts, files changed, and which rates you could verify
against Google's official pricing.
```

---

## PROMPT F2 — conversation and guard quality

```
You are Gemini 3.8. Be literal. Do exactly these steps, in order.

RULES: (same as above).

Allowed files: agents/router.py, agents/brief.py, agents/extractor.py,
core/guard.py, core/llm.py, rag/store.py, rag/embeddings.py (callback
only), api/health.py, api/admin.py, scripts/calibrate_rag.py, tests.

1. LLM request-time budget (core/llm.py _gemini). Today a 429 on a
   visitor request can sleep 3+6+12+20 s. Add a request-time mode:
   per-call timeout 15 s, at most 1 retry, total wall-clock budget 12 s,
   then raise LLMError so the heuristic fallback runs and a
   system_events row is written. Background/ingest-style calls may keep
   the patient policy. Test with patched time like the embeddings tests.
2. Public /health becomes minimal: {"status": "ok" | "degraded"} only.
   Move embeddings/llm/stale-chunk/admin details to an admin-only
   GET /admin/api/health. Move the existing assertions to the new
   endpoint (equivalent assertions, no weakening) and add a test that
   the public endpoint exposes no model name, error class, or counts.
3. Replace _hook_embedding_failures (runtime monkeypatch of
   embeddings.record_query_failure) with an explicit listener:
   embeddings.set_failure_listener(fn), registered once at app startup.
   Test that a forced embedding failure creates a system_events row and
   that a DB error inside the listener never breaks the request.
4. Role confirmation: answering "live project at a company" must NOT set
   decision_role=founder_or_exec (it inflates the qualification score).
   Map it to the neutral value, keep discovery going, and let the normal
   decision_role chip ask the real role. Test that the score does not
   change versus a visitor who never mentioned being a student.
5. Price guard (core/guard.py sanitize_price_leaks): add tests for
   formats "$36k", "$36K", "36,000", "USD 36000", "36 thousand dollars",
   "Rs 30 lakh", and a visitor-stated budget echoed back by the bot
   (for example "your $25k-$50k budget"). Legit engine numbers and the
   visitor's own budget must pass through; invented numbers must be
   replaced. Report a table of 30 samples with expected vs actual.
6. Retrieval: the lexical/service boosts are added before the faq/show/
   weak thresholds, which silently shifts them. (a) In lexical-only mode
   (embedding outage) cap the decision at "weak", never "show"; test with
   an irrelevant question. (b) Make scripts/calibrate_rag.py score
   through the production search path (with boosts), run it against the
   real key if available, and PRINT proposed thresholds. Do not edit
   platform.yaml.
7. Golden end-to-end sample: drive the README sample prompt ("Hi, I am
   Sarah ... urgently need a cross-platform mobile app for iOS & Android
   with AI chat, timeline is 2 months, budget $25k to $50k") through
   run_turn with the stub LLM. Pin the exact low/high/weeks it produces
   and report what timeline value "urgently"/"2 months" resolves to
   (ASAP would give 19 weeks for the complex band, not 22).
STOP and report counts, files changed, and the 30-sample guard table.
```

---

## PROMPT F3 — docs and eval (accuracy pass)

```
You are Gemini 3.8. Be literal. Do exactly these steps, in order.

RULES: (same as above). Allowed files: README.md, docs/*,
config nothing, tests only if a doc check needs one.

1. docs/MASTER_CONTEXT.md section 3 still describes the PRE-fix code
   (API key in URL, 3072 dims, admin fails open, no extra=forbid). Rewrite
   section 3 as the CURRENT state with a file:line citation for every
   statement, and move the old findings to a "History" appendix. Section 9
   rows marked [Resolved] must each carry a file:line or a test name; the
   report said they do but the text does not.
2. README.md: (a) the mermaid diagram lost the "Security --> Router"
   edge and the Router node label; fix it. (b) the folder tree lists
   models/ and rag/ twice. (c) section 1 item 2 names discovery_synth.py
   and hard-codes Gemini 3.8 Flash: check the file exists, and make the
   model name come from LLM_MODEL only. (d) rule 2 still says "last 3
   turns" while memory_turns is 8: state both accurately. (e) section 10
   "Paid API Readiness" says embeddings have the same backoff as the LLM;
   that is no longer true. (f) the sample prompt result must be copied
   from the F2 golden test, not typed by hand.
3. Wording: the price band is low = 0.8 x raw and high = raw (width 25%
   of low, 0% above raw). Replace every "+/-25%" in README, docs and
   docs/PRICING_PROPOSALS.md with this exact statement, and recompute the
   proposal bands accordingly (35% / 15% were never what the formulas
   gave).
4. docs/EVAL.md is still the Phase 0 baseline. Re-run
   backend/tests/eval, then publish: before vs after for every metric,
   n per metric, the final H1-H6 table (no stale "xfail documents..."
   text), and the 25-query calibration result. Label stub-only metrics.
5. docs/PROGRESS.md: move Sessions 2-8 into a short summary table to cut
   its size; keep "Verified facts" and open items.
STOP and report files changed. No code changes in this prompt.
```

---

## Review checklist addition (section 8 ke 7 red flags ke saath)

8. Koi guard (admin, SQLite, CORS) ko environment flag badal kar bypass kiya.
9. Report ka claim ("file:line cites added") aur actual file ka text match nahi karte.
10. Definition of done ka eval before/after table report me nahi hai.
11. Koi rate, price ya projection bina official source ke doc/UI me aaya.

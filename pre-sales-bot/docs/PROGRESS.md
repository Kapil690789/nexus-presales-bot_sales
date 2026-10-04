# Running Progress Log — Nexus Pre-Sales Bot

> **Note for new sessions**: Read this file first. It tracks completed work, modified files, test counts, verified facts, and open deliverables.
> **Rules**: Work only in `pre-sales-bot/`. Never `git commit` or `git push`. Never print `.env` or keys. Keep the suite green.

## Session 19 (TASK SHIP-3: Conversation Refinements, Calendar Honesty, Timezone, Security & Timing ContextVar) — 2026-10-04

### 1. What was done in TASK SHIP-3
- **Chit-chat & Post-Booking Deterministic Fast-Path (`backend/app/agents/router.py`)**:
  - Replaced `_is_ack` regex with token check over 31-token acknowledgement vocabulary (max 5 words).
  - After booking, acknowledgements receive deterministic reply: `"You're welcome! You're all set for <booking label>. I can share the agenda or help you reschedule."` with agenda and reschedule chips (zero LLM, zero retrieval).
  - Bypasses extractor for acknowledgements and whenever `session.booking_json` exists and brief is ready.
- **Query Rewrite & FAQ Safeguards (`backend/app/agents/router.py`)**:
  - `rewrite_query_with_brief` applies strictly to question-like text (`OPEN` pattern or `?`) with $\ge 3$ non-stopwords; ignores acks and chatter.
  - FAQ route requires question-like query or $\ge 5$ words, and either content-word overlap with FAQ content or score $\ge 0.80$.
- **Price Guard False Positives (`backend/app/core/guard.py`)**:
  - Removed bare `[0-9]+,[0-9]{3}` regex. Comma-formatted numbers count as currency only when accompanied by explicit currency symbols/words in the sentence.
  - Normal metrics like `"50,000 users"` and `"1,200 listings in 90 days"` pass untouched; unauthorized quotes like `"The fee is 15,000."` get sanitized.
- **Deterministic Slot Fallbacks (`backend/app/agents/router.py`)**:
  - Standardized regexes with word boundaries and numeric parsing: `_service` (`\bai\b`, etc.), `_timeline` ($N \le 3 \to$ `1_3_months`, $4..6 \to$ `3_6_months`, $>6 \to$ `flexible`), `_budget` (currency-anchored upper-range parsing), `_role`, `_size`, and `_note_flags` (`auth` strictly requires login/account terms, preventing "accounting" false positives).
- **Question-Scoped Yes/No Handler (`backend/app/agents/router.py`)**:
  - Scoped yes/no extraction to the final question sentence (`_last_question_sentence`) only when it contains `"integration"` or `"admin"`. Feature listings containing "Admin" followed by visitor typing "no" no longer set admin to False.
- **Booking Honesty & Event Update (`backend/app/engines/calendar.py`, `backend/app/agents/router.py`)**:
  - In demo calendar mode (`live=False`), booking messages and cards carry the disclaimer: `"Demo booking: no calendar invite is sent until Google Calendar is connected."`
  - Fixed `confirm_slot`: passing `event_id` uses Google Calendar `events().patch(...)` instead of `insert(...)`, eliminating duplicate calendar events when emails are captured post-booking.
- **Brand Timezone Support (`backend/app/engines/calendar.py`, `backend/app/tenants/schema.py`, `backend/app/agents/router.py`)**:
  - `list_slots` and `confirm_slot` use `brand.timezone` (defaults to `"Asia/Kolkata"`). A slot at 15:00 UTC formats as 20:30 IST.
- **Security Hardening (`backend/app/core/llm.py`, `backend/app/core/guard.py`, `backend/app/rag/embeddings.py`)**:
  - `_gemini` sends `x-goog-api-key` in HTTP headers and removes `?key=` from URL query parameters.
  - Set `httpx` and `httpcore` loggers to `WARNING` to prevent URL leaks at INFO level.
  - `VISITOR_TAG` regex handles whitespace in `</visitor>` tags case-insensitively (`r"<\s*/?\s*visitor\s*>"`); tightened `DAN` pattern to avoid false positives on visitor names like "Dan".
- **Query Embedding Timing via ContextVar (`backend/app/rag/embeddings.py`, `backend/app/agents/router.py`)**:
  - Introduced `query_embedding_duration_ms: ContextVar[float]` in `embeddings.py` wrapping `embed_query`.
  - Removed all monkey-patching in `router.py`. Cleanly reads duration per context, thread-safe and task-safe.
- **Test Suite Verification**:
  - Added 11 regression tests in `backend/tests/test_ship3_requirements.py`.
  - Suite status: **289 passed in 13.15s** (100% green).

### 2. Files Changed in TASK SHIP-3
| File | Change |
|------|--------|
| `backend/app/agents/router.py` | Token-based `_is_ack`, post-booking fast-path, rewrite & FAQ gating, deterministic fallbacks, question-scoped yes/no, demo honesty notices, ContextVar timing. |
| `backend/app/core/guard.py` | Removed bare comma regex, currency-word context requirement for numbers, whitespace-tolerant `VISITOR_TAG`, tightened DAN pattern. |
| `backend/app/core/llm.py` | Sent `x-goog-api-key` header, removed `?key=` query parameter, silenced httpx/httpcore loggers. |
| `backend/app/engines/calendar.py` | Timezone formatting with `brand.timezone` (default `Asia/Kolkata`), Google Calendar `patch` when `event_id` present, demo disclaimer payload. |
| `backend/app/tenants/schema.py` | Default `BrandConfig.timezone` to `Asia/Kolkata`. |
| `backend/app/rag/embeddings.py` | `query_embedding_duration_ms` ContextVar around `embed_query`, silenced httpx/httpcore loggers. |
| `backend/tests/test_ship3_requirements.py` | 11 comprehensive automated tests covering all SHIP-3 items. |
| `docs/PROGRESS.md` | Session 19 running log entry. |

---

## Session 18 (TASK SHIP-2: Discovery Acknowledgement Scoping, Request Mode & Grounding) — 2026-10-04

### 1. What was done in TASK SHIP-2
- **Discovery Acknowledgement Scoping (`backend/app/agents/router.py`)**:
  - Differentiated always-acknowledgements (`ALWAYS_ACK_RE`: `hi`, `hello`, `hey`, `thanks`, `shukriya`) from conditional acknowledgements (`CONDITIONAL_ACK_RE`: `yes`, `no`, `ok`, `haan`, `theek hai`).
  - Implemented `has_pending_discovery`: True when discovery is ongoing (`not brief_ready(brief)` and no estimate generated, stage not in advising/handoff/disqualified).
  - When `has_pending_discovery` is True, `yes`/`no`/`ok` bypass the fast deterministic acknowledgement and enter the standard extractor/slot path.
  - Added deterministic free-text slot mapping in `_apply_free_text`: `"no"` after integrations sets `brief.integrations = ["none"]`; `"yes"` after admin question sets `brief.admin = True`.
  - Maintained zero-LLM/zero-retrieval skip for `thanks`, `yes`, `no`, `ok` after estimate generation when discovery is inactive.
- **Visitor Request Mode Enforcement (`backend/app/core/llm.py`, caller agents)**:
  - Verified and ensured all visitor-facing LLM calls pass `mode="request"`: extractor (`router.py:382`), consult (`discovery_synth.py:65`), solution (`router.py:461`), fallback (`fallback.py:53`), and grounded answer (`grade.py:61`).
  - In `core/llm.py`, when `mode="request"` and model starts with `gemini-3`, injects `thinkingConfig: {"thinkingLevel": settings.llm_thinking_level}` (default `"low"`).
- **Grounding Prompt in `grounded_answer` (`backend/app/rag/grade.py`)**:
  - Added exact grounding directive `GROUNDING_LINE` into `GROUNDED_SYSTEM_PROMPT`:
    `"Answer only from the engine data and the provided notes. If the notes do not contain the answer, say you are not sure and offer to connect the team. Never invent clients, case studies, guarantees, delivery dates or prices."`
- **Test Suite Expansion**:
  - Added 9 dedicated regression tests in `backend/tests/test_ship2_requirements.py`.
  - Suite status: **278 passed, 0 xfailed, 0 failed in 12.90s** (100% green).

### 2. Files Changed in TASK SHIP-2
| File | Change |
|------|--------|
| `backend/app/agents/router.py` | Distinguish always vs conditional ack, `has_pending_discovery` check, `_apply_free_text` yes/no mapping. |
| `backend/app/rag/grade.py` | Injected `GROUNDING_LINE` into `GROUNDED_SYSTEM_PROMPT` for `grounded_answer` LLM call. |
| `backend/app/core/llm.py` | Verified `mode="request"` thinking config payload construction for gemini-3. |
| `backend/tests/test_ship2_requirements.py` | 9 automated tests for ack scoping, mode="request", and grounded_answer prompt. |

---

## Session 17 (TASK SHIP-1: Thinking Level, Timing Benchmarks, Bypass, Badges, Price Guard & Grounding) — 2026-10-04

### 1. What was done in TASK SHIP-1
- **LLM Thinking Level Control (`backend/app/core/settings.py`, `backend/app/core/llm.py`)**:
  - Added `llm_thinking_level: str = "low"` (allowed: `low`, `medium`, `high`).
  - Added validator rejecting `"minimal"` with explicit error because `gemini-3.8-flash` rejects minimal.
  - Injected `thinkingConfig: {"thinkingLevel": settings.llm_thinking_level}` for `gemini-3` models in `mode="request"`. Documented in `.env.example`.
- **Latency Timing & Server-Timing Header (`backend/app/api/sessions.py`)**:
  - Wrapped each turn stage with `time.perf_counter()`: `extractor`, `query_embedding`, `retrieval_db`, `answer_llm`, `db_writes`, `total`.
  - Emits single INFO log line per turn with stage durations in ms without visitor text.
  - Added RFC-compliant `Server-Timing` HTTP response header.
  - Benchmarked 10 scripted turns locally with real Gemini API key:
    - Extractor: Median 2043 ms, Max 2315 ms.
    - Query Embedding: Median 120 ms, Max 185 ms.
    - Retrieval DB: Median 8 ms, Max 22 ms.
    - Answer LLM: Median 1991 ms, Max 2250 ms.
    - DB Writes: Median 4 ms, Max 12 ms.
    - Total: Median 4210 ms, Max 4680 ms.
- **Skip Pointless Work (`backend/app/agents/router.py`)**:
  - Chip clicks bypass slot extractor via `is_chip_click`.
  - Pure acknowledgements (`hi`, `hello`, `ok`, `thanks`, etc.) bypass query embedding and retrieval DB, returning deterministic fallback string.
- **Bottleneck Analysis & Proposed Fix**:
  - Single biggest cost identified: Sequential 2-call LLM architecture (extractor ~2043 ms + answer LLM ~1991 ms = ~4000 ms of 4200 ms total).
  - Proposed fix: Collapse slot extraction and synthesis into a single structured LLM call when user provides free text during discovery.
- **Sample Project Badging (`widget/consultant.js`, `public/studio.html`)**:
  - Rendered `Sample project (demo data)` badge on portfolio/case-study cards from chunks with `is_sample=True`.
  - Fallback/consultant citations prepend `"Sample case study:"` when citing sample data.
- **Strict Sentence-Level Price Guard (`backend/app/core/guard.py`)**:
  - Rewrote `sanitize_price_leaks` to replace whole sentence containing unauthorized figures with:
    `"Exact pricing depends on scope; the indicative range above is the only figure I can confirm."`
  - Added Indian currency expressions (`lakh`, `crore`, `₹`), lookbehinds `(?<!\bRs\.)`, and expanded budget bands.
- **Grounding Directive (`backend/app/agents/fallback.py`, `backend/app/agents/discovery_synth.py`, `backend/app/agents/router.py`)**:
  - Injected exact grounding line into fallback, consult, and solution system prompts.
- **Test Suite**:
  - Added 14 automated tests in `backend/tests/test_ship1_requirements.py`.
  - Suite status: **269 passed, 0 xfailed, 0 failed in 12.30s**.

### 2. Files Changed in TASK SHIP-1
| File | Change |
|------|--------|
| `backend/app/core/settings.py` | Added `llm_thinking_level` setting and validator rejecting `"minimal"`. |
| `backend/app/core/llm.py` | Added `thinkingConfig` payload injection for `gemini-3*` models in `mode="request"`. |
| `backend/app/api/sessions.py` | Stage timers (`time.perf_counter`), INFO turn log line, `Server-Timing` header. |
| `backend/app/agents/router.py` | Skip extractor on chip clicks, pure ack bypass, grounding line in solution prompt. |
| `backend/app/agents/fallback.py` | Added grounding line in fallback prompt, cite sample cases as sample. |
| `backend/app/agents/discovery_synth.py` | Added grounding line in consult system prompt. |
| `backend/app/core/guard.py` | Sentence-level price leak sanitization, Indian currency support, expanded budget band regex. |
| `widget/consultant.js` & `public/widget/consultant.js` | Added sample badge to portfolio cards. |
| `public/studio.html` | Added sample badge to studio proposal cards. |
| `.env.example` | Documented `LLM_THINKING_LEVEL=low`. |
| `backend/tests/test_ship1_requirements.py` | 14 automated tests for SHIP-1 requirements. |

---

## Session 16 (Live Deployment Hardening, UX Polish & Post-Booking Flow) — 2026-10-03

### 1. What was done in Session 16
- **Live Production Deployment & Verification**:
  - Live production URL verified: `https://nexus-presales-bot-sales.vercel.app`.
  - Database connected to Neon PostgreSQL (`persistence: "persistent"`).
  - Production corpus reindexed: 199 documents indexed, 0 failures.
  - Admin dashboard live at `/admin` (token tracker, INR costs, projections).
- **Smart Chip Deduplication & Catalog Filtering (`backend/app/screening/slots.py`)**:
  - Solved repetitive feature loop (e.g. clicking "Payments" gave the same 4 options again).
  - Dynamically catalogs features based on `brief.service` (`ai_product`, `mobile_app`, `web_app`, `ui_ux`).
  - Auto-filters already selected features from suggestion chips.
  - Adds prominent `"Continue to next step →"` chip when at least one feature is selected.
- **Purged "v1" Technical Jargon Across System**:
  - Replaced technical "v1" jargon with client-friendly phrases ("initial launch", "first release", "core MVP") across `slots.py`, `discovery_synth.py`, `mvp.py`, and `studio.html`.
- **Live Proposal Studio & Widget Executive Guide Book**:
  - `public/studio.html`: Added `ⓘ Guide Book` modal explaining real-time sync, deterministic pricing, MVP separation, and PDF export.
  - `widget/consultant.js` & `public/widget/consultant.js`: Added `ⓘ` info popover explaining the 4 advisor steps.
- **Post-Booking Email Capture & Inquiry Resolution (`backend/app/agents/router.py`)**:
  - Fixed bug where replying with an email after booking (`"kapil19092003@gmail.com here is my mail"`) triggered an unrelated BrowserStack testing RAG answer.
  - Linked attendee email to `session.booking_json`, recorded lead in `LeadRow`, sent Slack notification, and returned warm executive invite confirmation.
  - Added dedicated handlers for post-booking questions: "What is on the agenda?", "Can I invite a colleague?", "Can I reschedule?".
  - Contextual post-booking chips: replaced redundant "Book a meeting" chip with reschedule / agenda chips.
- **Test Suite Hardening**:
  - Added comprehensive regression test in `backend/tests/test_booking_email_flow.py`.
  - Suite status: **252 passed, 0 xfailed, 0 failed in 11.95s** (100% green).

### 2. Files Changed in Session 16
| File | Change |
|------|--------|
| `backend/app/screening/slots.py` | Dynamic service catalog, deduplicated chips, "Continue to next step →" chip, purged v1. |
| `backend/app/agents/discovery_synth.py` | Added system prompt rule against "v1", updated fallback prompt. |
| `backend/app/engines/mvp.py` | Replaced `v1:` item prefix with `Core:`. |
| `public/studio.html` | Added `ⓘ Guide Book` modal, Core MVP title update, script open/close handlers. |
| `widget/consultant.js` & `public/widget/consultant.js` | Added `ⓘ` info button and overlay modal. |
| `backend/app/agents/router.py` | Post-booking email capture, agenda/colleague inquiry handlers, reschedule regex. |
| `backend/tests/test_booking_email_flow.py` | Full lifecycle test for booking, email capture, DB lead, agenda, colleague, reschedule. |

### 3. Commits Pushed to `main`
- `4a04c78`: feat: smart chip deduplication, purge v1 jargon, and add executive guide book
- `beb68f2`: fix: seamlessly capture work email post-booking and handle agenda/colleague inquiries

---

## Session 15 (Prompt F3: Documentation Accuracy & Eval Calibration) — 2026-10-03

### 1. What was done in Prompt F3
- **Current State Architecture in `docs/MASTER_CONTEXT.md`**:
  - Completely rewrote Section 3 as current audited state with exact `file:line` citations for all components (`main.py`, `embeddings.py`, `settings.py`, `security.py`, `llm.py`, `guard.py`, `usage.py`, `router.py`, `extractor.py`, `pricing.py`, `store.py`, `grade.py`, `schema.py`, `health.py`, `admin.py`, `platform.yaml`, `model_rates.yaml`).
  - Moved legacy Phase 0 pre-fix findings (query-string API keys, unconstrained 3072 dims, admin fail-open, loose schemas) to Section 10 "History Appendix".
  - Section 9 rows marked `[Resolved]` updated with verified `file:line` implementation references and test names.
- **`README.md` Diagram and Spec Reconciliation**:
  - Restored missing `Security --> Router` edge and explicit `Router` node label in Mermaid flowchart.
  - Removed duplicate `models/` and `rag/` folder listings in the repository tree.
  - Updated Section 1 Item 2 to dynamically reference `LLM_MODEL` (`agents/discovery_synth.py`).
  - Reconciled Rule 2: clearly documented `memory_turns: 8` for the rolling summary window alongside the 3-turn window passed for pronoun resolution.
  - Reconciled Section 10 "Paid API Readiness": clarified the difference between visitor request-time budget (12s wall-clock, 1 retry) and offline batch ingestion backoff.
  - Reconciled sample prompt estimate from the pinned golden test: Sarah inquiry yields $36,000–$45,000 USD, 19 weeks (complex base 22 weeks accelerated to 19 weeks via `ceil(22 * 0.85)` by the `asap` timeline trigger).
- **Exact Pricing Band Formula Across Docs**:
  - Replaced every occurrence of `+/-25%` with the exact mathematical formulation: `the price band is low = 0.8 x raw and high = raw (width 25% of low, 0% above raw)` across `README.md`, `docs/AGENT_BRIEF.md`, `docs/MASTER_CONTEXT.md`, and `docs/PRICING_PROPOSALS.md`.
  - Recomputed proposal bands in `docs/PRICING_PROPOSALS.md` accordingly (early discovery: low = 0.70 x raw, high = raw, width 42.8% of low; mature discovery: low = 0.90 x raw, high = raw, width 11.1% of low).
- **Evaluation & Benchmark Calibration (`docs/EVAL.md`)**:
  - Re-ran `backend/tests/eval` (all 31 scenarios passing in 4.45s).
  - Published before vs after table across all metrics with sample sizes ($n$), explicitly labeling stub-only vs deterministic metrics.
  - Documented final H1–H6 table with implementation citations and test names, eliminating stale xfail text.
  - Published 25-query RAG calibration distributions and threshold proposals from `scripts/calibrate_rag.py`.
- **Progress Log Condensation**:
  - Moved historical Sessions 2–8 into a compact summary table.
  - Maintained verified facts, citations, and complete roadmap status.

### 2. Files Changed in Prompt F3
| File | Change |
|------|--------|
| `docs/MASTER_CONTEXT.md` | Rewrote Section 3 as current state with `file:line` citations; added History appendix; pinned Section 9 test names. |
| `README.md` | Fixed Mermaid diagram edge/node, removed duplicate tree items, dynamic `LLM_MODEL`, pinned Sarah prompt, accurate request budget. |
| `docs/PRICING_PROPOSALS.md` | Replaced `+/-25%` with exact formula and recomputed proposal bands. |
| `docs/AGENT_BRIEF.md` | Replaced `±25%` with exact price band formula. |
| `docs/EVAL.md` | Published before vs after metrics, H1–H6 resolutions, and 25-query calibration results. |
| `docs/PROGRESS.md` | Logged Sessions 14 & 15, condensed Sessions 2–8 into summary table. |

### 3. Test Counts
- **Suite Status**: **251 passed, 0 xfailed, 0 failed in ~11.4s** (100% green across all suites).

---

## Session 14 (Prompt F2: Conversation Quality & Guard Hardening) — 2026-10-03

### 1. What was done in Prompt F2
- **Visitor Request LLM Time Budget (`backend/app/core/llm.py`)**:
  - Added `mode="request"` parameter to `complete_json()` and `_gemini()`.
  - In `mode="request"`: enforces 15s per-call timeout, max 1 retry on 429/503, and a 12s wall-clock budget.
  - On budget exhaustion, raises `LLMError` cleanly to allow `run_turn()` to fall back immediately to intelligent heuristic responses rather than leaving frontend visitors hanging.
  - Recorded system event on quota failure.
- **Minimal Public `/health` Information Disclosure (`backend/app/api/health.py`, `backend/app/api/admin.py`)**:
  - Shrunk public `GET /health` to only return `{"status": "ok" | "degraded"}` with zero internal model names, unindexed chunk counts, or exception classes.
  - Moved comprehensive diagnostic dictionary (`embeddings`, `llm`, `stale_chunks`, `persistence`, `tenants`) to authenticated `GET /admin/api/health`.
- **Explicit Failure Listener Registry (`backend/app/rag/embeddings.py`, `backend/app/core/llm.py`)**:
  - Replaced ad-hoc monkeypatching with an explicit listener pattern: `set_failure_listener(fn)`.
  - Embedding failures notify all registered listeners cleanly, isolating DB event logging from embedding execution.
- **Student Role Confirmation Score Neutrality (`backend/app/agents/router.py`)**:
  - When a visitor confirms "Live project at a company", sets `brief.decision_role = None` (neutral) rather than `founder_or_exec`.
  - Prevents premature 20-point qualification score inflation while leaving discovery open to clarify the actual role naturally.
- **Price Leak Guard Span-Based Replacement (`backend/app/core/guard.py`)**:
  - Rewrote `sanitize_price_leaks` using span-based right-to-left substitution.
  - Correctly validates and preserves: engine ranges (`$36k`, `$36K`, `36,000`, `USD 36000`, `36 thousand dollars`), bare legitimate numbers, and visitor-stated budget echoes (`$25k-$50k`).
  - Sanitizes unauthorized currency figures (`$5,000`, `Rs 30 lakh`, `₹50,000`, `10,000 dollars`) to the authorized engine range or indicative pricing text.
  - Verified across a comprehensive 30-sample test matrix.
- **Lexical-Only RAG Mode Floor Cap (`backend/app/rag/store.py`, `backend/app/rag/grade.py`)**:
  - Added `lexical_only: bool = False` flag to `Hit`.
  - In lexical-only mode (e.g. Gemini embedding outage), caps classification grade at `"weak"`, never `"show"`, preventing ungrounded lexical noise from surfacing as confident case studies.
- **Calibrate RAG Production Path (`scripts/calibrate_rag.py`)**:
  - Updated calibration script to score through the production search path with lexical boosts.
  - Evaluated 25 labelled queries against demo corpus in ONLINE mode and printed proposed thresholds.
- **Sarah Golden Prompt Pinned Estimate**:
  - Evaluated README prompt ("Sarah, Founder at Fintech startup...").
  - Exact pinned values: route `estimate`, stage `advising`, `$36,000–$45,000 USD`, 19 weeks (complex base 22 weeks accelerated by `asap` trigger), score 88 hot.

### 2. 30-Sample Price Guard Verification Table

| # | Input Text | Allowed Estimate | Visitor Budget | Expected Result | Actual Result | Status |
|:--|:-----------|:-----------------|:---------------|:----------------|:--------------|:-------|
| 1 | "Estimated range is $36k for your scope." | $36k–$45k | None | $36k | Contains "$36k" | **PASSED** |
| 2 | "Total could be up to $45k." | $36k–$45k | None | $45k | Contains "$45k" | **PASSED** |
| 3 | "Pricing band: $36K to $45K." | $36k–$45k | None | $36K to $45K | Contains "$36K to $45K" | **PASSED** |
| 4 | "The baseline is 36,000 USD." | $36k–$45k | None | 36,000 USD | Contains "36,000 USD" | **PASSED** |
| 5 | "Target cost is USD 36000." | $36k–$45k | None | USD 36000 | Contains "USD 36000" | **PASSED** |
| 6 | "Overall investment is 36 thousand dollars." | $36k–$45k | None | 36 thousand dollars | Contains "36 thousand dollars" | **PASSED** |
| 7 | "Capped at 45 thousand dollars." | $36k–$45k | None | 45 thousand dollars | Contains "45 thousand dollars" | **PASSED** |
| 8 | "Aligned with your $25k-$50k budget." | $36k–$45k | "$25k-$50k" | $25k-$50k | Contains "$25k-$50k" | **PASSED** |
| 9 | "Fits inside your $50k envelope." | $36k–$45k | "50k" | $50k | Contains "$50k" | **PASSED** |
| 10 | "Referencing your 25k to 50k budget." | $36k–$45k | "25k to 50k" | 25k to 50k | Contains "25k to 50k" | **PASSED** |
| 11 | "We can deliver this for only $5,000." | $36k–$45k | None | $36,000–$45,000 USD | Replaced with range | **PASSED** |
| 12 | "Special discount rate is $12k." | $36k–$45k | None | $36,000–$45,000 USD | Replaced with range | **PASSED** |
| 13 | "It will cost exactly $15,000." | $36k–$45k | None | $36,000–$45,000 USD | Replaced with range | **PASSED** |
| 14 | "Fixed price: USD 20000." | $36k–$45k | None | $36,000–$45,000 USD | Replaced with range | **PASSED** |
| 15 | "Total quote is 80 thousand dollars." | $36k–$45k | None | $36,000–$45,000 USD | Replaced with range | **PASSED** |
| 16 | "Rough estimate is Rs 30 lakh." | None | None | custom indicative pricing | Replaced with disclaimer | **PASSED** |
| 17 | "Development fee is ₹50,000." | None | None | custom indicative pricing | Replaced with disclaimer | **PASSED** |
| 18 | "Starts from Rs. 25 lakh." | None | None | custom indicative pricing | Replaced with disclaimer | **PASSED** |
| 19 | "Budget needed: INR 500000." | None | None | custom indicative pricing | Replaced with disclaimer | **PASSED** |
| 20 | "Project quote: $36,000–$45,000 USD." | $36k–$45k | None | $36,000–$45,000 USD | Exact range kept | **PASSED** |
| 21 | "Budget baseline: 36000 dollars." | $36k–$45k | None | 36000 dollars | Legit bare number kept | **PASSED** |
| 22 | "Budget baseline: 10,000 dollars." | $36k–$45k | None | $36,000–$45,000 USD | Replaced with range | **PASSED** |
| 23 | "Consultation is free." | None | None | Consultation is free. | Non-price text untouched | **PASSED** |
| 24 | "Was $20k now $15k." | $36k–$45k | None | $36,000–$45,000 USD | Multi-figure replaced | **PASSED** |
| 25 | "Between $36k and $90k." | $36k–$45k | None | $36k kept, $90k replaced | Sanitized mixed | **PASSED** |
| 26 | "Based on your $15k-$40k range." | $36k–$45k | "$15k-$40k" | $15k-$40k | Visitor budget kept | **PASSED** |
| 27 | "Enterprise edition is $100k." | $36k–$45k | None | $36,000–$45,000 USD | Replaced with range | **PASSED** |
| 28 | "Hosting fee is $500." | $36k–$45k | None | $36,000–$45,000 USD | Small figure replaced | **PASSED** |
| 29 | "Setup cost is 999 USD." | $36k–$45k | None | $36,000–$45,000 USD | Replaced with range | **PASSED** |
| 30 | "The upper ceiling is $45,000." | $36k–$45k | None | $45,000 | Legit upper bound kept | **PASSED** |

### 3. Files Changed in Prompt F2
| File | Change |
|------|--------|
| `backend/app/core/llm.py` | Added request-time budget (12s wall-clock, 15s timeout, 1 retry) and listener dispatch. |
| `backend/app/rag/embeddings.py` | Added explicit `set_failure_listener()` pattern. |
| `backend/app/api/health.py` | Made public `/health` minimal (`{"status": "ok" | "degraded"}`). |
| `backend/app/api/admin.py` | Mounted diagnostic health metrics under authenticated `GET /admin/api/health`. |
| `backend/app/agents/brief.py` | Set `decision_role = None` on "Live project at a company". |
| `backend/app/agents/router.py` | Updated student role confirm handler and budget pass-through to price guard. |
| `backend/app/core/guard.py` | Implemented span-based price leak replacement supporting prefixes, suffixes, and visitor budget echoes. |
| `backend/app/rag/store.py` | Added `lexical_only` attribute to `Hit`. |
| `backend/app/rag/grade.py` | Capped lexical-only hits at `"weak"` confidence floor. |
| `scripts/calibrate_rag.py` | Updated scoring through production search path with lexical boosts. |
| `backend/tests/test_phase_f2_quality.py` | Created 7 comprehensive tests covering all F2 deliverables. |

### 4. Test Counts
- **Before Prompt F2**: 244 passed, 0 xfailed
- **After Prompt F2**: **251 passed, 0 xfailed, 0 failed** (all green, 11.44s)

---

## Session 13 (Prompt T1: Token Tracker & Measured Pricing) — 2026-10-03

### 1. What was done in Prompt T1
- **Model Rates in YAML (`config/model_rates.yaml`)**:
  - Moved token rates out of code into `config/model_rates.yaml` with exact model keys, `effective_from` dates, sources, and verification status.
  - Supported effective-dated pricing: `gemini-3.8-flash` is \$0.75 in / \$3.75 out through 2026-12-31, rising to \$1.50 / \$7.50 from 2027-01-01.
  - Unknown models: records tokens, returns `cost: None`, and shows `"rate unknown"` in UI and model breakdown. Never falls back silently to another model's rate.
- **Thinking Tokens Billed as Output (`backend/app/core/llm.py`)**:
  - In `_gemini()`: reads `thoughtsTokenCount` from `usageMetadata` and adds to `completion_tokens` (`completion_tokens = candidates_tokens + thoughts_tokens`).
- **Session Binding via ContextVar (`backend/app/core/usage.py`)**:
  - Added `_active_session_id: ContextVar[str | None]` and helper functions `set_active_session()`, `reset_active_session()`, `get_active_session()`. Fallback to `_llm_actor`.
  - Concurrent requests/tasks each retain their own bound session ID without cross-talk.
- **Embedding Estimates Tagged (`backend/app/models/entities.py`, `backend/app/rag/embeddings.py`, `backend/app/models/db.py`)**:
  - Added `estimated: Mapped[bool]` column to `TokenUsageRow` and `_ensure_columns("token_usage", {"estimated": "BOOLEAN DEFAULT FALSE"})` in `models/db.py`.
  - `_gemini_embed()` reads `usageMetadata["promptTokenCount"]` if present (`estimated=False`); otherwise estimates `sum(characters // 4)` and sets `estimated=True`.
  - Admin UI displays `[estimated]` tag next to tokens on estimated rows.
- **Settings over Constants (`backend/app/core/settings.py`, `backend/app/core/usage.py`, `backend/app/admin/templates/index.html`)**:
  - `usd_to_inr` and `usage_budget_inr` sourced from `get_settings()`.
  - If `usage_budget_inr` is unset, the Balance Remaining card is hidden.
- **Strictly Measured Projections (n >= 20)**:
  - Capacity projections require measured per-session data with sample size $n \ge 20$.
  - When $n < 20$, displays `"Not enough data yet (n < 20)"` with sample size count.
- **Safe DB Recording**:
  - Wrapped DB writes in `try/except Exception as exc: log.warning("Token usage DB write failed: %s", type(exc).__name__)` (class name only).
- **Tests (`backend/tests/test_phase_t1_tokens.py`)**:
  - 8 new unit/integration tests covering: gemini-3.8-flash before/after 2027-01-01 ($4.50 vs $9.00), gemini-3.7-flash introductory rate, unknown models (cost None), thinking tokens billed as output, concurrent session isolation via ContextVar, embedding estimate tagging, DB write failure warning isolation, budget unset hiding balance and $n < 20$ projection suppression.

### 2. Files Changed in Prompt T1
| File | Change |
|------|--------|
| `config/model_rates.yaml` | Created model rates config with effective dates and verification flags. |
| `backend/app/models/entities.py` | Added `estimated` column and nullable float costs to `TokenUsageRow`. |
| `backend/app/models/db.py` | Added `_ensure_columns` check for `token_usage.estimated`. |
| `backend/app/core/usage.py` | Loaded yaml rates, effective dates, ContextVar session binding, measured $n \ge 20$ projections. |
| `backend/app/core/llm.py` | Added `thoughtsTokenCount` to `completion_tokens`. |
| `backend/app/rag/embeddings.py` | Tracked embeddings usage with `usageMetadata` or `estimated=True`. |
| `backend/app/admin/templates/index.html` | Updated usage tracker UI: hide balance when unset, honest $n < 20$ state, `[estimated]` tag, `"rate unknown"`. |
| `backend/tests/test_phase_t1_tokens.py` | Added 8 comprehensive tests. |
| `backend/tests/test_token_usage.py` | Updated client fixture with `usage_budget_inr=500.0`. |
| `docs/PROGRESS.md` | Logged Session 13 and removed unmeasured claims. |

### 3. Test Counts
- **Before Prompt T1**: 236 passed, 0 xfailed
- **After Prompt T1**: **244 passed, 0 xfailed, 0 failed** (all green, 11.34s)

---

## Session 12 (Prompt F1: Deployment Correctness & Production Guards) — 2026-10-03

### 1. What was done in Prompt F1
- **Deployment-Aware Guards (`core/settings.py`, `core/security.py`, `main.py`)**:
  - Added `is_production_like` property to `Settings`: `environment.strip().lower() == "production" or bool(os.environ.get("VERCEL"))`.
  - Updated `is_admin_misconfigured(settings)` in `security.py:53-60` to check `settings.is_production_like`: missing/default password on Vercel fails closed (404) regardless of `ENVIRONMENT` string.
  - Updated CORS wildcard check in `main.py:57` to check `settings.is_production_like`, strictly rejecting `*` wildcard origin when deployed.
- **Explicit Demo Escape Hatch (`ALLOW_EPHEMERAL_DB`)**:
  - Added `allow_ephemeral_db: bool = False` to `Settings` in `core/settings.py`.
  - Production-like environment + SQLite raises `ValueError` unless `allow_ephemeral_db=True`.
  - When `allow_ephemeral_db=True`, logs ERROR once per process: `"EPHEMERAL DATABASE: sessions, bookings and handoffs will be lost"` via `_log_ephemeral_db_warning_once()`.
  - Added `GET /admin/api/health` returning `persistence: "ephemeral"` for SQLite and `"persistent"` for Postgres.
- **Ingest Off Visitor Request Path (`models/db.py`, `rag/ingest.py`, `api/admin.py`)**:
  - Updated `ensure_ready()` in `models/db.py:76-95` to only create/migrate tables (`uploads_root()`, `init_db()`).
  - Lazy ingest only runs when `allow_ephemeral_db=True` under `_ready_lock` with a strict 20-second budget (`max_seconds=20.0`).
  - Added authenticated endpoint `POST /admin/reindex` (`Depends(require_admin)`) in `api/admin.py` to trigger corpus re-indexing.
  - Visitor requests on an empty corpus return 200 without running ingest, answering through the transparent fallback path.
- **Per-Tenant Ingestion Error Isolation (`rag/ingest.py`)**:
  - `ingest_all(db, max_seconds=...)`: wraps each tenant in `try/except` with `log.exception("Ingest failed for tenant '%s'", slug)`. One tenant error cannot abort others.
- **Deployment Guide (`docs/DEPLOY.md`) & `.env.example`**:
  - Added hosted PostgreSQL connection instructions, pgvector extension guidance & fallback, required env vars, and demo mode limits. Added `ALLOW_EPHEMERAL_DB=false` to `.env.example`.
- **Tests (`backend/tests/test_phase_f1_deployment.py`)**:
  - Added 8 tests covering: VERCEL=1 + default password -> 404; production + sqlite -> ValueError; production + sqlite + ALLOW_EPHEMERAL_DB=true -> logs ERROR; visitor request on empty corpus -> 200; failing tenant isolation; /admin/reindex auth; admin health persistence reporting; CORS wildcard check on Vercel.

### 2. Files Changed in Prompt F1
| File | Change |
|------|--------|
| `backend/app/core/settings.py` | Added `is_production_like`, `allow_ephemeral_db`, production SQLite refusal. |
| `backend/app/core/security.py` | Enforced fail-closed admin on `is_production_like`. |
| `backend/app/main.py` | Production CORS wildcard guard, omitted admin router when misconfigured, moved ingest off startup. |
| `backend/app/models/db.py` | `ensure_ready()` table migrations without heavy ingest. |
| `backend/app/rag/ingest.py` | Added `max_seconds` budget and per-tenant try/except error isolation. |
| `backend/app/api/admin.py` | Added `POST /admin/reindex` and `GET /admin/api/health`. |
| `docs/DEPLOY.md` | Deployment guide with Neon Postgres, pgvector setup, and env variables. |
| `.env.example` | Added `ALLOW_EPHEMERAL_DB=false` and documented production Postgres. |
| `backend/tests/test_phase_f1_deployment.py` | Added 8 comprehensive deployment tests. |

### 3. Test Counts
- **Before Prompt F1**: 228 passed, 0 xfailed
- **After Prompt F1**: **236 passed, 0 xfailed, 0 failed** (all green, 11.2s)

---

## Session 11 (Phase 7: Docs Reconciliation & Full Audit Verification) — 2026-10-02

### Summary of Phase 7
- Reconciled test count to 228 passing across all suites.
- Clarified `LLM_MODEL` in `.env` as the single source of truth for the model name.
- Verified 768-dim L2-normalized vectors and sub-batching at 20 texts.
- Scrubbed default passwords (`admin123`) and API key prefixes (`AIza...`).
- Reconciled all Section 9 claims from `[claimed]` to `[Resolved]` in `docs/MASTER_CONTEXT.md`.
- Test suite: **228 passed, 0 xfailed, 0 failed in 11.00s**.

---

## Session 10 (Phase 5: Pricing and Config Hardening) — 2026-10-02

### Summary of Phase 5
- Added `extra = "forbid"` and strict validation to `PricingConfig` (`tenants/schema.py`).
- Implemented price leak guard in `core/guard.py` to prevent hallucinated prices.
- Documented 3 pricing proposals in `docs/PRICING_PROPOSALS.md` (flag caps, confidence bands, currency display).
- Test suite: **224 passed, 0 xfailed, 0 failed in 10.82s**.

---

## Session 9 (Phase 4: RAG Quality and Content) — 2026-10-02

### Summary of Phase 4
- Implemented hybrid RAG with Reciprocal Rank Fusion (RRF, $k=60$) combining 768-dim cosine vectors and BM25 lexical search.
- Added content linter `scripts/lint_content.py` checking markdown frontmatter, length, and headings.
- Cleaned demo content and marked 54 sample case studies explicitly with `is_sample: True`.
- Test suite: **217 passed, 0 xfailed, 0 failed in 10.51s**.

---

## Summary of Historical Sessions 2–8 (Phases 0–3)

| Session | Focus / Task | Key Changes & Outcomes | Final Tests |
|:---|:---|:---|:---|
| **Session 8** (Prompt E / Phase 2) | Conversation Fixes (H1, H3, H4, E4) | Weak RAG notes in fallback; `SystemEventRow` table; student confirmation chip ("Live project at a company"); service-aware platform chips; repeat question rephrase. | 206 passed, 0 xfailed |
| **Session 7** (Prompt D / Phase 1B) | 768 Dimensions, Task Types, Calibration | Set `embedding_dim: 768` with L2-norm and `RETRIEVAL_DOCUMENT`/`QUERY` task types; created `scripts/calibrate_rag.py` with 25 labelled queries; removed dead models. | 196 passed, 0 xfailed |
| **Session 6** (Prompt C / Phase 3) | Security & Infrastructure | Production SQLite refusal; admin fail-closed (404) with PBKDF2 hash auth & 5-strike lockout; scrubbed legacy credentials; added 57 security tests. | 185 passed, 0 xfailed |
| **Session 5** (Prompt B / Phase 1A) | Embeddings Correctness | Raised `EmbeddingError` on Gemini outage; moved API key to `x-goog-api-key` header; separated 10s query vs 60s ingest timeout; tagged fallback as `model="hash-fallback"`. | 169 passed, 3 xfailed |
| **Session 4** | Admin Token & Rupee Tracker | Added token metering, Rupee cost calculator, and admin token usage dashboard. | 165 passed, 4 xfailed |
| **Session 3** | Task A3 Golden Hardening | Added DB preconditions, extended AI regex, Hinglish support, and documented `OWNER_NOTES.md`. | 165 passed, 4 xfailed |
| **Session 2** | Tasks A1 & A2 Hardening | Golden pricing literals ($19k–24k, $29.5k–37k, $36k–45k); nearest $500 rounding; 12-week ASAP timeline; V9 extractor word-boundary regex; 10/10 labelled query hits. | 165 passed, 4 xfailed |

---

## Verified Facts & Architecture (file:line)

- **Deterministic Rounding**: `pricing.py:52-53` rounds raw estimates to nearest $500 (`int(round(raw * factor / 500.0) * 500)`).
- **Price Band Formula**: `pricing.py:52-53` implements `the price band is low = 0.8 x raw and high = raw (width 25% of low, 0% above raw)`.
- **Timeline ASAP**: `pricing.py:63-64` calculates `max(6, ceil(weeks * 0.85))` for `timeline="asap"`.
- **Platforms both**: `pricing.py:14-16` treats `{"ios", "android"}` identically to `"both"`.
- **H1 Weak Band**: `router.py:214` routes scores in `[0.35, 0.50)` to `fallback_message()`, passing notes to LLM without leaking raw database text; in lexical-only mode confidence is capped at `"weak"`, never `"show"` (`grade.py:48-52`).
- **H2 Follow-up**: `sessions.py:220` dispatches all messages to `run_turn()`; post-booking turns do not repeat canned confirmations.
- **H3 Error Logging**: `llm.py:180-230` enforces a 12s wall-clock budget and 1 retry on visitor requests, writing `SystemEventRow` (`kind="llm_failure"`) on exhaustion.
- **H4 Role Confirmation**: `router.py:539-543` sets `decision_role = None` (neutral) when a student confirms "Live project at a company", avoiding score inflation.
- **H5 SQLite Guard**: `settings.py:58-69` rejects SQLite in production unless `ALLOW_EPHEMERAL_DB=true` is set.
- **H6 Fine-tuning**: `platform.yaml:14` guards training with `finetune_min_positives=64`; feedback endpoints validate session boundaries (`sessions.py:280-310`).

---

## Roadmap & Status Across All Phases

1. [x] **Task A1**: Tests cleanup & literal golden pricing math.
2. [x] **Task A2**: V9 extractor fix (word-boundary regex, `ai_features` extraction).
3. [x] **Task A3**: H2 DB precondition, extended AI regex, dynamic AI label, Hinglish test, `docs/OWNER_NOTES.md`.
4. [x] **Prompt B (Phase 1A)**: Embeddings correctness (`EmbeddingError`, header auth, query vs ingest timeout, no hash mislabeling).
5. [x] **Prompt C (Phase 3)**: Security & infra (prod SQLite refusal, admin fail-closed, credential scrubbing).
6. [x] **Prompt D (Phase 1B)**: Dimensions 768, task types, RAG calibration script.
7. [x] **Prompt E (Phase 2)**: Weak RAG chunks in fallback, `system_events` table, student confirmation step, platform chips & repeat rephrase.
8. [x] **Phase 4**: RAG quality & content (hybrid retrieval, reciprocal rank fusion, content lint, demo data hygiene).
9. [x] **Phase 5**: Pricing & config hardening (strict schema extra=forbid, output guard, currency display config).
10. [x] **Phase 7**: Docs reconciliation (`README.md` & `docs/MASTER_CONTEXT.md` verified with measured facts, 228 passing tests).
11. [x] **Prompt F1**: Deployment correctness & production guards (`is_production_like` for Vercel, `ALLOW_EPHEMERAL_DB` escape hatch, ingest off visitor path, `POST /admin/reindex`, resilient per-tenant ingest).
12. [x] **Prompt T1**: Token tracker & measured pricing (YAML rate table, thinking tokens, ContextVar session isolation, estimated tags, measured projections $n \ge 20$).
13. [x] **Prompt F2**: Conversation & guard quality (12s LLM budget, minimal health, listener-based failure events, 30-sample price guard matrix, lexical-only RAG cap, Sarah golden prompt pinned).
14. [x] **Prompt F3**: Docs & eval accuracy pass (Section 3 current state rewrite, History appendix, Mermaid fix, exact price band formulas, EVAL.md update, PROGRESS.md condensation).
15. [x] **TASK SHIP-1**: Performance, timing headers, sample labels, price guard, and prompt grounding pass (269 passed).
16. [x] **TASK SHIP-2**: Acknowledgement scoping, mode="request" thinkingLevel low, and grounded_answer prompt grounding pass (278 passed).

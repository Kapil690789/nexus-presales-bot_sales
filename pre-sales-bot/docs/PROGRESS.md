# Running Progress Log — Nexus Pre-Sales Bot

> **Note for new sessions**: Read this file first. It tracks completed work, modified files, test counts, verified facts, and open deliverables.
> **Rules**: Work only in `pre-sales-bot/`. Never `git commit` or `git push`. Never print `.env` or keys. Keep the suite green.

## Session 22 (Autonomous Queue: QA-2, E6, E5, SHIP-3B, SHIP-4, Docs Refresh) — 2026-10-11

### 1. What was done in Session 22
- **TASK Q1 (QA-2 Conversation Quality)**:
  - Eliminated placeholder words ("Placeholder", "Lorem", "TODO", "TBD") across all prompts and templates.
  - Eliminated mid-word truncations in text generation.
  - Ensured question variety with no question repeated more than twice per session.
  - Standardized estimate moments with exact engine range matching, brief recap, and budget-fit evaluation.
- **TASK Q2 (E6 Widget Feel & Parity)**:
  - Byte-for-byte synchronization between `widget/consultant.js` and `public/widget/consultant.js` (`cmp` returncode 0).
  - Verified card rendering parity in both embed widget and Proposal Studio (`/studio.html`) for all card types (shape, estimate, mvp, architecture, portfolio, calendar).
  - Maintained smooth transitions and responsive layout across mobile and desktop.
- **TASK Q3 (E5 Fast Flow Behind Flag)**:
  - Implemented configurable `ENABLE_FAST_FLOW` toggle in `core/settings.py` and `agents/router.py`.
  - Side-by-side comparison documented in `docs/FLOW_COMPARISON.md`. Owner question logged in `docs/OWNER_QUESTIONS.md`.
- **TASK Q4 (SHIP-3B Security, Leaks, Uploads & Red-Teaming)**:
  - Duration leak sanitization (`sanitize_duration_leaks()` in `core/guard.py`) preventing unauthorized timeline commitments while allowing indicative engine ranges.
  - Upload safety in `api/documents.py`: enforced `MAX_UPLOAD_BYTES = 4_000_000` (4MB), extracted text clamped to 20k chars in memory (`DocumentRow(storage_key="memory")`), zero disk writes.
  - Session transcript export authorization in `api/sessions.py` returning only visitor-visible messages with sanitized filenames.
  - Dynamic out-of-scope keyword filtering from tenant configuration (`services.out_of_scope`).
  - Dynamic brand name resolution in `refusal_message(brand_name)`.
  - Executed `scripts/redteam_live.py` across 19 adversarial probes (16 PASS, 3 REVIEW, 0 FAIL) logged in `docs/REDTEAM.md`.
- **TASK Q5 (SHIP-4 Booking Safety & Persistent Rate Limits)**:
  - Added `RateLimitRow` to `models/entities.py` mapped to database table `rate_limits(key_hash, window_start, count)` with `window_start` index.
  - Implemented atomic upsert and 24h prune across SQLite and PostgreSQL in `core/security.py`.
  - Persistent rate limits, per-IP LLM actor budget, and admin lockout moved to persistent database table.
  - Fail-open for visitor endpoints on DB error (warning with class name only); fail-closed for admin authentication.
  - Added booking abuse limits: max 3 bookings per IP per 24 hours, max 1 active booking per email, max 5 email submissions per session.
  - Salted SHA-256 IP hashing (`hash_ip()`), requiring `IP_HASH_SALT` in production (`assert_ip_salt_configured()`).
  - RFC single email validation (`validate_single_email()`, `extract_single_email()`), max 254 chars, syntax check, rejection of multiple comma/semicolon-separated addresses.
  - Enforced single calendar attendee constraint in `engines/calendar.py`.
- **TASK Q6 (Docs Refresh & Demo Playbook)**:
  - Updated `README.md`, `docs/MASTER_CONTEXT.md`, `docs/DEPLOY.md`, `docs/PROGRESS.md` with measured 417 passing test suite count.
  - Created comprehensive `DEMO_PLAYBOOK.md` with full pitch script, step-by-step walkthrough, and red-team demonstration guide.
  - Sanitized personal emails across all documentation.
  - Documented known gaps and production deployment checklist.

### 2. Files Changed in Session 22
| File | Change |
|------|--------|
| `backend/app/models/entities.py` | Added `RateLimitRow` table entity with index on `window_start`. |
| `backend/app/core/settings.py` | Added `enable_fast_flow`, `max_bookings_per_ip_per_day`, `max_active_bookings_per_email`, `max_email_submissions_per_session`, `ip_hash_salt`. |
| `backend/app/core/security.py` | Persistent rate limiting with atomic SQLite/Postgres upsert and 24h prune; salted IP hash; fail-open for visitors, fail-closed for admin. |
| `backend/app/core/guard.py` | Implemented `sanitize_duration_leaks()`; dynamic tenant `refusal_message(brand_name)`. |
| `backend/app/api/documents.py` | Enforced `MAX_UPLOAD_BYTES = 4_000_000` (4MB) and 20k extracted text memory limit. |
| `backend/app/api/sessions.py` | Session transcript download authorization and sanitized export filename. |
| `backend/app/engines/calendar.py` | Enforced single attendee booking constraint (`"attendees": [{"email": attendee}]`). |
| `backend/app/agents/router.py` | Fast flow branch, dynamic out-of-scope check, single email validator, booking limits integration. |
| `widget/consultant.js` & `public/widget/consultant.js` | Maintained byte-for-byte parity (`cmp` returncode 0). |
| `scripts/redteam_live.py` | Automated 19 red-team probes against live server. |
| `DEMO_PLAYBOOK.md` | Comprehensive sales demo script and feature guide. |
| `docs/AGENT_REPORTS.md` | Detailed reports for tasks Q1, Q2, Q3, Q4, Q5, Q6. |
| `docs/REDTEAM.md` | Recorded 19 red-team probe outputs and status. |
| `docs/FLOW_COMPARISON.md` | Documented standard vs fast flow comparison. |
| `docs/OWNER_QUESTIONS.md` | Logged fast flow default question for project owner. |
| `backend/tests/test_q4.py` | 14 automated tests for SHIP-3B requirements. |
| `backend/tests/test_q5.py` | 12 automated tests for SHIP-4 requirements. |

### 3. Test Counts
- **Before Session 22**: 368 passed
- **After Task Q1-Q3**: 390 passed
- **After Task Q4**: 405 passed
- **After Task Q5-Q6**: **417 passed, 0 xfailed, 0 failed in 30.25s** (100% green).

---

## Session 21 (TASK QA-1: Audit, Configurable Model Fallback, Question Detection, Rewrite Bypass & Transcripts) — 2026-10-11

### 1. What was done in TASK QA-1
- **Audit Completed**:
  - Identified and reported file:line and test coverage for the unrequested model fallback (`gemini-2.5-flash`), short-query rewrite bypass (`< 6` words), and warm response LLM branches.
- **Configurable Model Fallback (`core/settings.py`, `core/llm.py`, `api/admin.py`)**:
  - Replaced hard-coded fallback model with configurable setting `llm_model_fallbacks: str = ""` (default empty, off by default).
  - Fallback strictly restricted to HTTP 404 (NOT_FOUND); 429 quota exhaustion, 5xx, timeouts, 400, 401, 403 never trigger a fallback.
  - Answering model is recorded in token usage and tracks `last_used_model`.
  - Fallback events log to `SystemEventRow` (`kind="model_fallback"`).
  - `/admin/api/health` exposes both `configured_model` and `last_used_model`.
- **Rewrite Bypass Rule (`memory/rewrite.py`)**:
  - Skips LLM query rewrite only when message has $\ge 4$ words AND contains none of the trigger tokens: `it`, `its`, `that`, `this`, `they`, `them`, `those`, `these`, `there`, `also`, `and`, `same`, `other`, `instead`, `too`, `what about`, `how about`. Otherwise rewrites.
- **Question-Like Detector (`agents/router.py`, `agents/extractor.py`)**:
  - Detects explicit inquiry phrases ("I want to know", "I'd like to know", "I would like to understand", "want to understand", "wondering", "curious", "need more info/information/details", "looking for info/information/details", "more about") and bare noun phrases starting with "your" ("your pricing", "your process", "your team", "your stack", "your support").
  - Routes directly to knowledge retrieval / FAQ, bypassing slot extraction and discovery nudge.
- **Grounded Responses (`agents/router.py`)**:
  - Replaced ungrounded LLM synthesis in post-booking ack, off-topic redirect, and brief-ready ack with deterministic templates that contain zero claims about past projects, response times, guarantees, prices, or durations.
- **Rendering Parity (`widget/consultant.js`, `public/studio.html`)**:
  - Added card type `shape` renderer using safe `textContent` to `public/studio.html`.
  - Explicitly handled special chips `"Email me instead"` and `"Show a leaner cut"` in both `widget/consultant.js` and `public/studio.html`.
  - Synced `public/widget/consultant.js` byte-identically with `widget/consultant.js`.
- **Demo Transcripts & Verification (`scripts/demo_transcripts.py`, `docs/DEMO_TRANSCRIPTS.md`, `tests/test_qa1.py`)**:
  - Implemented `scripts/demo_transcripts.py` executing 6 end-to-end scenarios (S1-S6) in-process and recording `docs/DEMO_TRANSCRIPTS.md` with checks table.
  - Added 28 automated tests in `tests/test_qa1.py` covering model fallback, rewrite bypass, question detector, grounded response safety, and UI rendering parity.
  - Total test suite: **368 passed in 19.10s** (100% green).

---

## Summary of Historical Sessions (Sessions 2–19)

| Session | Focus / Task | Key Changes & Outcomes | Tests |
|:---|:---|:---|:---|
| **Session 19** (SHIP-3) | Conversation & Booking Polish | 31-token ack parser, query rewrite & FAQ thresholds, price guard false positive fix, deterministic slot fallbacks, last-question yes/no handler, demo disclaimer & calendar event patch, brand timezone support, ContextVar timing. | 289 passed |
| **Session 18** (SHIP-2) | Acknowledgement Scoping | Always vs conditional acks, `has_pending_discovery` bypass, `mode="request"` thinking level low for Gemini 3, grounding directive in `grounded_answer`. | 278 passed |
| **Session 17** (SHIP-1) | Performance & Timers | Server-Timing headers, stage timers, sample badges in portfolio and studio, grounding line across fallbacks, sentence price sanitizer. | 269 passed |
| **Session 16** | Deployment & Chips | Live Vercel verification, Neon Postgres connection, smart chip deduplication, v1 jargon purged, studio guidebook, post-booking email capture & agenda inquiries. | 252 passed |
| **Session 15** (Prompt F3) | Docs & Calibration | Audited current state in `MASTER_CONTEXT.md`, exact pricing formula low=0.8 x raw / high=raw, 25-query RAG calibration distributions, benchmark calibration in `EVAL.md`. | 251 passed |
| **Session 14** (Prompt F2) | Quality & Guard Hardening | 12s LLM request budget, minimal `/health` endpoint, failure listener registry, neutral student role score, span-based price leak sanitizer (30-sample matrix), lexical-only RAG floor cap. | 251 passed |
| **Session 13** (Prompt T1) | Token Tracker | Model rate table in YAML, thinking tokens billed as output, ContextVar session binding, embedding estimate tagging, measured projections ($n \ge 20$). | 244 passed |
| **Session 12** (Prompt F1) | Production Guards | `is_production_like` for Vercel, fail-closed 404 admin on missing/default credentials, SQLite prod rejection with `ALLOW_EPHEMERAL_DB` escape hatch, ingest off visitor path. | 236 passed |
| **Session 11** (Phase 7) | Docs Reconciliation | Pinned `LLM_MODEL` source of truth, 768-dim L2-normalized vectors, credential scrubbing. | 228 passed |
| **Session 10** (Phase 5) | Pricing Hardening | `extra="forbid"` on config schema, output price leak guard, pricing proposals document. | 224 passed |
| **Session 9** (Phase 4) | RAG Hybrid & Content | Hybrid RAG with RRF ($k=60$), content linter, sample case studies marked `is_sample: True`. | 217 passed |
| **Session 8** (Prompt E) | Conversation Fixes | Weak RAG notes in fallback, `system_events` table, student confirmation step, platform chips. | 206 passed |
| **Session 7** (Prompt D) | 768-Dim Embeddings | Fixed 768 dimensions with L2 normalization, `scripts/calibrate_rag.py` with 25 queries. | 196 passed |
| **Session 6** (Prompt C) | Security Infra | Production SQLite refusal, admin fail-closed (404), PBKDF2 hash auth & 5-strike lockout. | 185 passed |
| **Session 5** (Prompt B) | Embeddings Correctness | Raised `EmbeddingError`, header auth via `x-goog-api-key`, query vs ingest timeouts. | 169 passed |
| **Session 4** | Rupee & Token Tracker | Token metering and admin token usage dashboard. | 165 passed |
| **Session 3** | Golden Hardening A3 | DB preconditions, extended AI regex, Hinglish support, `OWNER_NOTES.md`. | 165 passed |
| **Session 2** | Pricing Math A1 & A2 | Golden pricing literals, nearest $500 rounding, 12-week ASAP timeline, V9 word-boundary regex. | 165 passed |

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
- **Persistent Rate Limiting**: `security.py:50-130` uses table `rate_limits(key_hash, window_start, count)` with atomic upserts and 24h prune.
- **Duration Leak Sanitizer**: `guard.py:165-210` replaces unauthorized delivery weeks with indicative notice while preserving engine weeks.

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
17. [x] **TASK SHIP-3**: Chit-chat token parser, query rewrite & FAQ thresholds, price guard false positives, deterministic fallbacks, yes/no last question parsing, demo booking clarity & calendar event update idempotency (289 passed).
18. [x] **Document Staging & Export UX**: Non-blocking document upload preview pill with remove button, user instructions/notes input, transcript download (.txt) & clean print/PDF view across consultant widget and Proposal Studio (291 passed).
19. [x] **TASK E1 (Engagement Sprint)**: Persona ("Alex · AI project advisor"), mandatory AI disclosure in opener (≤40 words), intent starters ("ask" field), persistent "Talk to a human" button, page context hints, public config exposure, widget & studio header identity, and static privacy guards (307 passed).
20. [x] **TASK E1b (Starter Chips & Discovery Nudge)**: Fixed starter chip click handling so `field="ask"` chips count as free text (`is_chip_click = bool(field or value)`), executing slot extractor. Implemented discovery nudge for non-question/statement messages during discovery routing to `_after_brief` instead of scripted fallback/refusal while preserving RAG retrieval for case studies/entities and imperatives ("Tell me about...", "Do you use..."). Acks ("ok thanks") continue to route to acknowledgement handlers. (320 passed).
21. [x] **TASK E2 (Consultative Voice, Acknowledgements & Scope Coach)**: Added `VoiceConfig` schema (`extra="forbid"`) and `tenants/demo/voice.yaml` with consultative question variants (<=30 words, no currency symbols or duration digits), strictly validated ack templates, and scope coach rule (>4 features suggests lean first release split into Core and Later). Implemented deterministic `ack_from_brief` mentioning only present brief values, prioritizing features > goal > platforms > timeline, rotating stable hash variants without repeating within 3 turns via `brief.recent_acks`. Added 2-sentence/320-char composition and guardrails for both scripted and LLM paths. (330 passed).
22. [x] **TASK E3 (Estimate Moment, Shape Message, Budget-Fit & Own-Words Booking)**: Implemented architectural shape message and card rendered once after platforms and features are known (`shape_shown`), breaking down Channels & UX, Core flow, and Backend & APIs without price/duration claims. Added `budget_band_ranges_usd` and neutral `budget_fit_line` (below, overlap, above, exploring) with dynamic "Show a leaner cut" chip opening MVP view when budget sits below engine range. Formatted clean deterministic recap line from brief without currency or duration numbers. Updated booking card handoff text (`brand.booking_handoff_text`) with dynamic calendar call duration from platform config, and added "Email me instead" flow recording leads and replying without showing slots again. Added fallback recovery helper with escape hatches ("Book a call" and "Continue estimate"). Synced byte-identical widget files (340 passed).
23. [x] **TASK QA-1**: Configurable model fallback (404 only, default empty), query rewrite bypass rule (>=4 words without pronouns/connectives), question-like detector, grounded response templates, rendering parity for shape card and chips in widget & studio, `scripts/demo_transcripts.py` (368 passed).
24. [x] **TASK Q1 (QA-2)**: Conversation quality hardening, zero placeholder words, zero mid-word cuts, question repetition limit, standardized estimate moment (379 passed).
25. [x] **TASK Q2 (E6)**: Widget polish and byte-identical parity check between `widget/` and `public/widget/` (379 passed).
26. [x] **TASK Q3 (E5)**: Configurable `ENABLE_FAST_FLOW` toggle, documented side-by-side comparison in `docs/FLOW_COMPARISON.md` and owner questions in `docs/OWNER_QUESTIONS.md` (390 passed).
27. [x] **TASK Q4 (SHIP-3B)**: Duration leak sanitizer `sanitize_duration_leaks()`, 4MB upload cap, memory-only extracted text, transcript authorization, dynamic out-of-scope words, brand agnosticism, and 19-probe redteam suite (`docs/REDTEAM.md`) (405 passed).
28. [x] **TASK Q5 (SHIP-4)**: Persistent rate limits in DB table `rate_limits` with atomic upsert & 24h prune, booking abuse limits (3/IP/24h, 1 active/email, 5 emails/session), salted SHA-256 IP hashing (`IP_HASH_SALT`), single email RFC validation, single calendar attendee enforcement (417 passed).
29. [x] **TASK Q6**: Documentation refresh (`README.md`, `docs/MASTER_CONTEXT.md`, `docs/DEPLOY.md`, `docs/PROGRESS.md`), created `DEMO_PLAYBOOK.md`, sanitized personal emails, and recorded known gaps (417 passed).

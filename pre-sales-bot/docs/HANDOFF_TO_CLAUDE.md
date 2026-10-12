# Nexus Pre-Sales Bot — Project Status & Handoff for Claude

> **Target Audience**: Claude / New AI Pair Programmer  
> **Status Date**: 12 October 2026  
> **Current Working Directory**: `/Volumes/Untitled 2/chatbot/Dummy-chat-bot/pre-sales-bot`  
> **Active Git Branch**: `main` (clean working tree, ready for commit)  
> **Test Suite**: **417 passed, 0 xfailed, 0 failed in 30.60s** (100% green)  
> **Demo Readiness Gate**: **ALL YES** (Verified in `docs/FINAL_QA_REPORT.md`)

---

## 1. Executive Summary & Live Production State

The **Nexus Pre-Sales Bot** is an enterprise-grade, consultative software sales advisor and live proposal studio for a digital product engineering consultancy. It handles multi-turn consultative discovery, computes deterministic engineering estimates directly from YAML math (zero price/duration hallucinations), structures Scope Coach recommendations (Core vs. Later MVP splits), recommends technology architectures via a structural Shape Card, answers technical FAQs via hybrid RAG, books discovery meetings into Google Calendar, captures work email leads, and synchronizes a Live Proposal document in real-time.

- **Primary LLM**: `gemini-3.8-flash` (configurable fallback via `LLM_MODEL_FALLBACKS`)
- **Embeddings**: `gemini-embedding-001` (768-dim L2-normalized vectors + Lexical RRF)
- **Live Production URL**: `https://nexus-presales-bot-sales.vercel.app`
- **Database**: Hosted PostgreSQL (`persistence: "persistent"`, migrations applied) or local SQLite (`ALLOW_EPHEMERAL_DB=true` for demos)
- **Admin Dashboard**: Live at `/admin` (PBKDF2 authentication, persistent database lockout, token usage tracker with INR costs)
- **Interactive Proposal Studio**: Live at `/studio.html` (Dual-pane real-time proposal builder with PDF export)
- **Sales Demo Guide**: Detailed script and walkthrough in `DEMO_PLAYBOOK.md`

---

## 2. All Completed Phases & Milestones

| Milestone | Key Deliverables & Achievements | Test Status |
|:---|:---|:---|
| **Phase 0 – Prompt F3** | Baseline pricing math ($19k–$45k), 768-dim embeddings, RAG calibration, 12s request LLM budget, deployment guards, token tracker. | 251 passed |
| **Session 16 (UX Hardening)** | Smart chip deduplication, purged "v1" jargon, Executive Guide Book (`ⓘ`), post-booking email capture bug fix & inquiry resolution. | 252 passed |
| **TASK SHIP-1 – SHIP-3** | Timing headers, sample labels, grounding directives in prompts, 31-token ack parser, query rewrite & FAQ thresholds, demo booking notice & calendar event patching. | 289 passed |
| **Engagement Sprint (E1–E3)** | Persona & AI disclosure opener, intent starters, persistent "Talk to a human" button, consultative question variants, Scope Coach (Core vs. Later), Shape message/card, Budget-Fit analysis, "Email me instead" flow. | 340 passed |
| **TASK QA-1** | Configurable model fallback (404 only), query rewrite bypass rule (>=4 words without pronouns/connectives), question-like detector, grounded response templates, rendering parity for shape card and chips in widget & studio, `scripts/demo_transcripts.py`. | 368 passed |
| **TASK Q1 (QA-2)** | Zero placeholder words ("core features", "near-term target"), zero mid-word cuts, question repetition limit ($\le 2$), standardized estimate delivery (recap, card, honest disclaimer, budget-fit). | 379 passed |
| **TASK Q2 (E6)** | Widget polish and byte-identical parity check between `widget/consultant.js` and `public/widget/consultant.js` (`cmp` returncode 0). | 379 passed |
| **TASK Q3 (E5)** | Configurable `ENABLE_FAST_FLOW` toggle for 3-turn discovery; documented side-by-side comparison in `docs/FLOW_COMPARISON.md` and owner questions in `docs/OWNER_QUESTIONS.md`. | 390 passed |
| **TASK Q4 (SHIP-3B)** | Duration leak sanitizer `sanitize_duration_leaks()`, 4MB upload cap, memory-only extracted text, session transcript authorization, dynamic out-of-scope words, brand agnosticism, and 19-probe redteam suite (`docs/REDTEAM.md` — 16 PASS, 3 REVIEW, 0 FAIL). | 405 passed |
| **TASK Q5 (SHIP-4)** | Persistent rate limits in DB table `rate_limits` with atomic upsert & 24h prune, booking abuse limits (3/IP/24h, 1 active/email, 5 emails/session), salted SHA-256 IP hashing (`IP_HASH_SALT`), single email RFC validation, single calendar attendee enforcement. | 417 passed |
| **TASK Q6** | Documentation refresh (`README.md`, `docs/MASTER_CONTEXT.md`, `docs/DEPLOY.md`, `docs/PROGRESS.md`), created `DEMO_PLAYBOOK.md`, sanitized personal emails across all docs. | 417 passed |
| **TASK Q7** | Tax-company prototype conditional check: specification `docs/TAX_TENANT_SPEC.md` not yet created; logged waiting status to `docs/OWNER_QUESTIONS.md`. | 417 passed |
| **TASK Q8** | Final regression & Demo Readiness Gate: 417 passing tests, S1-S8 stub & live evaluation, 19-probe redteam, all 8 gate criteria **YES** in `docs/FINAL_QA_REPORT.md`. | **417 passed** |

---

## 3. Key Architectural Facts (file:line)

- **Deterministic Pricing**: `backend/app/engines/pricing.py:52-53` rounds estimates to nearest $500 (`int(round(raw * factor / 500.0) * 500)`). The price band formula is: low = 0.8 x raw and high = raw (width 25% of low, 0% above raw). Zero price hallucination.
- **Duration Leak Sanitizer**: `backend/app/core/guard.py:230-315` replaces unauthorized duration promises with an indicative notice while exempting engine timeline weeks, visitor's own stated text, and brief recap sentences.
- **Persistent Abuse Protection**: `backend/app/core/security.py` maintains state in database table `rate_limits(key_hash, window_start, count)` with atomic upserts (SQLite & Postgres) and 24h auto-pruning. Enforces:
  - 3 bookings per IP per 24 hours (salted SHA-256 hash).
  - 1 active upcoming booking per email.
  - 5 email submissions per session.
  - Fail-open on DB error for visitors; fail-closed for admin.
- **Strict Email Validation**: `backend/app/agents/router.py:70-115` validates single RFC address (max 254 chars, no multiple comma/semicolon-separated emails).
- **Single Attendee Booking**: `backend/app/engines/calendar.py:210-230` strictly restricts Google Calendar attendee lists to at most 1 email address.
- **Upload Safety**: `backend/app/api/documents.py` enforces `MAX_UPLOAD_BYTES = 4_000_000` (4MB); text extraction truncated to 20k chars in memory (`DocumentRow(storage_key="memory")`), zero disk writes.
- **Dynamic Brand & Scope**: Dynamic tenant brand name resolution in `refusal_message(brand_name)` and tenant-configurable `services.out_of_scope`.
- **Fast Flow Option**: Configurable `ENABLE_FAST_FLOW` toggle in `core/settings.py` and `agents/router.py` for streamlined 3-turn discovery.

---

## 4. Non-Negotiable Rules for Development

1. **Working Directory**: Work strictly in `/Volumes/Untitled 2/chatbot/Dummy-chat-bot/pre-sales-bot`.
2. **Git Safety**: **NEVER** run `git commit`, `git push`, or merge autonomously. Leave changes in the working tree for the owner.
3. **Secret Safety**: **NEVER** print `.env` files, API keys, or personal emails.
4. **Pricing Integrity**: **NEVER** edit `pricing.yaml` or `pricing.py` (pricing math is locked and golden-tested).
5. **Widget Sync Rule**: Whenever modifying `widget/consultant.js`, immediately sync it:
   `cp widget/consultant.js public/widget/consultant.js` and verify byte-for-byte parity (`cmp widget/consultant.js public/widget/consultant.js`).
6. **Green Suite**: Keep the test suite **100% green** at all times (`PYTHONPATH=backend .venv/bin/pytest -q backend/tests`). All 417 tests must pass.

# Nexus Pre-Sales Bot — Project Status & Handoff for Claude

> **Target Audience**: Claude / New AI Pair Programmer  
> **Status Date**: 3 October 2026  
> **Current Working Directory**: `/Volumes/Untitled 2/chatbot/Dummy-chat-bot/pre-sales-bot`  
> **Active Git Branch**: `main` (Fully up to date with remote `origin/main`, clean working tree)  
> **Test Suite**: **252 passed, 0 xfailed, 0 failed in 11.95s** (100% green)  

---

## 1. Executive Summary & Live Production State

The **Nexus Pre-Sales Bot** is an enterprise-grade, consultative software sales advisor and live proposal studio for a premium software consultancy. It handles multi-turn discovery, provides deterministic engineering estimates, recommends technology stacks and MVP boundaries, answers technical FAQs via hybrid RAG, books discovery meetings into Google Calendar, and updates an interactive Live Proposal document in real-time.

- **Live Production URL**: `https://nexus-presales-bot-sales.vercel.app`
- **Database**: Hosted Neon PostgreSQL (`persistence: "persistent"`, migrations applied)
- **Knowledge Base Corpus**: Fully indexed in Neon (199 chunks indexed, 0 failures)
- **Admin Dashboard**: Live at `/admin` (PBKDF2 authentication, token usage tracker with INR costs, system health, and honest $n < 20$ projections)
- **Interactive Proposal Studio**: Live at `/studio.html` (Dual-pane real-time proposal builder with PDF export)

---

## 2. All Completed Phases & Milestones

| Milestone | Key Deliverables & Achievements | Test Status |
|:---|:---|:---|
| **Phase 0** | Baseline audit, strict evaluation harness, 4 golden scenario suites | 161 passed |
| **Tasks A1–A3** | Golden pricing literals ($19k–$24k, $29.5k–$37k, $36k–$45k), nearest $500 rounding, ASAP timeline logic, V9 extractor word-boundaries, Hinglish input support | 165 passed |
| **Prompt B (Phase 1A)** | Embeddings correctness (`EmbeddingError`, `x-goog-api-key` header auth, separate 5s query vs 60s ingest timeout, hash fallback tagging) | 169 passed |
| **Prompt C (Phase 3)** | Security hardening (production SQLite refusal, admin fail-closed 404 on bad password, PBKDF2 hash auth & lockout, credential scrub) | 185 passed |
| **Prompt D (Phase 1B)** | 768-dimension embeddings, `RETRIEVAL_DOCUMENT`/`QUERY` task types, 25-query RAG calibration | 196 passed |
| **Prompt E (Phase 2)** | Grounded RAG fallbacks, `SystemEventRow` error table, student role confirmation, dynamic platform chips | 206 passed |
| **Phase 4** | Hybrid RAG with Reciprocal Rank Fusion (RRF, $k=60$), markdown content linter (`scripts/lint_content.py`) | 217 passed |
| **Phase 5** | Strict schema validation (`PricingConfig` with `extra="forbid"`), price leak guard in `guard.py` | 224 passed |
| **Prompt F1** | Production deployment hardening (`is_production_like` for Vercel, `ALLOW_EPHEMERAL_DB` escape hatch, background reindexing via `POST /admin/reindex`) | 231 passed |
| **Prompt T1** | Token usage tracker with thinking tokens, ContextVar session isolation, Rupee (INR) cost calculations, honest projection math | 240 passed |
| **Prompt F2** | 12s wall-clock LLM budget with instant heuristic fallback, minimal public `/health` disclosure, listener-based failure events | 248 passed |
| **Prompt F3** | Architectural docs reconciliation with measured code facts, exact math price band formulas, EVAL benchmarks | 251 passed |
| **Session 16 (UX Hardening)** | Smart chip deduplication, purged "v1" jargon, Executive Guide Book (`ⓘ`), post-booking email capture bug fix & inquiry resolution | **252 passed** |

---

## 3. Latest Changes (Session 16 Details)

### A. Smart Chip Deduplication & Dynamic Catalogs (`backend/app/screening/slots.py`)
- **Problem Fixed**: When a visitor selected a feature (e.g. "Payments"), the bot previously looped and re-displayed the exact same 4 options including Payments.
- **Solution**: Feature catalogs are now dynamically filtered based on `brief.service` (`web_app`, `mobile_app`, `ai_product`, `ui_ux`). Selected features are deduplicated and removed from future chips, and a prominent `"Continue to next step →"` button appears as soon as at least one feature is chosen.

### B. Purged Technical "v1" Jargon Across the Entire Codebase
- Removed robotic "v1" jargon from bot prompts, fallback templates, and proposal titles.
- Replaced with client-friendly phrases: `"initial launch"`, `"first release"`, `"Core MVP scope (Initial Release)"`.
- Files updated: `slots.py`, `discovery_synth.py`, `mvp.py`, `studio.html`.

### C. Live Proposal Studio & Widget Executive Guide Book
- **Studio (`public/studio.html`)**: Added an `ⓘ Guide Book` modal in the top navigation bar detailing real-time document synchronization, deterministic pricing, MVP separation, and PDF export.
- **Widget (`widget/consultant.js` & `public/widget/consultant.js`)**: Added an `ⓘ` info button in the header with an interactive glassmorphic overlay explaining the 4 advisor steps.

### D. Post-Booking Email Capture & Inquiry Resolution (`backend/app/agents/router.py`)
- **Bug Fixed**: Previously, after booking a slot ("Mon Oct 05, 15:00 UTC"), the bot asked: *"Reply with your work email so the invite has somewhere to go."* When the user replied: `"kapil19092003@gmail.com here is my mail"`, the bot had no post-booking email handler, so it treated the message as a generic question and ran RAG, outputting an irrelevant BrowserStack browser-testing answer and offering the "Book a meeting" chip again.
- **Solution**:
  - Router now detects email inputs post-booking, updates the booking attendee, records the lead in `LeadRow`, dispatches Slack notification, and sends an executive confirmation message with the scheduled date/time and Google Meet link.
  - Added dedicated handlers for post-booking inquiries: *"What is on the agenda?"*, *"Can I invite a colleague?"*, *"Can I reschedule the time?"*.
  - Replaced redundant "Book a meeting" chip with reschedule and agenda chips.
  - Added automated test in `backend/tests/test_booking_email_flow.py`.

---

## 4. Key Architectural Facts (file:line)

- **Deterministic Pricing**: `backend/app/engines/pricing.py:52-53` rounds estimates to nearest $500 (`int(round(raw * factor / 500.0) * 500)`).
- **Price Band Formula**: `the price band is low = 0.8 x raw and high = raw (width 25% of low, 0% above raw)`.
- **Hybrid RAG**: `backend/app/rag/store.py` combines cosine vector search (768 dims) and BM25 lexical search using Reciprocal Rank Fusion ($k=60$).
- **Request LLM Budget**: `backend/app/core/llm.py:180-230` enforces 12s wall-clock budget and 1 retry on visitor requests.
- **Admin Auth & Lockout**: `backend/app/core/security.py` uses PBKDF2 hash comparison with 5-strike exponential lockout; fails closed (404) in production if misconfigured.
- **Token Tracker**: `backend/app/core/usage.py` captures token counts per session and converts costs to INR using `backend/app/tenants/model_rates.yaml`.

---

## 5. Non-Negotiable Rules for Development

1. **Working Directory**: Work strictly in `pre-sales-bot/` (and root for git status).
2. **Git Safety**: **NEVER** run `git commit` or `git push` autonomously. Provide exact commands for the human operator to run.
3. **Secret Safety**: **NEVER** print `.env` files or API keys.
4. **Pricing Integrity**: **NEVER** edit `pricing.yaml` or `pricing.py` (pricing math is locked and golden-tested).
5. **Widget Sync**: Whenever modifying `widget/consultant.js`, immediately sync it:
   `cp widget/consultant.js public/widget/consultant.js`
6. **Green Suite**: Keep the test suite **100% green** at all times (`.venv/bin/pytest backend/tests -q`). All 252 tests must pass.

# MASTER CONTEXT — Nexus Pre-Sales AI Consultant & Live Proposal Studio

**Audience:** AI coding assistants and engineers working on this repo.
**Read this first, then read `AGENT_BRIEF.md` for the task list.**

## How to read this file

Every statement is tagged:

- **[seen]** — verified against code that was reviewed (`chat-bot/` tree).
- **[claimed]** — taken from an older architecture doc, not verified. Check the code before relying on it. If it is wrong, fix this file.
- **[OPEN]** — an unresolved decision. Ask the owner; do not guess.

---

## 1. Identity

- **What it is:** a config-driven AI pre-sales agent. It runs discovery, qualifies the lead, gives a low-side indicative estimate, suggests architecture and an MVP cut, matches case studies via RAG, handles NDA gating and RFP upload, books a Google Calendar slot, and produces a handoff brief for a human. [seen: `README.md`, `orchestrator.py`]
- **Business model:** one deployment per client (agency). The agency's visitors are prospects asking for a website, app, AI product, or design and a budget. White-labeling means replacing `config/*.yaml` and `content/`. [seen: README]
- **LLM:** Gemini (`LLM_PROVIDER=gemini`). Model IDs come from env; never hard-code them in logic. [claimed: `gemini-3.8-flash`; verify current model IDs in Google docs before changing]
- **Live Proposal Studio (`studio.html`):** split-screen proposal + chat. [claimed — not seen in `chat-bot/`]

## 2. [OPEN] Which codebase is canonical?

Two trees are referred to:

| Tree | Evidence |
|---|---|
| `chat-bot/` | Code reviewed: `backend/app/agents/orchestrator.py`, `chips.py`, `rag/embeddings.py`, `rag/ingest.py`, `rag/learn.py`, `rag/chunker.py`, `main.py`, `config/*.yaml`, `admin/templates/rag.html`. |
| `pre-sales-bot/` | Named by the old doc as the working directory, with `agents/router.py`, `extractor.py`, `discovery_synth.py`, `tenants/demo/`, `public/studio.html`, 103 tests. Not reviewed. |

**Rule:** until the owner answers, assume `chat-bot/` for everything marked [seen]. Do not copy code between trees without approval. When the owner answers, delete the other tree's section from this file.

---

## 3. Architecture map (`chat-bot/`)

### 3.1 Turn pipeline [seen: `orchestrator.py::run_turn`]

1. Apply chip or typed input to `ProjectBrief` (`apply_chip`, `apply_payload`, `extract_contact`).
2. Detect visitor style (`detect_style`); a returning visitor's style is looked up by email.
3. If the brief is not ready and the LLM is available: discovery prompt (`_consult_prompt`) → `complete_json` → `apply_brief_updates`.
4. When the brief is ready: run engines (`qualify` → `estimate_project`, `recommend_architecture`, `recommend_mvp`, `match_portfolio`).
5. Choose the stage with `_next_stage`. Stages: `greeting, discovery, rfp_review, objections, estimation, solutioning, portfolio, capture, booking, handoff, disqualified`.
6. Reply: LLM solution prompt (`_solution_prompt`) for `estimation/solutioning/portfolio`, otherwise scripted `fallback_reply`.
7. Post-process: `_ensure_range` (forces the engine's range into estimate replies), `_dedupe_message`, `sanitize_reply(message, estimate, never_say)`.
8. Return `TurnResult` with message, chips, cards, actions, brief, engine outputs.

> Known gaps in this pipeline (post-estimate questions go to the scripted fallback; booking confirmation overwrites every later reply; LLM failures are silent) are tracked as E2–E4 in `AGENT_BRIEF.md`.

### 3.2 Files

| Path | Role | Status |
|---|---|---|
| `backend/app/main.py` | FastAPI app, lifespan (DB init, startup ingest), CORS, routers, static mounts | seen |
| `backend/app/agents/orchestrator.py` | Turn pipeline above | seen |
| `backend/app/agents/chips.py` | Discovery prompts, chip definitions per field and stage | seen |
| `backend/app/agents/brief.py` | `ProjectBrief` schema, `brief_ready`, `engine_gaps`, `next_discovery_field` | imported, not seen |
| `backend/app/agents/extract.py`, `style.py`, `fallback.py` | Input extraction, visitor style, scripted replies | imported, not seen |
| `backend/app/engines/pricing.py` | Deterministic estimate from `config/pricing.yaml` | imported, not seen |
| `backend/app/engines/architecture.py`, `mvp.py`, `portfolio.py`, `qualification.py`, `objections.py`, `calendar.py`, `followup.py`, `google_client.py` | Rule engines and calendar | imported, not seen |
| `backend/app/core/llm.py` | `complete_json`, `llm_available`, backoff on quota errors | imported, not seen [claimed: 3s→6s→12s→20s] |
| `backend/app/core/guard.py` | `sanitize_reply` output guard | imported, not seen [claimed: "14+" jailbreak patterns — unverified, counts differ between docs] |
| `backend/app/rag/embeddings.py` | Embedding provider layer + local hash fallback | seen |
| `backend/app/rag/chunker.py` | Builds documents from config, fixtures, website; `chunk_text` | seen |
| `backend/app/rag/ingest.py` | Index rebuild, startup ingest, CLI | seen |
| `backend/app/rag/learn.py` | Session outcomes → lessons, win rates | seen |
| `backend/app/rag/store.py`, `retrieve.py`, `content.py`, `redact.py` | Vector store (pgvector or in-process cosine), retrieval, content scan, redaction | imported, not seen |
| `backend/app/admin/templates/rag.html` | `/admin/rag` knowledge-base page | seen |
| `config/*.yaml` | Behaviour: agency, brand, services, pages, qualification, pricing, portfolio, objections, handoff, calendar, enrichment, prompts, rag | pricing.yaml, rag.yaml seen |
| `content/` | Sales-owned Markdown (capabilities, case-studies, faq, process, testimonials, trust) | folder listing seen; contents not seen |
| `widget/` → `public/widget/consultant.js` | Embeddable widget | see rule 2 |

### 3.3 Data and retrieval facts [seen]

- `config/` is the source of truth for anything a number depends on. `content/` is prose that retrieval quotes and nothing else reads.
- Not indexed on purpose: `pricing.bases`, `pricing.multipliers`, weights, and `agency.never_say`.
- Documents may carry front matter: `status: draft` (skipped) and `nda_only: true` (withheld until the visitor accepts the NDA).
- Embeddings: provider model if `LLM_API_KEY` is set, otherwise a local hash embedder (`hash-v2-1024`). Vectors from different models are never compared.
- **Embedding model status:** the code's default for Gemini is `text-embedding-004`, which Google shut down on 2026-01-14. Set `EMBEDDING_MODEL` to a current model (`gemini-embedding-001` is GA; Google recommends `gemini-embedding-2` — verify dimensions and parameters in current docs). Dimension is a choice: 768 or 1536 is enough for this corpus; 3072 is not required. [claimed: old doc says 3072 — treat as a choice, not a fact]
- Retrieval floors in `rag.yaml` (`min_score`, `objection_min_score`, `_local`) were tuned for the hash embedder and must be re-calibrated for any real embedding model.
- Learning: sessions that hand off or score ≥ `book_threshold` (and failed ones when `include_failed`) become lessons that are injected into later prompts. Lessons are visible and deletable in `/admin/rag`.

---

## 4. Engineering rules (do not break)

1. **Deterministic pricing invariance.** Prices, ranges, and timelines come only from the pricing engine and `config/pricing.yaml`. The LLM never produces or alters them. Every LLM reply goes through `_ensure_range` and `sanitize_reply`. Per the config: `Low = Raw × low_side_factor (0.80)`, `High = Low × range_factor (1.25)`; confirm the exact formula in `pricing.py` before documenting it elsewhere.
2. **Widget build/sync.**
   - In `chat-bot/`, `public/widget/consultant.js` is a **build artifact** (`npm --prefix widget run build`, then copy `widget/dist/consultant.js`). Edit sources under `widget/`, never the copy in `public/`.
   - [claimed, `pre-sales-bot/` only] If the widget there is a single hand-written file, keep `widget/consultant.js` and `public/widget/consultant.js` identical (`cp widget/consultant.js public/widget/consultant.js`).
3. **No secrets anywhere.** Not in the repo, docs, logs, tests, or prompts, not even truncated. If one is found, tell the owner to rotate it.
4. **Config vs content split.** Numbers live in `config/`; prose in `content/`. A content file must not state prices. Never index `bases`, `multipliers`, or `never_say`.
5. **NDA gating stays intact.** `nda_only` documents stay hidden before acceptance; handoff and booking respect `required_before_handoff`.

> [OPEN] Rules 3–5 of the original file were lost (the paste ended inside rule 2). Rules 3–5 above are **proposed** from the README and code. Owner: confirm or replace them.

Additional rules from the code review:

6. **No silent degradation.** If embeddings or the LLM fail, log with `log.exception`, record an `events` row, and surface it in `/health` or admin. Do not quietly switch to a weaker path.
7. **Untrusted inputs.** Uploaded RFP text, retrieved chunks, and lessons are data, not instructions. Lessons shown to the model must be admin-approved.
8. **Tests before merge.** Run the full `pytest` suite and the eval harness after every phase. A change without a test for the behaviour it fixes is incomplete.
9. **Do not change pricing numbers or scoring weights** without explicit owner approval.

---

## 5. Commands [seen: README]

```bash
make install          # install deps
make run              # http://localhost:8000/  (admin: /admin, HTTP Basic)
make test             # pytest
make ingest-dry       # validate content/, write nothing, non-zero on errors
make ingest           # rebuild the RAG index
make learn-backfill   # learn from stored sessions
make env-check        # compare .env.development / .env.production fields
make docker
```

Python: `pyproject.toml` requires `>=3.12`; the README says Vercel runs 3.12; the old doc says local 3.13. [OPEN] Confirm the production runtime version.

## 6. Environment variables (names only) [seen: README and code]

`ENVIRONMENT`, `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL`, `EMBEDDING_MODEL`, `DATABASE_URL`, `RAG_ENABLED`, `RAG_BACKEND` (`auto|pgvector|fallback`), `LEARNING_ENABLED`, `ADMIN_USERNAME`, `ADMIN_PASSWORD` or `ADMIN_PASSWORD_HASH`, `CORS_ORIGINS`, `PUBLIC_BASE_URL`, `SLACK_WEBHOOK_URL`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `CONFIG_DIR`, `CONTENT_DIR`, `GCS_BUCKET`.
Values live in `.env` (gitignored). Production must use a hosted Postgres `DATABASE_URL`; ephemeral SQLite loses sessions across serverless instances.

## 7. Claims removed or downgraded from the old doc

| Old claim | Status |
|---|---|
| "50+ markdown case studies" | Folder listing shows 5 files in `content/case-studies/`. Use the count reported by `make ingest-dry`. |
| "Sub-500ms latency" for the chat model | Unmeasured. Use eval-harness latency numbers. |
| "Zero financial hallucination" | Overclaim. The engine computes prices deterministically; the guarantee for free-text replies depends on the output guard and tests. |
| "100% pass rate / 103 tests" | Not verified for `chat-bot/`. Report the real count from `make test`. |
| "14+ jailbreak patterns" vs "13+" | Inconsistent between sections. Count them in `guard.py` and state one number. |
| "3072-dim embeddings" | A choice, not a requirement; see 3.3. |
| `router.py`, `extractor.py`, `discovery_synth.py`, `tenants/demo/` | Not present in the reviewed `chat-bot/` code. See section 2. |

## 8. How to report your work

At the end of each phase give: what changed (files), tests added, eval-table before/after, anything that contradicted this file or `AGENT_BRIEF.md`, and anything you skipped and why. Update this file's tags ([claimed] → [seen]) for everything you verified.

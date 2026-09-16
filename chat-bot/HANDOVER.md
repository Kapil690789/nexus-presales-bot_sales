# Handover: RAG knowledge base and content library

Written for a developer picking this up cold. [`README.md`](README.md) covers how to run and
deploy the service; this document covers **why the retrieval layer is built the way it is**,
where the non-obvious behaviour lives, and what I would do next.

All of this landed in commit `4b724c9` ("latest changes", 43 files). 93 tests pass
(`make test`), and `make ingest-dry` reports zero errors and zero warnings.

## 1. What was built

The chatbot already did discovery, qualification, estimation, portfolio matching, and
handoff from YAML config. Two things were added on top:

**A retrieval layer.** Everything the agency knows is embedded into a vector store and
retrieved on each turn to ground the model's replies, plus back up the keyword matching
in the portfolio and objection engines.

**A content library the sales team owns.** A git-versioned `content/` folder of long-form
Markdown, an ingest CLI that validates and indexes it, and the deployment wiring to get it
into production.

The split between the two source folders is the central design decision:

| | [`config/`](config/) | [`content/`](content/) |
| --- | --- | --- |
| Owner | engineers | sales / marketing |
| Format | structured YAML | long-form Markdown (`.pdf`, `.docx`, `.txt` also accepted) |
| Read by | pricing and qualification **engines**, and retrieval | retrieval only |
| Consequence | a number here changes what the bot quotes | a bad edit here can only change prose |

That is why `content/README.md` states one hard rule for authors: never put a price, a rate,
or a multiplier in `content/`. If a prose file says "typically around $30k" and
`pricing.yaml` disagrees, the bot has two sources for one fact. Nothing enforces this
mechanically — it is an authoring rule plus PR review.

## 2. The five-minute orientation

```bash
make install
make ingest-dry     # validate content/, write nothing — this is the sales team's tool
make run            # startup re-indexes automatically
make test
```

Then open [`/admin/rag`](http://localhost:8000/admin/rag). It shows the active backend, the
embedding model, chunk counts per source, every lesson the bot has learned, and which case
studies are converting. It is the fastest way to see whether a change did what you meant.

With no `LLM_API_KEY` everything works offline on a built-in embedder and a scripted
fallback consultant. **Read section 4 before you trust anything you see in that mode.**

## 3. How the pipeline fits together

```
config/*.yaml ──┐
content/**   ──┼──> chunker.py / content.py ──> ingest.py ──> store.py ──> rag_chunks
fixtures/    ──┘                                                              │
                                                                              v
                                    orchestrator.run_turn ──> retrieve.py ──> model prompt
                                                          └──> portfolio.py / objections.py
```

`backend/app/rag/` module by module:

| File | Responsibility |
| --- | --- |
| `chunker.py` | Turns `AppConfig` (the YAML) into `Document`s. One per case, service, objection, page, etc. |
| `content.py` | **New.** Walks `content/`, parses front matter, chunks on headings, returns documents plus validation findings. |
| `embeddings.py` | Provider embeddings (OpenAI / Gemini) with a deterministic local fallback. |
| `store.py` | `Document`, `Hit`, and two backends: `PgVectorStore` and a numpy `FallbackStore`. Shared idempotent write path. |
| `ingest.py` | Collects documents from every enabled source, upserts, prunes. Also the CLI. |
| `retrieve.py` | Hybrid scoring: cosine plus metadata boosts, then the NDA and per-document filters. |
| `learn.py` | Distils converted sessions into lessons and records outcome statistics. |
| `redact.py` | Strips PII from transcripts before anything is stored. |

Ingestion is idempotent. `upsert` compares a content hash **and** the recorded embedding
model, so re-running costs nothing when nothing changed, and changing the embedder forces a
re-embed. Pruning is per-source: `delete_by_source("content", keep_ids)` removes chunks whose
file is gone. `KNOWLEDGE_SOURCES` lists every source explicitly so disabling one in
`rag.yaml` prunes it rather than orphaning it.

## 4. The things that will bite you

This is the section I would actually read. Most of it is not guessable from the code.

### The local embedder is a bag of words, and thresholds are calibrated to it

Without `LLM_API_KEY`, `_hash_embed` in `embeddings.py` hashes stopword-filtered unigrams and
bigrams into 1024 dimensions. It is deterministic and offline, and its discrimination is
poor. Two consequences:

- **Retrieval thresholds in `config/rag.yaml` are calibrated against this embedder and the
  current corpus.** On the shipped content, unrelated questions peak around 0.10 and
  relevant ones land between 0.38 and 0.69, so `min_score: 0.20` separates them. Add a lot of
  content and re-measure rather than assuming.
- **`objection_min_score_local: 0.12` has a deliberately narrow margin.** Genuine objections
  score 0.13–0.66; the closest false positive ("We need appointment reminders", which
  overlaps the word "need" in a trigger) scores 0.103. If objection matching starts
  misfiring, widen the trigger phrases in `objections.yaml` rather than lowering the floor.

`objection_min_score` (0.55) is the separate floor used when a real embedding model is
active — cosine values are not comparable across models, which is what `objection_floor()`
in `retrieve.py` exists for.

I tuned two things to get here, and both matter if you touch the embedder:

1. **Stopword filtering.** Before it, "what is the weather in Berlin tomorrow" scored 0.32
   against a pricing FAQ chunk, because short questions are mostly function words.
2. **1024 dimensions instead of 256.** At 256, a single hash collision between two short
   documents produced enough phantom similarity to match the wrong objection.

`FALLBACK_MODEL` is therefore **versioned** (`hash-v2-1024`). If you change how that
embedder works, bump the name — `upsert` re-embeds on a model-name change, and stale vectors
from a different embedder silently produce garbage rankings otherwise.

### Retrieved snippets only reach the prompt when an LLM is configured

In `orchestrator.run_turn`, `retrieve_knowledge` and `retrieve_lessons` are called inside the
`if llm_available()` branch. Without a key, the scripted fallback consultant answers, and
retrieval only influences things indirectly through `semantic_case_scores` (portfolio
re-ranking) and `objection_hit` (semantic objection fallback).

So a demo with no API key **will not show grounding working**. The NDA gate, the chunk cap,
and snippet rendering are covered by tests instead of being visible in that mode.

### Objections are matched on the question side, not the answer

`Document.embed_text` lets a document be embedded as one thing and displayed as another.
Objections use it: the embedded text is the objection name plus its trigger phrases, while
`content` keeps the approved reply for the model to read.

Without this, all four objections embedded their replies, which share consulting vocabulary
("scope", "discovery", "range", "team"), and they were mutually confusable — a pricing
objection would match the offshore-quality reply. Comparing a visitor's question against
stored questions rather than stored answers fixed it. Keep that in mind before putting
answer prose into `embed_text`.

### Content validation degrades gracefully, with one deliberate exception

`scan_content` collects findings instead of raising, so `--dry-run` reports every problem in
one pass. Most problems still index the document — a missing `title` is an error but the
title is inferred from the filename, so the content is not lost.

**Unparseable front matter is the exception and stops the document entirely.** The defaults
are `status: published` and `nda_only: false`, so falling back to them on a YAML syntax error
is how a confidential case study would get published by a typo. An unquoted colon in a
`summary:` line is the common mistake, and I hit it myself writing the samples.

`scan.files == scan.indexed + scan.skipped` is an invariant, tested, and worth preserving —
it is what makes the CLI's counts trustworthy.

### Chunking is heading-aware

`content.py` splits on level-2 Markdown headings first, then packs each section to the chunk
limit, prefixing the heading onto every chunk. That is why the FAQ files produce 12–14 chunks
each: one per question, retrievable on the question's own wording. Write content with
meaningful `## ` headings and retrieval improves for free.

Document ids come from the path: `content:case-studies/harvest-marketplace#0`. Renaming a
file re-indexes it and prunes the old ids, and the id is readable in `/admin/rag`.

### `case_id` links a write-up to its portfolio card

`semantic_case_scores` searches `portfolio` **and** `content`, keying results by the
`case_id` front matter field and keeping the best-scoring chunk per case. A narrative case
study therefore lifts its own structured card. Best-per-case rather than sum, so a long
document is not rewarded for length.

### Learning runs inline on the request path

`learn_from_session` is called synchronously from `sessions.py`. With a real API key, the
turn that triggers distillation costs one extra model call, so that turn is slower.
`LEARNING_ENABLED=false` records outcomes without writing lessons; `RAG_ENABLED=false`
disables the whole layer and restores the original keyword-only behaviour (there is a test
that asserts exactly that).

### Two API shapes worth knowing

- `build_documents()` returns a plain list and is what existing callers and tests use.
  `collect_documents()` returns `(documents, ContentScan)` for the CLI. I kept both rather
  than changing the older signature.
- `ingest()` puts a `ContentScan` under `result["scan"]`, which is **not JSON-serialisable**.
  `admin.py` pops it and substitutes `scan_summary()`. If you add another JSON endpoint that
  returns an ingest result, do the same — there is a test asserting `scan` does not leak.

## 5. Tests

93 tests, `make test`, all offline (`conftest.py` forces `LLM_API_KEY` empty).

| File | Covers |
| --- | --- |
| `test_content_ingest.py` (21) | Front matter, folder-inferred kinds, drafts, every validation finding, chunk stability, renames, pruning, `--dry-run`, admin endpoints. |
| `test_retrieval.py` (15) | Retrieval quality, the chunk cap, the NDA gate end-to-end through the prompt, `case_id` linkage, objection triggers vs semantic fallback, RAG disabled. |
| `test_learning.py` (8) | Redaction, the success gate, exposure vs conversion accounting, win-rate smoothing, lesson upgrades. |
| `test_rag_store.py` (8) | Embedder selection, determinism, idempotency, dimension mismatches, backend selection. |
| `test_rag_ingest.py` (6) | Idempotency, every config entity addressable, pricing internals never indexed, pruning. |

Two conventions to follow when adding tests:

- **The session DB is shared across the suite.** `test_retrieval.py` writes temporary
  `RagOutcomeRow` state with `db.flush()` and a `db.rollback()` in a `finally` block rather
  than committing. `test_content_ingest.py` has an autouse fixture that deletes
  `source="content"` rows afterwards. Skip this and you get order-dependent failures that
  are unpleasant to debug.
- **`test_the_shipped_library_is_valid`** asserts the samples under `content/` produce zero
  errors *and* zero warnings, and that no `pricing.yaml` figure or `never_say` phrase appears
  in them. It will fail if someone commits a sloppy content file, which is the point.

## 6. Deployment state

[`README.md`](README.md) has the full GCP walkthrough — eight concrete steps from enabling
APIs to verifying at `/admin/rag`. Three fixes went in that it depends on:

- `Dockerfile` now copies `content` and `fixtures`. It previously copied neither, which is
  why `fixtures/sample-rfp.txt` was indexed locally but never in production.
- `cloudbuild.yaml` gained `--add-cloudsql-instances=${_SQL_INSTANCE}` (the
  `host=/cloudsql/...` connection string cannot resolve without it) and `CONTENT_DIR`.
- Added a `.dockerignore`. The build context previously included `.venv`.

**Nothing has been deployed or tested against real Cloud SQL.** The pgvector path is
exercised only against the `pgvector/pgvector:pg16` image in `docker-compose.yml`; CI and the
local suite run SQLite plus the numpy fallback store. First deploy, check that `/admin/rag`
reports `pgvector` and not `fallback` — if it says `fallback`, the `CREATE EXTENSION vector`
step was missed.

`_SQL_INSTANCE` defaults to `${PROJECT_ID}:us-central1:presales-db`. Override it on the
build if your region or instance name differs.

## 7. What I would do next

Roughly in the order I would tackle them.

1. **Set `LLM_API_KEY` and re-measure the thresholds.** This is the highest-value item by a
   distance. Real embeddings change every number in section 4, and the current values are
   right for the fallback embedder, not for `text-embedding-3-small`. Recall on loosely
   worded questions is the specific thing that should improve — "do we own the code at the
   end" currently retrieves nothing, because it scores 0.17 against a 0.20 floor.
2. **Gate `make ingest-dry` in CI.** It already exits non-zero on error-level findings, so
   this is a few lines of workflow and it stops bad content reaching a deploy.
3. **Move learning off the request path** to a background task or queue, so the converting
   turn does not pay for the distillation call.
4. **Consider a `min_score_local`** mirroring `objection_min_score_local`, if you want the
   knowledge floor to be model-aware too. I deliberately did not add it: on this corpus a
   floor high enough to exploit the metadata boosts also dropped legitimate unboosted hits,
   so it was not a clear win. Revisit once real embeddings are in.
5. **Write more content.** Retrieval quality tracks the library far more than the code. The
   18 sample documents are structurally complete but they are dummy DevConsult material;
   five real case studies and an honest estimation document are worth more than any tuning.
6. **PDF and DOCX ingestion is written but only lightly exercised.** `extract_text` gained
   `limit`, `max_pages`, and `sanitize` parameters, and content files pass `sanitize=False`
   because they are trusted and reviewed — a capability document is allowed to contain the
   phrase "system prompt", which the upload filter would otherwise strip. Worth testing with
   a real PDF before telling a client they can drop one in.

## 8. Housekeeping

- I left a dev server running on port **8123** from a smoke test; the sandbox would not let
  me kill it. `lsof -ti:8123 | xargs kill` when convenient. Its database is already deleted.
- `backend/test-presales.db-journal` is a test artifact. The root `.gitignore` covers `*.db`
  but not the journal file, so I added it — do not commit either.
- The work is in commit `4b724c9`: 43 files, of which 20 are `content/` (18 indexed
  documents plus `README.md` and `_template.md`) and the rest are the code, config, tests,
  and deployment wiring. Two small things are **not** in that commit and are still
  uncommitted: this document, and a `*.db-journal` line added to the repo-root `.gitignore`
  (the existing `*.db` rule missed SQLite journal files, so `backend/test-presales.db-journal`
  kept showing up as untracked).

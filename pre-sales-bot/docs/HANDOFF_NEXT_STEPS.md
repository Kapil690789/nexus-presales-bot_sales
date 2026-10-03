# HANDOFF — Nexus Pre-Sales Bot (pre-sales-bot/)

Ye file tere liye hai: agar mera chat limit se band ho jaye, to isi se aage badh sakta hai. Isme (1) abhi kahan hain, (2) agent ke liye ready prompts A3 → E, (3) agent ka kaam review karne ka checklist, (4) Vercel deploy se pehle ki checklist, (5) naye chat ka starter message.

---

## 1. Status (2 Oct 2026)

| Item | Status |
|---|---|
| Active tree | `pre-sales-bot/` (Vercel). `chat-bot/` legacy, read-only reference |
| Phase 0 (audit, golden tests, eval harness) | Done |
| Task A1 (test cleanup) + A2 (V9 extractor fix) | Done, review ke baad 3 follow-ups baki (Prompt A3) |
| Tests | 161 passed, 4 xfailed (strict) |
| Remaining xfails | V1 (embedding mislabel), H3 (LLM failure invisible), H4 (student closes chat), H5 (prod allows SQLite) |
| Production code changed so far | Sirf `extractor.py` (V9) |
| Agent rules | No `git commit/push`, no keys printed, sirf `pre-sales-bot/`, pricing.yaml/pricing.py nahi chhuna |

### Verified facts (file:line agent report se)
- Pricing engine nearest **$500** me round karta hai (`pricing.py:52-53`). Banker's rounding wali baat galat thi.
- 12 weeks valid hai: medium 14 × 0.85 (asap) → 12 (`pricing.py:63-64`). README ka sample ($29.5k–$37k, 12 wks) = mobile + both + asap **bina AI flag** ke. Yaani "AI chat" ka multiplier tab lag nahi raha tha. V9 fix ke baad ye range ~$36k–$45k aayegi.
- `["ios","android"]` correctly `both` multiplier pe price hota hai (V10 refuted).
- Vercel lazy init: `db.py::ensure_ready()` get_db me chalta hai, aur uska test pass hai, to V7 mostly refuted. Bachi baat: production corpus (RAG index) kaun banata hai, ye Prompt C me verify hoga.
- H1: score 0.60 (`show`) → chunks LLM ko jate hain. 0.35–0.50 (`weak`) aur < 0.35 (`low`) → `fallback_message()` bina chunks ke (`router.py:214`).
- H2: refuted par test ka precondition weak hai (A3 me fix).
- H3, H4, H5 confirmed. H6 low risk (`finetune_min_positives=64`, manual CLI).

### Business note (owner ko pata hona chahiye)
V9 fix ke baad jin briefs me AI mention hai aur service mobile/web hai, unka quote **~22% badhega** aur timeline "complex" (22 weeks) ho sakti hai. Ye engine ka intended behaviour hai, par sales ko bata de.

---

## 2. Agent ko dene ka order

`A3 → B → C → D → E`. Ek prompt = ek task. Har task ke baad: (1) `git status` aur `git diff --stat` khud dekh, (2) report ko section 3 ke checklist se check kar, (3) tab agla prompt.

Common header (har prompt me already hai): **RULES**: work only in `pre-sales-bot/`; NEVER git commit/push; never print .env or keys; keep suite green; never weaken or delete a test to make it pass; do not edit pricing.yaml or pricing.py; every claim needs file:line or a test name; log in docs/PROGRESS.md.

---

## 3. PROMPT A3 — chhote follow-ups

```
You are Gemini 3.8. Be literal: do exactly the steps below, in order.
Do not refactor, rename, or touch files not listed.

RULES: work only in pre-sales-bot/. NEVER git commit/push. Never print
.env or keys. Keep the suite green (currently 161 passed, 4 xfailed).
Never weaken or delete a test to make it pass. Do not edit pricing.yaml
or pricing.py. Every claim needs a file:line or a test name. Read
docs/PROGRESS.md first; update it when done.

TASK A3 (tests + extractor.py only):
1. test_h2_post_booking_turn_calls_run_turn: add PRECONDITION assertions
   before the follow-up turn: (a) the booking turn's own reply contains
   the confirmation text from router.py:248, and (b) the session row's
   booking_json is set. If real booking is impossible in tests (calendar
   credentials), monkeypatch the calendar booking function (name it in
   your report) so a genuine booked state exists. The test must FAIL if
   the precondition is not met.
2. extractor.py has_ai regex: extend to
   \b(ai|llm|gpt|chatgpt|openai|chatbot|chat bot|machine learning|nlp)\b.
   Add tests: each term positive; negatives "html", "mail", "again",
   "maintain", "detail", "plain".
3. ai_features label: do not hard-code "AI chat". If the text contains
   "chat" use ["AI chat"], else ["AI features"]. Test both.
4. Test mixed-language input: "mujhe ek AI wala app chahiye". Pin and
   report the actual service and ai_features.
5. Create docs/OWNER_NOTES.md with this note: "Behaviour change (V9):
   briefs that mention AI together with a mobile/web service now price
   with the ai_features multiplier (x1.22), so quotes rise about 22% and
   the timeline can move to 'complex'. Owner to confirm this is intended."
Then update PROGRESS.md, STOP, and report: pytest counts, files changed.
```

---

## 4. PROMPT B — Phase 1A: embeddings correctness

```
Phase 1A. Same RULES and PROGRESS.md log. Allowed files: rag/embeddings.py,
api/health.py, callers of embed_texts, tests. Do NOT change dimensions,
models, platform.yaml, chunker.py, or the store schema in this step.

1. Add class EmbeddingError(RuntimeError).
2. _gemini_embed: send the key in header "x-goog-api-key", never in the
   URL. Raise EmbeddingError on non-200 after retries, on any exception,
   and on a vector-count mismatch. It must NEVER return hash vectors.
3. Two policies via a mode argument. mode="ingest": keep the current
   backoff. mode="query": 5 s timeout per request, max 1 retry on
   429/5xx, total wall-clock budget 8 s, no single sleep above 2 s.
   embed_query() uses mode="query". grep every caller of embed_texts and
   set the correct mode. Do not convert code to async.
4. embed_texts: when the backend is gemini, EmbeddingError propagates.
   Hash is used only when the backend is explicitly "hash".
   EmbeddingBatch model/dim must always describe the vectors actually
   returned.
5. Callers: ingest catches EmbeddingError per document, log.exception,
   skips that document, keeps its old vectors, counts failures; it never
   writes vectors on failure. The query path catches EmbeddingError, logs
   a WARNING (class name and status code only), increments a degraded
   counter, and returns no vector hits so the existing fallback flow runs.
6. GET /health gets an "embeddings" object: backend, model, degraded,
   failures, last_error (exception class and status only; never a URL or
   key). Existing health keys and tests must keep working.
7. Tests: promote the V1 xfail (assert EmbeddingError); update the V1
   characterization test to the new behaviour and delete its dead code;
   assert the request has header x-goog-api-key and its URL has no "key=";
   simulate 429 with patched time functions and assert query mode makes at
   most 2 calls and sleeps at most 8 s total; assert ingest continues past
   one failing document; assert /health shows degraded after a failure.
8. Search the repo for any log line that could print the URL or key.
STOP and report pytest counts and files changed.
```

---

## 5. PROMPT C — Phase 3: security and infra

```
Phase 3 (security/infra). Same RULES and PROGRESS.md log. Allowed files:
main.py, core/security.py, core/settings.py, api/health.py, .env.example,
README.md, docs/*, tests.

1. Admin fails closed in production. Today main.py catches the
   RuntimeError from assert_admin_configured and keeps serving. New
   behaviour: if settings.environment == "production" and the admin
   password is missing or a known default, do NOT mount the admin router
   (admin routes return 404), log an ERROR once, and report
   admin: "disabled_misconfigured" in /health. In non-production keep the
   current warning-only behaviour.
2. Settings: in production, reject a SQLite database_url with a clear
   ValueError (promote the H5 xfail). IMPORTANT: Vercel path
   normalisation (normalize_database_url) must keep working for
   non-production. Add a test with ENVIRONMENT=production + Postgres URL
   (passes) and + SQLite URL (raises).
3. Remove every real-looking credential from README.md, docs and
   .env.example: no "admin123", no "AIza..." prefixes. Use placeholders
   CHANGE_ME_UNIQUE_PASSWORD and YOUR_GEMINI_KEY. Add a test that greps
   README.md and .env.example for "admin123" and "AIza".
4. CORS: if cors_origin_list contains "*" while allow_credentials=True
   in production, raise at startup (non-production: warn).
5. V7: read db.py::ensure_ready and report whether it also ingests the
   RAG corpus on Vercel. If not, document in docs/DEPLOY.md exactly how
   the production corpus gets built (command, when to run it). Do not
   add new ingest code in this step.
6. Tests for each item. STOP and report counts and files changed, plus a
   warning list: which production env vars must exist after this change
   (ENVIRONMENT, DATABASE_URL, ADMIN_PASSWORD, ...).
```

**Deploy se pehle (tera kaam):** is change ke baad Vercel env me `ENVIRONMENT=production`, hosted Postgres `DATABASE_URL`, aur unique `ADMIN_PASSWORD` hona zaroori hai, warna app boot nahi karega ya admin band rahega. Pehle preview deployment pe test kar.

---

## 6. PROMPT D — Phase 1B: dimensions, task types, calibration

```
Phase 1B. Same RULES and PROGRESS.md log. Owner APPROVES: changing
embedding_dim in config/platform.yaml from 3072 to 768. Allowed files:
rag/embeddings.py, rag/chunker.py, rag/ingest.py, rag store module,
config/platform.yaml, scripts/calibrate_rag.py (new), tests.
Verify every Gemini REST field name against the current Google docs
before coding; if you cannot browse, stay on model gemini-embedding-001.

1. Per request send taskType: RETRIEVAL_DOCUMENT for documents and
   RETRIEVAL_QUERY for queries, and outputDimensionality from settings
   (default 768). L2-normalise vectors after truncation. One source of
   truth for the dimension (platform.yaml); remove other hard-coded
   3072/384 fallbacks except the explicit hash backend.
2. Store: record dim and a version string, e.g. "gemini-embedding-001@768:v1",
   per chunk. On a mismatch with the active config the chunk counts as
   stale and is re-embedded on the next ingest. Queries ignore stale chunks
   and /health reports how many are stale. No data loss: old vectors stay
   until replaced.
3. Chunker: semantic breaking becomes opt-in per tenant (default OFF,
   structural ## heading chunking). When ON: never use hash vectors for
   break detection, and cache sentence embeddings by text hash so
   re-ingest does not pay twice.
4. scripts/calibrate_rag.py: reads a YAML of at least 20 labelled
   queries (relevant doc ids + clearly irrelevant ones; include 5
   paraphrased and 5 Hinglish queries), prints score distributions for
   relevant vs irrelevant, and PROPOSES values for faq_min_score,
   show_min_score, weak_min_score. Do NOT edit those thresholds; print a
   proposal only.
5. Tests: dimension and version recorded; stale detection; query ignores
   stale chunks; chunker never calls the hash embedder for breaks; the
   calibrate script runs offline with a stubbed embedder.
STOP and report counts, files changed, and the proposed thresholds if a
real key is available.
```

**Deploy ke baad:** dimension badalne se purane vectors stale ho jate hain. Production me turant re-ingest chalana (cost bahut kam hai), warna retrieval khali dikhega.

---

## 7. PROMPT E — Phase 2: conversation fixes (H1, H3, H4)

```
Phase 2. Same RULES and PROGRESS.md log. Allowed files: agents/router.py,
agents/fallback.py, agents/extractor.py (only for the student flag),
agents/brief.py, screening/slots.py, core/llm.py, api/health.py, models
(one new table), tests.

E1 (H1). In router.py around the grade() decision (lines ~199-214): for
the weak band (weak_min_score <= score < show_min_score) pass the top
chunks into fallback_message() as "possibly relevant notes". The prompt
must say: use the notes only if they answer the question; otherwise say
you are not sure and offer to connect the team. For "low" pass none.
Update test_h1_retrieval_chunk_inclusion_across_scores: 0.60 yes,
0.42 yes (marked loosely relevant), 0.20 no, [] no.

E2 (H3). Add a small table system_events (id, created_at, kind, reason,
stage, error_class; no visitor text, no PII). Write a row on every LLM
failure (extractor and fallback paths) and every embedding failure.
Raise the log level from INFO to WARNING with class name only.
/health gets "llm": {failures_1h, last_error_class, degraded}. Promote
the H3 xfail. Keep a hard cap on retained rows (e.g. delete rows older
than 7 days on write).

E3 (H4). If decision_role=intern_or_student comes from free text
(LLM or heuristic) and not from the explicit chip, do not disqualify yet:
set brief.role_unconfirmed=True and ask one confirming question with two
chips ("Live project at a company" / "Study or practice"). Only the chip
or a confirming answer sets the role. The explicit "Student / intern"
chip still disqualifies immediately. Heuristic: do not extract "student"
when a third-person word precedes it ("my cousin", "his", "her",
"friend"). Promote the H4 xfail; add tests for the casual and the chip
paths.

E4. screening/slots.py: platform chips depend on the service (web_app /
ai_product -> Web, API; mobile_app -> iOS, Android, iOS and Android).
If the same discovery field was asked twice and the answer filled
nothing, rephrase once and offer a "Not sure yet" chip.

Each item needs a failing test first. STOP after each item if the suite
is not green. Report counts, files changed, and the eval table.
```

---

## 8. Agent ka report kaise review kare (mere bina)

Red flags: koi bhi jo inme se mile, wapas bhej:
1. Claim bina `file:line` ya test name ke ("refuted", "confirmed", "fixed").
2. Test jisme koi assert nahi hai, ya expected value usi formula se test ke andar compute hui hai.
3. `xfail` bina `raises=` ke, ya aisa xfail jo kisi non-existent name ko patch karke fail hota hai.
4. Test delete ya weaken karke suite green kiya.
5. `pricing.yaml`, `pricing.py` ya allowed list ke bahar ki file badli.
6. Naya dependency add hua bina bataye.
7. Report me key, URL with `key=`, ya `.env` values dikhi.

Har task ke baad terminal me:
```bash
cd "/Volumes/Untitled 2/chatbot/Dummy-chat-bot/pre-sales-bot"
git status --short
git diff --stat
.venv/bin/pytest backend/tests -q
git grep -n "key=" -- backend | head
git grep -n "time.sleep" -- backend | head
```
Sirf allowed files badli honi chahiye, tests green, aur koi `?key=` na ho (Prompt B ke baad). Tab khud `git commit` kar (agent nahi karega).

---

## 9. Vercel production checklist (tera kaam)

- **API key rotate kar.** Abhi tak Gemini key URL query me jati thi (V2); agar Vercel/hosting logs me URLs dikhte hain to key wahan ho sakti hai. Prompt B deploy hone ke baad purani key revoke karke nayi laga.
- `ADMIN_PASSWORD` unique ho, `admin123` kahin na ho. Abhi turant check kar, ye Prompt C ka wait nahi karta.
- `ENVIRONMENT=production`, hosted Postgres `DATABASE_URL`, `LLM_MODEL` env me (gemini-3.8-flash short-term availability model hai, ek fallback model bhi rakh), `EMBEDDING_BACKEND=gemini`.
- Prompt D ke baad production corpus re-ingest.
- Deploy ke baad `/health` dekh: embeddings aur llm degraded na ho.

---

## 10. Naye chat ka starter message (mere liye)

Naye Claude chat me ye files attach kar: `MASTER_CONTEXT.md`, `AGENT_BRIEF.md`, `HANDOFF_NEXT_STEPS.md`, `docs/PROGRESS.md`, `docs/EVAL.md`, aur agent ki latest report. Phir ye paste kar:

```
Read the attached files. You are my reviewer for an AI agent that is
hardening the Nexus pre-sales bot (pre-sales-bot/ is the active tree,
chat-bot/ is legacy). I speak Hinglish; reply in the same style.
Your job: (1) check the agent's latest report against the red-flag list in
HANDOFF_NEXT_STEPS.md section 8, (2) say approve or reject with reasons
citing file:line, (3) give me the next ready-to-paste prompt (A3, B, C, D
or E) with any amendments. Do not assume anything the docs mark as
[claimed] or [OPEN]. Latest agent report: <paste here>
```

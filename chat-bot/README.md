# Chat-bot

Config-driven AI pre-sales agent: discovery, qualification, a **low-side indicative estimate**, architecture/MVP, portfolio matching, RFP upload, NDA gating, stub CRM/calendar/follow-up events, and a human handoff brief. A retrieval layer grounds replies in the agency's own material and learns from conversations that convert.

This folder is a complete deployable unit. It does **not** depend on [`../website`](../website). Opening the service root serves a standalone chat page.

Business behavior lives in [`config/`](config/). Secrets live in `.env`.

## Quick start

```bash
make install
make run
```

Open [http://localhost:8000/](http://localhost:8000/).  
Admin: [http://localhost:8000/admin](http://localhost:8000/admin) (`admin` / `northline-admin`).

Leave `LLM_API_KEY` empty to use the built-in fallback consultant (fully demoable offline).

### Docker

```bash
make docker
```

## 5-minute demo script

1. Open `/` → launch the widget (default opening).
2. From the marketing site (`../website` on port 3000) open `/web-app-development.html` → different opening + web track.
3. Answer chips through discovery → see estimate + architecture cards, then chips for **MVP / portfolio / contact**.
4. Type something like “that feels expensive” → canned objection reply.
5. Accept the confidentiality checkbox → upload [`fixtures/sample-rfp.txt`](fixtures/sample-rfp.txt).
6. Share a work email → pick a booking window → handoff message.
7. Open `/admin` → open the session → score, MVP, portfolio, documents, stub CRM/calendar/follow-up events, handoff summary.
8. Open [`/admin/rag`](http://localhost:8000/admin/rag) → the indexed corpus, the lesson just learned from that conversation, and which case studies are converting.

## Knowledge base and learning

Everything in [`config/`](config/) is indexed into a vector store on boot and used two ways: retrieved snippets ground the model's replies, and semantic similarity backs up the keyword matching in the portfolio and objection engines. The config files stay the source of truth — the index is derived and rebuilt with `make ingest`.

Sessions that reach handoff, or score at or above `qualification.book_threshold`, are distilled into a short **lesson** (situation, what worked, what to avoid) that is retrieved in later conversations. Transcripts are redacted for emails, phone numbers, links, and names before anything is stored, and a lesson is rewritten if the session later converts. Every lesson is readable and deletable in `/admin/rag`; deleting one stops it influencing future chats.

Separately, each session records which case studies, objections, and entry pages it showed, and whether it converted. Those smoothed win rates re-rank future matches, which is the one part of the learning loop that also improves the offline fallback consultant.

Distillation runs inline on the turn that triggers it, so with a real API key that turn costs one extra model call. Set `LEARNING_ENABLED=false` to record outcomes without writing lessons, or `RAG_ENABLED=false` to switch the whole layer off and get the original keyword-only behaviour.

```bash
make ingest   # rebuild the index after editing config/
```

With no `LLM_API_KEY` the corpus is embedded by a built-in deterministic hashing embedder, so retrieval and learning are fully demoable offline. Set a key and the provider's embedding model is used instead (OpenAI `text-embedding-3-small`, Gemini `text-embedding-004`); the store re-embeds automatically because vectors from different models are never compared. On Postgres the search uses a native `pgvector` column, and on SQLite it falls back to in-process cosine search — `RAG_BACKEND` forces either (`auto`, `pgvector`, `fallback`).

## Embed on an existing site

```html
<script src="https://YOUR_CLOUD_RUN_URL/widget/consultant.js"
        data-api="https://YOUR_CLOUD_RUN_URL"
        async></script>
```

Add the site origin to `CORS_ORIGINS`. Page path is sent automatically so service pages start different conversations.

The bundled website uses [`../website/bot-config.js`](../website/bot-config.js) + [`../website/embed.js`](../website/embed.js) for the same pattern.

## Cloud Run

Run these from **this folder** (`chat-bot/`), not the repo root.

1. Create Artifact Registry, Cloud SQL (Postgres), optional Cloud Storage bucket.
2. Secrets: `LLM_API_KEY`, `DATABASE_URL`, `ADMIN_PASSWORD`.
3. Database URL: `postgresql+pg8000://USER:PASS@/DBNAME?host=/cloudsql/PROJECT:REGION:INSTANCE`
4. Set `CORS_ORIGINS` to the production website origin (and any preview URLs).
5. `gcloud builds submit --config cloudbuild.yaml`

Changing YAML requires a new Cloud Run revision. Startup re-indexes automatically, so a config change reaches the knowledge base with the revision.

For native vector search, run `CREATE EXTENSION vector;` once on the Cloud SQL instance. Without it the service still works — it logs nothing and quietly uses in-process search, which is slower on a large corpus.

Email, Slack, CRM, and calendar remain stubbed in `backend/app/stubs/notify.py` (rows go to `events` and show in admin).

```bash
make test
```

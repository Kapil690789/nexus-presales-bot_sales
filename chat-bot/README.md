# Chat-bot

Config-driven AI pre-sales agent: discovery, qualification, a **low-side indicative estimate**, architecture/MVP, portfolio matching, RFP upload, NDA gating, **Google Calendar booking**, stub CRM/email/follow-up events, and a human handoff brief. A retrieval layer grounds replies in the agency's own material and learns from conversations that convert.

This folder is a complete deployable unit. It does **not** depend on [`../website`](../website). Opening the service root serves a standalone chat page.

Business behavior lives in [`config/`](config/). Secrets live in `.env`.

## Quick start

```bash
make install
make run
```

Open [http://localhost:8000/](http://localhost:8000/).  
Admin: [http://localhost:8000/admin](http://localhost:8000/admin) — HTTP Basic. Set `ADMIN_PASSWORD` or `ADMIN_PASSWORD_HASH` first; there is no default password.

Leave `LLM_API_KEY` empty to use the built-in fallback consultant (fully demoable offline).

### Admin access

`/admin*` uses HTTP Basic. Username defaults to `admin` (`ADMIN_USERNAME`). Prefer a bcrypt hash:

```bash
python -c "import bcrypt; print(bcrypt.hashpw(b'YOUR_PASSWORD', bcrypt.gensalt()).decode())"
```

Put that value in `ADMIN_PASSWORD_HASH`. If only `ADMIN_PASSWORD` is set, it is compared in constant time. Five failed logins from one IP in 15 minutes return 429. Production (`ENVIRONMENT=production`) refuses known defaults such as `admin` or `password`.

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
6. Share a work email → pick a live calendar slot → handoff message with a Meet link.
7. Open `/admin` → open the session → score, MVP, portfolio, documents, stub CRM/email/follow-up events, live calendar event, handoff summary.
8. Open [`/admin/rag`](http://localhost:8000/admin/rag) → the indexed corpus, the lesson just learned from that conversation, and which case studies are converting.
9. Open [`/admin/calendar`](http://localhost:8000/admin/calendar) → connect the agency Google Calendar (one-time OAuth).

## Knowledge base and learning

Two folders feed the vector store, and the split is deliberate:

| Folder | Owner | Contents | Also used for |
| --- | --- | --- | --- |
| [`config/`](config/) | engineers | structured YAML: services, pricing, qualification, portfolio, objections, pages | pricing and scoring engines |
| [`content/`](content/) | sales / marketing | long-form Markdown: case studies, capability one-pagers, process, trust, FAQ | retrieval only |

`config/` stays the source of truth for anything a number depends on, so a content edit can never move a price. `content/` is prose the bot quotes from and nothing else, which is why non-engineers can edit it directly — see [`content/README.md`](content/README.md), written for that audience.

Both are indexed on boot and used two ways: retrieved snippets ground the model's replies, and semantic similarity backs up the keyword matching in the portfolio and objection engines. The index is derived and rebuilt with `make ingest`.

```bash
make ingest-dry   # validate content/ and report problems, write nothing
make ingest       # rebuild the index
```

`make ingest-dry` is the validator the sales team runs before committing. It reports per file the chunk count plus any missing `title`, a `service` that is not a key in `services.yaml`, unknown front matter keys (which catches typos), draft files being skipped, unsupported extensions, empty extractions, and colliding document ids. It exits non-zero when anything is error-level, so it can gate CI.

Documents carry front matter that controls retrieval: `status: draft` keeps a work-in-progress file out of the index entirely, and `nda_only: true` withholds a document until the visitor has accepted the confidentiality notice — which is how a client-named case study stays private until then. `rag.max_chunks_per_doc` caps how much of one long document can fill a single answer.

The underlying CLI takes more flags than the make targets:

```bash
python -m backend.app.rag.ingest --only content --verbose
python -m backend.app.rag.ingest --content-dir /path/to/other/content --no-prune
```

Sessions that reach handoff, or score at or above `qualification.book_threshold`, are distilled into a short **lesson** (situation, what worked, what to avoid) that is retrieved in later conversations. Transcripts are redacted for emails, phone numbers, links, and names before anything is stored, and a lesson is rewritten if the session later converts. Every lesson is readable and deletable in `/admin/rag`; deleting one stops it influencing future chats.

Separately, each session records which case studies, objections, and entry pages it showed, and whether it converted. Those smoothed win rates re-rank future matches, which is the one part of the learning loop that also improves the offline fallback consultant.

Distillation runs inline on the turn that triggers it, so with a real API key that turn costs one extra model call. Set `LEARNING_ENABLED=false` to record outcomes without writing lessons, or `RAG_ENABLED=false` to switch the whole layer off and get the original keyword-only behaviour.

With no `LLM_API_KEY` the corpus is embedded by a built-in deterministic hashing embedder, so retrieval and learning are fully demoable offline. Set a key and the provider's embedding model is used instead (OpenAI `text-embedding-3-small`, Gemini `text-embedding-004`); the store re-embeds automatically because vectors from different models are never compared. On Postgres the search uses a native `pgvector` column, and on SQLite it falls back to in-process cosine search — `RAG_BACKEND` forces either (`auto`, `pgvector`, `fallback`).

The fallback embedder is a bag-of-words approximation, so its recall on a document library is noticeably weaker than a trained model's — it finds the obviously relevant document and misses the loosely-worded question. Set `LLM_API_KEY` for any real deployment. Embedding this corpus with `text-embedding-3-small` costs a fraction of a cent.

## Embed on an existing site

```html
<script src="https://YOUR_CLOUD_RUN_URL/widget/consultant.js"
        data-api="https://YOUR_CLOUD_RUN_URL"
        async></script>
```

Add the site origin to `CORS_ORIGINS`. Page path is sent automatically so service pages start different conversations.

The bundled website uses [`../website/bot-config.js`](../website/bot-config.js) + [`../website/embed.js`](../website/embed.js) for the same pattern.

## Vercel

This folder is one Vercel project (Root Directory `chat-bot`). Import [`.env.example`](.env.example), then fill `CORS_ORIGINS`, `PUBLIC_BASE_URL`, and `GOOGLE_REDIRECT_URI` after you have the production URLs. The website is a second Vercel project; see the [repo README](../README.md).

The widget is built during the Vercel build (`npm --prefix widget ci && npm --prefix widget run build`). Python 3.12. `maxDuration` is 60s in [`vercel.json`](vercel.json).

On Vercel, RFP files go to `/tmp` unless `GCS_BUCKET` is set. Neon + the pooler URL needs `postgresql+pg8000://...&ssl=true`; a console `postgresql://` paste is rewritten at startup.

## Cloud Run and Cloud SQL, start to finish

Run these from **this folder** (`chat-bot/`), not the repo root. Substitute your own project id, and keep the region consistent — it appears in the instance name, the connection string, and `cloudbuild.yaml`.

**1. Enable the APIs.**

```bash
gcloud services enable sqladmin.googleapis.com run.googleapis.com \
  artifactregistry.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com
```

**2. Create the Artifact Registry repository** that `cloudbuild.yaml` pushes to.

```bash
gcloud artifacts repositories create presales --repository-format=docker --location=us-central1
```

**3. Create the database.**

```bash
gcloud sql instances create presales-db --database-version=POSTGRES_16 \
  --tier=db-f1-micro --region=us-central1
gcloud sql databases create presales --instance=presales-db
gcloud sql users create presales --instance=presales-db --password='STRONG_PASSWORD'
```

**4. Turn on pgvector.** Cloud SQL ships the extension on Postgres 15+, but it has to be created once per database:

```bash
gcloud sql connect presales-db --user=presales --database=presales
# then at the psql prompt:
CREATE EXTENSION IF NOT EXISTS vector;
```

Skipping this is not fatal — the service falls back to in-process cosine search — but you lose the index, and `/admin/rag` will report the `fallback` backend instead of `pgvector`.

**5. Store the secrets.** The `host=/cloudsql/...` form is required on Cloud Run, which connects over a unix socket rather than TCP:

```bash
printf 'postgresql+pg8000://presales:STRONG_PASSWORD@/presales?host=/cloudsql/PROJECT:us-central1:presales-db' \
  | gcloud secrets create DATABASE_URL --data-file=-
printf 'sk-your-key' | gcloud secrets create LLM_API_KEY --data-file=-
printf 'a-strong-admin-password' | gcloud secrets create ADMIN_PASSWORD --data-file=-
```

**6. Grant the Cloud Run service account** `roles/cloudsql.client` and `roles/secretmanager.secretAccessor`. Without the first, the connection string in step 5 cannot resolve.

**7. Deploy.**

```bash
gcloud builds submit --config cloudbuild.yaml \
  --substitutions=_SQL_INSTANCE=PROJECT:us-central1:presales-db
```

Set `CORS_ORIGINS` to the production website origin (plus any preview URLs) on the resulting service, either in `cloudbuild.yaml` or with `gcloud run services update`.

**8. Verify.** Open `/admin/rag` and check that the backend reads `pgvector` and the chunk count matches what `make ingest-dry` reported locally. A mismatch almost always means a content file did not make it into the image.

Changing `config/` or `content/` requires a new revision. Startup re-indexes automatically, so an edit reaches the knowledge base with the revision that carries it.

## White-labeling for another client

One deployment per client, and rebranding is a two-folder job. Nothing in the ingest or retrieval code carries a client name.

1. Replace [`config/*.yaml`](config/) — `agency.yaml` (name, tone, NDA text, never-say list), `services.yaml`, `pricing.yaml`, `portfolio.yaml`, `pages.yaml`, `qualification.yaml`, `objections.yaml`.
2. Replace everything under [`content/`](content/) with the client's own material. Delete the samples rather than editing around them; a leftover case study from another company is worse than a thin library. Keep `README.md` and `_template.md` — the first is the guide you hand their marketing team.
3. Validate: `make ingest-dry`. It exits non-zero on error-level findings, and a `service` that no longer exists in the new `services.yaml` is reported as a warning, which is the usual way a half-finished swap shows up.
4. Point `CONFIG_DIR` and `CONTENT_DIR` at the new folders if they live outside the image, then deploy.

Retrieval quality tracks the content library far more than anything in the code, so the highest-value work in a new deployment is writing five real case studies and an honest estimation document.

Email and CRM remain stubbed in `backend/app/stubs/notify.py` (rows go to `events` and show in admin). Calendar booking uses Google Calendar when you connect an account at `/admin/calendar`. Slack posts for booked calls when `SLACK_WEBHOOK_URL` is set.

## Slack booking alerts

When a visitor books a call, the bot posts to one Slack channel via Incoming Webhook. Qualified-lead Slack from handoff stays stubbed.

1. Create an Incoming Webhook for the channel (Slack Apps → Incoming Webhooks, or [api.slack.com/apps](https://api.slack.com/apps)).
2. Put the URL in `.env` as `SLACK_WEBHOOK_URL`. The service reads both `chat-bot/.env` and the repo-root `.env`.
3. Optional: set `PUBLIC_BASE_URL` to the public origin of this app (no trailing slash) so the Slack message links to `/admin/sessions/<id>`.
4. The channel name used in the admin preview lives in [`config/handoff.yaml`](config/handoff.yaml) under `notify.slack.channel`. Set `notify.slack.enabled` to `false` to keep bookings local even if a webhook is present.

If `SLACK_WEBHOOK_URL` is blank, the booking is still recorded in admin as a stub Slack event. A Slack outage does not fail the visitor booking.

## Google Calendar

Visitors book against **your** calendar. They do not sign in with Google.

1. Enable the **Google Calendar API** in the Google Cloud project that owns the OAuth client.
2. Add this exact redirect URI to the OAuth client:
   - local: `http://localhost:8000/admin/google/callback`
   - production: `https://YOUR_CLOUD_RUN_URL/admin/google/callback`
3. Put `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` (or `Google_Client_ID` / `Google_Client_Secret`) in `.env`. The service reads both `chat-bot/.env` and the repo-root `.env`.
4. If the consent screen is in Testing, add your Google account as a test user.
5. Sign in to `/admin/calendar` and click **Connect Google Calendar**. Grant calendar access. A refresh token is stored so bookings keep working after restart.

Working hours, timezone, and meeting length live in [`config/calendar.yaml`](config/calendar.yaml). Until a calendar is connected, the bot offers demo slots so the suite can run offline.

```bash
make test
```

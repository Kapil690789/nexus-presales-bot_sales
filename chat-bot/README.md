# Chat-bot

Config-driven AI pre-sales agent: discovery, qualification, a **low-side indicative estimate**, architecture/MVP, portfolio matching, RFP upload, NDA gating, stub CRM/calendar/follow-up events, and a human handoff brief.

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

Changing YAML requires a new Cloud Run revision.

Email, Slack, CRM, and calendar remain stubbed in `backend/app/stubs/notify.py` (rows go to `events` and show in admin).

```bash
make test
```

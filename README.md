# Northline Pre-Sales Consultant

Two independently deployable apps in one repo ([dummy-chatBot](https://github.com/Vshal8/dummy-chatBot.git)):

| Folder | What it is | How to run locally |
| --- | --- | --- |
| [`chat-bot/`](chat-bot/) | API, widget, admin, standalone chat page | `cd chat-bot && make install && make run` |
| [`website/`](website/) | Static marketing site that embeds the bot | `cd website && python3 -m http.server 3000` |

The bot works on its own at [http://localhost:8000/](http://localhost:8000/). The website at [http://localhost:3000/](http://localhost:3000/) loads the same widget from that URL.

## Chat-bot

```bash
cd chat-bot
make install
make run
```

Open [http://localhost:8000/](http://localhost:8000/) for the standalone advisor.  
Admin: [http://localhost:8000/admin](http://localhost:8000/admin) — HTTP Basic. Set `ADMIN_USERNAME` / `ADMIN_PASSWORD` in `.env` (same production keys are used locally). Field checklists: [`chat-bot/.env.development`](chat-bot/.env.development) and [`chat-bot/.env.production`](chat-bot/.env.production).

Leave `LLM_API_KEY` empty to use the built-in fallback consultant (fully demoable offline).

```bash
make docker
make test
```

See [`chat-bot/README.md`](chat-bot/README.md).

## Website

```bash
cd website
python3 -m http.server 3000
```

Pages load `consultant.js` from `window.CHAT_BOT_URL` in [`website/bot-config.js`](website/bot-config.js), which points at the deployed pre-sales bot. Add the website origin to the pre-sales bot `CORS_ORIGINS`.

See [`website/README.md`](website/README.md).

## Deploy on Vercel (two projects)

Create **two** Vercel projects from this GitHub repo. Do not deploy the repo root as a single project.

### 1. Chat-bot

1. New Project → this repo → **Root Directory** `chat-bot`.
2. Settings → Environment Variables → import [`chat-bot/.env.production`](chat-bot/.env.production). Copy the same API keys you use locally from `.env`.
3. Deploy. Copy the URL (`https://YOUR-BOT.vercel.app`).
4. In the Neon SQL editor run `CREATE EXTENSION IF NOT EXISTS vector;` so RAG can use pgvector. Without it the bot still runs (in-process fallback).

### 2. Website

1. New Project → this repo → **Root Directory** `website`.
2. Import [`website/.env.production`](website/.env.production).
3. Set `CHAT_BOT_URL` to the pre-sales bot URL (`https://pre-sales-bot-ten.vercel.app`, no trailing slash) and `CHAT_BOT_TENANT=demo`.
4. Deploy. Copy the URL (`https://YOUR-SITE.vercel.app`).

### 3. After both URLs exist

Update the **bot** project env and redeploy:

```
CORS_ORIGINS=https://YOUR-SITE.vercel.app,https://YOUR-BOT.vercel.app
PUBLIC_BASE_URL=https://YOUR-BOT.vercel.app
GOOGLE_REDIRECT_URI=https://YOUR-BOT.vercel.app/admin/google/callback
```

Optional: set `CORS_ORIGIN_REGEX` to `https://.*\.vercel\.app` so Preview deployments can call the API. Blank CORS values also fall back to localhost plus that Vercel regex.

In Google Cloud OAuth, add `https://YOUR-BOT.vercel.app/admin/google/callback` as an authorized redirect URI, then connect the calendar at `/admin/calendar`.

RFP uploads on Vercel are stored under `/tmp` and are not durable unless you later set `GCS_BUCKET`.

Cloud Run remains supported for the bot only (`cd chat-bot && gcloud builds submit --config cloudbuild.yaml`). See [`chat-bot/README.md`](chat-bot/README.md).

## Embed on any site

```html
<script src="https://YOUR_BOT_URL/widget/consultant.js"
        data-api="https://YOUR_BOT_URL"
        async></script>
```

Add the site origin to `CORS_ORIGINS`. Page path is sent automatically so service pages start different conversations.

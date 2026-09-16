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
Admin: [http://localhost:8000/admin](http://localhost:8000/admin) (`admin` / `northline-admin`).

Leave `LLM_API_KEY` empty to use the built-in fallback consultant (fully demoable offline).

```bash
make docker
make test
```

Cloud Run deploys **only** `chat-bot/`:

```bash
cd chat-bot
gcloud builds submit --config cloudbuild.yaml
```

See [`chat-bot/README.md`](chat-bot/README.md).

## Website

```bash
cd website
python3 -m http.server 3000
```

Keep the bot running on port 8000. Pages load `consultant.js` from `window.CHAT_BOT_URL` in [`website/bot-config.js`](website/bot-config.js). Change that value for production, and add the website origin to `chat-bot` `CORS_ORIGINS`.

See [`website/README.md`](website/README.md).

## Embed on any site

```html
<script src="https://YOUR_CLOUD_RUN_URL/widget/consultant.js"
        data-api="https://YOUR_CLOUD_RUN_URL"
        async></script>
```

Add the site origin to `CORS_ORIGINS`. Page path is sent automatically so service pages start different conversations.

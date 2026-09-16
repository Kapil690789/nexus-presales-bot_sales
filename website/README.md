# Website

Static DevConsult marketing site. Deploy this folder on its own (GCS + CDN, Netlify, Firebase Hosting, or any static host). There is no Python or Docker build for the site.

The advisor is **not** bundled here. Pages load it from the chat-bot service via [`bot-config.js`](bot-config.js) and [`embed.js`](embed.js).

## Local

Start the bot first (`cd ../chat-bot && make run` on port 8000), then:

```bash
python3 -m http.server 3000
```

Open [http://localhost:3000/](http://localhost:3000/). Home, service, and pricing pages should show the chat launcher and talk to `http://localhost:8000`.

## Point at a deployed bot

Edit [`bot-config.js`](bot-config.js):

```js
window.CHAT_BOT_URL = "https://YOUR_CLOUD_RUN_URL";
```

Add the website origin (for example `https://www.example.com` or `http://localhost:3000`) to the bot’s `CORS_ORIGINS`.

## Deploy

Upload this folder as a static site. No website Cloud Run service is required. Keep `bot-config.js` pointed at the production chat-bot URL.

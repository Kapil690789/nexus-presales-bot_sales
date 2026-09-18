# Website

Static DevConsult marketing site. Deploy this folder on its own (GCS + CDN, Netlify, Firebase Hosting, or any static host). There is no Python or Docker build for the site.

The advisor is **not** bundled here. Pages load it from the chat-bot service via [`bot-config.js`](bot-config.js) and [`embed.js`](embed.js).

## Local

Start the bot first (`cd ../chat-bot && make run` on port 8000), then:

```bash
python3 -m http.server 3000
```

Open [http://localhost:3000/](http://localhost:3000/). The header switches dummy screens — **Website**, **Mobile apps**, **AI solutions**, **UI/UX**, and **Staff aug** — plus Home, Work, and Contact. Each service tab has its own mock UI, and opening the advisor starts a conversation for that page. Refreshing the same tab restores the thread; switching tabs starts a new one. Use **New conversation** in the widget header to clear the chat and begin again. The contact page also has a **Book a live consultation** button that opens the advisor.

## Point at a deployed bot

Edit [`bot-config.js`](bot-config.js):

```js
window.CHAT_BOT_URL = "https://YOUR_CLOUD_RUN_URL";
```

Add the website origin (for example `https://www.example.com` or `http://localhost:3000`) to the bot’s `CORS_ORIGINS`.

## Deploy

Upload this folder as a static site. No website Cloud Run service is required. Keep `bot-config.js` pointed at the production chat-bot URL.

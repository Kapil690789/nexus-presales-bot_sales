const fs = require("fs");
const path = require("path");

const DEFAULT_URL = "https://pre-sales-bot-ten.vercel.app";
const configured = String(process.env.CHAT_BOT_URL || "")
  .trim()
  .replace(/\/$/, "");
// The website used to embed the older chat-bot. Keep that host from winning
// a rebuild when the Vercel env var is still set to it.
const url = !configured || configured.includes("dummy-chat-bot") ? DEFAULT_URL : configured;
const tenant = String(process.env.CHAT_BOT_TENANT || "demo").trim() || "demo";

const target = path.join(__dirname, "..", "bot-config.js");
fs.writeFileSync(
  target,
  `window.CHAT_BOT_URL = ${JSON.stringify(url)};\nwindow.CHAT_BOT_TENANT = ${JSON.stringify(tenant)};\n`
);

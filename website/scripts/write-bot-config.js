const fs = require("fs");
const path = require("path");

const url = String(process.env.CHAT_BOT_URL || "")
  .trim()
  .replace(/\/$/, "");
if (!url) {
  process.exit(0);
}

const target = path.join(__dirname, "..", "bot-config.js");
fs.writeFileSync(target, `window.CHAT_BOT_URL = ${JSON.stringify(url)};\n`);

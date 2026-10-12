window.CHAT_BOT_URL =
  window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
    ? "http://localhost:8010"
    : "https://pre-sales-bot-ten.vercel.app";
window.CHAT_BOT_TENANT = "demo";

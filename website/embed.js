(function loadConsultant() {
  function mount() {
    if (document.querySelector('script[src*="consultant.js"]')) {
      return;
    }
    var isLocal = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
    var fallbackUrl = isLocal ? "http://localhost:8010" : "https://nexus-presales-bot-sales.vercel.app";
    var base = String(window.CHAT_BOT_URL || fallbackUrl).replace(/\/$/, "");
    var tenant = String(window.CHAT_BOT_TENANT || "demo").trim();
    var script = document.createElement("script");
    script.src = base + "/widget/consultant.js";
    script.dataset.api = base;
    script.dataset.tenant = tenant;
    script.async = true;
    document.body.appendChild(script);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();

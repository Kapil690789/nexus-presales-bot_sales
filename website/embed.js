(function loadConsultant() {
  if (!document.body) {
    document.addEventListener("DOMContentLoaded", loadConsultant);
    return;
  }
  var base = String(window.CHAT_BOT_URL || "https://pre-sales-bot-ten.vercel.app").replace(/\/$/, "");
  var tenant = String(window.CHAT_BOT_TENANT || "demo").trim();
  var script = document.createElement("script");
  script.src = base + "/widget/consultant.js";
  script.dataset.api = base;
  script.dataset.tenant = tenant;
  script.async = true;
  document.body.appendChild(script);
})();

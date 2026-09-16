(function loadConsultant() {
  if (!document.body) {
    document.addEventListener("DOMContentLoaded", loadConsultant);
    return;
  }
  var base = String(window.CHAT_BOT_URL || "http://localhost:8000").replace(/\/$/, "");
  var script = document.createElement("script");
  script.src = base + "/widget/consultant.js";
  script.dataset.api = base;
  script.async = true;
  document.body.appendChild(script);
})();

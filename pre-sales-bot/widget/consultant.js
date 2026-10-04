(function () {
  var script = document.currentScript || document.querySelector("script[data-tenant]");
  if (!script) return;
  var tenant = (script.dataset.tenant || "").trim();
  var api = (script.dataset.api || "").trim().replace(/\/$/, "");
  if (!api) api = window.location.origin.replace(/\/$/, "");

  var brand = {
    primary: "#0A0A0A",
    accent: "#3B82F6",
    background: "#0A0A0A",
    surface: "#121212",
    text: "#EDEDED",
    muted: "#A1A1AA",
    radius_px: 16,
    logo_text: "Nexus Advisor",
    launcher_text: "Talk to an advisor",
    launcher_subtitle: "Scope, estimate, and next steps",
    widget_title: "Nexus Advisor",
    widget_subtitle: "Online",
    placeholder: "Type your message...",
    position: "bottom-right"
  };

  var ICONS = {
    chat: '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M5 6.5A2.5 2.5 0 0 1 7.5 4h9A2.5 2.5 0 0 1 19 6.5v7A2.5 2.5 0 0 1 16.5 16H11l-4 3.2V16H7.5A2.5 2.5 0 0 1 5 13.5v-7Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="M8.5 9h7M8.5 12h4" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>',
    close: '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M7 7l10 10M17 7 7 17" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
    expand: '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    compress: '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4 14h6v6M20 10h-6V4M10 14l-7 7M14 10l7-7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    restart: '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M3 12a9 9 0 0 1 15.5-6.4L21 8M21 3v5h-5M21 12a9 9 0 0 1-15.5 6.4L3 16M3 21v-5h5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    info: '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.8"/><path d="M12 16v-4M12 8h.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
    clip: '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M15.2 7.2 8.4 14a3.1 3.1 0 0 0 4.4 4.4l7.1-7.2a5 5 0 0 0-7.1-7.1L6 11.8" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>',
    download: '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 3v13M12 16l4-4M12 16l-4-4M4 19h16" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    print: '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M6 9V3h12v6M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><rect x="6" y="14" width="12" height="7" rx="1" stroke="currentColor" stroke-width="1.8"/><circle cx="18" cy="12" r="1" fill="currentColor"/></svg>',
    send: '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M5 12 20 5l-6.2 14-2.1-5.2L5 12Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="m11.7 13.8 8.3-8.8" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>',
    avatar: '<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><rect width="80" height="80" fill="#0A0A0A"/><circle cx="40" cy="30" r="14" fill="#EDEDED"/><path d="M16 72c4-16 16-24 24-24s20 8 24 24" fill="#EDEDED"/><rect x="28" y="48" width="24" height="18" rx="6" fill="#0A0A0A"/></svg>'
  };

  var font = document.createElement("link");
  font.rel = "stylesheet";
  font.href = "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap";
  document.head.appendChild(font);

  var style = document.createElement("style");
  style.textContent = [
    ".ps-root{--ps-primary:#0a0a0a;--ps-accent:#3b82f6;--ps-bg:#0a0a0a;--ps-surface:#121212;--ps-text:#ededed;--ps-muted:#a1a1aa;--ps-success:#10b981;--ps-border:rgba(255,255,255,0.1);--ps-silver:#18181b;--ps-radius:16px;font-family:Inter,ui-sans-serif,system-ui,sans-serif;color:var(--ps-text)}",
    ".ps-root,.ps-root *{box-sizing:border-box}",
    ".ps-launcher{position:fixed;z-index:2147483000;width:56px;height:56px;padding:0;border:1px solid rgba(255,255,255,0.18);cursor:pointer;background:#0A0A0A;color:#fff;border-radius:50%;box-shadow:0 10px 30px rgba(0,0,0,.6);display:grid;place-items:center;animation:ps-launcher-in 320ms ease-out}",
    ".ps-launcher.bottom-right{right:40px;bottom:40px}",
    ".ps-launcher.bottom-left{left:40px;bottom:40px}",
    ".ps-launcher svg{width:22px;height:22px;display:block}",
    ".ps-launcher[hidden]{display:none !important}",
    ".ps-panel{position:fixed;z-index:2147483001;width:min(400px,calc(100vw - 32px));height:min(580px,calc(100vh - 96px));background:#0A0A0A;border:1px solid rgba(255,255,255,0.12);border-radius:var(--ps-radius);box-shadow:0 20px 50px rgba(0,0,0,.8);display:flex;flex-direction:column;overflow:hidden;opacity:0;transform:translateY(18px);pointer-events:none;visibility:hidden}",
    ".ps-panel.bottom-right{right:40px;bottom:40px}",
    ".ps-panel.bottom-left{left:40px;bottom:40px}",
    ".ps-panel.is-open{opacity:1;transform:translateY(0);pointer-events:auto;visibility:visible;animation:ps-enter 300ms ease-out}",
    "@keyframes ps-enter{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:translateY(0)}}",
    "@keyframes ps-launcher-in{from{opacity:0;transform:scale(.86)}to{opacity:1;transform:scale(1)}}",
    "@keyframes ps-msg-in{from{opacity:0}to{opacity:1}}",
    "@keyframes ps-chip-in{from{opacity:0}to{opacity:1}}",
    ".ps-header{background:#0D0E12;border-bottom:1px solid rgba(255,255,255,0.08);color:#fff;padding:14px 14px 14px 16px;display:flex;align-items:center;justify-content:space-between;gap:10px;flex-shrink:0;position:relative;z-index:2}",
    ".ps-avatar{width:36px;height:36px;border-radius:50%;border:1px solid rgba(255,255,255,0.2);overflow:hidden;flex-shrink:0;background:#18181B}",
    ".ps-avatar svg{display:block;width:100%;height:100%}",
    ".ps-identity{flex:1;min-width:0;margin-left:2px}",
    ".ps-identity strong{display:block;font-size:14px;font-weight:700;letter-spacing:-.01em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#FFFFFF}",
    ".ps-status{display:flex;align-items:center;gap:6px;margin:2px 0 0;font-size:11px;font-weight:500;color:#A1A1AA}",
    ".ps-online-dot{width:7px;height:7px;border-radius:50%;background:var(--ps-success);box-shadow:0 0 8px var(--ps-success)}",
    ".ps-header-actions{display:flex;align-items:center;gap:4px;flex-shrink:0}",
    ".ps-header-btn{background:transparent;color:#A1A1AA;border:0;cursor:pointer;width:30px;height:30px;display:grid;place-items:center;border-radius:6px;padding:0;transition:all 150ms ease}",
    ".ps-header-btn:hover{color:#FFFFFF;background:rgba(255,255,255,.08)}",
    ".ps-header-btn svg{width:16px;height:16px;display:block}",
    ".ps-close{background:transparent;color:#A1A1AA;border:0;cursor:pointer;width:30px;height:30px;display:grid;place-items:center;border-radius:6px;padding:0;transition:all 150ms ease}",
    ".ps-close:hover{color:#FFFFFF;background:rgba(255,255,255,.08)}",
    ".ps-close svg{width:16px;height:16px;display:block}",
    ".ps-panel.is-centered{width:min(760px,calc(100vw - 32px)) !important;height:min(680px,calc(100vh - 60px)) !important;top:50% !important;left:50% !important;right:auto !important;bottom:auto !important;transform:translate(-50%,-50%) !important;box-shadow:0 25px 60px -12px rgba(0,0,0,.9),0 0 0 100vmax rgba(0,0,0,.65) !important;border-radius:20px !important}",
    ".ps-panel.is-centered .ps-thread{padding:20px 24px}",
    ".ps-panel.is-centered .ps-msg{max-width:78%;font-size:15px}",
    ".ps-panel.is-centered .ps-compose{padding:4px 16px 16px}",
    ".ps-thread{flex:1;min-height:0;overflow-x:hidden;overflow-y:auto;padding:16px 16px 8px;background:#0A0A0A}",
    ".ps-msg{width:fit-content;max-width:86%;margin:0 0 10px;padding:10px 12px;border-radius:14px;font-size:13.5px;line-height:1.5;white-space:pre-wrap;animation:ps-msg-in 220ms ease-out}",
    ".ps-msg.assistant{background:#141518;color:#EDEDED;border:1px solid rgba(255,255,255,0.06);margin-right:auto;border-radius:4px 14px 14px 14px}",
    ".ps-msg.user{background:#2563EB;color:#fff;margin-left:auto;border-radius:14px 4px 14px 14px}",
    ".ps-msg.ps-typing{min-width:180px;padding:14px;animation:none}",
    ".ps-shimmer{display:flex;flex-direction:column;gap:8px;width:168px}",
    ".ps-shimmer-line{display:block;height:8px;width:100%;border-radius:999px;background:linear-gradient(90deg,#222 0%,#333 45%,#222 100%);background-size:200% 100%;animation:ps-shimmer 1.15s ease-in-out infinite}",
    ".ps-shimmer-line-mid{width:78%;animation-delay:.12s}",
    ".ps-shimmer-line-short{width:52%;animation-delay:.24s}",
    "@keyframes ps-shimmer{0%{background-position:100% 0}100%{background-position:-100% 0}}",
    ".ps-card{background:#111215;border:1px solid rgba(255,255,255,0.1);border-radius:14px;padding:14px 16px;margin:0 0 10px;font-size:13px;box-shadow:0 8px 24px rgba(0,0,0,.5);animation:ps-msg-in 240ms ease-out;color:#EDEDED}",
    ".ps-card h4{margin:0 0 8px;font-size:14px;color:#FFFFFF}",
    ".ps-card p{margin:6px 0 0;color:#A1A1AA}",
    ".ps-card .ps-range{font-size:20px;color:#60A5FA;font-weight:700}",
    ".ps-card ul{margin:8px 0 0;padding-left:18px;color:#D4D4D8}",
    ".ps-card a{color:#60A5FA}",
    ".ps-card strong{display:block;margin-top:8px;color:#FFFFFF}",
    ".ps-disclaimer{color:#71717A;font-size:11px;margin-top:8px}",
    ".ps-booking{display:flex;flex-direction:column;gap:8px}",
    ".ps-booking-link{color:#60A5FA;font-weight:600;font-size:13px}",
    ".ps-chips{display:flex;flex-wrap:wrap;gap:8px;padding:4px 16px 12px;flex-shrink:0;position:relative;z-index:2;background:#0A0A0A}",
    ".ps-chips:empty{display:none}",
    ".ps-chip{border:1px solid rgba(255,255,255,0.15);background:rgba(255,255,255,0.04);color:#F4F4F5;border-radius:999px;padding:6px 12px;cursor:pointer;font-size:12px;font-weight:500;font-family:inherit;transition:all 150ms ease-in-out;animation:ps-chip-in 200ms ease-out both}",
    ".ps-chip:nth-child(1){animation-delay:0ms}",
    ".ps-chip:nth-child(2){animation-delay:40ms}",
    ".ps-chip:nth-child(3){animation-delay:80ms}",
    ".ps-chip:nth-child(4){animation-delay:120ms}",
    ".ps-chip:hover{background:#FFFFFF;color:#000000;border-color:#FFFFFF}",
    ".ps-thumb{display:flex;gap:10px;margin-top:8px}",
    ".ps-thumb button{border:0;background:transparent;color:#71717A;font:inherit;font-size:11px;font-weight:500;cursor:pointer;padding:0}",
    ".ps-thumb button:hover{color:#FFFFFF}",
    ".ps-thumb button:disabled{opacity:.4;cursor:default}",
    ".ps-compose{padding:0 12px 12px;border-top:1px solid rgba(255,255,255,0.08);background:#0A0A0A;flex-shrink:0;position:relative;z-index:2}",
    ".ps-compose form{display:flex;align-items:center;gap:4px;min-width:0}",
    ".ps-compose input[type=text]{flex:1;border:0;outline:0;background:transparent;padding:10px 4px;font:inherit;font-size:14px;color:#FFFFFF;min-width:0}",
    ".ps-compose input[type=text]::placeholder{color:#52525B}",
    ".ps-attachment-box{padding:6px 4px 4px;display:flex;align-items:center;gap:6px;animation:ps-msg-in 140ms ease-out}",
    ".ps-attachment-pill{display:inline-flex;align-items:center;gap:6px;background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.15);border-radius:8px;padding:4px 8px;font-size:12px;color:#EDEDED;max-width:100%}",
    ".ps-attachment-name{font-weight:500;max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}",
    ".ps-attachment-size{color:#A1A1AA;font-size:11px}",
    ".ps-attachment-remove{background:transparent;border:0;color:#A1A1AA;font-size:15px;line-height:1;cursor:pointer;padding:0 3px;border-radius:4px;display:grid;place-items:center}",
    ".ps-attachment-remove:hover{color:#EF4444;background:rgba(239,68,68,0.15)}",
    ".ps-icon-btn.has-attachment{color:#60A5FA;background:rgba(96,165,250,0.15)}",
    ".ps-hidden{position:absolute !important;width:1px !important;height:1px !important;padding:0 !important;margin:-1px !important;overflow:hidden !important;clip:rect(0,0,0,0) !important;white-space:nowrap !important;border:0 !important;opacity:0}",
    ".ps-icon-btn{width:34px;height:34px;border:0;background:transparent;color:#A1A1AA;display:grid;place-items:center;cursor:pointer;border-radius:8px;flex:0 0 34px;padding:0}",
    ".ps-icon-btn:hover{background:rgba(255,255,255,0.06);color:#FFFFFF}",
    ".ps-icon-btn svg{width:18px;height:18px;display:block}",
    ".ps-send{width:36px;height:36px;border:0;border-radius:50%;background:#FFFFFF;color:#000000;display:grid;place-items:center;cursor:pointer;flex:0 0 36px;padding:0;transition:transform 150ms ease}",
    ".ps-send:hover{transform:scale(1.05)}",
    ".ps-send svg{width:16px;height:16px;display:block}",
    ".ps-send:disabled,.ps-compose input:disabled{opacity:.4;cursor:default}",
    ".ps-thread::-webkit-scrollbar{width:5px}.ps-thread::-webkit-scrollbar-thumb{background:rgba(255,255,255,.15);border-radius:4px}.ps-thread::-webkit-scrollbar-thumb:hover{background:rgba(255,255,255,.25)}",
    ".ps-msg code{background:rgba(255,255,255,.08);padding:2px 5px;border-radius:4px;font-size:12px;font-family:ui-monospace,monospace;color:#60A5FA}",
    ".ps-msg.assistant a{color:#60A5FA;font-weight:600;text-decoration:underline}",
    ".ps-char-count{font-size:10px;color:var(--ps-muted);text-align:right;padding:0 8px 4px;margin-top:-4px;display:none}",
    ".ps-char-count.visible{display:block}",
    ".ps-char-count.warn{color:#e11d48;font-weight:600}",
    ".ps-thumb-btn{border:0;background:transparent;color:var(--ps-muted);font:inherit;font-size:11px;font-weight:500;cursor:pointer;padding:2px 6px;border-radius:4px;transition:background 150ms ease}",
    ".ps-thumb-btn:hover{background:var(--ps-silver);color:var(--ps-text)}",
    ".ps-thumb-btn.selected{color:var(--ps-success);font-weight:600;pointer-events:none}",
    ".ps-guide-overlay{position:absolute;inset:0;background:rgba(0,0,0,0.85);backdrop-filter:blur(4px);z-index:100;display:flex;align-items:center;justify-content:center;padding:16px;animation:ps-msg-in 180ms ease-out}",
    ".ps-guide-box{background:#111215;border:1px solid rgba(255,255,255,0.15);border-radius:14px;padding:18px;max-width:340px;width:100%;color:#EDEDED;box-shadow:0 12px 32px rgba(0,0,0,0.7)}",
    ".ps-guide-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;border-bottom:1px solid rgba(255,255,255,0.08);padding-bottom:10px}",
    ".ps-guide-header h4{margin:0;font-size:14px;font-weight:600;color:#FFFFFF}",
    ".ps-guide-close{background:transparent;border:0;color:#A1A1AA;font-size:20px;line-height:1;cursor:pointer;padding:0 4px}",
    ".ps-guide-close:hover{color:#fff}",
    ".ps-guide-body{display:flex;flex-direction:column;gap:12px;font-size:12px;line-height:1.45;color:#A1A1AA}",
    ".ps-guide-step{display:flex;gap:10px;align-items:flex-start}",
    ".ps-guide-step strong{color:#FFFFFF;display:inline}",
    ".ps-step-badge{background:rgba(59,130,246,0.18);color:#60A5FA;border:1px solid rgba(96,165,250,0.3);width:20px;height:20px;border-radius:50%;display:grid;place-items:center;font-size:10px;font-weight:700;flex-shrink:0;margin-top:1px}",
    ".ps-guide-ok{margin-top:16px;width:100%;background:#2563EB;color:#fff;border:0;border-radius:8px;padding:8px;font-size:12px;font-weight:600;cursor:pointer;transition:background 150ms}",
    ".ps-guide-ok:hover{background:#1D4ED8}",
    "@media (max-width:520px){.ps-panel,.ps-panel.bottom-right,.ps-panel.bottom-left{width:100vw;height:100vh;height:100dvh;right:0 !important;left:0 !important;bottom:0 !important;border-radius:0}.ps-launcher.bottom-right,.ps-launcher.bottom-left{right:16px;bottom:16px;left:auto}.ps-compose input[type=text]{font-size:16px}.ps-compose{padding-bottom:max(12px, env(safe-area-inset-bottom))}}",
    "@media (prefers-reduced-motion:reduce){.ps-launcher,.ps-panel.is-open,.ps-msg,.ps-card,.ps-chip,.ps-online-dot,.ps-shimmer-line{animation:none !important}}",
    "@media print{body>*:not(#ps-widget-root){display:none !important}#ps-widget-root .ps-launcher{display:none !important}#ps-widget-root .ps-panel{display:block !important;position:static !important;width:100% !important;height:auto !important;max-height:none !important;border:none !important;box-shadow:none !important;background:#fff !important;color:#111 !important}#ps-widget-root .ps-header{border-bottom:1px solid #ddd !important;background:#f8fafc !important;color:#111 !important}#ps-widget-root .ps-header-actions,#ps-widget-root .ps-chips,#ps-widget-root .ps-compose,#ps-widget-root .ps-guide-overlay{display:none !important}#ps-widget-root .ps-thread{overflow:visible !important;height:auto !important;padding:16px 0 !important}#ps-widget-root .ps-msg{color:#111 !important;border:1px solid #e2e8f0 !important}#ps-widget-root .ps-msg.assistant{background:#f8fafc !important}#ps-widget-root .ps-msg.user{background:#eff6ff !important;border-color:#bfdbfe !important}#ps-widget-root .ps-card{background:#fff !important;border:1px solid #cbd5e1 !important;color:#111 !important}}"
  ].join("");
  document.head.appendChild(style);

  var root = el("div", "ps-root");
  root.id = "ps-widget-root";
  var launcher = el("button", "ps-launcher bottom-right");
  launcher.type = "button";
  launcher.innerHTML = ICONS.chat;
  var panel = el("section", "ps-panel bottom-right");
  panel.setAttribute("aria-hidden", "true");
  var header = el("div", "ps-header");
  var avatar = el("div", "ps-avatar");
  avatar.innerHTML = ICONS.avatar;
  var identity = el("div", "ps-identity");
  var titleEl = el("strong");
  var status = el("p", "ps-status");
  var dot = el("span", "ps-online-dot");
  dot.setAttribute("aria-hidden", "true");
  var statusEl = el("span");
  status.appendChild(dot);
  status.appendChild(statusEl);
  identity.appendChild(titleEl);
  identity.appendChild(status);

  var headerActions = el("div", "ps-header-actions");
  var infoBtn = el("button", "ps-header-btn");
  infoBtn.type = "button";
  infoBtn.title = "How Nexus Advisor works";
  infoBtn.setAttribute("aria-label", "How Nexus Advisor works");
  infoBtn.innerHTML = ICONS.info;

  var downloadBtn = el("button", "ps-header-btn");
  downloadBtn.type = "button";
  downloadBtn.title = "Download chat transcript";
  downloadBtn.setAttribute("aria-label", "Download chat transcript");
  downloadBtn.innerHTML = ICONS.download;

  var printBtn = el("button", "ps-header-btn");
  printBtn.type = "button";
  printBtn.title = "Print conversation / PDF";
  printBtn.setAttribute("aria-label", "Print conversation / PDF");
  printBtn.innerHTML = ICONS.print;

  var restartBtn = el("button", "ps-header-btn");
  restartBtn.type = "button";
  restartBtn.title = "Start new conversation";
  restartBtn.setAttribute("aria-label", "Start new conversation");
  restartBtn.innerHTML = ICONS.restart;

  var expandBtn = el("button", "ps-header-btn");
  expandBtn.type = "button";
  expandBtn.title = "Center studio view";
  expandBtn.setAttribute("aria-label", "Center studio view");
  expandBtn.innerHTML = ICONS.expand;

  var close = el("button", "ps-close");
  close.type = "button";
  close.setAttribute("aria-label", "Close");
  close.innerHTML = ICONS.close;

  headerActions.appendChild(infoBtn);
  headerActions.appendChild(downloadBtn);
  headerActions.appendChild(printBtn);
  headerActions.appendChild(restartBtn);
  headerActions.appendChild(expandBtn);
  headerActions.appendChild(close);

  header.appendChild(avatar);
  header.appendChild(identity);
  header.appendChild(headerActions);
  var thread = el("div", "ps-thread");
  thread.id = "ps-log";
  var chipsBox = el("div", "ps-chips");
  var compose = el("div", "ps-compose");
  var attachmentBox = el("div", "ps-attachment-box");
  attachmentBox.style.display = "none";
  var form = el("form");
  var input = document.createElement("input");
  input.type = "text";
  input.maxLength = 1000;
  var uploadId = "ps-upload-" + Math.random().toString(36).slice(2, 8);
  var uploadBtn = el("label", "ps-icon-btn");
  uploadBtn.title = "Upload a brief";
  uploadBtn.setAttribute("aria-label", "Upload a brief");
  uploadBtn.htmlFor = uploadId;
  uploadBtn.innerHTML = ICONS.clip;
  var file = document.createElement("input");
  file.type = "file";
  file.id = uploadId;
  file.className = "ps-hidden";
  file.accept = ".pdf,.doc,.docx,.txt,.md";
  var send = el("button", "ps-send");
  send.type = "submit";
  send.setAttribute("aria-label", "Send");
  send.innerHTML = ICONS.send;
  form.appendChild(input);
  form.appendChild(uploadBtn);
  form.appendChild(send);
  form.appendChild(file);
  compose.appendChild(attachmentBox);
  compose.appendChild(form);
  panel.appendChild(header);
  panel.appendChild(thread);
  panel.appendChild(chipsBox);
  panel.appendChild(compose);

  var guideModal = el("div", "ps-guide-overlay");
  guideModal.style.display = "none";
  guideModal.innerHTML = [
    '<div class="ps-guide-box">',
      '<div class="ps-guide-header">',
        '<h4>How Nexus Advisor Works</h4>',
        '<button type="button" class="ps-guide-close" aria-label="Close guide">&times;</button>',
      '</div>',
      '<div class="ps-guide-body">',
        '<div class="ps-guide-step">',
          '<span class="ps-step-badge">1</span>',
          '<div><strong>Interactive Scoping:</strong> Select features or share your vision. Chips adapt intelligently without repetitive loops.</div>',
        '</div>',
        '<div class="ps-guide-step">',
          '<span class="ps-step-badge">2</span>',
          '<div><strong>Technical Architecture:</strong> Recommends modern stack, key integrations, and initial launch boundaries.</div>',
        '</div>',
        '<div class="ps-guide-step">',
          '<span class="ps-step-badge">3</span>',
          '<div><strong>Deterministic Estimates:</strong> Calibrated engineering squad sizing and timelines without guesswork.</div>',
        '</div>',
        '<div class="ps-guide-step">',
          '<span class="ps-step-badge">4</span>',
          '<div><strong>Direct Booking:</strong> Schedule a 30-min discovery call or export your project proposal.</div>',
        '</div>',
      '</div>',
      '<button type="button" class="ps-guide-ok">Got it</button>',
    '</div>'
  ].join("");
  panel.appendChild(guideModal);

  infoBtn.addEventListener("click", function(e) {
    e.stopPropagation();
    guideModal.style.display = guideModal.style.display === "none" ? "flex" : "none";
  });
  guideModal.querySelector(".ps-guide-close").addEventListener("click", function() {
    guideModal.style.display = "none";
  });
  guideModal.querySelector(".ps-guide-ok").addEventListener("click", function() {
    guideModal.style.display = "none";
  });
  guideModal.addEventListener("click", function(e) {
    if (e.target === guideModal) {
      guideModal.style.display = "none";
    }
  });

  root.appendChild(launcher);
  root.appendChild(panel);
  document.body.appendChild(root);

  var sessionId = "";
  var ndaVersion = "";
  var busy = false;

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
  }

  function esc(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function safeUrl(url) {
    var value = String(url || "").trim();
    if (!/^https?:\/\//i.test(value)) return "";
    return esc(value);
  }

  function list(items) {
    if (!items || !items.length) return "";
    return "<ul>" + items.map(function (item) { return "<li>" + esc(item) + "</li>"; }).join("") + "</ul>";
  }

  function applyBrand() {
    root.style.setProperty("--ps-primary", brand.primary || "#0A0A0A");
    root.style.setProperty("--ps-accent", brand.accent || "#3B82F6");
    root.style.setProperty("--ps-bg", brand.background || "#0A0A0A");
    root.style.setProperty("--ps-surface", brand.surface || "#121212");
    root.style.setProperty("--ps-text", brand.text || "#EDEDED");
    root.style.setProperty("--ps-muted", brand.muted || "#A1A1AA");
    root.style.setProperty("--ps-radius", (brand.radius_px || 16) + "px");
    var pos = brand.position === "bottom-left" ? "bottom-left" : "bottom-right";
    launcher.classList.remove("bottom-left", "bottom-right");
    launcher.classList.add(pos);
    panel.classList.remove("bottom-left", "bottom-right");
    panel.classList.add(pos);
    titleEl.textContent = brand.widget_title || "Nexus Advisor";
    statusEl.textContent = brand.widget_subtitle || "Online";
    input.placeholder = brand.placeholder || "Type your message...";
    input.setAttribute("aria-label", brand.placeholder || "Message");
    launcher.setAttribute("aria-label", [brand.launcher_text, brand.launcher_subtitle].filter(Boolean).join(". "));
    panel.setAttribute("aria-label", brand.widget_title || "Nexus Advisor");
  }

  function scrollThread() {
    thread.scrollTop = thread.scrollHeight;
  }

  function renderMarkdown(text) {
    if (!text) return "";
    var safe = esc(text);
    safe = safe.replace(/`([^`]+)`/g, "<code>$1</code>");
    safe = safe.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    safe = safe.replace(/\*([^*]+)\*/g, "<em>$1</em>");
    safe = safe.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
    return safe;
  }

  function say(role, text) {
    if (!text) return null;
    var node = el("div", "ps-msg " + (role === "user" ? "user" : "assistant"));
    if (role === "assistant") {
      node.innerHTML = renderMarkdown(text);
    } else {
      node.textContent = text;
    }
    thread.appendChild(node);
    scrollThread();
    return node;
  }

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && panel.classList.contains("is-open")) {
      closePanel();
    }
  });

  function showTyping() {
    hideTyping();
    var node = el("div", "ps-msg assistant ps-typing");
    node.id = "ps-typing";
    node.setAttribute("aria-label", "Advisor is typing");
    node.innerHTML = '<div class="ps-shimmer"><span class="ps-shimmer-line"></span><span class="ps-shimmer-line ps-shimmer-line-mid"></span><span class="ps-shimmer-line ps-shimmer-line-short"></span></div>';
    thread.appendChild(node);
    scrollThread();
  }

  function hideTyping() {
    var node = document.getElementById("ps-typing");
    if (node) node.remove();
  }

  function beginWait() {
    if (busy) return false;
    busy = true;
    input.disabled = true;
    send.disabled = true;
    showTyping();
    return true;
  }

  function endWait() {
    busy = false;
    input.disabled = false;
    send.disabled = false;
    hideTyping();
  }

  function setChips(chips) {
    chipsBox.innerHTML = "";
    (chips || []).forEach(function (chip) {
      var button = el("button", "ps-chip", chip.label || "");
      button.type = "button";
      button.onclick = function () {
        if (!sessionId || busy) return;
        setChips([]);
        say("user", chip.label || "");
        if (!beginWait()) return;
        post("/api/v1/sessions/" + sessionId + "/messages", { content: chip.label || "", chip: chip }).then(renderReply).catch(fail);
      };
      chipsBox.appendChild(button);
    });
  }

  function renderCard(card) {
    var wrap = el("div", "ps-card");
    var html = "";
    if (card.type === "booking") {
      if (card.slots) {
        html = "<h4>" + esc(card.title || "Pick a time") + "</h4>";
        if (card.live === false) html += '<p class="ps-disclaimer">Demo times until Google Calendar is connected.</p>';
      } else {
        wrap.className = "ps-card ps-booking";
        html = "<h4>" + esc(card.title || "You're booked") + "</h4>";
        if (card.label) html += "<p>" + esc(card.label) + "</p>";
        if (safeUrl(card.meet_url)) html += '<a class="ps-booking-link" href="' + safeUrl(card.meet_url) + '" target="_blank" rel="noreferrer">Join Google Meet</a>';
        if (safeUrl(card.html_link)) html += '<a class="ps-booking-link" href="' + safeUrl(card.html_link) + '" target="_blank" rel="noreferrer">Open in Google Calendar</a>';
      }
      wrap.innerHTML = html;
      return wrap;
    }
    if (card.type === "estimate") {
      html = "<h4>" + esc(card.title || "Indicative range") + "</h4>";
      html += '<div class="ps-range">' + esc(card.range || "") + "</div>";
      var meta = [];
      if (card.weeks != null && card.weeks !== "") meta.push(esc(card.weeks) + " weeks");
      if (card.team && card.team.length) meta.push(esc(card.team.join(", ")));
      if (meta.length) html += "<div>" + meta.join(" · ") + "</div>";
      if (card.inclusions && card.inclusions.length) html += "<div><strong>Includes</strong>" + list(card.inclusions) + "</div>";
      if (card.assumptions && card.assumptions.length) html += "<div><strong>What drives this range</strong>" + list(card.assumptions) + "</div>";
      if (card.disclaimer) html += '<p class="ps-disclaimer">' + esc(card.disclaimer) + "</p>";
    } else if (card.type === "architecture") {
      html = "<h4>" + esc(card.title || "Architecture") + "</h4>";
      if (card.frontend && card.frontend.length) html += "<p>Frontend: " + esc(card.frontend.join(", ")) + "</p>";
      if (card.backend && card.backend.length) html += "<p>Backend: " + esc(card.backend.join(", ")) + "</p>";
      html += list(card.notes);
    } else if (card.type === "mvp") {
      html = "<h4>" + esc(card.title || "MVP") + "</h4>";
      html += "<strong>MVP</strong>" + list(card.mvp);
      html += "<strong>Later</strong>" + list(card.later);
    } else if (card.type === "portfolio") {
      html = "<h4>" + esc(card.title || "Similar work") + "</h4>";
      (card.cases || []).forEach(function (item) {
        var href = safeUrl(item.url);
        var title = esc(item.title || "Project");
        var isSample = item.is_sample || card.is_sample;
        html += "<p>";
        if (isSample) {
          html += '<span class="ps-badge-sample" style="display:inline-block;font-size:11px;padding:2px 6px;border-radius:4px;background:#fef3c7;color:#92400e;margin-bottom:4px;font-weight:600;">Sample project (demo data)</span><br>';
        }
        html += href ? '<a href="' + href + '" target="_blank" rel="noreferrer">' + title + "</a>" : title;
        if (item.outcome) html += "<br>" + esc(item.outcome);
        html += "</p>";
      });
    } else {
      html = "<h4>" + esc(card.title || card.type || "Details") + "</h4>";
    }
    wrap.innerHTML = html;
    return wrap;
  }

  function renderReply(payload) {
    endWait();
    if (!payload || payload.detail) {
      say("assistant", (payload && typeof payload.detail === "string" && payload.detail) || "Something went wrong. Please try again.");
      return;
    }
    var node = say("assistant", payload.message || "");
    (payload.cards || []).forEach(function (card) {
      thread.appendChild(renderCard(card));
    });
    setChips(payload.chips || []);
    if (node && payload.message_id && payload.route && payload.route !== "discovery") {
      var thumbs = el("div", "ps-thumb");
      ["up", "down"].forEach(function (rating) {
        var button = el("button", "", rating === "up" ? "Helpful" : "Not helpful");
        button.type = "button";
        button.onclick = function () {
          post("/api/v1/sessions/" + sessionId + "/feedback", { message_id: payload.message_id, rating: rating })
            .then(function () { button.disabled = true; });
        };
        thumbs.appendChild(button);
      });
      node.appendChild(thumbs);
    }
    scrollThread();
  }

  function post(path, body) {
    return fetch(api + path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }).then(function (res) {
      return res.json().then(function (data) {
        if (!res.ok) throw data;
        return data;
      });
    });
  }

  function fail(error) {
    endWait();
    var detail = "";
    if (typeof error === "string") detail = error;
    else if (error && typeof error.detail === "string") detail = error.detail;
    say("assistant", detail || "Something went wrong. Please try again.");
  }

  function closePanel() {
    panel.classList.remove("is-open");
    panel.setAttribute("aria-hidden", "true");
    launcher.hidden = false;
  }

  function open() {
    panel.classList.add("is-open");
    panel.setAttribute("aria-hidden", "false");
    launcher.hidden = true;
    input.focus();
    if (sessionId) return;
    if (!tenant) {
      say("assistant", "This embed is missing data-tenant.");
      return;
    }
    if (!beginWait()) return;
    fetch(api + "/api/v1/public-config?tenant=" + encodeURIComponent(tenant))
      .then(function (res) { return res.json().then(function (data) { if (!res.ok) throw data; return data; }); })
      .then(function (data) {
        brand = Object.assign(brand, data.brand || {});
        ndaVersion = (data.nda && data.nda.version) || "";
        applyBrand();
        return post("/api/v1/sessions", { tenant: tenant, path: window.location.pathname, page_url: window.location.href });
      })
      .then(function (data) {
        if (!data) return;
        sessionId = data.session_id;
        try { localStorage.setItem("ps_sess_" + tenant, sessionId); } catch (e) {}
        renderReply(data);
      })
      .catch(function () {
        endWait();
        say("assistant", "This workspace is not available.");
      });
  }

  var stagedFile = null;

  function formatFileSize(bytes) {
    if (!bytes) return "0 B";
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1048576) return (bytes / 1024).toFixed(0) + " KB";
    return (bytes / 1048576).toFixed(1) + " MB";
  }

  function clearStagedFile() {
    stagedFile = null;
    file.value = "";
    attachmentBox.innerHTML = "";
    attachmentBox.style.display = "none";
    uploadBtn.classList.remove("has-attachment");
    input.placeholder = brand.placeholder || "Type your message...";
  }

  file.onchange = function () {
    if (!file.files || !file.files[0]) return;
    stagedFile = file.files[0];
    attachmentBox.innerHTML = [
      '<div class="ps-attachment-pill">',
        '<span class="ps-attachment-icon">📄</span>',
        '<span class="ps-attachment-name" title="' + esc(stagedFile.name) + '">' + esc(stagedFile.name) + '</span>',
        '<span class="ps-attachment-size">(' + formatFileSize(stagedFile.size) + ')</span>',
        '<button type="button" class="ps-attachment-remove" title="Remove attachment" aria-label="Remove attachment">&times;</button>',
      '</div>'
    ].join("");
    attachmentBox.style.display = "flex";
    uploadBtn.classList.add("has-attachment");
    input.placeholder = "Add instructions or press send...";
    input.focus();

    var removeBtn = attachmentBox.querySelector(".ps-attachment-remove");
    if (removeBtn) {
      removeBtn.onclick = function (e) {
        e.preventDefault();
        e.stopPropagation();
        clearStagedFile();
      };
    }
  };

  form.onsubmit = function (event) {
    event.preventDefault();
    var value = input.value.trim();
    if (!sessionId || busy) return;

    if (stagedFile) {
      var f = stagedFile;
      var notes = value;
      clearStagedFile();
      input.value = "";
      setChips([]);

      var userText = "📎 Uploaded document: " + f.name;
      if (notes) userText += "\n\n" + notes;
      say("user", userText);

      if (!beginWait()) return;
      var data = new FormData();
      data.append("file", f);
      if (notes) data.append("notes", notes);
      fetch(api + "/api/v1/sessions/" + sessionId + "/documents", { method: "POST", body: data })
        .then(function (res) { return res.json().then(function (body) { if (!res.ok) throw body; return body; }); })
        .then(renderReply)
        .catch(fail);
      return;
    }

    if (!value) return;
    input.value = "";
    setChips([]);
    say("user", value);
    if (!beginWait()) return;
    post("/api/v1/sessions/" + sessionId + "/messages", { content: value }).then(renderReply).catch(fail);
  };

  function buildTranscriptText() {
    var lines = [
      "# " + (brand.widget_title || "Nexus Advisor") + " — Consultation Transcript",
      "Date: " + new Date().toLocaleString(),
      "Session: " + (sessionId || "unassigned"),
      "--------------------------------------------------------------------------------",
      ""
    ];
    var msgs = thread.querySelectorAll(".ps-msg, .ps-card");
    if (!msgs || msgs.length === 0) {
      lines.push("(No messages in this consultation yet.)");
    } else {
      for (var i = 0; i < msgs.length; i++) {
        var m = msgs[i];
        if (m.classList.contains("ps-msg")) {
          var sender = m.classList.contains("user") ? "You" : (brand.widget_title || "Advisor");
          var clone = m.cloneNode(true);
          var thumbs = clone.querySelectorAll(".ps-thumb, .ps-thumb-btn");
          for (var t = 0; t < thumbs.length; t++) thumbs[t].remove();
          var txt = clone.innerText.trim();
          lines.push("[" + sender + "]");
          lines.push(txt);
          lines.push("");
        } else if (m.classList.contains("ps-card")) {
          lines.push("--- [Card: " + (m.querySelector("h4") ? m.querySelector("h4").innerText : "Details") + "] ---");
          lines.push(m.innerText.trim());
          lines.push("");
        }
      }
    }
    lines.push("--------------------------------------------------------------------------------");
    lines.push("Exported from " + (brand.widget_title || "Nexus Advisor") + " Consultation");
    return lines.join("\n");
  }

  function downloadChat() {
    var text = buildTranscriptText();
    var blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = "nexus-consultation-" + (sessionId || "transcript").slice(0, 8) + ".txt";
    document.body.appendChild(a);
    a.click();
    setTimeout(function () {
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }, 200);
  }

  function printChat() {
    var text = buildTranscriptText();
    var printWin = window.open("", "_blank", "width=800,height=900");
    if (printWin) {
      var html = [
        '<!DOCTYPE html><html><head><meta charset="utf-8">',
        '<title>' + esc(brand.widget_title || "Nexus Advisor") + ' Consultation Transcript</title>',
        '<style>',
        'body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;margin:30px;color:#0f172a;line-height:1.6;font-size:13px}',
        'h2{margin:0 0 6px;color:#0f172a;font-size:20px}',
        '.meta{color:#64748b;font-size:12px;margin-bottom:20px;padding-bottom:12px;border-bottom:2px solid #3b82f6}',
        'pre{white-space:pre-wrap;word-break:break-word;background:#f8fafc;border:1px solid #e2e8f0;padding:16px;border-radius:8px;font-family:inherit;font-size:13px;line-height:1.6}',
        '@media print{body{margin:15mm}pre{background:#fff;border:none;padding:0}}',
        '</style>',
        '</head><body>',
        '<h2>' + esc(brand.widget_title || "Nexus Advisor") + ' — Consultation Transcript</h2>',
        '<div class="meta">Exported on ' + new Date().toLocaleString() + ' &bull; Session: ' + esc(sessionId || "unassigned") + '</div>',
        '<pre>' + esc(text) + '</pre>',
        '<script>window.onload=function(){window.print();};<\/script>',
        '</body></html>'
      ].join("");
      printWin.document.write(html);
      printWin.document.close();
    } else {
      window.print();
    }
  }

  downloadBtn.onclick = downloadChat;
  printBtn.onclick = printChat;

  var isExpanded = false;
  expandBtn.onclick = function () {
    isExpanded = !isExpanded;
    if (isExpanded) {
      panel.classList.add("is-centered");
      expandBtn.innerHTML = ICONS.compress;
      expandBtn.title = "Minimize to drawer";
    } else {
      panel.classList.remove("is-centered");
      expandBtn.innerHTML = ICONS.expand;
      expandBtn.title = "Center studio view";
    }
  };

  restartBtn.onclick = function () {
    if (confirm("Start a new conversation and clear current session?")) {
      try { localStorage.removeItem("ps_sess_" + tenant); } catch (e) {}
      sessionId = "";
      thread.innerHTML = "";
      setChips([]);
      open();
    }
  };

  close.onclick = closePanel;
  launcher.onclick = function () {
    if (panel.classList.contains("is-open")) closePanel();
    else open();
  };

  var advisorAPI = {
    open: function (centered) {
      open();
      if (centered && !isExpanded) {
        expandBtn.click();
      }
    },
    close: closePanel,
    restart: function () {
      restartBtn.click();
    },
    send: function (text, centered) {
      open();
      if (centered && !isExpanded) {
        expandBtn.click();
      }
      input.value = text;
      form.dispatchEvent(new Event("submit", { cancelable: true }));
    }
  };

  window.NexusAdvisor = advisorAPI;
  window.NorthlineAdvisor = advisorAPI;
  window.Advisor = advisorAPI;

  applyBrand();
  void ndaVersion;
})();

import css from "./styles.css?inline";

type Chip = { label: string; field: string; value: unknown; also?: Record<string, unknown> };
type Card = {
  type: string; title?: string; range?: string; weeks?: number; team?: string[];
  inclusions?: string[]; exclusions?: string[]; disclaimer?: string;
  frontend?: string[]; backend?: string[]; notes?: string[]; mvp?: string[]; later?: string[];
  cases?: { title: string; outcome: string; url: string }[]; reasons?: string[];
};
type Brand = {
  primary: string; accent: string; background: string; surface: string; text: string; muted: string;
  success?: string; radius_px: number; logo_text: string; launcher_text: string; launcher_subtitle: string;
  position: string; widget_title: string; widget_subtitle: string; placeholder: string;
};

const script = document.currentScript as HTMLScriptElement | null;
const API = (script?.dataset.api || window.location.origin).replace(/\/$/, "");

const ICONS = {
  chat: `<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M5 6.5A2.5 2.5 0 0 1 7.5 4h9A2.5 2.5 0 0 1 19 6.5v7A2.5 2.5 0 0 1 16.5 16H11l-4 3.2V16H7.5A2.5 2.5 0 0 1 5 13.5v-7Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="M8.5 9h7M8.5 12h4" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>`,
  close: `<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M7 7l10 10M17 7 7 17" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>`,
  clip: `<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M15.2 7.2 8.4 14a3.1 3.1 0 0 0 4.4 4.4l7.1-7.2a5 5 0 0 0-7.1-7.1L6 11.8" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>`,
  smile: `<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="12" cy="12" r="8.25" stroke="currentColor" stroke-width="1.7"/><circle cx="9.2" cy="10.2" r="1" fill="currentColor"/><circle cx="14.8" cy="10.2" r="1" fill="currentColor"/><path d="M8.8 14.2c.9 1.4 2 2.1 3.2 2.1s2.3-.7 3.2-2.1" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>`,
  send: `<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M5 12 20 5l-6.2 14-2.1-5.2L5 12Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="m11.7 13.8 8.3-8.8" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>`,
  avatar: `<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><rect width="80" height="80" fill="#1A2B4C"/><circle cx="40" cy="30" r="14" fill="#E2E8F0"/><path d="M16 72c4-16 16-24 24-24s20 8 24 24" fill="#E2E8F0"/><rect x="28" y="48" width="24" height="18" rx="6" fill="#1A2B4C"/></svg>`,
};

const EMOJIS = ["👍", "😊", "🙏", "💼", "🚀", "✅", "👋", "💡"];
const SHIMMER = `<div class="nl-shimmer" aria-label="Advisor is typing"><span></span><span></span><span></span></div>`;

function el<K extends keyof HTMLElementTagNameMap>(tag: K, className?: string, text?: string) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

function md(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br>");
}

function renderCard(card: Card): HTMLElement {
  const wrap = el("div", "nl-card");
  wrap.innerHTML = `<h4>${card.title || card.type}</h4>`;
  if (card.type === "estimate") {
    wrap.innerHTML += `<div class="nl-range">${card.range || ""}</div><div>${card.weeks ?? ""} weeks · ${(card.team || []).join(", ")}</div><div><strong>Includes</strong><ul>${(card.inclusions || []).map((i) => `<li>${i}</li>`).join("")}</ul></div><p class="nl-disclaimer">${card.disclaimer || ""}</p>`;
  } else if (card.type === "architecture") {
    wrap.innerHTML += `<p>Frontend: ${(card.frontend || []).join(", ")}</p><p>Backend: ${(card.backend || []).join(", ")}</p><ul>${(card.notes || []).map((i) => `<li>${i}</li>`).join("")}</ul>`;
  } else if (card.type === "mvp") {
    wrap.innerHTML += `<strong>MVP</strong><ul>${(card.mvp || []).map((i) => `<li>${i}</li>`).join("")}</ul><strong>Later</strong><ul>${(card.later || []).map((i) => `<li>${i}</li>`).join("")}</ul>`;
  } else if (card.type === "portfolio") {
    wrap.innerHTML += (card.cases || []).map((c) => `<p><a href="${c.url}" target="_blank" rel="noreferrer">${c.title}</a><br>${c.outcome}</p>`).join("");
  } else if (card.reasons) {
    wrap.innerHTML += `<ul>${card.reasons.map((i) => `<li>${i}</li>`).join("")}</ul>`;
  }
  return wrap;
}

async function readSSE(
  response: Response,
  onToken: (t: string) => void,
  onEvent: (n: string, d: Record<string, unknown>) => void,
) {
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  const reader = response.body?.getReader();
  if (!reader) return;
  const decoder = new TextDecoder();
  let buffer = "";
  let event = "message";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const part of parts) {
      let dataLine = "";
      for (const line of part.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        if (line.startsWith("data:")) dataLine += line.slice(5).trim();
      }
      if (!dataLine) continue;
      const data = JSON.parse(dataLine);
      if (event === "token") onToken(data.text || "");
      else onEvent(event, data);
      event = "message";
    }
  }
}

async function boot() {
  if (document.getElementById("nl-widget-root")) return;
  const style = el("style");
  style.textContent = css;
  document.head.appendChild(style);

  const cfg = await fetch(`${API}/api/v1/public-config`).then((r) => r.json());
  const brand: Brand = cfg.brand;
  const root = el("div", "nl-root");
  root.id = "nl-widget-root";
  const vars: Record<string, string> = {
    "--nl-primary": brand.primary,
    "--nl-accent": brand.accent,
    "--nl-bg": brand.background,
    "--nl-surface": brand.surface,
    "--nl-text": brand.text,
    "--nl-muted": brand.muted,
    "--nl-success": brand.success || "#10B981",
    "--nl-radius": `${brand.radius_px}px`,
  };
  Object.entries(vars).forEach(([k, v]) => root.style.setProperty(k, v));

  const launcher = el("button", `nl-launcher ${brand.position}`);
  launcher.type = "button";
  launcher.setAttribute("aria-label", brand.launcher_text);
  launcher.innerHTML = ICONS.chat;

  const panel = el("div", `nl-panel ${brand.position}`);
  panel.setAttribute("aria-hidden", "true");

  const header = el("div", "nl-header");
  const avatar = el("div", "nl-avatar");
  avatar.innerHTML = ICONS.avatar;
  const identity = el("div", "nl-identity");
  identity.innerHTML = `<strong>${brand.widget_title}</strong><p class="nl-status"><span class="nl-online-dot" aria-hidden="true"></span>${brand.widget_subtitle}</p>`;
  const close = el("button", "nl-close");
  close.type = "button";
  close.setAttribute("aria-label", "Close chat");
  close.innerHTML = ICONS.close;
  header.append(avatar, identity, close);

  const thread = el("div", "nl-thread");
  const chipsBox = el("div", "nl-chips");
  const compose = el("div", "nl-compose");
  const tools = el("div", "nl-tools");

  const ndaWrap = el("div", "nl-nda");
  const ndaLabel = el("label");
  const ndaBox = document.createElement("input");
  ndaBox.type = "checkbox";
  ndaLabel.append(ndaBox, document.createTextNode(" " + (cfg.nda?.label || "I agree to keep this confidential.")));
  ndaLabel.title = cfg.nda?.body || "";
  const ndaBody = el("p", "nl-nda-body", cfg.nda?.body || "");
  ndaWrap.append(ndaLabel, ndaBody);

  const SESSION_KEY = `nl-session:${API}`;

  const bookBtn = el("button", "nl-chip", "Request a consultation");
  bookBtn.type = "button";
  bookBtn.hidden = true;

  tools.append(ndaWrap, bookBtn);

  const form = document.createElement("form");
  const input = document.createElement("input");
  input.type = "text";
  input.placeholder = brand.placeholder;
  input.setAttribute("aria-label", brand.placeholder);

  const uploadBtn = el("label", "nl-icon-btn");
  uploadBtn.title = "Upload brief";
  uploadBtn.setAttribute("aria-label", "Upload brief");
  const fileInput = document.createElement("input");
  fileInput.type = "file";
  fileInput.accept = ".pdf,.docx,.txt,.md";
  fileInput.className = "nl-hidden";
  uploadBtn.innerHTML = ICONS.clip;
  uploadBtn.appendChild(fileInput);

  const emojiBtn = el("button", "nl-icon-btn");
  emojiBtn.type = "button";
  emojiBtn.setAttribute("aria-label", "Insert emoji");
  emojiBtn.innerHTML = ICONS.smile;

  const emojiBox = el("div", "nl-emoji");
  emojiBox.hidden = true;
  EMOJIS.forEach((emoji) => {
    const btn = el("button", "", emoji);
    btn.type = "button";
    btn.addEventListener("click", () => {
      input.value += emoji;
      input.focus();
      emojiBox.hidden = true;
    });
    emojiBox.appendChild(btn);
  });

  const send = el("button", "nl-send");
  send.type = "submit";
  send.setAttribute("aria-label", "Send");
  send.innerHTML = ICONS.send;

  form.append(input, uploadBtn, emojiBtn, send);
  compose.append(tools, form, emojiBox);
  panel.append(header, thread, chipsBox, compose);
  root.append(launcher, panel);
  document.body.appendChild(root);

  let sessionId = "";
  let busy = false;
  let ndaAccepted = false;

  const openPanel = () => {
    panel.classList.add("is-open");
    panel.setAttribute("aria-hidden", "false");
    launcher.hidden = true;
  };
  const closePanel = () => {
    panel.classList.remove("is-open");
    panel.setAttribute("aria-hidden", "true");
    launcher.hidden = false;
    emojiBox.hidden = true;
  };

  const addMsg = (role: string, html: string, typing = false) => {
    const node = el("div", `nl-msg ${role}${typing ? " nl-typing" : ""}`);
    node.innerHTML = html;
    thread.appendChild(node);
    thread.scrollTop = thread.scrollHeight;
    return node;
  };
  const setChips = (chips: Chip[]) => {
    chipsBox.innerHTML = "";
    chips.forEach((chip) => {
      const btn = el("button", "nl-chip", chip.label);
      btn.type = "button";
      btn.addEventListener("click", () => {
        if (chip.field === "download_ics") {
          if (sessionId) window.open(`${API}/api/v1/sessions/${sessionId}/calendar.ics`, "_blank");
          return;
        }
        void sendMessage(chip.label, chip);
      });
      chipsBox.appendChild(btn);
    });
  };
  const addCards = (cards: Card[]) => {
    cards.forEach((card) => thread.appendChild(renderCard(card)));
    thread.scrollTop = thread.scrollHeight;
  };

  async function ensureSession() {
    if (sessionId) return;
    const saved = localStorage.getItem(SESSION_KEY);
    if (saved) {
      const existing = await fetch(`${API}/api/v1/sessions/${saved}`);
      if (existing.ok) {
        const body = await existing.json();
        sessionId = body.session_id;
        localStorage.setItem(SESSION_KEY, sessionId);
        ndaAccepted = !!body.nda_accepted;
        ndaBox.checked = ndaAccepted;
        bookBtn.hidden = !body.can_book;
        (body.messages || []).forEach((item: { role: string; content: string }) => addMsg(item.role, md(item.content || "")));
        setChips(body.chips || []);
        addCards(body.cards || []);
        return;
      }
      localStorage.removeItem(SESSION_KEY);
    }
    const created = await fetch(`${API}/api/v1/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ page_url: location.href, page_title: document.title, path: location.pathname }),
    }).then((r) => r.json());
    sessionId = created.session_id;
    localStorage.setItem(SESSION_KEY, sessionId);
    addMsg("assistant", md(created.message || ""));
    setChips(created.chips || []);
    addCards(created.cards || []);
  }

  async function acceptNda() {
    if (!sessionId || ndaAccepted) return;
    const result = await fetch(`${API}/api/v1/sessions/${sessionId}/nda`, { method: "POST" }).then((r) => r.json());
    ndaAccepted = !!result.nda_accepted;
    ndaBox.checked = ndaAccepted;
  }

  async function sendMessage(content: string, chip?: Chip) {
    if (busy) return;
    busy = true;
    emojiBox.hidden = true;
    try {
      await ensureSession();
      if (content) addMsg("user", md(content));
      setChips([]);
      const bubble = addMsg("assistant", SHIMMER, true);
      const response = await fetch(`${API}/api/v1/sessions/${sessionId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content, chip, nda_accepted: ndaBox.checked }),
      });
      let acc = "";
      await readSSE(
        response,
        (token) => {
          acc += token;
          bubble.classList.remove("nl-typing");
          bubble.innerHTML = md(acc);
          thread.scrollTop = thread.scrollHeight;
        },
        (name, data) => {
          if (name === "cards") addCards((data.cards as Card[]) || []);
          if (name === "chips") setChips((data.chips as Chip[]) || []);
          if (name === "meta") {
            bookBtn.hidden = !data.can_book;
            if (data.nda_accepted) {
              ndaAccepted = true;
              ndaBox.checked = true;
            }
          }
        },
      );
      if (!acc && bubble.classList.contains("nl-typing")) {
        bubble.classList.remove("nl-typing");
        bubble.remove();
      }
    } catch (err) {
      addMsg("assistant", md(err instanceof Error ? err.message : "Something went wrong. Please try again."));
    } finally {
      busy = false;
    }
  }

  async function book(windowValue: string) {
    if (!sessionId) return;
    if (!ndaBox.checked) {
      addMsg("assistant", "Please accept the confidentiality notice before requesting a consultation.");
      return;
    }
    try {
      await acceptNda();
      const result = await fetch(`${API}/api/v1/sessions/${sessionId}/booking`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ window: windowValue }),
      }).then(async (r) => {
        if (!r.ok) {
          const body = await r.json().catch(() => ({}));
          throw new Error(body.detail || `Booking failed (${r.status})`);
        }
        return r.json();
      });
      addMsg("assistant", md(result.message || "Requested."));
      addCards(result.cards || []);
      setChips(result.chips || []);
    } catch (err) {
      addMsg("assistant", md(err instanceof Error ? err.message : "Could not book right now."));
    }
  }

  launcher.addEventListener("click", async () => {
    openPanel();
    await ensureSession();
  });
  close.addEventListener("click", closePanel);
  emojiBtn.addEventListener("click", () => {
    emojiBox.hidden = !emojiBox.hidden;
  });
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const v = input.value.trim();
    if (!v) return;
    input.value = "";
    void sendMessage(v);
  });
  ndaBox.addEventListener("change", () => {
    if (ndaBox.checked) void acceptNda().catch(() => {
      ndaBox.checked = false;
      addMsg("assistant", "Could not save the confidentiality acceptance. Please try again.");
    });
  });
  fileInput.addEventListener("change", async () => {
    if (!fileInput.files?.[0] || !sessionId) return;
    if (!ndaBox.checked) {
      addMsg("assistant", "Please accept the confidentiality notice before uploading a brief.");
      fileInput.value = "";
      return;
    }
    try {
      await acceptNda();
      const body = new FormData();
      body.append("file", fileInput.files[0]);
      body.append("nda_accepted", "true");
      const bubble = addMsg("assistant", SHIMMER, true);
      const response = await fetch(`${API}/api/v1/sessions/${sessionId}/documents`, { method: "POST", body });
      let acc = "";
      await readSSE(
        response,
        (token) => {
          acc += token;
          bubble.classList.remove("nl-typing");
          bubble.innerHTML = md(acc);
        },
        (name, data) => {
          if (name === "cards") addCards((data.cards as Card[]) || []);
          if (name === "chips") setChips((data.chips as Chip[]) || []);
          if (name === "meta") {
            bookBtn.hidden = !data.can_book;
            if (data.nda_accepted) {
              ndaAccepted = true;
              ndaBox.checked = true;
            }
          }
        },
      );
      if (!acc && bubble.classList.contains("nl-typing")) {
        bubble.classList.remove("nl-typing");
        bubble.remove();
      }
    } catch (err) {
      addMsg("assistant", md(err instanceof Error ? err.message : "Upload failed."));
    } finally {
      fileInput.value = "";
    }
  });
  bookBtn.addEventListener("click", () => {
    void sendMessage("Request a consultation", { field: "booking_window", value: "this_week" });
  });
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => void boot());
else void boot();

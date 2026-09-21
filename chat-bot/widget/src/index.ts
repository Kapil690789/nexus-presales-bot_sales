import css from "./styles.css?inline";

type Chip = { label: string; field: string; value: unknown; also?: Record<string, unknown> };
type BookingSlot = { slot_iso: string; label: string };
type BookingDay = { date: string; label: string; slots: BookingSlot[] };
type Card = {
  type: string; title?: string; range?: string; weeks?: number; team?: string[];
  inclusions?: string[]; exclusions?: string[]; assumptions?: string[]; disclaimer?: string;
  frontend?: string[]; backend?: string[]; notes?: string[]; mvp?: string[]; later?: string[];
  cases?: { title: string; outcome: string; url: string }[]; reasons?: string[];
  live?: boolean; timezone?: string; duration_minutes?: number; window?: string;
  days?: BookingDay[]; slots?: BookingSlot[]; meet_url?: string; html_link?: string;
  slot_iso?: string; error?: string;
};
type Brand = {
  primary: string; accent: string; background: string; surface: string; text: string; muted: string;
  success?: string; radius_px: number; logo_text: string; launcher_text: string; launcher_subtitle: string;
  position: string; widget_title: string; widget_subtitle: string; placeholder: string;
};

const FALLBACK_BRAND: Brand = {
  primary: "#1A2B4C",
  accent: "#1A2B4C",
  background: "#FFFFFF",
  surface: "#FFFFFF",
  text: "#1A2B4C",
  muted: "#5C6670",
  success: "#10B981",
  radius_px: 16,
  logo_text: "DevConsult",
  launcher_text: "Talk to an advisor",
  launcher_subtitle: "Scope, estimate, and next steps",
  position: "bottom-right",
  widget_title: "DevConsult Advisor",
  widget_subtitle: "Online",
  placeholder: "Type your message...",
};

declare global {
  interface Window {
    CHAT_BOT_URL?: string;
  }
}

function resolveApi(): string {
  const tagged = document.querySelector<HTMLScriptElement>('script[src*="consultant.js"][data-api]');
  const fromScript = (tagged?.dataset.api || "").trim();
  if (fromScript) return fromScript.replace(/\/$/, "");
  const fromWindow = String(window.CHAT_BOT_URL || "").trim();
  if (fromWindow) return fromWindow.replace(/\/$/, "");
  return window.location.origin.replace(/\/$/, "");
}

let API = "";

let onBookSlot: ((iso: string, windowValue: string, label: string) => void) | null = null;

const ICONS = {
  chat: `<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M5 6.5A2.5 2.5 0 0 1 7.5 4h9A2.5 2.5 0 0 1 19 6.5v7A2.5 2.5 0 0 1 16.5 16H11l-4 3.2V16H7.5A2.5 2.5 0 0 1 5 13.5v-7Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="M8.5 9h7M8.5 12h4" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>`,
  close: `<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M7 7l10 10M17 7 7 17" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>`,
  clip: `<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M15.2 7.2 8.4 14a3.1 3.1 0 0 0 4.4 4.4l7.1-7.2a5 5 0 0 0-7.1-7.1L6 11.8" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>`,
  smile: `<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="12" cy="12" r="8.25" stroke="currentColor" stroke-width="1.7"/><circle cx="9.2" cy="10.2" r="1" fill="currentColor"/><circle cx="14.8" cy="10.2" r="1" fill="currentColor"/><path d="M8.8 14.2c.9 1.4 2 2.1 3.2 2.1s2.3-.7 3.2-2.1" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>`,
  send: `<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M5 12 20 5l-6.2 14-2.1-5.2L5 12Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="m11.7 13.8 8.3-8.8" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>`,
  avatar: `<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><rect width="80" height="80" fill="#1A2B4C"/><circle cx="40" cy="30" r="14" fill="#E2E8F0"/><path d="M16 72c4-16 16-24 24-24s20 8 24 24" fill="#E2E8F0"/><rect x="28" y="48" width="24" height="18" rx="6" fill="#1A2B4C"/></svg>`,
  refresh: `<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M7.2 7.2A6.5 6.5 0 0 1 18.5 12M16.8 16.8A6.5 6.5 0 0 1 5.5 12" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/><path d="M18.5 7.5V12h-4.5M5.5 16.5V12H10" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
};

const EMOJIS = ["👍", "😊", "🙏", "💼", "🚀", "✅", "👋", "💡"];
const SHIMMER = `<div class="nl-shimmer" aria-label="Advisor is typing"><span class="nl-shimmer-line"></span><span class="nl-shimmer-line nl-shimmer-line-mid"></span><span class="nl-shimmer-line nl-shimmer-line-short"></span></div>`;
const WORD_DELAY_MS = 40;

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

function prefersReducedMotion() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function friendlyError(err: unknown, fallback: string): string {
  const msg = err instanceof Error ? err.message : "";
  if (!msg || /failed to fetch|networkerror|load failed/i.test(msg)) {
    return "Cannot reach the advisor on port 8000. Start the bot with `make run`.";
  }
  return msg || fallback;
}

function normalizePath(path: string): string {
  let normalized = (path || "/").split("?")[0].replace(/\/+$/, "") || "/";
  if (normalized.endsWith(".html")) normalized = normalized.slice(0, -".html".length);
  if (normalized.endsWith("/index")) normalized = normalized.slice(0, -"/index".length) || "/";
  return normalized;
}

function typeWords(bubble: HTMLElement, text: string, thread: HTMLElement): Promise<void> {
  return new Promise((resolve) => {
    const finish = () => {
      bubble.innerHTML = md(text);
      thread.scrollTop = thread.scrollHeight;
      resolve();
    };
    if (!text || prefersReducedMotion()) {
      finish();
      return;
    }
    const parts = text.split(/(\s+)/);
    let acc = "";
    let index = 0;
    const tick = () => {
      if (index >= parts.length) {
        finish();
        return;
      }
      acc += parts[index];
      bubble.innerHTML = md(acc);
      thread.scrollTop = thread.scrollHeight;
      const delay = parts[index].trim() ? WORD_DELAY_MS : 0;
      index += 1;
      if (delay) window.setTimeout(tick, delay);
      else tick();
    };
    tick();
  });
}

function localTime(iso: string) {
  return new Date(iso).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

function localDay(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" });
}

function groupLocalDays(slots: BookingSlot[]): BookingDay[] {
  const map = new Map<string, BookingDay>();
  for (const slot of slots) {
    const date = new Date(slot.slot_iso).toLocaleDateString("en-CA");
    const existing = map.get(date);
    const item = { slot_iso: slot.slot_iso, label: localTime(slot.slot_iso) };
    if (existing) existing.slots.push(item);
    else map.set(date, { date, label: localDay(slot.slot_iso), slots: [item] });
  }
  return [...map.values()];
}

function renderBookingCard(card: Card): HTMLElement {
  const wrap = el("div", "nl-card nl-booking");
  wrap.appendChild(el("h4", "", card.title || "Book a call"));
  if (card.error) wrap.appendChild(el("p", "nl-booking-error", card.error));
  const minutes = card.duration_minutes || 45;
  wrap.appendChild(el("p", "nl-disclaimer", `${minutes} min · times shown in your local timezone`));
  if (card.live === false) wrap.appendChild(el("p", "nl-disclaimer", "Demo times until Google Calendar is connected."));
  const slots = card.slots || (card.days || []).flatMap((day) => day.slots);
  const days = groupLocalDays(slots);
  if (!days.length) {
    wrap.appendChild(el("p", "nl-disclaimer", "No times left in this window. Try next week."));
    return wrap;
  }
  const tabs = el("div", "nl-days");
  const grid = el("div", "nl-times");
  let selectedDay = days[0].date;
  let selectedIso = "";
  const confirm = el("button", "nl-confirm", `Confirm ${minutes}-min call`);
  confirm.type = "button";
  confirm.disabled = true;
  const paintTimes = () => {
    grid.innerHTML = "";
    const day = days.find((item) => item.date === selectedDay) || days[0];
    day.slots.forEach((slot) => {
      const btn = el("button", `nl-time${slot.slot_iso === selectedIso ? " is-selected" : ""}`, slot.label);
      btn.type = "button";
      btn.addEventListener("click", () => {
        selectedIso = slot.slot_iso;
        paintTimes();
        confirm.disabled = false;
      });
      grid.appendChild(btn);
    });
  };
  days.forEach((day) => {
    const tab = el("button", `nl-day${day.date === selectedDay ? " is-selected" : ""}`, day.label);
    tab.type = "button";
    tab.dataset.date = day.date;
    tab.addEventListener("click", () => {
      selectedDay = day.date;
      [...tabs.children].forEach((node) => node.classList.toggle("is-selected", (node as HTMLElement).dataset.date === day.date));
      paintTimes();
    });
    tabs.appendChild(tab);
  });
  confirm.addEventListener("click", () => {
    if (!selectedIso) return;
    onBookSlot?.(selectedIso, card.window || "this_week", `${localDay(selectedIso)}, ${localTime(selectedIso)}`);
  });
  wrap.append(tabs, grid, confirm);
  paintTimes();
  return wrap;
}

function renderConfirmCard(card: Card): HTMLElement {
  const wrap = el("div", "nl-card nl-booking");
  wrap.appendChild(el("h4", "", card.title || "You're booked"));
  const when = card.slot_iso ? `${localDay(card.slot_iso)}, ${localTime(card.slot_iso)}` : card.label || "";
  wrap.appendChild(el("p", "", when));
  if (card.duration_minutes) wrap.appendChild(el("p", "nl-disclaimer", `${card.duration_minutes} minutes`));
  if (card.meet_url) {
    const link = el("a", "nl-booking-link", "Join Google Meet");
    link.href = card.meet_url;
    link.target = "_blank";
    link.rel = "noreferrer";
    wrap.appendChild(link);
  }
  if (card.html_link) {
    const link = el("a", "nl-booking-link", "Open in Google Calendar");
    link.href = card.html_link;
    link.target = "_blank";
    link.rel = "noreferrer";
    wrap.appendChild(link);
  }
  return wrap;
}

function renderCard(card: Card): HTMLElement {
  if (card.type === "booking") return renderBookingCard(card);
  if (card.type === "booking_confirm") return renderConfirmCard(card);
  const wrap = el("div", "nl-card");
  wrap.innerHTML = `<h4>${card.title || card.type}</h4>`;
  if (card.type === "estimate") {
    wrap.innerHTML += `<div class="nl-range">${card.range || ""}</div><div>${card.weeks ?? ""} weeks · ${(card.team || []).join(", ")}</div><div><strong>Includes</strong><ul>${(card.inclusions || []).map((i) => `<li>${i}</li>`).join("")}</ul></div>${(card.assumptions || []).length ? `<div><strong>What drives this range</strong><ul>${(card.assumptions || []).map((i) => `<li>${i}</li>`).join("")}</ul></div>` : ""}<p class="nl-disclaimer">${card.disclaimer || ""}</p>`;
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

async function loadPublicConfig(): Promise<{ brand: Brand; nda?: { title?: string; body?: string; label?: string } } | null> {
  try {
    const response = await fetch(`${API}/api/v1/public-config`);
    if (!response.ok) return null;
    const data = await response.json();
    if (!data?.brand) return null;
    return data;
  } catch {
    return null;
  }
}

async function boot() {
  if (document.getElementById("nl-widget-root")) return;
  const style = el("style");
  style.textContent = css;
  document.head.appendChild(style);

  API = resolveApi();
  const loaded = await loadPublicConfig();
  const reachable = loaded !== null;
  const cfg = loaded || { brand: FALLBACK_BRAND };
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
  const reset = el("button", "nl-reset");
  reset.type = "button";
  reset.title = "New conversation";
  reset.setAttribute("aria-label", "New conversation");
  reset.innerHTML = ICONS.refresh;
  const headerActions = el("div", "nl-header-actions");
  headerActions.append(reset, close);
  header.append(avatar, identity, headerActions);

  const thread = el("div", "nl-thread");
  const chipsBox = el("div", "nl-chips");
  const compose = el("div", "nl-compose");
  const tools = el("div", "nl-tools");

  const ndaWrap = el("div", "nl-nda");
  const ndaTitle = el("strong", "nl-nda-title", cfg.nda?.title || "Confidentiality notice");
  const ndaBody = el("div", "nl-nda-body", cfg.nda?.body || "");
  ndaBody.tabIndex = 0;
  const ndaLabel = el("label");
  const ndaBox = document.createElement("input");
  ndaBox.type = "checkbox";
  ndaLabel.append(ndaBox, document.createTextNode(" " + (cfg.nda?.label || "I agree to keep this confidential.")));
  ndaWrap.append(ndaTitle, ndaBody, ndaLabel);

  const SESSION_KEY = `nl-session:${API}`;

  const bookBtn = el("button", "nl-chip", "Book a call");
  bookBtn.type = "button";
  bookBtn.hidden = true;

  tools.append(ndaWrap, bookBtn);

  const form = document.createElement("form");
  const input = document.createElement("input");
  input.type = "text";
  input.placeholder = brand.placeholder;
  input.setAttribute("aria-label", brand.placeholder);

  const uploadId = `nl-upload-${Math.random().toString(36).slice(2, 8)}`;
  const uploadBtn = el("label", "nl-icon-btn");
  uploadBtn.title = "Upload brief";
  uploadBtn.setAttribute("aria-label", "Upload brief");
  uploadBtn.htmlFor = uploadId;
  uploadBtn.innerHTML = ICONS.clip;
  const fileInput = document.createElement("input");
  fileInput.type = "file";
  fileInput.id = uploadId;
  fileInput.accept = ".pdf,.docx,.txt,.md";
  fileInput.className = "nl-hidden";

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

  form.append(input, uploadBtn, emojiBtn, send, fileInput);
  compose.append(tools, form, emojiBox);
  panel.append(header, thread, chipsBox, compose);
  root.append(launcher, panel);
  document.body.appendChild(root);

  let sessionId = "";
  let busy = false;
  let ndaAccepted = false;

  const syncTools = () => {
    tools.hidden = ndaWrap.hidden && bookBtn.hidden;
  };
  syncTools();

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
  const setConversationClosed = (closed: boolean) => {
    compose.classList.toggle("is-locked", closed);
    input.disabled = closed;
    send.disabled = closed;
    if (closed) input.placeholder = "Conversation ended — start a new one";
    else input.placeholder = brand.placeholder;
  };
  if (!reachable) {
    addMsg("assistant", md("Cannot reach the advisor API right now. The chat button is available, but messages will not send until the service is healthy."));
    setConversationClosed(true);
  }
  const applyMeta = (data: Record<string, unknown>) => {
    bookBtn.hidden = !data.can_book || data.stage === "handoff";
    if (data.nda_accepted) {
      ndaAccepted = true;
      ndaBox.checked = true;
      ndaWrap.hidden = true;
    }
    setConversationClosed(data.stage === "handoff");
    syncTools();
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
  const revealAssistant = async (
    bubble: HTMLElement,
    text: string,
    cards: Card[] = [],
    chips: Chip[] = [],
    meta?: Record<string, unknown>,
  ) => {
    bubble.classList.remove("nl-typing");
    if (!text) {
      bubble.remove();
    } else {
      await typeWords(bubble, text, thread);
    }
    if (cards.length) addCards(cards);
    setChips(chips);
    if (meta) applyMeta(meta);
  };

  async function ensureSession() {
    if (sessionId) return;
    const pagePath = location.pathname;
    const saved = localStorage.getItem(SESSION_KEY);
    if (saved) {
      const existing = await fetch(`${API}/api/v1/sessions/${saved}`);
      if (existing.ok) {
        const body = await existing.json();
        if (normalizePath(body.path || "") === normalizePath(pagePath)) {
          sessionId = body.session_id;
          localStorage.setItem(SESSION_KEY, sessionId);
          ndaAccepted = !!body.nda_accepted;
          ndaBox.checked = ndaAccepted;
          ndaWrap.hidden = ndaAccepted;
          bookBtn.hidden = !body.can_book || body.stage === "handoff";
          setConversationClosed(body.stage === "handoff");
          syncTools();
          (body.messages || []).forEach((item: { role: string; content: string }) => addMsg(item.role, md(item.content || "")));
          setChips(body.chips || []);
          addCards(body.cards || []);
          return;
        }
      }
      localStorage.removeItem(SESSION_KEY);
    }
    const created = await fetch(`${API}/api/v1/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ page_url: location.href, page_title: document.title, path: pagePath }),
    }).then((r) => r.json());
    sessionId = created.session_id;
    localStorage.setItem(SESSION_KEY, sessionId);
    if (created.message) {
      const bubble = addMsg("assistant", SHIMMER, true);
      await revealAssistant(bubble, created.message, created.cards || [], created.chips || []);
    } else {
      setChips(created.chips || []);
      addCards(created.cards || []);
    }
  }

  async function startNewConversation() {
    if (busy) return;
    busy = true;
    reset.disabled = true;
    try {
      localStorage.removeItem(SESSION_KEY);
      sessionId = "";
      ndaAccepted = false;
      ndaBox.checked = false;
      ndaWrap.hidden = false;
      bookBtn.hidden = true;
      setConversationClosed(false);
      thread.innerHTML = "";
      setChips([]);
      syncTools();
      await ensureSession();
    } finally {
      busy = false;
      reset.disabled = false;
    }
  }

  async function acceptNda(opts?: { silent?: boolean }) {
    if (!sessionId || ndaAccepted) return;
    const result = await fetch(`${API}/api/v1/sessions/${sessionId}/nda`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ version: cfg.nda?.version }),
    }).then(async (r) => {
      if (!r.ok) {
        const body = await r.json().catch(() => ({}));
        throw new Error(body.detail || `Could not save confidentiality acceptance (${r.status})`);
      }
      return r.json();
    });
    ndaAccepted = !!result.nda_accepted;
    ndaBox.checked = ndaAccepted;
    ndaWrap.hidden = ndaAccepted;
    if (opts?.silent) {
      syncTools();
      return;
    }
    applyMeta(result);
    if (result.stage === "booking" || result.stage === "handoff" || (result.cards || []).length) {
      const bubble = addMsg("assistant", SHIMMER, true);
      await revealAssistant(bubble, result.message || "", result.cards || [], result.chips || [], result);
    } else {
      syncTools();
    }
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
      try {
        const response = await fetch(`${API}/api/v1/sessions/${sessionId}/messages`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content, chip, nda_accepted: ndaBox.checked, nda_version: cfg.nda?.version }),
        });
        let acc = "";
        let pendingCards: Card[] = [];
        let pendingChips: Chip[] = [];
        let pendingMeta: Record<string, unknown> | undefined;
        await readSSE(
          response,
          (token) => {
            acc += token;
          },
          (name, data) => {
            if (name === "cards") pendingCards = (data.cards as Card[]) || [];
            if (name === "chips") pendingChips = (data.chips as Chip[]) || [];
            if (name === "meta") pendingMeta = data;
          },
        );
        await revealAssistant(bubble, acc, pendingCards, pendingChips, pendingMeta);
      } catch (err) {
        bubble.remove();
        throw err;
      }
    } catch (err) {
      addMsg("assistant", md(friendlyError(err, "Something went wrong. Please try again.")));
    } finally {
      busy = false;
    }
  }

  async function book(slotIso: string, windowValue: string, label: string) {
    if (!sessionId) return;
    if (!ndaBox.checked) {
      addMsg("assistant", "Please accept the confidentiality notice before booking a call.");
      return;
    }
    if (busy) return;
    busy = true;
    try {
      await acceptNda({ silent: true });
      addMsg("user", md(label || "Book this time"));
      setChips([]);
      const bubble = addMsg("assistant", SHIMMER, true);
      try {
        const result = await fetch(`${API}/api/v1/sessions/${sessionId}/booking`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ window: windowValue, slot: slotIso }),
        }).then(async (r) => {
          if (!r.ok) {
            const body = await r.json().catch(() => ({}));
            throw new Error(body.detail || `Booking failed (${r.status})`);
          }
          return r.json();
        });
        await revealAssistant(bubble, result.message || "Booked.", result.cards || [], result.chips || [], result);
      } catch (err) {
        bubble.remove();
        throw err;
      }
    } catch (err) {
      addMsg("assistant", md(friendlyError(err, "Could not book right now.")));
    } finally {
      busy = false;
    }
  }
  onBookSlot = (iso, windowValue, label) => {
    void book(iso, windowValue, label);
  };

  launcher.addEventListener("click", async () => {
    openPanel();
    await ensureSession();
  });
  close.addEventListener("click", closePanel);
  reset.addEventListener("click", () => {
    void startNewConversation();
  });
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
    if (ndaBox.checked) {
      void acceptNda().catch(() => {
        ndaBox.checked = false;
        addMsg("assistant", "Could not save the confidentiality acceptance. Please try again.");
      });
    } else if (ndaAccepted) {
      ndaBox.checked = true;
    }
  });
  fileInput.addEventListener("change", async () => {
    if (!fileInput.files?.[0] || !sessionId) return;
    if (!ndaBox.checked) {
      addMsg("assistant", "Please accept the confidentiality notice before uploading a brief.");
      fileInput.value = "";
      return;
    }
    try {
      await acceptNda({ silent: true });
      const body = new FormData();
      body.append("file", fileInput.files[0]);
      body.append("nda_accepted", "true");
      body.append("nda_version", cfg.nda?.version || "");
      const bubble = addMsg("assistant", SHIMMER, true);
      try {
        const response = await fetch(`${API}/api/v1/sessions/${sessionId}/documents`, { method: "POST", body });
        let acc = "";
        let pendingCards: Card[] = [];
        let pendingChips: Chip[] = [];
        let pendingMeta: Record<string, unknown> | undefined;
        await readSSE(
          response,
          (token) => {
            acc += token;
          },
          (name, data) => {
            if (name === "cards") pendingCards = (data.cards as Card[]) || [];
            if (name === "chips") pendingChips = (data.chips as Chip[]) || [];
            if (name === "meta") pendingMeta = data;
          },
        );
        await revealAssistant(bubble, acc, pendingCards, pendingChips, pendingMeta);
      } catch (err) {
        bubble.remove();
        throw err;
      }
    } catch (err) {
      addMsg("assistant", md(friendlyError(err, "Upload failed.")));
    } finally {
      fileInput.value = "";
    }
  });
  bookBtn.addEventListener("click", () => {
    void sendMessage("Book a call", { field: "booking_window", value: "this_week" });
  });
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => void boot());
else void boot();

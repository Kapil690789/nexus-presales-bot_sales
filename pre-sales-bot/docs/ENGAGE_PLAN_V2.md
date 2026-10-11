# ENGAGE PLAN V2 — make the Nexus bot feel like a consultant, not a questionnaire

Status date: 10 Oct 2026. Active tree: `pre-sales-bot/`. Client feedback: "feels like a specific questionnaire / chatting with a boring agent / not engaging enough". Client's demo to their own customers is next week.

This file replaces the first ENGAGE plan. Read `docs/PROGRESS.md` first. Do not use the name "SHIP-4" for this work: SHIP-4 is the earlier safety task (upload limit, booking abuse, persistent rate limits) and is still pending before any public embed.

## 0. COMMON HEADER (paste above every prompt)

```
RULES: work only in pre-sales-bot/. NEVER git commit/push/merge. Never print
.env, keys, database URLs or personal emails. Keep the suite green (currently
291 passed). Never weaken or delete a test. Do not edit pricing.yaml or
pricing.py. Every claim needs file:line or a test name. Read docs/PROGRESS.md
first and append a short entry when done. Verify external APIs and legal
statements against current sources before relying on them. Work for preview
deployments only. After each work package STOP and report: pytest counts,
files changed, anything that contradicted the instructions.
```

## 1. What the research says (checked 10 Oct 2026)

These are patterns that several independent guides agree on. Numbers quoted by vendors ("3.5x", "+40%") are marketing claims; do not repeat them to the client.

1. **Value before data.** Guides on lead-qualification bots say to answer visitor questions and give something useful before asking for contact details; email last, not first.
2. **Few questions.** Typical advice is 3–6 questions; "ask only questions that change the route"; seven questions in one chat "feels like a survey". Budget as an early question is called out as a classic mistake.
3. **Progressive profiling and one question at a time**, with quick-reply buttons plus free text. Intent-first openings ("what are you looking for?") beat identity-first openings.
4. **A human escape hatch at all times**, and a handoff that carries a full summary so the rep does not start cold.
5. **Page-context qualification** (tailor the first message to the page) and **behaviour-based triggers** (not an instant pop-up on page load; do not block content).
6. **Persona plus disclosure.** A named advisor is fine, but the EU AI Act Article 50 chatbot-disclosure duty has applied since 2 Aug 2026 (the Digital Omnibus did not delay it): the visitor must be told at the first interaction that they are talking to an AI. Applies when the system reaches EU users. A visible "AI advisor" label is cheap and builds trust everywhere.
7. **Measure it**: completion per step, drop-off per question, time to first value, meetings booked.

Client reference: the page the client sent (SoftwareFinder, iVueit listing) is a directory page. Its chat widget appears to be from Blazeo (formerly ApexChat); I could not verify the persona name "Colin" or the 15-second auto-open from public pages, so do not state them as facts. Blazeo's own pages describe: intent buttons, an AI chatbot that answers from a knowledge base, qualifies leads and schedules meetings, brand-voice templates, human takeover.

Other current references (vendor descriptions, open the live sites to observe): Qualified (Piper AI SDR; Salesforce completed its acquisition on 1 Apr 2026), Intercom Fin for Sales, HubSpot chatbot, Chili Piper Chat AI. Drift is being wound down in favour of Salesloft's 1Mind, so do not use Drift as a reference.

## 2. Diagnosis of our bot (from code, not opinion)

| Finding | Evidence |
|---|---|
| The first message is a form question | `sessions.py` opener: "I'm Nexus's assistant. What are you looking to build — mobile, web, AI, or design?" |
| Too many questions before any value | Discovery fields: service, goal, features, user_flow, platforms, users, integrations, timeline, budget_band, decision_role, company_size (11) |
| Budget, role and company size are asked mid-flow | `slots.py` DISCOVERY_PROMPTS order |
| No named persona, no AI label, no human escape chip | widget header; no `advisor_name` in `BrandConfig` |
| Same tone every turn; scripted fallback prompts are dry | `slots.py` DISCOVERY_PROMPTS |
| Acknowledgement is generic or missing | `discovery_synth.py` only when LLM succeeds |
| Slow replies (4–5 s) feel dead | SHIP-1 timing table |

## 3. Review of the first ENGAGE plan

Keep: persona and warm opener (ENGAGE-1), warmer prompts (3), page-context preload (7), name capture (10), brief card (6), better "I don't know" (9).
Change:
- ENGAGE-2 typing indicator: the plan adds a fake 600–1200 ms delay. With 4–5 s real latency that is pure harm. Show the indicator the moment the request starts and remove it when the answer arrives; hold it for about 500–800 ms only when the reply is instant (chips, acknowledgements).
- ENGAGE-4 proactive trigger: do not auto-open the full widget. Show a small teaser bubble after a delay on desktop only, once per session, dismissible; no session or LLM call until the visitor sends a message. Exit-intent does not exist on mobile.
- ENGAGE-1: a human name must come with an "AI advisor" label (research point 6).
Fix (invented facts that break our own grounding rule):
- ENGAGE-8: "a directional range based on similar projects we've delivered" is an unsupported claim. Say "based on typical scope for this kind of project".
- ENGAGE-9: "They usually respond within a few hours" is an invented SLA. Remove.
- ENGAGE-8: "20-minute call" contradicts the 30-minute agenda text. Read the duration from config.
- Do not use the invented statistics ("3.5x", "20–30%", "#1 engagement trick").
Missing and most important: the questionnaire feel is structural. Warmer words on 11 questions is still a questionnaire. The plan needs fewer questions, value earlier, an open first question, "help me decide" options, a human exit, per-tenant voice, and measurement.

## 4. Design principles

1. One open question first ("tell me about your idea in a sentence, or pick one").
2. Understand before asking: extract every slot from the first free text, recap what was understood, ask only for what is missing.
3. Fast path: five questions to an estimate (service, goal, platforms, timeline, budget-as-ballpark). Everything else becomes an optional "sharpen this estimate" step after the first value.
4. Specific acknowledgement beats generic praise. Never repeat the same acknowledgement within three turns. At most one emoji per message, none in estimates or price text.
5. Every message at most two short sentences (recap, estimate and cards excepted).
6. Never claim anything not in the engine data or approved notes: no clients, no SLAs, no guarantees, no durations, no prices.
7. A human is always one click away ("Talk to a human").
8. Show progress. Let the visitor correct what the bot understood.
9. Honest speed: indicator while waiting, streaming where possible.
10. Measure everything that matters for engagement.

## 5. Target conversation (acceptance script for the demo)

```
Alex · AI advisor: Hi, I'm Alex, Nexus's AI project advisor. Tell me what you want to build in a sentence, or pick a starting point.
 [I have an app idea] [I need a web platform] [Add AI to my product] [Just exploring costs] [Talk to a human]
Visitor: A fitness app where trainers send workout plans to clients
Alex: A coaching app for trainers and their clients, got it. Should it run on iOS, Android, or both?   [iOS and Android] [Web] [Not sure, suggest]
Visitor: Not sure, suggest
Alex: For a first release most teams keep cost down with one cross-platform build, so I'll assume iOS and Android. Change it any time.   [Sounds good] [Let me choose]
Alex: When would you like to launch?   [ASAP] [1–3 months] [3–6 months] [Flexible]
Alex: Last one: a rough budget ballpark helps me size this. No commitment.   [Still exploring] [Under $15k] [$15–40k] ...
Alex: Here's what I understood: mobile coaching app, iOS and Android, launch in 3–6 months. If anything is off, tell me.
 [estimate card from the engine] [MVP] [sample projects]
Alex: That's a first-pass range based on typical scope for this kind of project. Want to sharpen it, see the MVP cut, or talk to the team?
 [Sharpen this estimate] [See the MVP] [Book a call] [Talk to a human]
```

Five questions, one recap, then the estimate.

## 6. Work packages

Do them in order. Each package needs failing tests first. Do not change engine numbers.

### E1. Persona, AI label, opener, intent starters, human exit, page context

```
TASK E1 (allowed: api/sessions.py, screening/slots.py, tenants/schema.py,
tenants/demo/brand.yaml, widget/consultant.js (+ sync to public/widget),
public/studio.html, tests).
1. BrandConfig: advisor_name (default "Alex"), advisor_title (default "AI
   project advisor"), advisor_avatar (optional URL or initials), starters
   (list of {label, intent}), opening_variants (list of strings).
2. Opening message: at most 40 words; contains the advisor name, the words
   "AI" and "advisor", what it does in one clause, and ONE open question.
   Do not promise a duration unless config says so. No pricing.
3. Starter chips: "I have an app idea" (service unknown), "I need a web
   platform" (web_app), "Add AI to my product" (ai_product), "Just exploring
   costs" (flow continues, estimate offered as early as possible), and a
   persistent "Talk to a human" that opens the booking/contact flow.
4. Widget and studio header: avatar or initials, "<advisor_name> · AI
   advisor", online dot, and a "Talk to a human" link visible at all times.
5. Page context: map the page path to a service with a config table
   (brand.page_hints), pre-fill the service and adapt the opener ("Looks
   like you're exploring mobile apps") without skipping the AI label.
6. Tests: opener length and label; each starter sets the right state; the
   human link works from every stage; an unknown path keeps the default
   opener; the widget file is identical in widget/ and public/widget/.
```

### E2. Voice and variation (per-tenant)

```
TASK E2 (allowed: screening/slots.py, agents/discovery_synth.py,
agents/router.py, agents/fallback.py, tenants/schema.py,
tenants/demo/voice.yaml (new), tests).
1. tenants/<slug>/voice.yaml: for every discovery field 3 question
   variants; acknowledgement templates that reference the captured value
   ("{service_label} for {goal_short}, got it"); banned phrases ("Great
   question", repeated "Love it"); emoji policy (at most one per message,
   none in estimate/price text); maximum 2 sentences (320 characters) for
   normal messages. Load and validate it with the tenant (unknown keys fail).
2. Variant choice is deterministic per (session id, field, attempt) so a
   page refresh does not reshuffle, and no acknowledgement repeats within 3
   turns.
3. LLM prompt for the consult step: add the voice rules, the last 3 bot
   acknowledgements (to avoid repeats), "be specific, not flattering", and
   keep the grounding line. The deterministic fallback uses the variants.
4. Acknowledgements may only mention values present in the brief.
5. Tests: no repeat within 3 turns; no emoji in estimate or price text;
   messages at most 320 characters unless estimate/recap/cards; banned
   phrases never appear; acknowledgement never mentions a value not in the
   brief; voice.yaml typo fails loading.
```

### E3. Estimate moment, recap and next steps

```
TASK E3 (allowed: agents/router.py, agents/fallback.py,
screening/slots.py, widget/consultant.js (+ sync), public/studio.html,
tests).
1. Before the estimate card add a deterministic recap line built only from
   the brief: service label, platforms, up to 4 features, timeline, budget
   band, goal cut to 120 characters on one line. It contains no price and no
   duration. Then "If anything is off, tell me and I'll update the estimate."
2. After the engine card add one warm sentence that says "based on typical
   scope for this kind of project". It must not mention projects we
   delivered, response times, guarantees or discounts.
3. Chips: "Sharpen this estimate", "See the MVP", "See sample projects",
   "Book a call", "Talk to a human". Call length comes from the calendar
   config (never hard-coded).
4. "I don't know" recovery in fallback.py: "That's outside what I have on
   hand right now. I can connect you with the team, or keep scoping your
   estimate." with two chips (Book a call, Continue estimate). No promise
   about reply times.
5. Tests: the recap contains no currency or duration; the engine range
   appears exactly once; no banned claim phrases ("similar projects we've
   delivered", "usually respond within") anywhere in backend/app; the call
   length equals the config value.
```

### E4. "Help me decide"

```
TASK E4 (allowed: screening/slots.py, agents/router.py, agents/fallback.py,
engines/architecture.py (read only unless a bug), tests).
1. Add a "Not sure, suggest" chip on platforms, features and timeline.
2. Handler: build a recommendation from the brief, the architecture rules
   and approved notes (retrieval). One or two sentences with the reason, no
   price and no duration, then chips "Sounds good" / "Let me choose". If the
   notes do not support a reason, use only the neutral rule from
   engines/architecture.py and say so in plain words.
3. "Sounds good" sets the slot; "Let me choose" re-shows the options.
4. Tests: no currency or duration in suggestions; accepting sets the slot;
   with an empty corpus it still answers neutrally; the grounding line is in
   the prompt.
```

### E5. Fast flow behind a flag (needs owner OK before it becomes the default)

```
TASK E5 (allowed: agents/brief.py, agents/router.py, agents/extractor.py,
screening/slots.py, engines/qualification.py (read only), tenants/schema.py,
tests). Pricing files stay untouched.
1. READ brief_ready, next_discovery_field and qualify and report how each
   uses the 11 fields.
2. New BrandConfig.flow: "classic" (default) | "fast". In "fast" the
   estimate becomes available when service, goal, platforms, timeline and
   budget_band are known (platforms is implied for ui_ux). features, users,
   integrations, user_flow, decision_role and company_size become optional:
   asked after the estimate as "Sharpen this estimate" steps, or inferred
   (company from the email domain when available).
3. First free-text message: extract every slot at once, recap what was
   captured, ask only what is missing, one question at a time.
4. Budget wording: "a rough ballpark helps me size this, no commitment" with
   a "Still exploring" option. Never ask budget before goal and platforms.
5. Each "Sharpen" answer recomputes the estimate with the existing engine.
6. Tests for both flows. The same brief gives the same engine numbers in
   both flows. Fast flow reaches an estimate in at most 6 bot questions for
   a clear first message. Classic flow behaviour is unchanged (all existing
   tests pass).
```

### E6. Widget feel

```
TASK E6 (allowed: widget/consultant.js (+ sync to public/widget),
public/studio.html, backend only for a progress field in the reply, tests).
1. Typing indicator: show it as soon as the request starts and remove it when
   the answer arrives. If the answer arrives in under 400 ms, keep it visible
   for about 600 ms. Never add delay to slow answers. Respect
   prefers-reduced-motion. aria-live="polite" on the thread.
2. Quick-reply chips wrap on small screens; tapping sends immediately.
3. Progress hint in the fast flow ("2 of 5"), subtle.
4. "Your brief" compact card: collapsed by default, shows the captured fields;
   tapping a field offers to change it (sends a chip to update the slot).
5. Teaser bubble (not an auto-open): after brand.teaser_delay_ms (default
   10000, 0 disables) on desktop only, once per session, dismissible, stored
   in sessionStorage. No session and no LLM call until the visitor sends a
   message. No exit-intent logic.
6. Manual check list for the report: iPhone width, Android width, keyboard
   open, dark and light host pages.
```

### E7. Streaming (week 2)

```
TASK E7 (allowed: api/sessions.py (new streaming route), core/llm.py,
agents/router.py, core/guard.py, widget/consultant.js (+ sync), tests).
First check the current Vercel docs for streaming responses from Python
functions; if unsupported on this plan, stop and report.
1. New route POST /api/v1/sessions/{id}/messages/stream (SSE). Free-text
   turns: stage 1 is the existing non-streamed structured call for slots;
   stage 2 streams the plain-text reply from
   models/{model}:streamGenerateContent?alt=sse (alt=sse is required; send
   the key in the x-goog-api-key header; request-mode time budget).
2. Sentence-buffered: each complete sentence passes through
   sanitize_price_leaks (and the duration guard if present) BEFORE it is
   sent. The final event carries chips, cards and state.
3. Any error falls back to the existing non-streaming route. No key or URL
   in logs.
4. Tests: a leaked price in a streamed sentence is replaced before sending;
   fallback on error; the final event has chips; the old route still works.
```

### E8. Name capture (optional, light)

```
TASK E8 (allowed: agents/router.py, screening/slots.py, tests).
After the first value, ask once "What should I call you?" with a skip chip.
Accept "I'm Rahul", "Rahul", "Rahul from Acme" (Hinglish too); keep letters
and spaces up to 40 characters; store in contact.name. Use it at most twice
(estimate intro and booking). Never in price or duration sentences. Tests:
skip works, odd input is ignored, "Dan" is a valid name, at most two uses.
```

### E9. Measure engagement

```
TASK E9 (allowed: models/entities.py + models/db.py (one table), api/admin.py,
admin template, api/sessions.py, tests).
engagement_events(session_id, kind, step, variant, created_at), no message
text. Kinds: started, answered_step, reached_estimate, requested_human,
booked, thumbs. Assign variant per session (opener A/B, flow classic/fast).
Admin page "Engagement": funnel (started, estimate, booked), median
questions to estimate, median time to estimate, drop-off per step, thumbs by
step, filtered by variant. Tests: events recorded once, no text stored,
admin-only access.
```

## 7. Do-not-break list

Price comes only from the engine; every outgoing message passes through the price guard; the grounding line stays in all prompts; admin fail-closed; header-based API key; `mode="request"` on every visitor LLM call; sample badges on demo case studies; the 291 existing tests.

## 8. Order for this week (demo next week)

1. E1 + E2 + E3 (words, persona, recap): biggest visible change, lowest risk.
2. E6 (typing, AI label, chips, teaser, brief card).
3. E4 ("help me decide").
4. E5 fast flow behind a flag, then flip it in preview and compare; owner decides the default.
5. Then the earlier SHIP-4 safety task before any public embed. E7, E8, E9 after the client's feedback.

## 9. Acceptance (you can check these yourself)

- First bot message: at most 40 words, includes the advisor name and "AI advisor", asks one open question.
- Fast flow: estimate after at most 6 bot questions for a clear first message.
- No acknowledgement phrase repeats within 3 turns; at most one emoji per message; none in estimate or price text.
- Typing indicator appears at once and never delays slow answers.
- "Talk to a human" is reachable from every stage.
- Estimate numbers are identical in both flows for the same brief.
- Red-team table (from the earlier SHIP-3B prompt) still passes.

## 10. How to review the agent's report

Reject if: a claim has no file:line or test; a test asserts nothing; pricing files changed; a banned claim phrase appears; the widget differs between widget/ and public/widget/; no pytest count; the agent committed or pushed; a personal email, key or database host appears anywhere.

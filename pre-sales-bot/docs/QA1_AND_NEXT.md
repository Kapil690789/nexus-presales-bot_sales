# QA-1 AND NEXT STEPS (10 Oct 2026)

## 1. Verdict on the E1b + E2 + E3 report

Conditional approve, not final sign-off.

Good: 307 + 13 + 10 + 10 = 340, the arithmetic matches; the `ask`-chip bug and the discovery nudge are fixed; the three features I asked for exist; widget files are identical.

Problems:
1. **Required evidence is missing.** The prompts asked for READ answers, the E1b table, files changed, and a scripted transcript (E2: 6 turns, E3: opener to booking card). None is in the report, so the actual conversation quality cannot be judged.
2. **Unrequested changes appeared in "Model & Latency Configuration":**
   - A fallback model `gemini-2.5-flash`. The client asked for 3.8 only, Google lists 2.5 Flash as deprecated on the Developer API (only previously active projects keep access), and it was not in any prompt. A silent model switch changes behaviour and cost.
   - "Query rewrites bypassed for short queries (<6 words)". Short follow-ups ("what about Android?") are exactly where the rewrite is needed.
   - "Context-aware warm responses" for post-booking, off-topic and brief-ready. No tests are listed, and warm text is where invented claims creep in.
3. **Not shown to work:** the new card type "shape", the "Email me instead" chip and the "Show a leaner cut" chip must render in BOTH the widget and `studio.html`. Byte-identical widget files do not prove that.
4. **Likely gap:** the discovery nudge treats any non-question text as an answer. Phrases like "I want to know your tech stack" or "need more details about your process" have no question mark and may be swallowed.
5. **Still pending from earlier:** SHIP-3B (duration guard, 4 MB upload limit, notes cap, transcript authorization, out-of-scope list from config, no hard-coded "Nexus", red-team table) and SHIP-4 (booking abuse, persistent rate limits). Calendar is still in demo mode.

## 2. Prompt QA-1

Paste the COMMON HEADER from `ENGAGE_PLAN_V2.md` section 0 first (suite count 340).

```
TASK QA-1 (allowed: core/llm.py, core/settings.py, agents/router.py,
agents/fallback.py, memory/rewrite.py, widget/consultant.js (+ sync to
public/widget), public/studio.html, scripts/demo_transcripts.py (new),
docs/DEMO_TRANSCRIPTS.md (new), tests/test_qa1.py (new)). Pricing files and
engines stay untouched.

1. AUDIT, no change yet. Report, with file:line and test names, for each
   unrequested change: (a) the fallback model, (b) the short-query rewrite
   bypass, (c) the "context-aware warm responses" (post-booking, off-topic,
   brief-ready). For each say what it does, which tests cover it, and which
   exact strings the bot can now say.
2. Model fallback. It must be OFF by default and configurable. New setting
   LLM_MODEL_FALLBACKS (comma separated, default empty). Remove any
   hard-coded model id. Fallback only on 404 NOT_FOUND or "model unavailable"
   errors; never on 429, 5xx, timeouts, 400, 401 or 403. Usage tracking
   records the model that actually answered. A system_events row (kind
   "model_fallback", class name only) is written when a fallback is used.
   /admin/api/health shows the configured and last-used model. Tests: 404
   falls back when a fallback is set; 404 with no fallback raises LLMError;
   429 does not fall back; usage is billed to the answering model.
3. Rewrite bypass. Skip the LLM query rewrite only when the message has at
   least 4 words AND contains none of: it, its, that, this, they, them,
   those, these, there, also, and, what about, how about, same, other,
   instead, too. Otherwise rewrite. Tests: "what about Android?" after a
   Flutter answer is rewritten; "Which cloud do you host on?" is not.
4. Question-like detector. Treat these as questions (retrieval, not the
   discovery nudge): "I want to know", "I'd like to know", "I would like to
   understand", "want to understand", "wondering", "curious", "need more
   info/information/details", "looking for info/information/details",
   "more about", and a bare noun phrase starting with "your" (your pricing,
   your process, your team, your stack, your support). Tests for each, and
   the E1b tests still pass.
5. Warm responses (item 1c). Either add tests that pin their exact text and
   confirm they contain no claim about past projects, response times,
   guarantees, prices or durations, or remove them.
6. Rendering. Confirm in BOTH widget/consultant.js and public/studio.html that
   the card type "shape", the chip "Email me instead" and the chip "Show a
   leaner cut" render. If one is missing, implement it (textContent only, no
   innerHTML for server text). Static tests check the strings and the card
   type handler exist in both files. Sync the widget.
7. scripts/demo_transcripts.py: runs six scenarios through the API in
   process (stub LLM by default; --live uses the real key if present and never
   prints it) and writes docs/DEMO_TRANSCRIPTS.md with every turn (visitor
   text, bot message, chips, card types, route, ms) and a checks table.
   Scenarios:
   S1 "We want it on both iOS and Android. For the first release we just need
      login, calendar booking, and push notifications. Budget around $25k to
      $35k, 2 to 3 months."
   S2 starter chip "I'm just exploring costs"
   S3 starter chip "I have an app idea", then "A marketplace for local farmers"
   S4 a seven-feature list in one message
   S5 Hinglish: "mujhe ek delivery app chahiye, iOS aur Android dono, 3 mahine
      me"
   S6 after an estimate: "Do you use Flutter?", "Which cloud do you use?",
      "Can you guarantee 4 weeks?", then book a slot, then "cool thanks"
   Checks per scenario: the first bot message has the standalone word "AI";
   every normal bot message has at most 2 sentences and 320 characters; no
   acknowledgement repeats within 3 turns; no banned phrase; the estimate
   card range equals the engine range for the final brief; no currency or
   duration figure outside the engine; number of bot questions before the
   estimate; turns to estimate.
STOP and report: pytest counts, files changed, the audit answers, the checks
table, and paste the full S1 and S3 transcripts in the report.
```

## 3. Manual check on the preview (10 minutes, you)

1. Click each starter chip and read the answer. It must move the conversation forward, never say "not sure" or an FAQ.
2. Send S1's long first message. The bot should acknowledge the specific features, skip what it already knows, and not ask the platform question again.
3. Add 6 features in one message. You should see the "lean first release" coaching sentence and a Core/Later split.
4. Reach the estimate. Check the order: recap line, engine card, one honest sentence, budget-fit line, chips. Read every line for claims you cannot back.
5. Check that the shape message (Channels/UX, Core flow, Backend/APIs) appears once, before the timeline question.
6. Booking: card text, "Email me instead", then book. A demo-mode note must still say no invite is sent until the calendar is connected.
7. "Talk to a human" at every stage. Phone width, long names, dark and light host page.
8. Ask: "I want to know your tech stack", "what about Android?" after a Flutter answer, "Can you guarantee 4 weeks?".

## 4. Plan for the days before the demo

| Order | Work | Why |
|---|---|---|
| 1 | QA-1 above | Evidence, remove surprises |
| 2 | E6 from `ENGAGE_PLAN_V2.md` (typing indicator, progress, brief card, teaser) | Biggest "alive" feel |
| 3 | E5 fast flow behind a flag, then compare in preview. You decide the default | Fewer questions is the real cure for "questionnaire" |
| 4 | SHIP-3B leftovers: duration guard, 4 MB upload limit, notes cap, out-of-scope list from config, no hard-coded "Nexus", red-team table | Safe to show other people's clients |
| 5 | Calendar connect on a demo Google account (consent screen "In production") | A real invite and Meet link impress more than a demo notice |
| 6 | Tax-company prototype tenant, only after Vishal answers what the bot should do | Do not start blind |
| 7 | Billing alert, rotate the Gemini key, `LLM_CALLS_PER_IP_PER_HOUR` 200 and `LLM_CALLS_PER_SESSION` 60 for the demo day | Avoid silent basic mode during the demo |

Skip for now: journey tracking, streaming, name capture, metrics dashboard, A/B tests. They can follow after the demo.

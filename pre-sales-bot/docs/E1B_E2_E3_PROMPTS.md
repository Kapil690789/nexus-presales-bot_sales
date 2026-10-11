# PROMPTS E1b, E2, E3 (10 Oct 2026)

Paste the COMMON HEADER from `ENGAGE_PLAN_V2.md` section 0 above each prompt (update the suite count to the current one: 307 after E1). Run in order: E1b, then E2, then E3. After each one, review the report with `ENGAGE_PLAN_V2.md` section 10.

## E1b. Starter chips and the "nothing filled" gap

Why: `router.py` computes `is_chip_click` from the original chip dict, so a chip with field "ask" (the new starters) counts as a chip click and skips the extractor. A message that is not a question and fills no slot (for example "I have an app idea", "I'm just exploring costs") then falls through to retrieval and the scripted fallback, which answers "not sure" to a visitor who is simply starting. This must be confirmed by a test, then fixed.

```
TASK E1b (allowed: agents/router.py, tests/test_engage_e1b.py (new)).
1. READ and prove with a test (no fix yet): post each starter text twice,
   once as a plain message and once as a chip {"field":"ask","value":<text>}.
   For each of "I have an app idea", "I need a web platform", "I want to add
   AI to my product", "I'm just exploring costs" record: route, stage,
   whether extract_slots ran (mock it), and the first 120 characters of the
   reply. Report the table.
2. Fix 1: a chip whose field is "ask" is free text. is_chip_click must be
   false for it (compute it from the field after the "ask" reset).
3. Fix 2, discovery nudge: during discovery (brief not ready, no estimate)
   a message that (a) is not question-like (no "?", does not start with
   what/how/who/why/when/where/can/do/does/is/are/have/will/should, and does
   not start with tell/show/explain/describe/list/give/share), (b) fills no
   slot, (c) is not an objection and (d) is not an acknowledgement must NOT go
   to retrieval or the scripted fallback. Reply with a one-clause
   acknowledgement and the next discovery question with its chips (use
   _after_brief and count the attempt in brief.field_attempts so the repeat
   rephrase still works). Imperatives such as "Tell me about your process"
   still go to retrieval.
4. Tests: each starter text (plain and as an "ask" chip) gives route
   "discovery" and a reply that contains a question mark and the next field's
   chips; extract_slots runs once for an "ask" chip and zero times for a
   normal chip; "Tell me about your process" still uses retrieval;
   "Do you use Flutter?" still uses retrieval; "too expensive" still gets the
   objection reply; "ok thanks" is still an acknowledgement.
STOP and report: pytest counts, files changed, the READ table.
```

## E2. Voice: specific acknowledgements, variety, scope coach

```
TASK E2 (allowed: screening/slots.py, agents/discovery_synth.py,
agents/router.py, agents/fallback.py, agents/brief.py (one new field),
tenants/schema.py, tenants/loader.py, tenants/demo/voice.yaml (new),
tests/test_engage_e2.py (new)). Pricing files and engines stay untouched.
READ first and report: where DISCOVERY_PROMPTS and REPHRASED_PROMPTS are
used, and how discovery_synth builds its prompt and fallback.

1. voice.yaml and schema (extra="forbid"). VoiceConfig:
   - questions: for every discovery field, a list of 2 to 3 variants (each
     up to 30 words, no currency symbols, no digits followed by weeks, months,
     minutes or hours).
   - acks: templates with the placeholders {service_label}, {goal_short},
     {platforms}, {features_list}, {timeline_label}. Unknown placeholders
     fail loading.
   - scope_coach: one or two sentences used when the visitor lists more than
     4 features.
   - banned_phrases: list. emoji_max: 1. max_chars: 320.
   A tenant without voice.yaml uses built-in defaults equal to today's
   prompts, so other tenants keep working.
2. Write tenants/demo/voice.yaml in our own words. Rules for the copy: be
   specific, not flattering; no "Love it", "Great idea", "Smart approach";
   no "v1"; no claims about past projects, response times or guarantees.
   Examples of the style (adapt, do not copy verbatim): goal -> "A
   {service_label} for {goal_short}: that gives me a clear picture."; features
   (up to 3) -> "{features_list} is a solid core for a first release.";
   scope_coach -> "That's a rich list. A lean first release usually keeps cost
   and risk down, so I'll split it into Core and Later for you."; platforms
   -> "{platforms}, noted."
3. ack_from_brief(brief, changed_fields, voice, session_id): deterministic.
   It mentions only values present in the brief, picks by priority (features,
   goal, platforms, timeline), and returns nothing when no field changed.
   Variant index = stable hash of (session_id, field, attempt). Keep the last
   3 ack ids in a new ProjectBrief field recent_acks; never reuse one of
   them.
4. Message composition: ack + next question, at most 2 sentences and
   max_chars. The scripted path and the LLM path both use it. LLM path: the
   consult prompt receives the voice rules, the last 3 acks and the values
   that changed, keeps the grounding line, and the reply is validated:
   length, sentence count, emoji count, banned phrases, and the existing
   price guard. If validation fails, use the deterministic composition.
5. Tests (literals): same session and field give the same variant; no ack
   repeats within 3 turns; an ack never mentions a value that is not in the
   brief; 5 features trigger scope_coach, 3 do not; banned phrases never
   appear in 40 simulated turns; a message over 320 characters is replaced by
   the deterministic one; a typo in voice.yaml fails loading; a tenant without
   voice.yaml still works; no emoji in price text.
STOP and report: pytest counts, files changed, READ answers, and a sample
transcript of 6 scripted turns (stub LLM).
```

## E3. Estimate moment, shape message, budget-fit, own-words booking card

```
TASK E3 (allowed: agents/router.py, agents/fallback.py, agents/brief.py
(one new field), screening/slots.py, tenants/schema.py,
tenants/demo/qualification.yaml (one new optional key only),
tenants/demo/brand.yaml, widget/consultant.js (+ sync to public/widget),
public/studio.html, tests/test_engage_e3.py (new)). Pricing files and
engines stay untouched. Do not copy any competitor wording.
READ first and report: what recommend_architecture and recommend_mvp need as
input and return; where the calendar call length is configured (platform.yaml
or tenant); how the post-booking and email-capture blocks in router.py work.

1. Shape message. After platforms and features are known and before the
   timeline and budget questions, show once (new brief field shape_shown) a
   deterministic message and card with three parts: Channels and UX (from the
   architecture frontend list), Core flow (the top 3 MVP items), Backend and
   APIs (from the architecture backend list). No price, no duration, no
   claim about past work. If the engines need a fuller brief, build the
   message from the architecture rules only.
2. Budget-fit line. Add optional qualification key budget_band_ranges_usd
   in the tenant config, for example {exploring: null, under_15k: [0, 15000],
   15_40k: [15000, 40000], 40_80k: [40000, 80000], 80k_plus: [80000, null]}.
   budget_fit_line(band, estimate, ranges) returns one neutral sentence:
   band below the engine range -> "Your budget band sits below this
   first-pass range. The usual lever is a leaner scope; I can show a
   Core-only cut." (with chip "Show a leaner cut" that opens the MVP view);
   overlapping -> "Your budget band overlaps this first-pass range.";
   above -> "Your budget band is above this first-pass range, so there is
   room to add scope."; exploring or missing -> no line. It never prints a
   new currency figure and never uses the words "realistic" or "guarantee".
3. Estimate sequence: a deterministic recap line from the brief (service
   label, platforms, up to 4 features, timeline, budget band, goal cut to 120
   characters on one line; no price or duration) + "If anything is off, tell
   me and I'll update the estimate."; then the engine card; then one honest
   sentence ("That's a first-pass range based on typical scope for this kind
   of project."); then the budget-fit line; then chips Sharpen this estimate,
   See the MVP, See sample projects, Book a call, Talk to a human.
4. Booking card wording (own words, config key brand.booking_handoff_text,
   default): "The team will see this whole conversation, so you won't need to
   repeat anything." Add a chip "Email me instead". Its handler replies "Sure.
   What's the best email?" and sets contact.prefers_email; when an email then
   arrives, record the lead and answer "Thanks, the team will email you the
   summary." without showing slots again.
5. Call length in any text comes from the calendar config (never hard-coded).
6. "I don't know" recovery in fallback.py: "That's outside what I have on
   hand right now. I can connect you with the team, or keep scoping your
   estimate." with chips Book a call and Continue estimate. No promise about
   reply times.
7. Tests (literals): the recap has no currency or duration; the engine range
   appears exactly once in the estimate message; budget-fit for each of
   below, overlap, above, exploring; the shape message appears once and
   before the timeline question; no text in backend/app contains "similar
   projects we've delivered", "usually respond within", or "realistic";
   "Email me instead" does not show slots; the call length text equals the
   config; the widget files are byte-identical.
STOP and report: pytest counts, files changed, READ answers, and one full
scripted transcript (stub LLM) from the opener to the booking card.
```

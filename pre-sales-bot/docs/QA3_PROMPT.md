# QA-3: fix what the live transcripts show (blocking before any demo)

Applies the AUTOPILOT RULES in `FINAL_AGENT_QUEUE.md` section 0 (no commits, no pricing edits, report with evidence in `docs/AGENT_REPORTS.md`, owner questions in `docs/OWNER_QUESTIONS.md`). Suite count to start from: 417.

I reviewed `docs/DEMO_TRANSCRIPTS.md` (generated 11 Oct 16:19 UTC, the Q1 version; I have not seen the final `FINAL_QA_REPORT.md`, `REDTEAM.md` or `FLOW_COMPARISON.md`). The "all checks pass" tables do not match the dialogue. The "Demo Readiness Gate: all YES" claim is therefore not accepted until QA-3 is done and the stricter checks below pass.

## 1. Evidence from the live section (gemini-3.8-flash)

| # | What the transcript shows | Where |
|---|---|---|
| 1 | Turn latency 2 to 38 seconds. Examples: S1 t1 29.9 s, S1 t2 14.8 s, S2 t1 38.2 s, S2 t2 11.9 s, S3 t3 10.9 s. The Q1 "fix" raised the request budget and timeout from 12 s to 25 s to silence a warning, which hides the problem and lets a visitor wait up to 25+ seconds | S1, S2, S3, S6, S7 |
| 2 | The starter chip "I have an app idea" gets the objection reply "We can work toward a fixed commercial once discovery is locked..." (route "objection") | S3 t1, S8 t1 |
| 3 | "$40k to $80k" (a budget answer) gets the same objection reply, and the budget is not stored: the final recap says "a budget of still exploring" and the estimate is delivered for the wrong service | S2 t7 and t8 |
| 4 | Every time a budget is given, the bot's own acknowledgement is deleted and replaced with "Exact pricing depends on scope; the indicative range above is the only figure I can confirm." although no range has been shown yet | S3 t6, S5 t3, S7 t7, S8 t6 |
| 5 | "I'm just exploring costs" sets the service to web and the goal to nothing useful; then "Mobile app" gets "You mentioned a web app earlier, but mobile as the platform." (the visitor never said web). The shape card shows Next.js for a mobile idea. The recap says "a web application for Mobile app" | S2 |
| 6 | The goal and features are captured wrongly: S3/S8 recap "a web application for marketplace for local farmers, on web, iOS and Android, with Marketplace" (the four real features are lost); S6 recap "a mobile app for cross-platform mobile app for iOS and Android, on iOS and Android, with Workout logger, Push notifications" (the real idea "Fitness coaching" is lost, platforms repeated) | S3, S6, S8 |
| 7 | The shape message contains "Core user flows for the Core flow" in every scenario (placeholder text) | all |
| 8 | A 7-feature clinic management system with telemedicine, prescriptions and insurance verification is quoted $19,000 to $24,000 over 8 weeks (the plain base range) and the bot says the budget "is above this first-pass range, so there is room to add scope". The pricing engine ignores feature count | S4 |
| 9 | After the estimate, answering the role question re-sends the whole estimate block a second time | S4 t5 |
| 10 | "Do you use Flutter?" and "Which cloud do you use?" get the identical FAQ sentence twice in a row; company-size chips (Startup, SMB...) appear on a FAQ reply and after booking | S6 |
| 11 | The recap grammar is still broken ("a mobile app for sports clinic booking application for direct patients") and prints the budget band ($15k to $40k) instead of what the visitor said ($25k to $35k) | S1, S7 |

Why the tables show all ✓: the checks only test length, a few banned words and casing. They do not compare the recap with what the visitor said, do not flag objection routes, guard replacements, repeated messages or latency.

## 2. TASK QA-3

```
TASK QA-3 (allowed: core/llm.py, core/settings.py, core/guard.py,
core/usage.py (read), agents/router.py, agents/extractor.py,
agents/discovery_synth.py, agents/fallback.py, agents/brief.py,
screening/slots.py, engines/objections.py, engines/mvp.py (read),
engines/architecture.py (read), rag/grade.py, tenants/schema.py,
tenants/demo/voice.yaml, scripts/demo_transcripts.py,
docs/DEMO_TRANSCRIPTS.md, docs/AGENT_REPORTS.md, docs/OWNER_QUESTIONS.md,
tests/test_qa3.py (new)). Pricing files stay untouched. Do the items in
order, test first, pytest green after each.

1. LATENCY (first). Revert the request-time budget to 12 s total and 12 s per
   call. Then find the real cause:
   a. Instrument every LLM call in a turn: purpose (extractor, consult,
      grade, grounded, fallback, synth), model, wall time, prompt tokens,
      output tokens, thinking tokens, retry count, whether 429 backoff ran.
      Confirm in the request body (log presence only, never the key) that
      generationConfig.thinkingConfig.thinkingLevel is "low" for EVERY call.
   b. Count LLM calls per turn for S1 to S8 and print a table (turn, calls,
      ms per call, thinking tokens).
   c. Measure a minimal call (one short prompt) to separate API time from our
      code. Report the numbers.
   d. Reduce work: one structured call per free-text turn that returns both
      the extracted slots and the short acknowledgement message (remove the
      separate consult call); no LLM call at all for chip answers (use the
      deterministic acknowledgement from voice.yaml); no relevance-grade call
      when the top score is at least 0.75.
   e. Target in --live S1 to S8: median at most 4 s, p95 at most 8 s, max at
      most 12 s per turn, at most 2 LLM calls per turn. If the budget is hit,
      the deterministic path answers (never a long wait).
   f. If 3.8 Flash is still above target after d, write in
      docs/OWNER_QUESTIONS.md: "Allow LLM_MODEL_LIGHT for extraction and
      acknowledgements while 3.8 stays the main model?" with the table. Do not
      switch models yourself.
2. OBJECTION HIJACK. The semantic objection match must not fire unless the
   message has an objection cue (expensive, cost, costly, price, pricing,
   cheaper, discount, afford, budget is tight, too long, slow, faster, fixed
   price, fixed bid, lump sum, offshore, outsourced, negotiate) OR the match
   score is at least 0.80 and the message has more than 4 words and contains a
   money or time-pressure word. It never runs for: starter texts, an
   acknowledgement, a message that is a slot answer (budget range or band,
   timeline, platform, role, company size), or a message of 4 words or fewer
   without a cue. Tests with a mocked search that returns a high objection
   score: "I have an app idea", "$40k to $80k", "3 to 6 months", "A marketplace
   for local farmers" are not objections; "that's too expensive" and "can you
   do a fixed price?" are.
3. BUDGET CAPTURE. A typed budget ("$40k to $80k", "around 25 to 35k", "$25k
   to $35k", "under 15k") sets budget_band (the band that contains the range's
   midpoint) and stores budget_text (max 40 characters, the visitor's own
   words). The recap echoes budget_text ("around $25k to $35k"). Tests,
   including the S2 script: the recap must never say "still exploring" after a
   figure was given.
4. PRICE GUARD ON NON-ESTIMATE TURNS. If the session has no estimate yet, a
   sentence with an unauthorized figure is deleted (not replaced), and the
   rest of the message, including the question, is kept. Never insert "the
   indicative range above" when no range was shown. Figures that match the
   visitor's budget_text or band are always allowed (accept "$40k to $80k",
   "$40k-$80k", "$40,000 to $80,000", "40k to 80k"). Add to the consult/
   synth prompt: "Do not repeat the visitor's budget or any currency figure."
   When the guard fires, write the original sentence to the transcript output
   (script only, never to logs in production). Tests for each case.
5. BRIEF CONSISTENCY. Add service_source to the brief ("chip", "explicit",
   "guess"). Rules:
   a. "I'm just exploring costs" and similar set neither service nor goal; the
      bot answers "Happy to help you explore costs. What are you thinking of
      building: a mobile app, a web platform, AI, or design?" with the service
      chips.
   b. The bot says "You mentioned X earlier" only if X came from the visitor's
      own words (service_source "chip" or "explicit"); a guess is replaced
      silently.
   c. A first free-text message becomes the goal only if it describes a
      product idea (a build verb with a noun phrase, or at least 3 words that
      are not only platform, budget, timeline or role words). Platform-only or
      budget-only text never becomes the goal.
   d. A list answer appends to features; it never replaces the goal and the
      goal never replaces features.
   e. "web and mobile" sets platforms ["web","ios","android"]; with no service
      set, set mobile_app and write the pricing implication in
      docs/OWNER_QUESTIONS.md.
   f. Literal expected final briefs (assert them):
      S1: platforms iOS+Android, features [login, calendar booking, push
          notifications], goal contains "sports clinic booking", timeline
          1_3_months, budget_band 15_40k, budget_text "$25k to $35k".
      S2: service mobile_app, goal "Field service and asset tracking",
          platforms iOS+Android, features [Offline data collection, barcode
          scanning, GPS tracking], timeline 1_3_months, budget_band 40_80k.
      S3/S8: goal "A marketplace for local farmers", features [Produce
          catalog, Stripe checkout, farmer payouts, direct chat], platforms
          web+iOS+Android, timeline 3_6_months, budget_band 40_80k.
      S6: goal contains "Fitness coaching", features include workout logger
          and push notifications, platforms iOS+Android.
      S4: service web_app, goal contains "clinic management", 7 features.
6. RECAP AND ACKNOWLEDGEMENT GRAMMAR. Build the recap from structured parts,
   not by splicing the goal into a sentence:
   "Here's what I understood: <article> <service lower case> - <goal phrase>.
   Platforms: <display_platforms>. Features: <up to 4, then 'and N more'>.
   Timeline: <timeline_label>. Budget: <budget_text or label>."
   goal phrase = the visitor's words with a leading "I am building / we need
   / I want a" removed, any platform words already shown under Platforms
   removed, at most 90 characters, cut at a word boundary. Omit unknown parts.
   Remove every "for <goal>" splice from acknowledgement templates.
7. SHAPE MESSAGE. Replace "Core user flows for the Core flow" with the top
   three MVP items from engines/mvp.py. The frontend and backend text must
   follow the visitor's service and platforms (no Next.js shape for a mobile
   idea). If MVP items are missing, omit that part. Tests for S2 and S7.
8. AFTER THE ESTIMATE.
   a. Role or company-size answers get a short acknowledgement and the next-step
      chips; the estimate block is never sent twice.
   b. The same FAQ text is never sent twice in a row; the second time use
      another approved FAQ entry, or "Our team can go into detail on a call"
      with the booking chips.
   c. Company-size chips appear only after "Sharpen this estimate" is clicked.
9. SCOPE-VS-RANGE CAUTION (no pricing change). If features_count is at least 5
   and the engine low is not above the service base range, add one sentence
   after the honest sentence: "This range assumes the Core scope; a list this
   long will likely need more, and the team can size it precisely." plus the
   chip "Show the Core cut". Do not say the budget "has room to add scope" in
   that case. Write in docs/OWNER_QUESTIONS.md: "pricing ignores feature count
   (S4: 7 features quoted $19,000 to $24,000). Options: a feature-count
   multiplier (needs approval) or leave the caution line only."
10. FAST FLOW FLAG. The spec asked for a per-tenant BrandConfig.flow
    ("classic" or "fast"); the report used an environment variable
    ENABLE_FAST_FLOW. Make the tenant setting the source of truth (keep the
    env var only as an override for tests) and report which one the demo uses.
11. STRICTER CHECKS in scripts/demo_transcripts.py (a check with no data is
    N/A or FAIL, never a tick). Add:
    - the final brief equals the literal expected brief of the scenario;
    - the recap lists those exact features, platforms, timeline and budget;
    - no word or platform name repeated in the recap ("iOS and Android" twice,
      "app for application");
    - route "objection" only on turns tagged as objections (S6 "Can you
      guarantee 4 weeks?");
    - no guard-replacement sentence before an estimate exists;
    - no two identical bot message bodies in a row, and the estimate block
      appears once per scenario;
    - banned strings: "for the Core flow", "No problem", "indicative range
      above" before an estimate, "You mentioned" without a source;
    - latency per scenario (--live): median at most 4 s, p95 at most 8 s, max
      at most 12 s, at most 2 LLM calls per turn.
    Add scenarios S9 (first message is only a budget: "my budget is $40k to
    $80k") and S10 (starter "I have an app idea", then "a booking app for
    barbers", then "web and mobile", then a 5-feature list, then chips to the
    estimate).
12. Re-run S1 to S10 in stub and --live. Paste S1, S2, S3, S4, S6 and S10 in
    full for both modes in your report (all chips, cards, route, ms, number of
    LLM calls), plus the checks tables and the latency table. List the 10
    worst bot messages you can find yourself, with your fix for each.
STOP and report. Do not claim the Demo Readiness Gate until every check above
passes in --live.
```

## 3. Safest demo path until QA-3 is merged (owner)

Use a single long first message like S1 (platforms, features, budget and timeline in one go): it reaches the estimate in three turns and avoids the budget turn that triggers the guard line and the starter chips that trigger the objection reply. Do not click "I have an app idea" or "Just exploring costs", and do not type a budget in words. Keep the demo on the preview, not production, and expect 4 to 8 seconds per free-text turn.

## 4. After QA-3

1. Owner: 10-minute manual check on the preview, using the S2, S3, S4 and S10 inputs above; read every bot line.
2. Paste the live S1, S2, S3, S4, S6 and S10 transcripts and the checks tables here for review.
3. Then decide the fast-flow default from `docs/FLOW_COMPARISON.md`, answer `docs/OWNER_QUESTIONS.md` (light model for extraction, pricing and feature count, web and mobile pricing), and send Vishal's tax-bot question.
4. Calendar connect, billing alert, key rotation, and the demo-day env limits remain on the owner list in `FINAL_AGENT_QUEUE.md` section 3.

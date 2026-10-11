# E1 PROMPT AND PLAN DELTA (10 Oct 2026)

Read after `docs/ENGAGE_PLAN_V2.md`. This file (A) reviews the Landbot / G2 / Intercom findings, (B) lists the changes to the plan, and (C) gives the literal TASK E1. Paste the COMMON HEADER from `ENGAGE_PLAN_V2.md` section 0 above the prompt in (C).

## A. Review of the live-test findings

The findings are good. The right reading: **the demo is a capability pitch, so it has to be impressive and never wrong.** A wrong or invented sentence costs more than a missing feature.

### Adopt
1. **Specific acknowledgement built from what the visitor said** ("login + booking + push") instead of a generic "great idea". Build it from the extracted brief values, never from model imagination.
2. **A visible "shape" of the solution** in three parts (channels/UX, core flow, backend/APIs) before asking for budget. This is value before data. Build it from our own engines (`recommend_architecture`, `recommend_mvp`), with no prices or durations.
3. **Scope discipline.** When the feature list is long, say a lean first release usually keeps cost and risk down, and show Core versus Later. Our MVP engine already splits this.
4. **Email last**, after value (Intercom asking for email on turn 1 confirms the research).
5. **Booking card that hands over context**, plus an "Email me instead" option. Write our own words. Do not copy their sentence ("they'll have this conversation on hand, so no starting from zero"). Suggested own wording: "The team will see this whole conversation, so you won't need to repeat anything."
6. **Page context** from the page path (already E1).

### Adapt
- Landbot told the visitor that a budget and timeline were "realistic". We must not let a model say that. Build a deterministic **budget-fit line** from the engine range and the visitor's budget band: below, overlapping, or above, in neutral words, with a leaner-scope suggestion when below. Needs numeric ranges for the budget bands in tenant config (new optional key, not in pricing files).
- Use "first release" or "Day-1 launch", not "v1" (we removed "v1" jargon in Session 16).

### Do not do
- **Do not copy their code, config, prompts or marketing copy.** Observing public behaviour is fine. Reusing their script, the storage config file, flows or text is not (copyright and likely their terms of use). Re-implement ideas in our own words and code. Do not automate repeated testing of their service.
- **Do not build the "journey" tracking** (referrer, dwell time, scroll depth, revisit greeting stored in localStorage) now. It is personal-data processing. India's DPDP Act and GDPR need a notice and in many cases consent. For E1 read only `location.pathname` once at session start, store nothing. A consented revisit feature can come later with a privacy notice (confirm with the client's legal advice).
- Do not copy the cross-sell ("build my agent free") or any claim about outcomes.

## B. Changes to the plan

| Package | Change |
|---|---|
| E1 | As specified in (C). No tracking beyond the path. |
| E2 | Add `ack_from_brief(brief, changed_fields)`: a deterministic, specific acknowledgement that mentions only values present in the brief. Add the "scope coach" rule: with more than 4 features, one sentence suggesting a lean first release and promising the Core/Later split. |
| E3 | Add (1) the three-part "How I'd shape it" message before the timeline and budget questions (from the engines, no numbers); (2) the deterministic budget-fit line; (3) booking card wording above plus an "Email me instead" chip. Keep the recap and honest estimate sentence from V2. |
| E5 | Unchanged, plus order: shape message before the budget question. |
| E6 | Add the returning-visitor greeting only after a consent and privacy notice exists. |
| New E10 | Tenant #2 prototype for the client's tax-consultation pitch. Needs client input first (see below). |

### Tax-consultation pitch (new, important)
The client wants a strong pitch for a tax-consultation company. Our current engine is a software-project estimator; its slots (platforms, integrations, features) do not fit tax work. Options, cheapest first:
1. **FAQ + intake + booking tenant**: services list, approved FAQs (retrieval), 3–4 intake questions (individual or business, what do you need help with, urgency, city), document checklist, lead capture, booking. Uses existing pieces: FAQ route, retrieval, booking, leads. Needs only tenant content and a small flow variant.
2. **Fee indication**: only if the client gives approved starting fees; shown from tenant config, never invented.
3. **Config-driven slot schema per tenant**: the real white-label step, bigger refactor; not for next week.
Risks to state to the client: the bot must not give tax advice, figures, deadlines or penalties from the model; every tax answer must come from the firm's approved content, with a "not tax advice" disclaimer, a human handoff for notices and disputes, and the AI label.
Question to ask Vishal: "For the tax company, what should the bot do: answer FAQs, collect client details, book consultations, give a document checklist, give a fee quote?"

## C. TASK E1 (literal)

```
TASK E1 (allowed: api/sessions.py, api/public_config.py (only if the widget
needs the new brand fields), screening/slots.py, tenants/schema.py,
tenants/demo/brand.yaml, widget/consultant.js, public/widget/consultant.js,
public/studio.html, tests/test_engage_e1.py (new) and the existing tests
that assert the old opener text). Pricing files and engines stay untouched.

FIRST READ and report (no change yet):
 a. How the widget gets brand data (public config route) and which fields
    it exposes today.
 b. The create-session request model: does it accept a page path?
 c. How the widget sends and renders chips, in particular chips with
    field "ask": what text appears as the visitor message and what the
    router receives.
 d. Whether public/studio.html uses widget/consultant.js or has its own
    chat code and header.
 e. Which existing tests assert the old opener text.

Then implement, test first, in this order.

1. Schema (tenants/schema.py). Use extra="forbid" on every new model.
   BrandConfig gets:
   - advisor_name: str = "Alex" (1-30 characters: letters, spaces, hyphen,
     apostrophe, period).
   - advisor_title: str = "AI project advisor". Validator: must contain the
     standalone word "AI".
   - advisor_avatar: str = "" (empty, or an https:// URL up to 300
     characters; anything else fails validation).
   - human_label: str = "Talk to a human" (up to 32 characters).
   - starters: list of Starter(label up to 32 characters, text up to 120
     characters). Default four: "I have an app idea" / "I have an app idea",
     "I need a web platform" / "I need a web platform", "Add AI to my
     product" / "I want to add AI to my product", "Just exploring costs" /
     "I'm just exploring costs". At most 5.
   - opening_variants: list[str] = [] (each up to 25 words; no $, EUR,
     rupee or percent signs; at most one emoji).
   - page_hints: list of PageHint(match: path prefix that starts with "/",
     service: optional key that must exist in the tenant's in_scope
     services, question: up to 25 words). Cross-check the service key when
     the tenant loads and fail with a clear message.
   Update tenants/demo/brand.yaml only with these keys (defaults are fine).

2. Opening message (api/sessions.py). Build it from two parts:
   disclosure = f"Hi, I'm {advisor_name}, {brand.name}'s {advisor_title}."
   question = the first matching page_hint question, else an
   opening_variant chosen deterministically from a hash of the session id,
   else "Tell me what you'd like to build in a sentence, or pick a starting
   point."
   text = disclosure + " " + question. At most 40 words. The disclosure part
   is ALWAYS present, so the visitor is always told it is an AI. Use the
   tenant's brand name, never a hard-coded "Nexus". No price, no duration
   promise, no emoji by default.

3. Starter chips and the human chip.
   - Starters become chips {"label": starter.label, "field": "ask",
     "value": starter.text}, shown only on the opening message.
   - If a page_hint with a service matched, set that service in the new
     session's brief and show only the human chip (no starters), because the
     opener already asks about the idea.
   - The human chip is {"label": human_label, "field": "booking_window",
     "value": "this_week"} (reuse the existing booking handler) and is also
     returned with the opening chips.
   Check what you reported in READ c. If "ask" chips do not show the chip
   text as the visitor's message, fix that in the widget so the visitor
   sees their own words.

4. Page path. If READ b says no path is accepted, add an optional
   path: str = "" (maximum 200 characters) to the create-session request.
   The widget sends location.pathname only. Use only the path (ignore query
   string and fragment) to choose a page_hint. Do not store the path, the
   referrer, the time on page or the scroll depth anywhere. Do not add any
   localStorage tracking.

5. Public config. Expose advisor_name, advisor_title, advisor_avatar and
   human_label to the widget (and nothing else new). Never expose
   internal fields. The widget falls back to the defaults if they are
   missing.

6. Widget and studio header (widget/consultant.js, public/studio.html).
   - Show an avatar (image if advisor_avatar is set, with an onerror
     fallback to initials; otherwise initials in a circle), the text
     "<advisor_name> - <advisor_title>", an online dot, and a "Talk to a
     human" link that is visible at all times and sends the human chip.
   - Render all text from config with textContent (never innerHTML). Set
     referrerpolicy="no-referrer" on the avatar image.
   - Keep the existing info (i), reset, expand and close controls.
   - After editing run: cp widget/consultant.js public/widget/consultant.js
   - If the studio has its own chat code (READ d), apply the same header
     and opener behaviour there.

7. Tests (tests/test_engage_e1.py). Each must fail before the change.
   - Schema: advisor_title without "AI" fails; an http:// avatar fails; an
     unknown page_hint service fails; unknown keys fail; defaults load.
   - Opener: at most 40 words; contains the advisor name, the brand name
     and the standalone word "AI"; contains no "Nexus" for a tenant named
     "Acme" (use a test tenant); the same session id gives the same
     variant; two different ids can give different variants.
   - Chips: the opening message has the starters plus the human chip; a
     starter chip sent back is treated as free text and the bot replies
     without error; the human chip returns booking slots.
   - Page hint: path "/mobile" with a hint sets the service and shows only
     the human chip; an unknown path gives the default opener; a path with a
     query string matches by path only.
   - Privacy: the create-session handler and the widget do not read or
     store referrer, dwell time or scroll depth (static test on the widget
     source for "document.referrer", "scroll" and "localStorage" additions
     that are new in this change).
   - Public config: exposes the four new fields and no secret field.
   - Widget: widget/consultant.js and public/widget/consultant.js are
     byte-identical; the header source contains the badge text and the
     human link; config text is set with textContent (static check).
   - Update the existing tests that assert the old opener text with
     equivalent assertions for the new opener. Do not delete them.

8. Manual preview checklist (list the results in your report): desktop and
   phone width, dark and light host page, long advisor name, missing avatar,
   avatar load failure, keyboard navigation to the human link, reduced
   motion.

STOP and report: pytest counts (before 291), files changed, the answers to
READ a-e, test names added, and anything that contradicted these steps.
```

## D. After E1

Review the report with the checklist in `ENGAGE_PLAN_V2.md` section 10. Next: E2 and E3 with the deltas in section B above (specific acknowledgement, shape message, budget-fit line, own-words booking card, "Email me instead").

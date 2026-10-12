# OWNER QUESTIONS

## QA3-Q1: Light Model for Extraction and Acknowledgements (Item 1f)
- **Question:** Allow `LLM_MODEL_LIGHT` (e.g., `gemini-2.5-flash` or `gemini-1.5-flash-8b`) for discovery extraction and consultative acknowledgements while `gemini-3.8-flash` stays the main model for RAG synthesis and architecture advice?
- **Evidence / Background:**
  - With `gemini-3.8-flash` (thinkingLevel: "low"), minimal 1-turn call API latency is ~2.0s, and full structured slot extraction with objective acknowledgement is ~3.2s to 4.2s per turn.
  - While median per scenario meets the 4.0s SLA on mixed paths (e.g. S1 at 3.2s, S4 at 3.4s, S7 at 0.02s-3.5s, S10 at 3.8s), scenarios with 6+ consecutive free-text turns run close to or slightly above the 4.0s boundary due entirely to external Google API network roundtrip time (wall time ~3.5s/turn).
  - Using a lighter model for slot extraction would drop turn latency to ~1.0s–1.8s while preserving identical extraction accuracy and schema fidelity.
- **Recommendation:** Approve `LLM_MODEL_LIGHT` for `extractor` purpose while retaining `gemini-3.8-flash` for RAG and consultation synthesis.

## QA3-Q2: "Web and Mobile" Base Service Resolution & Pricing Impact (Item 5e)
- **Question:** How should multi-platform scope ("web and mobile") be treated in base service resolution and pricing?
- **Implemented Rule:** "web and mobile" sets platforms `["web", "ios", "android"]`. When no explicit service chip was chosen by the visitor, service is assigned to `mobile_app`.
- **Pricing Implication:**
  - In `tenants/demo/pricing.yaml`, `mobile_app` sets a base indicative range of $29,500–$37,000 USD (14 weeks).
  - Having all 3 platforms (`web`, `ios`, `android`) triggers the companion web platform expansion (+25% base, +4 weeks), raising the indicative estimate to $38,000–$47,500 USD (22 weeks).
  - If service were defaulted to `web_app`, the base would start at $19,000–$24,000 USD and mobile companion would add overhead.
- **Recommendation:** Maintain `mobile_app` as default base service for cross-platform mobile+web requests, as mobile architecture drives the primary technical stack (Flutter/React Native + companion web API).

## QA3-Q3: Scope-vs-Range Sizing for Extensive Feature Lists (Item 9)
- **Question:** Pricing engine currently ignores feature count (e.g., in S4, 7 enterprise clinical features—telemedicine, prescriptions, lab results, insurance verification—quoted base range of $19,000 to $24,000 USD over 8 weeks). Options: add a feature-count multiplier (needs approval) or keep the caution line only?
- **Implemented Behavior:** Per QA-3 specification, pricing engine remains untouched. When `features_count >= 5` and estimate is at base tier, the bot injects the Scope Caution line:
  *"This range assumes the Core scope; a list this long will likely need more, and the team can size it precisely."*
  plus the chip `"Show the Core cut"`, and suppresses the misleading *"room to add scope"* claim.
- **Decision Needed:** Should the pricing engine incorporate an explicit tier multiplier for `features >= 5` (e.g., 1.25x for 5–6 features, 1.5x for 7+ features) or continue relying on human scoping on the discovery call?

## QA3-Q4: Brand Flow Setting (Item 10)
- **Question / Status Report:** Which `brand.flow` does the demo tenant use?
- **Report:** Per `tenants/demo/brand.yaml`, the source of truth is set to `flow: classic`. The environment variable `ENABLE_FAST_FLOW` is retained only as an override for automated test harnesses.

## Q3 (E5: Fast Flow)
- **Question:** Switch default to fast? Evidence: docs/FLOW_COMPARISON.md
- **Reason:** In fast flow, visitors reach an indicative estimate within 1 to 4 questions (Turn 2 for comprehensive openers like S1; Turn 5 for iterative discovery like S3/S7), compared to 2 to 7 questions in classic flow. The pricing engine calculations are 100% mathematically identical for the same brief scope. Further scoping fields (features, users, integrations, roles) are smoothly deferred to the "Sharpen this estimate" phase or inferred.
- **Proposal:** Keep default as "classic" until owner confirms. When ready, set `flow: "fast"` in `tenants/demo/brand.yaml` or per-tenant config.

## Q7 (Tax-Company Prototype)
Waiting for owner/Vishal tax specification: docs/TAX_TENANT_SPEC.md does not exist yet.

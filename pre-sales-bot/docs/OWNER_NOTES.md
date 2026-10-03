# Owner Notes — Nexus Pre-Sales Bot

## Behaviour Change (V9 Fix)

Behaviour change (V9): briefs that mention AI together with a mobile/web service now price with the ai_features multiplier (x1.22), so quotes rise about 22% and the timeline can move to 'complex'. Owner to confirm this is intended.

### Context
- Previously, the heuristic extractor did not extract the `ai_features` flag from free-text scope descriptions.
- As a result, requests like "iOS and Android app with AI chat" were priced as plain mobile apps without the AI multiplier ($29,500–$37,000, 14 weeks).
- With the V9 fix in `extractor.py`, AI capabilities mentioned alongside a mobile or web service are preserved as `brief.ai_features` (e.g. `["AI chat"]`), activating the `pricing.yaml` `flags.ai_features: 1.22` multiplier.
- The same request now prices at $36,000–$45,000, 22 weeks (complexity 1.32 × 1.22 = 1.6104 $\ge$ 1.55 $\rightarrow$ complex band).

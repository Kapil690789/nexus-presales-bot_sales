# Config (dummy data)

Every file is validated on boot. Edit YAML and restart (or rebuild on Cloud Run). Do not put API keys here.

| File | Controls |
|---|---|
| `agency.yaml` | Name, tone, disclaimer, NDA copy, never-say list |
| `brand.yaml` | Widget colors, launcher, labels |
| `services.yaml` | In-scope / out-of-scope work and approved stacks |
| `pages.yaml` | URL path → opening line and service track |
| `qualification.yaml` | Score weights, thresholds, book gate |
| `pricing.yaml` | Bases, multipliers, `low_side_factor`, team mix |
| `portfolio.yaml` | Case studies used for matching |
| `objections.yaml` | Trigger phrases and approved replies |
| `handoff.yaml` | Summary sections and stub notify targets |
| `enrichment.yaml` | Dummy CRM company directory by email domain |
| `prompts.yaml` | LLM persona and stage goals |

Public widget config only exposes brand + NDA + disclaimer. Pricing and scoring never leave the server.

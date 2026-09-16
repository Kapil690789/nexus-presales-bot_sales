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
| `prompts.yaml` | LLM persona, stage goals, lesson contract |
| `rag.yaml` | Retrieval depth, similarity floors, redaction, learning gate |

Public widget config only exposes brand + NDA + disclaimer. Pricing and scoring never leave the server.

## These files are the source of truth

The vector store is a **derived index** over this folder, not a replacement for it.
Pricing and qualification read these numbers directly, so they stay here. Edit the
YAML, then re-run `make ingest` (or hit **Re-index** in `/admin/rag`) to refresh the
index — unchanged documents are not re-embedded, and removed entries are pruned.

Long-form prose lives in [`../content/`](../content/) instead, and is indexed the same
way but read by nothing else. That folder is owned by the sales team; this one is owned
by engineers. The dividing line is that a number the product depends on only ever lives
here, so a content edit cannot move a price.

Two things are deliberately never indexed: the pricing `bases` and `multipliers`, and
the `never_say` list. Retrieved chunks are injected into the model prompt, and feeding
banned phrases back in is the fastest way to make the model say them.

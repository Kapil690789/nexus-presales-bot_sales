# The content library

This folder is the sales team's half of what the chatbot knows. Everything in here is
long-form prose: case studies, capability one-pagers, process explanations, trust
documents, FAQ answers, and approved quotes. You can edit it without touching code.

The other half lives in `../config/*.yaml` and is owned by engineering. That is where
prices, multipliers, qualification scoring, and the service catalogue live.

## The one hard rule

**Never put a price, a day rate, or a multiplier in this folder.**

The estimate the bot gives a visitor is calculated from `config/pricing.yaml`. If a
document in here says "typically starts around $30k" and the config says something
else, the bot has two contradictory sources for the same fact and will eventually
quote the wrong one. Describe *what is included* and *what drives cost up or down*
in words, and let the engine produce the number.

Everything else — outcomes, timelines you actually delivered, stacks, what you cut
from an MVP — belongs here and makes the bot noticeably better.

## How to add a document

1. Copy `_template.md` into the right folder and rename it. Use lowercase words
   separated by hyphens: `case-studies/acme-field-service.md`.
2. Fill in the front matter block at the top (the part between the `---` lines).
3. Write the body in Markdown. Use `## ` headings — each section is retrieved
   independently, so a good heading is what makes a section findable.
4. Validate it before you commit:
   ```bash
   make ingest-dry
   ```
   That reads every file, reports problems, and writes nothing. Fix anything printed
   as `ERROR`. Warnings are usually worth reading too — a `WARNING` about an unknown
   front matter key almost always means a typo.
5. Commit and open a pull request. The document is indexed on the next deploy, or
   immediately with `make ingest`.

## The folders

| Folder | What goes in it |
| --- | --- |
| `case-studies/` | One file per client engagement. The most valuable documents here. |
| `capabilities/` | One per service in `config/services.yaml`: what it includes and what it is not. |
| `process/` | How discovery, delivery, estimation, and change control actually work. |
| `trust/` | Security, data handling, confidentiality, IP ownership. |
| `faq/` | Real questions prospects ask, written as question headings. |
| `testimonials/` | Approved quotes, with the approval noted. |

The folder a file sits in tells the bot what kind of document it is, so you rarely
need to set `kind` yourself.

## Front matter fields

Only `title` is required. Everything else improves how well the document is matched
to the right conversation.

| Field | Why it matters |
| --- | --- |
| `title` | **Required.** Shown to the bot as the name of the source. |
| `service` | Must match a key in `config/services.yaml` (`mobile_app`, `web_app`, `ai_product`, `ui_ux`, `staff_augmentation`). Strongly boosts matching when the visitor wants that service. |
| `case_id` | For case studies, the matching `id` in `config/portfolio.yaml`. Links the narrative to the portfolio card so both rank together. |
| `industry` | e.g. `marketplace`, `fintech`, `health`. Matched against what the visitor is building. |
| `platforms` | e.g. `[ios, android]`, `[web]`. |
| `stacks` | e.g. `[Flutter, Firebase]`. |
| `tags` | Free-form themes: `[marketplace, payments, two-sided]`. |
| `outcome` | One sentence on the measurable result. |
| `url` | Page on the marketing site, so the bot can offer to open it. |
| `status` | `published` (default) or `draft`. Draft files are validated but never shown to visitors. |
| `nda_only` | `true` keeps the document out of retrieval until the visitor accepts the confidentiality notice. Use it for anything naming a client who has not agreed to be named. |
| `updated` | The date you last reviewed it, as `YYYY-MM-DD`. |

Anything else you add is reported as an unknown key and ignored.

## Writing so the bot can use it

- **Lead with the substance.** A section that starts with the answer retrieves and
  reads better than one that builds up to it.
- **Use the words a prospect would use.** For FAQ files, make the heading the actual
  question: `## Can we start with just a prototype?` beats `## Prototypes`.
- **Keep sections self-contained.** Sections are retrieved on their own, so a section
  that only makes sense after reading the one above it will be quoted out of context.
- **Be specific and true.** "Cut first-draft time from three days to four hours" is
  useful. "Dramatically faster" is not, and the bot is instructed not to embellish.
- **Do not promise.** No guaranteed dates, no "100% satisfaction", no naming clients
  you cannot name. The bot has a filter for some of these phrases, but the filter is
  a backstop, not a substitute for judgement.
- **One document per subject.** A 30-page everything-doc retrieves badly. If a file
  is warned about for producing too many chunks, split it.

## Other formats

`.md` is preferred because it reviews cleanly in a pull request. `.pdf`, `.docx`, and
`.txt` also work as drop-ins, so you can commit what you already have. Those formats
carry no front matter, so the title and kind are inferred from the filename and
folder — meaning matching is weaker. Slide-deck PDFs in particular often extract as
unusable fragments; `make ingest-dry` warns when a file yields suspiciously little
text, and the fix is to rewrite it as Markdown.

## Rebranding this folder for another client

Each client gets their own deployment, so making this bot theirs is a two-folder job:
replace `../config/*.yaml` with their brand, services, pricing, and portfolio, then
replace everything under `content/` with their material. Delete the sample documents
rather than editing around them — a leftover case study from another company is worse
than a thin library. Then run `make ingest-dry` to confirm the library is clean, and
deploy. No client name is baked into any code.

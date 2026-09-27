# Pre-sales consultant

White-label pre-sales chat, deployed on its own. The older app in `../chat-bot` is a separate service and is not imported here.

One process serves every client. The embed script sends `data-tenant`. That slug selects the client's collection, screening questions, documents, and brand. Local port is **8010**.

## Run

```bash
cd pre-sales-bot
make install
make run
```

Open [http://localhost:8010/](http://localhost:8010/). Admin is [http://localhost:8010/admin](http://localhost:8010/admin) (HTTP Basic). Set `ADMIN_PASSWORD` in `.env` first.

```bash
make test
make ingest
make finetune TENANT=demo
make docker
```

Docker publishes the API on port 8010 and Postgres with pgvector on port 5433, so it does not collide with the other chatbot.

## Embed

```html
<script src="https://BOT_URL/widget/consultant.js"
        data-api="https://BOT_URL"
        data-tenant="acme"
        async></script>
```

Add the site origin to `CORS_ORIGINS`. An unknown `data-tenant` is rejected.

## How a message is answered

1. Estimate slots still missing, and the visitor is answering one: store it and ask the next slot. A range is quoted only after service, goal, platforms, timeline, budget band, and decision role are known. Prices come from that client's `pricing.yaml`, never from documents.
2. Screening FAQ: the question is embedded, not the answer. A hit at or above `faq_min_score` (0.82) returns the stored answer and does not call the generator.
3. Otherwise the client's collection is searched. The grader shows a grounded answer only when the top score is at least 0.55 and, if a generator is configured, the snippets actually answer the question.
4. Below that, the assistant says it does not have a matching source, may add a clearly indicative range when the brief is complete, and asks the visitor to book a meeting. It does not quote chunks the grader withheld.
5. Thumbs-up, and a completed booking, store query-to-chunk pairs. `make finetune TENANT=acme` trains `BAAI/bge-small-en-v1.5` with MultipleNegativesRankingLoss once that client has 64 positive pairs, then re-embeds only that collection. That job needs `pip install 'sentence-transformers>=3.3.0'` on a machine that can hold PyTorch. Vercel does not install it: the wheel is several gigabytes and exceeds the function size limit. Search there uses the built-in hash embedder.

Follow-up questions that use words like "that" are rewritten with the recent summary and the previous visitor message before search.

## Layout

| Path | Role |
| --- | --- |
| `.env` | The only environment file |
| `config/platform.yaml` | Chunk size, overlap, score floors, fine-tune gate |
| `tenants/<slug>/` | Brand, FAQs, pricing, portfolio, objections, `content/` |
| `models/<slug>/` | Fine-tuned embedder, created by the fine-tune job |

Documents in `content/` may be Markdown, PDF, DOCX, or TXT. `nda_only: true` in front matter hides a file until the visitor accepts that client's notice. `status: draft` skips a file.

## What you need to fill in

Copy secrets into `pre-sales-bot/.env` only:

- `LLM_API_KEY` if you want generated wording. Provider stays `gemini`. Empty key still answers from retrieved notes.
- `DATABASE_URL` when you want Postgres. Leave the SQLite default for local development. RAG then uses in-process cosine until pgvector is available.
- `ADMIN_PASSWORD`
- `CORS_ORIGINS` for each site that embeds the widget
- `PUBLIC_BASE_URL` after the bot has a public URL

Per client, add a folder or use Admin → New client, then:

- Screening FAQ pairs in `faqs.yaml`
- Case studies, projects, and testimonials under `content/`, with no prices in those files
- Google OAuth client id and secret in `.env`, then connect that client's calendar at `/admin/google/start?tenant=<slug>`
- Optional Slack webhook on the tenant if booking alerts should post

The `demo` tenant ships with sample Northline material so the service can be tried immediately.

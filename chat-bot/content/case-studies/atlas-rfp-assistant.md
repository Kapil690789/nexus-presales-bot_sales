---
title: Atlas — RFP assistant for a consultancy
case_id: atlas-ai
service: ai_product
industry: professional_services
platforms: [web]
stacks: [Python, RAG, pgvector]
tags: [ai, documents, rag, search, citations]
outcome: Cut first-draft response time from 3 days to 4 hours on a 12,000-page corpus.
url: /work/atlas.html
status: published
nda_only: false
updated: 2026-02-04
---

## The problem

A consultancy answered roughly 200 RFPs a year. Every response reused material from
past bids, but that material lived in 12,000 pages of previous submissions, and finding
the right paragraph meant asking the one partner who remembered which bid it was in.
A first draft took three days, most of it spent searching rather than writing.

They asked for "an AI that writes our RFP responses". That is not the product we built,
because a system that writes unsupervised produces confident text that a bid team then
has to fact-check line by line — which is slower than writing it.

## What we shipped

An assistant that drafts with its sources attached:

- The bid team uploads the RFP. Atlas splits it into individual questions.
- For each question it retrieves the most relevant passages from the past-bid corpus
  and drafts an answer grounded in them.
- Every sentence in the draft carries a citation to the source passage, and the source
  panel sits next to the editor so a reviewer can check a claim in one click.
- Where nothing relevant exists in the corpus, it says so rather than inventing an
  answer. That was the single most important behaviour in the product.
- Approved responses are fed back into the corpus, so the library improves with use.

## The stack and why

Python and FastAPI for the backend, Next.js for the editor, PostgreSQL with pgvector
for the embeddings. pgvector rather than a dedicated vector database because the corpus
is tens of thousands of chunks, not tens of millions, and keeping the vectors in the
same database as the documents and permissions removed an entire class of consistency
problem.

Retrieval combined vector similarity with metadata filters on client, sector, and bid
date, because recency matters enormously in this domain — a compliance answer from four
years ago is a liability, not a resource.

## What we cut from the MVP

- **Automatic submission formatting.** Their template was a Word document with strict
  styling; export as clean text and let a human paste was correct for v1.
- **Multi-language support.** English bids only, which was 90% of volume.
- **Fine-tuning a model on their writing.** Retrieval with citations solved the actual
  problem. Fine-tuning would have added cost and made the sourcing harder to trace.
- **Win-probability scoring.** Interesting, unvalidated, and a distraction.

## The outcome

First-draft time went from three days to about four hours. The subtler win was that
juniors could produce a defensible first draft without a partner's recall, which moved
the partner's time from searching to reviewing. Adoption was near-total within a month,
which we attribute mostly to the citation panel: the team trusted it because they could
check it.

## The quote

"It does not tell us what we want to hear. When we have never answered something, it
says we have never answered it. That is why we use it." — Bid Director

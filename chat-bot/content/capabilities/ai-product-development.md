---
title: AI product development
service: ai_product
platforms: [web, api, embedded]
stacks: [Python + FastAPI, Next.js, pgvector]
tags: [ai, rag, assistants, documents, agents, evaluation, guardrails]
summary: Assistants, retrieval over your documents, document intelligence, and agent workflows.
url: /ai-development
status: published
nda_only: false
updated: 2026-02-12
---

## What this covers

Products where a language model does real work: assistants grounded in your own
documents, document intelligence and extraction, classification and routing, and agent
workflows that take actions in your systems. Usually a web product or an API, sometimes
a component embedded in something you already run.

## How we approach it

The starting question is not which model. It is what job the system does, and how you
will know whether it did the job well. Almost every AI project that disappoints does so
because that second question was never answered, so the team could not tell an
improvement from a regression.

We work in this order:

1. **Name the job precisely.** "Answer questions about our policies with a citation" is
   a buildable product. "An AI for our knowledge base" is not yet.
2. **Look at the data before promising anything.** Retrieval quality is set by the
   corpus far more than by the model. Scanned PDFs, inconsistent structure, and
   contradictory documents are the usual reality and they are addressable, but only
   when they are known about in week one.
3. **Build an evaluation set early.** A few dozen real questions with agreed good
   answers. It is unglamorous and it is what makes the rest of the project measurable.
4. **Ground and cite.** Retrieval with visible sources, so a user can verify a claim.
   Adoption tracks trust, and trust tracks being able to check the work.
5. **Design the failure case.** What the system does when it does not know. Saying so
   is a feature; a confident wrong answer costs you the user's trust permanently.

## The stacks we work in

Python and FastAPI for the backend, Next.js for the interface. PostgreSQL with pgvector
for retrieval up to the low millions of chunks, which covers most document corpora and
avoids running a second database; dedicated vector stores when scale genuinely calls for
one.

We stay model-agnostic — OpenAI, Anthropic, and Gemini all appear in work we have
shipped — and keep the provider behind an interface, because the price and capability
ranking has changed repeatedly and will change again.

## What a first release usually looks like

One workflow, one user group, grounded in a defined corpus, with citations and an
evaluation set that runs on every change. Human review kept in the loop where an error
has consequences.

Usually deferred: fine-tuning, multi-language, autonomous multi-step agents, and a
chat interface over everything at once.

## What this is not

- We do not train foundation models.
- We do not promise an accuracy percentage before seeing your data. Anyone who does is
  guessing.
- We do not build systems that take irreversible actions without human review, in the
  first release. Earn that with a track record and an audit trail.
- We do not put an assistant in front of a corpus nobody has read. If the source
  material is wrong or contradictory, retrieval surfaces that faster than anything else
  you could build.

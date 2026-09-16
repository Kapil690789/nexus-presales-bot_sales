---
title: Ledgerly — multi-entity finance ops console
case_id: ledger-web
service: web_app
industry: fintech
platforms: [web]
stacks: [Next.js, PostgreSQL]
tags: [saas, admin, auth, internal-tools, permissions]
outcome: Replaced three spreadsheets with a role-based ops console for 40 accountants.
url: /work/ledgerly.html
status: published
nda_only: false
updated: 2026-01-28
---

## The problem

Ledgerly's accounting team ran month-end close for 14 legal entities out of three
shared spreadsheets and a folder of bank exports. It worked, in the sense that the
numbers came out right, but it took nine days and depended on two people knowing which
tab was authoritative. There was no audit trail, and anyone with the link could edit
anything.

The trigger was an external audit finding: no segregation of duties. They needed a
system where the person who entered a transaction could not also approve it.

## What we shipped

A web console for the finance team, not a customer-facing product:

- Entity-scoped ledgers, so an accountant assigned to three entities sees only those.
- Four roles — preparer, reviewer, approver, and read-only auditor — with the
  approval chain enforced by the data model rather than by convention.
- Bank statement import with reconciliation suggestions, which the preparer accepts
  or overrides. Every override is recorded with who and why.
- An immutable audit log on every state change, exportable for the auditors.
- A close dashboard showing what is outstanding per entity, which replaced the
  standing status meeting.

## The stack and why

Next.js and PostgreSQL. This was a permissions and data-integrity problem far more than
an interface problem, so the interesting work went into the schema: row-level scoping by
entity, append-only history tables, and constraints that make an invalid approval state
impossible to write rather than merely unlikely.

We used their existing single sign-on provider for authentication. Building our own
user management would have added scope and made the audit finding harder to close, not
easier.

## What we cut from the MVP

- **Automated bank feeds.** Statement upload shipped first; live feeds came later once
  the reconciliation logic had proven itself against real files.
- **Custom report builder.** We shipped the four reports the team actually ran every
  month, and an export, rather than a builder nobody had time to learn.
- **Mobile app.** Nobody closes the books on a phone.
- **Forecasting.** Genuinely valuable, genuinely a separate product.

## The outcome

Forty accountants moved onto the console over two months. Close went from nine days to
four. The audit finding was closed at the next review, which was the actual point of
the project — the four days were the bonus.

## The quote

"The spreadsheets were never the problem. Not knowing who changed what was the problem,
and that is what this fixed." — Financial Controller, Ledgerly

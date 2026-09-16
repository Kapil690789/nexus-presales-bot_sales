---
title: Security and data handling
tags: [security, data, gdpr, hipaa, compliance, access, hosting, encryption]
summary: How we handle your data and your systems during and after an engagement.
status: published
nda_only: false
updated: 2026-02-09
---

## Where your data and code live

In your accounts. Repositories, cloud infrastructure, and databases are created under
your organisation wherever possible, and we work inside them with access you grant and
can revoke. When a project starts in our environment because yours is not ready, moving
it is part of the plan from the beginning rather than a migration at the end.

You own the code and the data throughout. Nothing is held back pending final payment,
and there is no dependency on a platform of ours to keep the product running.

## Access

- Named individual accounts. No shared logins and no shared credentials.
- Least privilege: engineers get the access the work requires, and production access is
  limited to the people who need it, when they need it.
- Multi-factor authentication on every account that touches your systems.
- Access is reviewed when someone joins or leaves the project team, and we tell you when
  the team changes.
- On completion, we hand over and ask you to revoke our access. If you forget, we chase
  you about it.

## Production data

We work with synthetic or anonymised data by default. Where real data is genuinely
required — reconciliation logic and document extraction are the common cases — we agree
the handling in writing first: what subset, where it lives, who can see it, and when it
is deleted.

Production data does not go on laptops, into shared drives, or into a third-party tool
that has not been agreed with you.

## In the software we build

Standard practice, not an upsell:

- Encryption in transit, and at rest for anything sensitive.
- Secrets in a managed secret store, never in the repository.
- Authentication through an established provider rather than hand-rolled.
- Authorisation enforced server-side on every request, not in the interface.
- Dependency scanning in the build, and dependencies kept current during the engagement.
- No personal or clinical data in logs or analytics.
- Audit trails wherever someone will eventually need to prove who changed what.

## Compliance regimes

We have delivered under HIPAA and under GDPR. The approach that works is to treat the
constraints as design inputs in week one — data flow mapped and reviewed with your
compliance owner before the integration is built — rather than as a hardening phase
before launch. Retrofitting compliance is substantially more expensive than designing
for it, and sometimes means rebuilding the data model.

What we do not do is certify anything ourselves. Formal audits, penetration tests, and
compliance certification are performed by specialist third parties, and they are excluded
from our estimates. We scope and fix against their findings, and on Riverview that is
exactly how it ran: their security team tested, we remediated.

## AI and third-party services

Where a product uses a language model or any external service, what is sent to it is
explicit and agreed. We use providers' API tiers with training on submitted data
disabled, we do not send data to a service that has not been agreed with you, and where
the data is sensitive enough to warrant it we design so identifying details never leave
your environment.

## This chatbot

Worth stating, since you are talking to one. This conversation is stored so a strategist
can pick up where you left off, and transcripts may be used to improve how the assistant
handles similar conversations — with identifying details stripped out first. Documents you
upload are used to understand your requirements and are not shared outside our team. The
figures the assistant gives are indicative and are not a contractual quote. Ask for the
conversation to be deleted and it will be.

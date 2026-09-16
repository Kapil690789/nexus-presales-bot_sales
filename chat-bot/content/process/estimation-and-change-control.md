---
title: Estimation and change control
tags: [process, estimation, scope, change-control, budget, fixed-price, contingency]
summary: How we estimate, why early figures are ranges, and what happens when scope changes mid-project.
status: published
nda_only: false
updated: 2026-02-12
---

## Why an early figure is a range

An estimate given before discovery is a statement about uncertainty, not about price. At
first contact we know the service, roughly the platforms, and roughly the integrations.
We do not yet know your authentication constraints, the state of the data you want to
migrate, how many stakeholders have to approve a screen, or which of your integrations
has undocumented behaviour.

So we give a range and label it indicative. The alternative — a single confident number
early — is worse for you, not better: it is either padded to cover what we cannot see,
or it is optimistic and becomes a change request in month two. The range narrows to a
firm commercial proposal at the end of discovery, when the unknowns have been closed.

## What drives an estimate up or down

In roughly the order they matter:

- **Number of platforms.** Two mobile platforms is more than one, though far less than
  double if the product is cross-platform.
- **Integrations.** Each external system is scope, and the cost is dominated by how well
  documented and how stable it is rather than by how many endpoints it has. One
  undocumented legacy system can outweigh three modern APIs.
- **Roles and permissions.** One user type is straightforward. Four, with an approval
  chain between them, changes the data model and every screen that touches it.
- **Real-time behaviour.** Live updates, presence, and collaborative editing are a
  different class of problem from request-and-response.
- **Two-sided or marketplace mechanics.** Two audiences means two products that have to
  work with each other, plus payments between them.
- **AI features.** Retrieval quality, evaluation, and guardrails are real work, and the
  state of your source documents drives it more than the model choice does.
- **Compliance regimes.** HIPAA, PCI, or similar constraints are design inputs from week
  one, not a hardening phase at the end. Cheaper handled that way, but not free.
- **Data migration.** Frequently the largest single surprise in a project, and impossible
  to estimate honestly before seeing the data.

What does *not* move the number much: the visual polish of the interface, the number of
screens, and the framework.

## What is in the number, and what is not

The estimate covers the discovery workshop, design for the agreed release, engineering,
QA on your primary devices or browsers, and the weekly delivery cadence with a named
lead. The exclusions are listed explicitly alongside every estimate — third-party
subscription fees, formal security audits and penetration tests, post-launch retainers,
and integrations discovered after scope is agreed are the usual ones.

We list exclusions in writing because an unwritten exclusion becomes an assumed
inclusion, and that assumption always surfaces at the worst moment.

## When the budget is smaller than the range

This is a normal conversation and it has a good answer, which is not a discount.

Discounting the same scope means either the price was wrong or the team gets thinner, and
you would find out which one during delivery. Instead we cut scope to fit the budget:
one platform instead of two, one user journey instead of three, manual steps where
automation can wait, an admin process run out of the database until volume justifies a
screen. You get a smaller product that works properly, rather than the whole product
built thinly.

Almost every case study in our portfolio is an example. Harvest cut messaging, logistics,
invoicing, and ratings from the first release. Ledgerly cut automated bank feeds and the
report builder. Riverview cut care-team messaging, which would have doubled the project
without moving the metric they cared about.

If the budget is far enough below the range that no useful version fits, we say so at the
first conversation rather than after a proposal.

## When the date is fixed

Same principle, different axis. If a launch has to hit an event, a funding milestone, or
a regulatory deadline, we shrink the first release to fit the date rather than promise the
full scope sooner. Adding people to hit a date makes it later, for reasons that are well
documented and that we have watched happen.

## Fixed price

We can work to a fixed commercial once discovery is complete and scope is locked, and a
lot of clients want that. What we will not do is fix a price before discovery: pricing a
scope nobody has examined means pricing the risk, which makes it expensive, and then
every clarification becomes a contractual argument instead of a conversation.

Discovery is deliberately a small, fixed-price phase precisely so you can buy certainty
about the big number without committing to the big number first.

## Change control

Scope changes during delivery. That is normal and the process is designed for it rather
than against it.

- **Anything material gets written down** with its impact on scope, timeline, and cost,
  before work starts on it.
- **Small trades are free and encouraged.** Swapping something of similar size out of the
  release for something you have learned matters more needs a conversation with the
  delivery lead, not paperwork. This happens constantly and it is the point of working
  iteratively.
- **Additions are a decision, not an argument.** New scope either replaces something in
  the release, extends the timeline, or extends the budget. We put the three options in
  front of you and you pick. What we do not do is silently absorb it and let the date
  slip, which is where trust actually gets lost.
- **Discoveries are shared immediately.** When we find that an integration behaves
  differently than documented, you hear it in that week's update with the options, not
  when the invoice changes.

## Why we are direct about all of this

The failure mode in this industry is a proposal that says yes to everything and a project
that then discovers what the yes cost. We would rather have the uncomfortable
conversation at the first estimate. It occasionally loses us work at the proposal stage,
which is a better outcome for both sides than losing it in month four.

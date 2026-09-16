---
title: Northstar — B2B onboarding redesign
case_id: northstar-ux
service: ui_ux
industry: b2b
platforms: [web]
stacks: [Figma]
tags: [saas, onboarding, activation, research, design-system]
outcome: Redesigned activation; trial-to-paid conversion +22%.
url: /work/northstar.html
status: published
nda_only: false
updated: 2026-02-06
---

## The problem

Northstar sold a B2B analytics product with healthy trial sign-ups and poor conversion.
Their read was that the product needed more features to justify the price. The data said
something different: 60% of trials never connected a data source, and a trial that never
connected a source had essentially no chance of converting.

So the problem was not the product's ceiling. It was the first fifteen minutes.

## What we did

Design engagement, no engineering from us — their team built it:

- Watched eleven trial users attempt setup, unprompted, on a call. Nine of them stalled
  at the same step, where the product asked for database credentials with no explanation
  of what it would do with them.
- Mapped every step between sign-up and first chart, and counted how many required
  something the user did not have to hand. It was four.
- Redesigned the path around a sample dataset, so a new user reaches a real chart before
  being asked for any credential at all.
- Rebuilt the credential step to say what it accesses, what it does not, and to offer a
  read-only role script for the user's DBA — because the actual blocker was often that
  the trial user was not the person who owned the database.
- Delivered high-fidelity flows, a component set that matched their existing code, and
  a prioritised list of what to build in what order.
- Ran a five-user validation pass on the prototype before their team wrote any code.

## What we cut

- **A full design-system rebuild.** Tempting, adjacent, and not what was broken. We
  extended the components they had.
- **Redesigning the main dashboard.** Users who got that far were converting fine.
- **A guided product tour.** Tours mostly paper over a flow that asks for the wrong
  thing at the wrong time. We fixed the flow.

## The outcome

Their team shipped the redesigned path over six weeks. Trial-to-paid conversion improved
22% over the following quarter. Source-connection rate — the metric we actually
designed against — went from 40% to 71%, which is the number we would point to as the
result.

## Why this is a design case study, not an engineering one

Northstar is the clearest example in our portfolio of a project that would have gone
badly as a build engagement. If they had asked us to build features, we could have built
good ones, and conversion would not have moved. The engagement that helped was two
researchers and a designer for six weeks, and then getting out of the way.

## The quote

"We asked for a redesign and got told our onboarding asked for a database password
before it had earned one. Nobody internally had said it that bluntly." — VP Product,
Northstar

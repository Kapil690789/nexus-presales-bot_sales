---
title: How we run discovery
tags: [process, discovery, workshop, scoping, kickoff, requirements]
summary: The first phase of every engagement — what happens, what you get, and what it decides.
status: published
nda_only: false
updated: 2026-02-08
---

## What discovery is for

Discovery exists to answer three questions before anyone writes production code: who is
the first user, what is the smallest version that is genuinely useful to them, and what
could make this project go wrong. Every engagement starts with it, including engagements
where the client arrives with a finished specification — often especially those, because
a detailed spec tends to describe the finished product rather than the first release.

It is a fixed, short phase. The output is a scope both sides have signed up to, not a
document that gets filed.

## What happens

**A workshop, usually two to three sessions.** Your stakeholders and our delivery lead,
designer, and technical lead. We map the users, the journeys, and the systems the product
has to touch. The most productive part is usually disagreement between your own
stakeholders surfacing in the room, which is much better than surfacing in week ten.

**A technical review.** What exists today, what the product must integrate with, what
constraints are non-negotiable — a compliance regime, an existing authentication
provider, a database that cannot be modified. This is where we find the work that
estimates usually miss.

**Prioritisation.** Everything on the table gets sorted into the first release, the next
one, and the list of things we agree not to build. The third list is the important one
and we insist on writing it down, because an unwritten exclusion becomes an assumed
inclusion.

**A technical recommendation.** Stack, architecture, and the reasoning. We recommend
after discovery rather than before, and who maintains the product in two years weighs
more heavily than any framework comparison.

## What you get at the end

- A scope document: the first release, named exclusions, and the assumptions the plan
  rests on.
- A recommended architecture and stack, with the reasoning written down.
- A delivery plan with the phases and the shape of the team.
- A firm commercial proposal, replacing the indicative range from earlier conversations.
- The risks we know about, and what we would do about each.

## What discovery decides that people expect it to decide later

- Whether we are the right fit at all. It occasionally concludes that the project does
  not need us, or does not need building yet. That is a good outcome for both sides and
  cheaper than the alternative.
- What "done" means for the first release, in terms specific enough to disagree with.
- Who on your side can make a decision. Projects stall on ambiguous ownership more often
  than on technical difficulty.

## Who needs to be in the room

Whoever can decide what is in and what is out. Discovery with people who have to check
every decision with someone absent takes twice as long and produces a weaker scope. We
would rather have three people with authority than nine without it. If a compliance,
security, or data owner will need to approve the approach, they belong in the technical
review session rather than at the end.

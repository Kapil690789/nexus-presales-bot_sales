---
title: Delivery model and cadence
tags: [process, delivery, sprints, cadence, qa, handover, communication]
summary: How work runs week to week once discovery is done, and what handover includes.
status: published
nda_only: false
updated: 2026-02-08
---

## The shape of a week

Two-week iterations with a demo of working software at the end of each. Weekly written
update in between. Your team has direct access to the people building the product —
a shared channel, not a ticket queue through an account manager.

The demo is always running software in a live environment. Not a slide deck, not a
recorded video, not a design file. If something is not demonstrable at the end of an
iteration, we say that and say why, which is the most useful signal a project produces.

## Who you work with

Every engagement has a named delivery lead who is your single point of contact and stays
for the life of the project. The rest of the team varies by service — design and mobile
engineering for an app, solutions architecture and AI engineering for an assistant, and
so on — and the specific composition comes with the proposal.

The people you meet are the people who do the work. Nobody is swapped out mid-project
without your agreement.

## What you have access to

- The repository, from day one. It is yours.
- The live staging environment, continuously deployed.
- The task board, with the current iteration and the backlog.
- The delivery lead, directly.

We would rather you see work in progress than a polished version at the end. Projects go
wrong quietly, and visibility is what makes the problem cheap to fix.

## Quality

Automated tests on the logic that matters, code review on every change, and QA on the
devices and browsers your users actually have — established in discovery, not assumed.
Continuous deployment to staging so nothing is integrated for the first time in the
final week.

We do not treat testing as a phase at the end. A test phase after a build phase is how
you discover in week fourteen that two features were built on incompatible assumptions.

## Timelines, and what we will and will not say about them

The plan from discovery has phases and target dates, and we hold ourselves to them. What
we avoid is promising an immovable launch date at the point of first contact, before
scope is agreed — an early date given to be agreeable is the most common way a project
starts badly.

When something slips, you hear it in the next update with the reason and the options,
not at the deadline. Dependencies on your side — an API credential, a review, a decision
— are tracked in the same place as ours, because they slip projects just as often.

## Handover

Whatever the engagement, you end up able to run the product without us:

- Source code and infrastructure in your accounts, under your ownership.
- Deployment and environment documentation, and a walkthrough of the architecture.
- A working local setup any competent engineer can follow.
- A support window after launch for defects in what we built.

Ongoing feature work after launch is a separate retainer. We say so up front rather than
letting the assumption ride, and plenty of clients take over entirely — Riverview's team
had the codebase four weeks after launch, which was the plan from the start.

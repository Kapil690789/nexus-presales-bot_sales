---
title: Harvest — farm-to-buyer marketplace
case_id: harvest-mobile
service: mobile_app
industry: marketplace
platforms: [ios, android]
stacks: [Flutter, Firebase]
tags: [marketplace, mobile, payments, two-sided]
outcome: Launched a two-sided MVP in 16 weeks; first 1,200 listings in 90 days.
url: /work/harvest.html
status: published
nda_only: false
updated: 2026-02-11
---

## The problem

Harvest wanted to connect small growers directly with restaurant buyers. The trade was
happening already, over phone calls and WhatsApp photos, and both sides were losing
time to it: growers could not show what they had available today, and buyers could not
compare two suppliers without ringing both.

The founders arrived with a spec for a full platform — grower profiles, buyer teams,
messaging, logistics scheduling, invoicing, and a ratings system. Building all of it
before finding out whether growers would keep their listings current would have been
the expensive way to learn.

## What we shipped

A single mobile app with two roles, built on one codebase for iOS and Android:

- Growers post what is available this week, with a photo, quantity, and unit price.
- Buyers browse by produce type and distance, and place an order against a listing.
- Payment is captured on order and released to the grower on confirmed delivery.
- Both sides get push notifications on the four events that actually matter: new
  listing in a followed category, order placed, order confirmed, payment released.

## The stack and why

Flutter, because the two audiences needed the same app on both platforms and the
interface was list-and-form heavy rather than anything platform-specific. One codebase
was the difference between shipping both platforms in the first release and shipping
one.

Firebase for authentication, data, and push. A marketplace at launch has unpredictable
read patterns and near-zero write volume, and the team had no interest in running
infrastructure. Stripe Connect handled the split payment and the grower payouts, which
is a genuinely hard problem to build and a solved problem to integrate.

## What we cut from the MVP

Named explicitly at the end of discovery, so nobody was surprised later:

- **In-app messaging.** Both sides already had each other's numbers. We linked out.
- **Logistics and delivery scheduling.** The first cohort was all within one metro
  area and arranged collection themselves.
- **Invoicing and accounting export.** Deferred until buyers asked, which they did in
  month four, and it was the second release.
- **Ratings and reviews.** A ratings system with forty users tells nobody anything.
- **Web app for buyers.** Added later once desktop ordering demand was proven.

## The outcome

The MVP went live 16 weeks after kickoff. 1,200 listings went up in the first 90 days
across 60 growers. The thing the founders learned — which no amount of specification
would have told them — was that growers updated listings reliably in the morning and
never in the afternoon, so the buyer experience had to lead with freshness of the
listing rather than the catalogue. That reshaped the second release.

## The quote

"We came in with a twenty-page spec and left discovery with a five-page one. The five
pages were the right ones." — Head of Product, Harvest

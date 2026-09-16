---
title: Web application development
service: web_app
platforms: [web]
stacks: [Next.js, React, Vue]
tags: [saas, web, dashboard, internal-tools, admin, permissions]
summary: Custom SaaS, dashboards, and operational web products.
url: /web-app-development
status: published
nda_only: false
updated: 2026-02-10
---

## What this covers

Custom web products: customer-facing SaaS, internal operations consoles, dashboards, and
admin tooling. The kind of software where the value is in the data model and the
permissions rather than in the visual surface.

## The stacks we work in

- **Next.js** — our default. Server rendering where it helps, one language across the
  stack, and a hiring pool your team can recruit from later.
- **React** as a single-page app when the product sits behind a login and there is no
  public-facing content to render.
- **Vue** when your team already works in it.

Backends are Node.js or Python FastAPI with PostgreSQL. We reach for PostgreSQL by
default: relational constraints are what stop an operations product from accumulating
invalid states, and most products described as "needing NoSQL" turn out to need a
schema.

## What a first release usually looks like

The core object model, authentication, roles, and the two or three workflows that
represent the actual job. For internal tools that generally means one team's work
end-to-end rather than a thin slice of every team's.

Where the real complexity in these projects lives, and where we spend design time
early: role and permission modelling, audit trails where somebody will eventually need
to prove who changed what, and how data gets in from wherever it lives today —
imports, integrations, or migration from a spreadsheet.

Usually deferred: custom report builders (ship the reports people actually run, plus an
export), configurable workflow engines, white-labelling, and a public API before anyone
has asked to integrate.

## What we include

Discovery and scoping, product design, engineering, QA across the browsers your users
have, deployment into your cloud account, and handover documentation. Weekly demos on
a live environment.

## What this is not

- We do not build brochure or marketing websites, landing pages, or content sites.
- We do not do Shopify, WordPress, or Webflow theme work.
- We do not take over an unfamiliar codebase without a paid technical review first.
- Data migration from legacy systems is scoped separately once we have seen the data.
  Estimating it blind is how projects go wrong, and it is frequently larger than the
  product work.

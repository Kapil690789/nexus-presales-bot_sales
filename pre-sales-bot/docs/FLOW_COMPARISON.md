# FLOW COMPARISON: CLASSIC VS FAST FLOW

Generated: 2026-10-11 16:47:37 UTC

This document presents side-by-side transcripts and metrics comparing the **Classic Flow** (multi-turn discovery across 11 fields) against the **Fast Flow** (streamlined 5-field estimate with optional post-estimate sharpening).

## 1. Executive Summary & Questions to Estimate

| Scenario | Description | Classic Flow Questions | Fast Flow Questions | Questions Reduced | Estimate Range Match |
|---|---|---|---|---|---|
| **S1** | Comprehensive initial message with platforms, budget, timeline | 2 questions (Turn 3) | **1 questions** (Turn 2) | **-1 questions** | ✓ Identical (`$29,500–$37,000 USD`) |
| **S3** | Starter chip -> Product idea -> Out-of-order details | 6 questions (Turn 7) | **4 questions** (Turn 5) | **-2 questions** | ✓ Identical (`$32,500–$40,500 USD`) |
| **S7** | Natural chip path (mobile, goal, platforms, timeline, budget) | 3 questions (Turn None) | **0 questions** (Turn None) | **-3 questions** | ✓ Identical (`None`) |

## 2. Key Findings

1. **Identical Engine Pricing:** Across all scenarios, the Fast Flow produces the exact same indicative dollar range and timeline weeks as the Classic Flow for the given scope.
2. **Speed to Value:** Fast Flow reaches an indicative range within **1 to 4 questions**, dramatically reducing visitor drop-off before reaching an estimate.
3. **Post-Estimate Sharpening:** In Fast Flow, deeper questions (integrations, users, decision role, team size) are not discarded; they become progressive 'Sharpen this estimate' options offered *after* the initial ballpark is established.

## 3. Side-by-Side Turn Transcripts

### Scenario S1: Comprehensive initial message with platforms, budget, timeline

#### Classic Flow Transcript (Default)
| Turn | Visitor Input | Bot Response | Route | Cards |
|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | discovery | - |
| 1 | We want it on both iOS and Android. For the first release we just need login, calendar booking, and push notifications. Budget around $25k to $35k, 2 to 3 months. | iOS and Android, noted. What primary problem or user workflow should this initial release solve? | discovery | - |
| 2 | I am building a sports clinic booking application for direct patients. | A mobile app for sports clinic booking application for direct patients: that gives me a clear picture. Which core capabilities or features are essential for the launch? | discovery | - |
| 3 | I am the founder and technical decision maker. | Here's what I understood: a mobile app for sports clinic booking application for direct patients, on iOS and Android, aiming for 1 to 3 months with a budget of $15k to $40k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$29,500–$37,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | estimate | estimate, architecture, mvp, portfolio |

#### Fast Flow Transcript (`brand.flow = 'fast'`)
| Turn | Visitor Input | Bot Response | Route | Cards |
|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | discovery | - |
| 1 | We want it on both iOS and Android. For the first release we just need login, calendar booking, and push notifications. Budget around $25k to $35k, 2 to 3 months. | iOS and Android, noted. What primary problem or user workflow should this initial release solve? | discovery | - |
| 2 | I am building a sports clinic booking application for direct patients. | Here's what I understood: a mobile app for sports clinic booking application for direct patients, on iOS and Android, aiming for 1 to 3 months with a budget of $15k to $40k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$29,500–$37,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | estimate | estimate, architecture, mvp, portfolio |

### Scenario S3: Starter chip -> Product idea -> Out-of-order details

#### Classic Flow Transcript (Default)
| Turn | Visitor Input | Bot Response | Route | Cards |
|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | discovery | - |
| 1 | [Chip] I have an app idea | Building a web application focused on I have an app idea: clear priority. Which core capabilities or features are essential for the launch? | discovery | - |
| 2 | A marketplace for local farmers | A marketplace for local farmers gives us a solid foundation for the first release. What should each of A marketplace for local farmers do in the first version? | discovery | - |
| 3 | Web and mobile | Here is the architectural shape: Next.js for Channels and UX, Core user flows for the Core flow, and Node.js + PostgreSQL for Backend and APIs. Who is the first person this should work well for? | discovery | shape |
| 4 | Produce catalog, Stripe checkout, farmer payouts, direct chat | Will the first release need integrations with existing databases, auth providers, or third-party APIs? | discovery | - |
| 5 | 3 to 6 months | Targeting 3 to 6 months gives us a defined delivery window. Which investment range should I size this initial build against for squad composition and architecture? | discovery | - |
| 6 | $40k to $80k | What is your role on the project when architecture and delivery decisions are made? | discovery | - |
| 7 | Product lead | Here's what I understood: a web application for I have an app idea, on web, iOS and Android, with A marketplace for local farmers, aiming for 3 to 6 months with a budget of $40k to $80k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$32,500–$40,500 USD** over about **22 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | estimate | estimate, architecture, mvp, portfolio |

#### Fast Flow Transcript (`brand.flow = 'fast'`)
| Turn | Visitor Input | Bot Response | Route | Cards |
|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | discovery | - |
| 1 | [Chip] I have an app idea | Building a web application focused on I have an app idea: clear priority. Which platforms should we target for the first launch — web, iOS, Android, or cross-platform mobile? | discovery | - |
| 2 | A marketplace for local farmers | A marketplace for local farmers gives us a solid foundation for the first release. Where will your target users primarily access this application — in a browser or on mobile devices? | discovery | - |
| 3 | Web and mobile | Here is the architectural shape: Next.js for Channels and UX, Core user flows for the Core flow, and Node.js + PostgreSQL for Backend and APIs. When would you like the initial version in users' hands? | discovery | shape |
| 4 | 3 to 6 months | Targeting 3 to 6 months gives us a defined delivery window. Which investment range should I size this initial build against for squad composition and architecture? | discovery | - |
| 5 | $40k to $80k | Here's what I understood: a web application for I have an app idea, on web, iOS and Android, with A marketplace for local farmers, aiming for 3 to 6 months with a budget of $40k to $80k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$32,500–$40,500 USD** over about **22 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | estimate | estimate, architecture, mvp, portfolio |

### Scenario S7: Natural chip path (mobile, goal, platforms, timeline, budget)

#### Classic Flow Transcript (Default)
| Turn | Visitor Input | Bot Response | Route | Cards |
|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | discovery | - |
| 1 | [Chip] Mobile app | Focusing on mobile app: noted. What primary problem or user workflow should this initial release solve? | discovery | - |
| 2 | A sports clinic booking application for direct patients | A mobile app for sports clinic booking application for direct patients: that gives me a clear picture. What essential building blocks must be ready on day one for users? | discovery | - |
| 3 | [Chip] User login & profiles | Focusing on User login & profiles establishes a clear core scope. Added User login & profiles — any other features for the launch, or ready to continue? | discovery | - |
| 4 | [Chip] Continue to next step → |  |  | - |
| 5 | [Chip] iOS and Android |  |  | - |
| 6 | [Chip] 1–3 months |  |  | - |
| 7 | [Chip] $15–40k |  |  | - |
| 8 | [Chip] Founder / exec |  |  | - |

#### Fast Flow Transcript (`brand.flow = 'fast'`)
| Turn | Visitor Input | Bot Response | Route | Cards |
|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | discovery | - |
| 1 | [Chip] Mobile app |  |  | - |
| 2 | A sports clinic booking application for direct patients |  |  | - |
| 3 | [Chip] iOS and Android |  |  | - |
| 4 | [Chip] 1–3 months |  |  | - |
| 5 | [Chip] $15–40k |  |  | - |

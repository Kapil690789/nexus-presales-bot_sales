# DEMO TRANSCRIPTS & QA CHECKS (COMPLETE QA-2 + QA-3 + QA-4 VALIDATION)

Generated: 2026-10-12 13:32:45 UTC
Primary model configured: `gemini-3.8-flash` (thinkingLevel: `low`)

## Classic Flow: In-Process Deterministic Stub (Offline / Fallback)

### 1. QA Checks Summary Table (Complete QA-2 + QA-3 Validation)

| Scenario | Title | Opener | Max 2Sent/320c | No Placeholders | Platform Casing | No Mid-Word Cut | No Verbatim Repeat | Shape Card (S7) | Brief Match | Recap Exact | No Recap Reps | Objection Valid | No Guard Pre-Est | No Dup Bot | Est Once | Banned Strings | Latency & Calls | Turns to Est |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **S1** | Long comprehensive initia... | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 3 |
| **S2** | Starter chip 'I'm just ex... | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 8 |
| **S3** | Starter chip 'I have an a... | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 7 |
| **S4** | Seven-feature list in one... | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 4 |
| **S5** | Hinglish: 'mujhe ek deliv... | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 4 |
| **S6** | Post-estimate technical q... | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 6 |
| **S7** | Natural chip path: Mobile... | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 8 |
| **S8** | Out-of-order answers (the... | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 7 |
| **S9** | First message is only a b... | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 7 |
| **S10** | Starter 'I have an app id... | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 7 |

### 2. Scenario Latency & Call Statistics

| Scenario | Turns | Median (s) | p95 (s) | Max (s) | Max Calls/Turn | Pass/Fail |
|---|---|---|---|---|---|---|
| **S1** | 3 | 0.03s | 0.04s | 0.04s | 0 | ✓ PASS |
| **S2** | 8 | 0.02s | 0.03s | 0.03s | 0 | ✓ PASS |
| **S3** | 7 | 0.02s | 0.05s | 0.05s | 0 | ✓ PASS |
| **S4** | 5 | 0.02s | 0.02s | 0.02s | 0 | ✓ PASS |
| **S5** | 4 | 0.02s | 0.02s | 0.02s | 0 | ✓ PASS |
| **S6** | 11 | 0.02s | 1.13s | 1.13s | 0 | ✓ PASS |
| **S7** | 8 | 0.02s | 0.03s | 0.03s | 0 | ✓ PASS |
| **S8** | 7 | 0.02s | 0.02s | 0.02s | 0 | ✓ PASS |
| **S9** | 7 | 0.02s | 0.02s | 0.02s | 0 | ✓ PASS |
| **S10** | 7 | 0.02s | 0.02s | 0.02s | 0 | ✓ PASS |

### 3. Full Turn-by-Turn Transcripts & LLM Instrumentation

#### Scenario S1: Long comprehensive initial message with platforms, features, budget, and timeline

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 87.0 | 0 |
| 1 | We want it on both iOS and Android. For the first release we just need login, calendar booking, and push notifications. Budget around $25k to $35k, 2 to 3 months. | Channels and UX: Flutter. Core flow: login, calendar booking, push notifications. Backend and APIs: Node.js + PostgreSQL. What should this first version actually do for people? | Book appointments, Manage customers, Take payments | shape | discovery | 37.4 | 0 |
| 2 | I am building a sports clinic booking application for direct patients. | sports clinic booking application for direct patients: that gives me a clear picture. What audience is this initial release designed for — consumer users, business accounts, or your operations team? | Consumers, Business users, Internal team | - | discovery | 21.1 | 0 |
| 3 | I am the founder and technical decision maker. | Here's what I understood: a mobile app - sports clinic booking application for direct patients. Platforms: iOS and Android. Features: login, calendar booking, push notifications. Timeline: 1 to 3 months. Budget: around $25k to $35k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$32,000–$40,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 27.3 | 0 |

#### Scenario S2: Starter chip 'I'm just exploring costs'

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 15.1 | 0 |
| 1 | I'm just exploring costs | Happy to help you explore costs. What are you thinking of building: a mobile app, a web platform, AI, or design? | Mobile app, Web platform, AI product, UI/UX design | - | discovery | 20.5 | 0 |
| 2 | Mobile app | Targeting iOS and Android sets our technical architecture. What core business outcome or user experience should this first launch deliver? | Book appointments, Manage customers, Take payments | - | discovery | 27.2 | 0 |
| 3 | Field service and asset tracking | Focusing on Field service and asset tracking: clear priority. What essential building blocks must be ready on day one for users? | User login & profiles, In-app payments, Push notifications, Search & discovery, Not sure yet | - | discovery | 20.9 | 0 |
| 4 | iOS and Android | What essential building blocks or capabilities do you envision for the initial release? | User login & profiles, In-app payments, Push notifications, Search & discovery, Not sure yet, Not sure, suggest | - | discovery | 18.6 | 0 |
| 5 | Offline data collection, barcode scanning, GPS tracking | Channels and UX: Flutter. Core flow: Offline data collection, barcode scanning, GPS tracking. Backend and APIs: Node.js + PostgreSQL. Who is the first person this should work well for? | Consumers, Business users, Internal team | shape | discovery | 20.6 | 0 |
| 6 | 1 to 3 months | Working toward 1 to 3 months sets the development pace. Are there any external services or APIs this must connect with on day one, like payments or CRM? | None on day one, Payments, CRM | - | discovery | 21.0 | 0 |
| 7 | $40k to $80k | Are you leading this as founder, product manager, operations lead, or another role? | Founder / exec, Product or ops, Manager, Student / intern | - | discovery | 18.9 | 0 |
| 8 | Founder | Here's what I understood: a mobile app - Field service and asset tracking. Platforms: iOS and Android. Features: Offline data collection, barcode scanning, GPS tracking. Timeline: 1 to 3 months. Budget: $40k to $80k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$29,500–$37,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band is above this first-pass range, so there is room to add scope. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 21.7 | 0 |

#### Scenario S3: Starter chip 'I have an app idea' -> 'A marketplace for local farmers'

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 16.9 | 0 |
| 1 | I have an app idea | Tell me what your app does in a sentence or two — who is it for and what's the core workflow? | Mobile app, Web platform, AI product, UI/UX design | - | discovery | 19.4 | 0 |
| 2 | A marketplace for local farmers | Focusing on marketplace for local farmers: clear priority. What essential building blocks must be ready on day one for users? | User authentication, Payment checkout, Admin dashboard, Analytics & reports, Not sure yet | - | discovery | 52.1 | 0 |
| 3 | Web and mobile | Targeting web, iOS and Android sets our technical architecture. What essential building blocks must be ready on day one for users? | User login & profiles, In-app payments, Push notifications, Search & discovery, Not sure yet | - | discovery | 17.8 | 0 |
| 4 | Produce catalog, Stripe checkout, farmer payouts, direct chat | Channels and UX: Flutter. Core flow: Produce catalog, Stripe checkout, farmer payouts. Backend and APIs: Node.js + PostgreSQL. Who is the first person this should work well for? | Consumers, Business users, Internal team | shape | discovery | 22.3 | 0 |
| 5 | 3 to 6 months | Working toward 3 to 6 months sets the development pace. Are there any external services or APIs this must connect with on day one, like payments or CRM? | None on day one, Payments, CRM | - | discovery | 20.4 | 0 |
| 6 | $40k to $80k | What is your role on the project when architecture and delivery decisions are made? | Founder / exec, Product or ops, Manager, Student / intern | - | discovery | 22.7 | 0 |
| 7 | Product lead | Here's what I understood: a mobile app - marketplace for local farmers. Platforms: web, iOS and Android. Features: Produce catalog, Stripe checkout, farmer payouts, direct chat. Timeline: 3 to 6 months. Budget: $40k to $80k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$38,000–$47,500 USD** over about **22 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 18.1 | 0 |

#### Scenario S4: Seven-feature list in one message (triggers Scope Coach)

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 14.7 | 0 |
| 1 | I want a web app for clinic management. Features: patient booking, telemedicine video, prescriptions, billing, lab results, doctor scheduling, insurance verification. | Channels and UX: Next.js. Core flow: patient booking, telemedicine video, prescriptions. Backend and APIs: Node.js + PostgreSQL. Who is the first person this should work well for? | Consumers, Business users, Internal team | shape | discovery | 20.4 | 0 |
| 2 | Web application | Who do you picture using this first — end consumers, business clients, or your own team? | Consumers, Business users, Internal team, Not sure yet, Not sure, suggest | - | discovery | 18.8 | 0 |
| 3 | 1 to 3 months | Working toward 1 to 3 months sets the development pace. Will the first release need integrations with existing databases, auth providers, or third-party APIs? | None on day one, Payments, CRM | - | discovery | 20.2 | 0 |
| 4 | $40k to $80k | Here's what I understood: a web application - for clinic management. Platforms: web. Features: patient booking, telemedicine video, prescriptions, billing, and 3 more. Timeline: 1 to 3 months. Budget: $40k to $80k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$19,000–$24,000 USD** over about **8 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  This range assumes the Core scope; a list this long will likely need more, and the team can size it precisely. | Show the Core cut, Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 19.2 | 0 |
| 5 | Founder | Noted, I have updated your project brief. What would you like to explore next? | Book a call, See the MVP, See sample projects, Talk to a human | - | discovery | 21.6 | 0 |

#### Scenario S5: Hinglish: 'mujhe ek delivery app chahiye, iOS aur Android dono, 3 mahine me'

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 12.7 | 0 |
| 1 | mujhe ek delivery app chahiye, iOS aur Android dono, 3 mahine me | mujhe ek delivery app chahiye, iOS aur Android: that gives me a clear picture. What essential building blocks must be ready on day one for users? | User login & profiles, In-app payments, Push notifications, Search & discovery, Not sure yet | - | discovery | 19.1 | 0 |
| 2 | Live order tracking, customer ratings, driver assignment | Channels and UX: Flutter. Core flow: Live order tracking, customer ratings, driver assignment. Backend and APIs: Node.js + PostgreSQL. Who is the first person this should work well for? | Consumers, Business users, Internal team | shape | discovery | 19.3 | 0 |
| 3 | $15k to $40k | Will the first release need integrations with existing databases, auth providers, or third-party APIs? | None on day one, Payments, CRM | - | discovery | 17.7 | 0 |
| 4 | Founder | Here's what I understood: a mobile app - mujhe ek delivery app chahiye. Platforms: iOS and Android. Features: Live order tracking, customer ratings, driver assignment. Timeline: 1 to 3 months. Budget: $15k to $40k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$29,500–$37,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 18.0 | 0 |

#### Scenario S6: Post-estimate technical questions, calendar slot booking, and post-booking ack

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 13.6 | 0 |
| 1 | We need a cross-platform mobile app for iOS and Android. | iOS and Android, noted. What primary problem or user workflow should this initial release solve? | Book appointments, Manage customers, Take payments | - | discovery | 19.6 | 0 |
| 2 | Fitness coaching app with workout logger and push notifications. | Channels and UX: Flutter. Core flow: workout logger, push notifications. Backend and APIs: Node.js + PostgreSQL. Who is the first person this should work well for? | Consumers, Business users, Internal team | shape | discovery | 17.6 | 0 |
| 3 | Workout tracking, user profiles, video demonstrations | Will the first release need integrations with existing databases, auth providers, or third-party APIs? | None on day one, Payments, CRM | - | discovery | 21.7 | 0 |
| 4 | 1 to 3 months | Targeting 1 to 3 months gives us a defined delivery window. Which investment range should I size this initial build against for squad composition and architecture? | Still exploring, Under $15k, $15–40k, $40–80k, $80k+ | - | discovery | 21.0 | 0 |
| 5 | $15k to $40k | What is your role on the project when architecture and delivery decisions are made? | Founder / exec, Product or ops, Manager, Student / intern | - | discovery | 21.4 | 0 |
| 6 | Founder | Here's what I understood: a mobile app - Fitness coaching app. Platforms: iOS and Android. Features: workout logger, push notifications. Timeline: 1 to 3 months. Budget: $15k to $40k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$29,500–$37,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 25.9 | 0 |
| 7 | Do you use Flutter? | Our engineering team can go into detail on those specific technical requirements on a discovery call. | Book a meeting, See similar work | - | fallback | 26.5 | 0 |
| 8 | Which cloud do you use? | We can dive deeper into that architecture and technical setup during a quick discovery call. | Book a meeting, See similar work | - | fallback | 21.1 | 0 |
| 9 | Can you guarantee 4 weeks? | Our engineering team can go into detail on those specific technical requirements on a discovery call. | Book a meeting, See similar work | - | fallback | 18.8 | 0 |
| 10 | Friday Oct 16, 3:00 PM UTC | You're booked for Fri Oct 16, 20:30 IST — Demo booking: no calendar invite is sent until Google Calendar is connected. Reply with your work email so the invite has somewhere to go. | Can I reschedule?, See similar work | booking | booking | 1130.3 | 0 |
| 11 | cool thanks | You're all set for Fri Oct 16, 20:30 IST. The team will see this whole conversation, so you won't need to repeat anything. | What is on the agenda?, Can I reschedule the time? | - | ack | 20.8 | 0 |

#### Scenario S7: Natural chip path: Mobile app, goal text, feature chips, platform chip, timeline chip, budget chip, role chip

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 17.4 | 0 |
| 1 | Mobile app | mobile app, understood. What core business outcome or user experience should this first launch deliver? | Book appointments, Manage customers, Take payments | - | discovery | 26.3 | 0 |
| 2 | A sports clinic booking application for direct patients | Focusing on sports clinic booking application for direct patients: clear priority. What essential building blocks must be ready on day one for users? | User login & profiles, In-app payments, Push notifications, Search & discovery, Not sure yet | - | discovery | 25.5 | 0 |
| 3 | User login & profiles | User login & profiles gives us a solid foundation for the first release. Added User login & profiles — any other features for the launch, or ready to continue? | Continue to next step →, + User login & profiles, + In-app payments, + Push notifications, Ready with this list | - | discovery | 17.3 | 0 |
| 4 | Continue to next step → | What should each of User login & profiles do in the first version? | That's enough | - | discovery | 17.7 | 0 |
| 5 | iOS and Android | Channels and UX: Flutter. Core flow: User login & profiles. Backend and APIs: Node.js + PostgreSQL. Who is the first person this should work well for? | Consumers, Business users, Internal team | shape | discovery | 20.2 | 0 |
| 6 | 1–3 months | Working toward 1 to 3 months sets the development pace. Are there any external services or APIs this must connect with on day one, like payments or CRM? | None on day one, Payments, CRM | - | discovery | 17.5 | 0 |
| 7 | $15–40k | Are you leading this as founder, product manager, operations lead, or another role? | Founder / exec, Product or ops, Manager, Student / intern | - | discovery | 18.0 | 0 |
| 8 | Founder / exec | Here's what I understood: a mobile app - sports clinic booking application for direct patients. Platforms: iOS and Android. Features: User login & profiles. Timeline: 1 to 3 months. Budget: $15k to $40k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$32,000–$40,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 18.1 | 0 |

#### Scenario S8: Out-of-order answers (the old S3 script)

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 15.7 | 0 |
| 1 | I have an app idea | Tell me what your app does in a sentence or two — who is it for and what's the core workflow? | Mobile app, Web platform, AI product, UI/UX design | - | discovery | 18.6 | 0 |
| 2 | A marketplace for local farmers | marketplace for local farmers: that gives me a clear picture. What essential building blocks must be ready on day one for users? | User authentication, Payment checkout, Admin dashboard, Analytics & reports, Not sure yet | - | discovery | 19.2 | 0 |
| 3 | Web and mobile | web, iOS and Android, noted. Which core capabilities or features are essential for the launch? | User login & profiles, In-app payments, Push notifications, Search & discovery, Not sure yet | - | discovery | 16.4 | 0 |
| 4 | Produce catalog, Stripe checkout, farmer payouts, direct chat | Channels and UX: Flutter. Core flow: Produce catalog, Stripe checkout, farmer payouts. Backend and APIs: Node.js + PostgreSQL. Who is the first person this should work well for? | Consumers, Business users, Internal team | shape | discovery | 20.2 | 0 |
| 5 | 3 to 6 months | Working toward 3 to 6 months sets the development pace. Are there any external services or APIs this must connect with on day one, like payments or CRM? | None on day one, Payments, CRM | - | discovery | 17.1 | 0 |
| 6 | $40k to $80k | Are you leading this as founder, product manager, operations lead, or another role? | Founder / exec, Product or ops, Manager, Student / intern | - | discovery | 19.8 | 0 |
| 7 | Product lead | Here's what I understood: a mobile app - marketplace for local farmers. Platforms: web, iOS and Android. Features: Produce catalog, Stripe checkout, farmer payouts, direct chat. Timeline: 3 to 6 months. Budget: $40k to $80k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$38,000–$47,500 USD** over about **22 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 18.7 | 0 |

#### Scenario S9: First message is only a budget: 'my budget is $40k to $80k'

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 18.3 | 0 |
| 1 | my budget is $40k to $80k | What core business outcome or user experience should this first launch deliver? | Book appointments, Manage customers, Take payments | - | discovery | 20.4 | 0 |
| 2 | Mobile app | Targeting iOS and Android sets our technical architecture. What core business outcome or user experience should this first launch deliver? | Book appointments, Manage customers, Take payments | - | discovery | 17.1 | 0 |
| 3 | An on-demand tutor marketplace | Focusing on on-demand tutor marketplace: clear priority. What essential building blocks must be ready on day one for users? | User login & profiles, In-app payments, Push notifications, Search & discovery, Not sure yet | - | discovery | 23.6 | 0 |
| 4 | iOS and Android | What essential building blocks or capabilities do you envision for the initial release? | User login & profiles, In-app payments, Push notifications, Search & discovery, Not sure yet, Not sure, suggest | - | discovery | 18.3 | 0 |
| 5 | Matching algorithm, in-app messaging, tutor reviews | Channels and UX: Flutter. Core flow: Matching algorithm, in-app messaging, tutor reviews. Backend and APIs: Node.js + PostgreSQL. Who is the first person this should work well for? | Consumers, Business users, Internal team | shape | discovery | 19.7 | 0 |
| 6 | 1 to 3 months | Working toward 1 to 3 months sets the development pace. Are there any external services or APIs this must connect with on day one, like payments or CRM? | None on day one, Payments, CRM | - | discovery | 20.8 | 0 |
| 7 | Founder | Here's what I understood: a mobile app - on-demand tutor marketplace. Platforms: iOS and Android. Features: Matching algorithm, in-app messaging, tutor reviews. Timeline: 1 to 3 months. Budget: my budget is $40k to $80k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$38,000–$47,500 USD** over about **22 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 18.6 | 0 |

#### Scenario S10: Starter 'I have an app idea' -> 'a booking app for barbers' -> 'web and mobile'

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 15.5 | 0 |
| 1 | I have an app idea | Tell me what your app does in a sentence or two — who is it for and what's the core workflow? | Mobile app, Web platform, AI product, UI/UX design | - | discovery | 17.5 | 0 |
| 2 | a booking app for barbers | booking app for barbers: that gives me a clear picture. What essential building blocks must be ready on day one for users? | User authentication, Payment checkout, Admin dashboard, Analytics & reports, Not sure yet | - | discovery | 19.2 | 0 |
| 3 | web and mobile | Targeting web, iOS and Android sets our technical architecture. What essential building blocks must be ready on day one for users? | User login & profiles, In-app payments, Push notifications, Search & discovery, Not sure yet | - | discovery | 17.6 | 0 |
| 4 | Appointment scheduling, barber portfolio, customer SMS alerts, loyalty points, payment processing | Channels and UX: Flutter. Core flow: Appointment scheduling, barber portfolio, customer SMS alerts. Backend and APIs: Node.js + PostgreSQL. Who is the first person this should work well for? | Consumers, Business users, Internal team | shape | discovery | 20.0 | 0 |
| 5 | 1–3 months | Targeting 1 to 3 months gives us a defined delivery window. Will the first release need integrations with existing databases, auth providers, or third-party APIs? | None on day one, Payments, CRM | - | discovery | 19.6 | 0 |
| 6 | $15–40k | What is your role on the project when architecture and delivery decisions are made? | Founder / exec, Product or ops, Manager, Student / intern | - | discovery | 16.8 | 0 |
| 7 | Founder / exec | Here's what I understood: a mobile app - booking app for barbers. Platforms: web, iOS and Android. Features: Appointment scheduling, barber portfolio, customer SMS alerts, loyalty points, and 1 more. Timeline: 1 to 3 months. Budget: $15k to $40k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$29,500–$37,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 20.3 | 0 |

## Classic Flow: Live LLM Evaluation (Primary Provider: gemini-3.8-flash)

### 1. QA Checks Summary Table (Complete QA-2 + QA-3 Validation)

| Scenario | Title | Opener | Max 2Sent/320c | No Placeholders | Platform Casing | No Mid-Word Cut | No Verbatim Repeat | Shape Card (S7) | Brief Match | Recap Exact | No Recap Reps | Objection Valid | No Guard Pre-Est | No Dup Bot | Est Once | Banned Strings | Latency & Calls | Turns to Est |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **S1** | Long comprehensive initia... | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | 3 |
| **S2** | Starter chip 'I'm just ex... | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 8 |
| **S3** | Starter chip 'I have an a... | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | 7 |
| **S4** | Seven-feature list in one... | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | 4 |
| **S5** | Hinglish: 'mujhe ek deliv... | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | 4 |
| **S6** | Post-estimate technical q... | ✓ | ✗ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 6 |
| **S7** | Natural chip path: Mobile... | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 8 |
| **S8** | Out-of-order answers (the... | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | 7 |
| **S9** | First message is only a b... | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | 7 |
| **S10** | Starter 'I have an app id... | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 7 |

### 2. Scenario Latency & Call Statistics

| Scenario | Turns | Median (s) | p95 (s) | Max (s) | Max Calls/Turn | Pass/Fail |
|---|---|---|---|---|---|---|
| **S1** | 3 | 4.52s | 4.64s | 4.64s | 1 | ✗ FAIL |
| **S2** | 8 | 3.84s | 4.99s | 4.99s | 1 | ✓ PASS |
| **S3** | 7 | 4.35s | 5.27s | 5.27s | 1 | ✗ FAIL |
| **S4** | 5 | 4.05s | 4.34s | 4.34s | 1 | ✗ FAIL |
| **S5** | 4 | 4.57s | 5.30s | 5.30s | 1 | ✗ FAIL |
| **S6** | 11 | 3.73s | 6.77s | 6.77s | 1 | ✓ PASS |
| **S7** | 8 | 0.02s | 6.17s | 6.17s | 0 | ✓ PASS |
| **S8** | 7 | 4.42s | 5.43s | 5.43s | 1 | ✗ FAIL |
| **S9** | 7 | 4.01s | 4.73s | 4.73s | 1 | ✗ FAIL |
| **S10** | 7 | 2.72s | 6.34s | 6.34s | 1 | ✓ PASS |

### 3. Full Turn-by-Turn Transcripts & LLM Instrumentation

#### Scenario S1: Long comprehensive initial message with platforms, features, budget, and timeline

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 14.4 | 0 |
| 1 | We want it on both iOS and Android. For the first release we just need login, calendar booking, and push notifications. Budget around $25k to $35k, 2 to 3 months. | Channels and UX: Flutter. Core flow: login, calendar booking, push notifications. Backend and APIs: Node.js + PostgreSQL. Who is the first person this should work well for? | Consumers, Business users, Internal team | shape | discovery | 4518.3 | 1 |
| 2 | I am building a sports clinic booking application for direct patients. | Targeting direct patients as consumer end-users helps streamline the appointment scheduling and notification architecture. Are there any external services or APIs this must connect with on day one, like payments or CRM? | None on day one, Payments, CRM | - | discovery | 4640.7 | 1 |
| 3 | I am the founder and technical decision maker. | Here's what I understood: a mobile app - with calendar booking and notifications. Platforms: iOS and Android. Features: login, calendar booking, push notifications. Timeline: 1 to 3 months. Budget: around $25k to $35k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$32,000–$40,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 4406.8 | 1 |

*LLM Call Instrumentation (Turn, Purpose, Model, Wall ms, Thinking Tokens, Prompt Tokens, Output Tokens):*
| Turn | Purpose | Model | Wall ms | Thinking Tok | Prompt Tok | Output Tok |
|---|---|---|---|---|---|---|
| 1 | extractor | gemini-3.8-flash | 4454.6 | 0 | 945 | 213 |
| 2 | extractor | gemini-3.8-flash | 4587.9 | 0 | 1058 | 202 |
| 3 | extractor | gemini-3.8-flash | 4338.4 | 0 | 1068 | 156 |

#### Scenario S2: Starter chip 'I'm just exploring costs'

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 15.5 | 0 |
| 1 | I'm just exploring costs | Understood, we can walk through ballpark ranges once we narrow down the high-level scope and technical requirements. What primary problem or user workflow should this initial release solve? | Book appointments, Manage customers, Take payments | - | discovery | 3024.8 | 1 |
| 2 | Mobile app | Understood, scoping this for a mobile application. What primary problem or user workflow should this initial release solve? | Book appointments, Manage customers, Take payments | - | discovery | 3260.4 | 1 |
| 3 | Field service and asset tracking | Channels and UX: Flutter. Core flow: Asset tracking, Field service management. Backend and APIs: Node.js + PostgreSQL. Any systems this needs to talk to on day one? | None on day one, Payments, CRM | shape | discovery | 3376.4 | 1 |
| 4 | iOS and Android | Will this connect with any outside systems, like payments, email, or a CRM? | None on day one, Payments, CRM, Not sure yet, Not sure, suggest | - | discovery | 3426.0 | 1 |
| 5 | Offline data collection, barcode scanning, GPS tracking | Supporting offline data sync alongside hardware-level integrations like barcode scanning and GPS tracking will require a robust local database and sync resolution architecture. What timeframe are you aiming for to get this initial software product into users' hands? | ASAP, 1–3 months, 3–6 months, Flexible | - | discovery | 4257.4 | 1 |
| 6 | 1 to 3 months | A 1 to 3 month timeline provides a focused window to build and validate the core tracking workflows. What is your role on the project when architecture and delivery decisions are made? | Founder / exec, Product or ops, Manager, Student / intern | - | discovery | 4827.9 | 1 |
| 7 | $40k to $80k | Targeting this allocation gives sufficient room to support offline sync architectures, native device hardware integrations, and cross-platform mobile reliability. Are you leading this as founder, product manager, operations lead, or another role? | Founder / exec, Product or ops, Manager, Student / intern | - | discovery | 4994.7 | 1 |
| 8 | Founder | Here's what I understood: a mobile app - Field service and asset tracking. Platforms: iOS and Android. Features: Asset tracking, Field service management, Offline data collection, Barcode scanning, and 1 more. Timeline: 1 to 3 months. Budget: $40k to $80k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$29,500–$37,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band is above this first-pass range, so there is room to add scope. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 4620.1 | 1 |

*LLM Call Instrumentation (Turn, Purpose, Model, Wall ms, Thinking Tokens, Prompt Tokens, Output Tokens):*
| Turn | Purpose | Model | Wall ms | Thinking Tok | Prompt Tok | Output Tok |
|---|---|---|---|---|---|---|
| 1 | extractor | gemini-3.8-flash | 2975.1 | 0 | 907 | 163 |
| 2 | extractor | gemini-3.8-flash | 3207.5 | 0 | 955 | 149 |
| 3 | extractor | gemini-3.8-flash | 3306.4 | 0 | 977 | 171 |
| 4 | extractor | gemini-3.8-flash | 3370.1 | 0 | 1029 | 162 |
| 5 | extractor | gemini-3.8-flash | 4201.1 | 0 | 1035 | 211 |
| 6 | extractor | gemini-3.8-flash | 4776.4 | 0 | 1063 | 204 |
| 7 | extractor | gemini-3.8-flash | 4908.2 | 0 | 1087 | 178 |
| 8 | extractor | gemini-3.8-flash | 4545.2 | 0 | 1088 | 199 |

#### Scenario S3: Starter chip 'I have an app idea' -> 'A marketplace for local farmers'

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 16.1 | 0 |
| 1 | I have an app idea | Understood, scoping out a new application concept. What primary problem or user workflow should this initial release solve? | Book appointments, Manage customers, Take payments | - | discovery | 2949.7 | 1 |
| 2 | A marketplace for local farmers | A two-sided marketplace architecture will need clear separation between farmer vendor profiles and consumer browsing flows. Which core capabilities or features are essential for the launch? | User login & profiles, In-app payments, Push notifications, Search & discovery, Not sure yet | - | discovery | 4803.8 | 1 |
| 3 | Web and mobile | Supporting both web and mobile will ensure broad reach across desktop and on-the-go users. What essential building blocks must be ready on day one for users? | User login & profiles, In-app payments, Push notifications, Search & discovery, Not sure yet | - | discovery | 5265.5 | 1 |
| 4 | Produce catalog, Stripe checkout, farmer payouts, direct chat | Channels and UX: Flutter. Core flow: Produce catalog, Stripe checkout, Farmer payouts. Backend and APIs: Node.js + PostgreSQL. When would you like the initial version in users' hands? | ASAP, 1–3 months, 3–6 months, Flexible | shape | discovery | 3716.7 | 1 |
| 5 | 3 to 6 months | A three to six month window provides adequate runway to design and build across both platforms. What rough budget scale makes sense for this first release to help calibrate our architecture recommendations? | Still exploring, Under $15k, $15–40k, $40–80k, $80k+ | - | discovery | 4352.0 | 1 |
| 6 | $40k to $80k | This target allows for comprehensive cross-platform development and robust payment infrastructure. What is your role on the project when architecture and delivery decisions are made? | Founder / exec, Product or ops, Manager, Student / intern | - | discovery | 4137.5 | 1 |
| 7 | Product lead | Here's what I understood: a mobile app - marketplace for local farmers. Platforms: web, iOS and Android. Features: Produce catalog, Stripe checkout, Farmer payouts, Direct chat. Timeline: 3 to 6 months. Budget: $40k to $80k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$41,000–$51,000 USD** over about **22 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 4665.8 | 1 |

*LLM Call Instrumentation (Turn, Purpose, Model, Wall ms, Thinking Tokens, Prompt Tokens, Output Tokens):*
| Turn | Purpose | Model | Wall ms | Thinking Tok | Prompt Tok | Output Tok |
|---|---|---|---|---|---|---|
| 1 | extractor | gemini-3.8-flash | 2898.8 | 0 | 906 | 149 |
| 2 | extractor | gemini-3.8-flash | 4747.3 | 0 | 929 | 164 |
| 3 | extractor | gemini-3.8-flash | 5165.5 | 0 | 959 | 166 |
| 4 | extractor | gemini-3.8-flash | 3651.6 | 0 | 1004 | 190 |
| 5 | extractor | gemini-3.8-flash | 4269.8 | 0 | 1045 | 161 |
| 6 | extractor | gemini-3.8-flash | 4082.0 | 0 | 1069 | 167 |
| 7 | extractor | gemini-3.8-flash | 4570.7 | 0 | 1098 | 201 |

#### Scenario S4: Seven-feature list in one message (triggers Scope Coach)

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 20.6 | 0 |
| 1 | I want a web app for clinic management. Features: patient booking, telemedicine video, prescriptions, billing, lab results, doctor scheduling, insurance verification. | Channels and UX: Next.js. Core flow: Patient booking, Telemedicine video, Prescriptions. Backend and APIs: Node.js + PostgreSQL. When would you like the initial version in users' hands? | ASAP, 1–3 months, 3–6 months, Flexible | shape | discovery | 3831.7 | 1 |
| 2 | Web application | Is there a target milestone or launch timeframe you have in mind? | ASAP, 1–3 months, 3–6 months, Flexible, Not sure yet, Not sure, suggest | - | discovery | 4046.8 | 1 |
| 3 | 1 to 3 months | A one to three month timeline requires a focused initial rollout prioritizing core clinic operations and telemedicine workflows. What rough budget scale makes sense for this first release to help calibrate our architecture recommendations? | Still exploring, Under $15k, $15–40k, $40–80k, $80k+ | - | discovery | 4343.7 | 1 |
| 4 | $40k to $80k | Here's what I understood: a web application - Clinic management system with telemedicine, billing, and scheduling. Platforms: web. Features: Patient booking, Telemedicine video, Prescriptions, Billing, and 3 more. Timeline: 1 to 3 months. Budget: $40k to $80k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$20,500–$25,500 USD** over about **8 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  This range assumes the Core scope; a list this long will likely need more, and the team can size it precisely. | Show the Core cut, Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 4176.9 | 1 |
| 5 | Founder | Noted, I have updated your project brief. What would you like to explore next? | Book a call, See the MVP, See sample projects, Talk to a human | - | discovery | 23.1 | 0 |

*LLM Call Instrumentation (Turn, Purpose, Model, Wall ms, Thinking Tokens, Prompt Tokens, Output Tokens):*
| Turn | Purpose | Model | Wall ms | Thinking Tok | Prompt Tok | Output Tok |
|---|---|---|---|---|---|---|
| 1 | extractor | gemini-3.8-flash | 3762.7 | 0 | 931 | 240 |
| 2 | extractor | gemini-3.8-flash | 3967.0 | 0 | 1053 | 161 |
| 3 | extractor | gemini-3.8-flash | 4251.6 | 0 | 1056 | 163 |
| 4 | extractor | gemini-3.8-flash | 4098.4 | 0 | 1085 | 259 |

#### Scenario S5: Hinglish: 'mujhe ek delivery app chahiye, iOS aur Android dono, 3 mahine me'

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 22.7 | 0 |
| 1 | mujhe ek delivery app chahiye, iOS aur Android dono, 3 mahine me | Developing a cross-platform delivery application for both iOS and Android within a three-month timeframe requires a clear scope focusing on core logistics and tracking workflows. What essential building blocks must be ready on day one for users? | User login & profiles, In-app payments, Push notifications, Search & discovery, Not sure yet | - | discovery | 5130.8 | 1 |
| 2 | Live order tracking, customer ratings, driver assignment | Channels and UX: Flutter. Core flow: Live order tracking, Customer ratings, Driver assignment. Backend and APIs: Node.js + PostgreSQL. Any systems this needs to talk to on day one? | None on day one, Payments, CRM | shape | discovery | 4006.0 | 1 |
| 3 | $15k to $40k | Targeting this investment range aligns well with building and shipping a focused cross-platform mobile product. Are you leading this as founder, product manager, operations lead, or another role? | Founder / exec, Product or ops, Manager, Student / intern | - | discovery | 5301.2 | 1 |
| 4 | Founder | Here's what I understood: a mobile app - delivery app. Platforms: iOS and Android. Features: Live order tracking, Customer ratings, Driver assignment. Timeline: 1 to 3 months. Budget: $15k to $40k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$29,500–$37,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 3795.7 | 1 |

*LLM Call Instrumentation (Turn, Purpose, Model, Wall ms, Thinking Tokens, Prompt Tokens, Output Tokens):*
| Turn | Purpose | Model | Wall ms | Thinking Tok | Prompt Tok | Output Tok |
|---|---|---|---|---|---|---|
| 1 | extractor | gemini-3.8-flash | 5058.3 | 0 | 918 | 182 |
| 2 | extractor | gemini-3.8-flash | 3933.0 | 0 | 985 | 193 |
| 3 | extractor | gemini-3.8-flash | 5201.4 | 0 | 1027 | 169 |
| 4 | extractor | gemini-3.8-flash | 3729.4 | 0 | 1065 | 192 |

#### Scenario S6: Post-estimate technical questions, calendar slot booking, and post-booking ack

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 25.5 | 0 |
| 1 | We need a cross-platform mobile app for iOS and Android. | Developing a cross-platform mobile application targeting iOS and Android allows for a unified codebase and efficient deployment across both ecosystems. What core business outcome or user experience should this first launch deliver? | Book appointments, Manage customers, Take payments | - | discovery | 3522.7 | 1 |
| 2 | Fitness coaching app with workout logger and push notifications. | Channels and UX: Flutter. Core flow: Workout logger, Push notifications. Backend and APIs: Node.js + PostgreSQL. Any systems this needs to talk to on day one? | None on day one, Payments, CRM | shape | discovery | 4763.1 | 1 |
| 3 | Workout tracking, user profiles, video demonstrations | Captured the core features for workout tracking, user profiles, and video demonstration playback. What is your target launch horizon for getting this first release live? | ASAP, 1–3 months, 3–6 months, Flexible | - | discovery | 3726.7 | 1 |
| 4 | 1 to 3 months | Targeting 1 to 3 months gives us a defined delivery window. Which investment range should I size this initial build against for squad composition and architecture? | Still exploring, Under $15k, $15–40k, $40–80k, $80k+ | - | discovery | 6774.9 | 0 |
| 5 | $15k to $40k | Targeting this investment band provides a practical baseline for structuring the cross-platform mobile build. What is your role on the project when architecture and delivery decisions are made? | Founder / exec, Product or ops, Manager, Student / intern | - | discovery | 4471.8 | 1 |
| 6 | Founder | Here's what I understood: a mobile app - Fitness coaching app with workout logger and push notifications. Platforms: iOS and Android. Features: Workout logger, Push notifications, Workout tracking, User profiles, and 1 more. Timeline: 1 to 3 months. Budget: $15k to $40k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$29,500–$37,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 4618.6 | 1 |
| 7 | Do you use Flutter? | We build modern web, mobile, and cloud solutions using frameworks like React, Node.js, Python, Flutter, and native cloud services on AWS, GCP, and Azure. | Book a meeting, See similar work | - | faq | 2485.8 | 0 |
| 8 | Which cloud do you use? | We help you weigh tradeoffs; Flutter or React Native works exceptionally well for fast time-to-market, while native Swift/Kotlin suits high-performance hardware needs. | Book a meeting, See similar work | - | faq | 5893.7 | 1 |
| 9 | Can you guarantee 4 weeks? | The timeline assumes a small senior team. If a date is fixed, we shrink the first release rather than promising the full product sooner. | Book a meeting, See similar work | - | objection | 1675.2 | 0 |
| 10 | Friday Oct 16, 3:00 PM UTC | You're booked for Fri Oct 16, 20:30 IST — Demo booking: no calendar invite is sent until Google Calendar is connected. Reply with your work email so the invite has somewhere to go. | Can I reschedule?, See similar work | booking | booking | 558.5 | 0 |
| 11 | cool thanks | You're all set for Fri Oct 16, 20:30 IST. The team will see this whole conversation, so you won't need to repeat anything. | What is on the agenda?, Can I reschedule the time? | - | ack | 28.9 | 0 |

*LLM Call Instrumentation (Turn, Purpose, Model, Wall ms, Thinking Tokens, Prompt Tokens, Output Tokens):*
| Turn | Purpose | Model | Wall ms | Thinking Tok | Prompt Tok | Output Tok |
|---|---|---|---|---|---|---|
| 1 | extractor | gemini-3.8-flash | 3440.5 | 0 | 914 | 167 |
| 2 | extractor | gemini-3.8-flash | 4637.6 | 0 | 963 | 191 |
| 3 | extractor | gemini-3.8-flash | 3654.5 | 0 | 1018 | 193 |
| 5 | extractor | gemini-3.8-flash | 4405.1 | 0 | 1070 | 168 |
| 6 | extractor | gemini-3.8-flash | 4549.9 | 0 | 1098 | 209 |
| 8 | synth | gemini-3.8-flash | 3662.6 | 0 | 115 | 78 |

#### Scenario S7: Natural chip path: Mobile app, goal text, feature chips, platform chip, timeline chip, budget chip, role chip

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 18.7 | 0 |
| 1 | Mobile app | Focusing on mobile app: noted. What primary problem or user workflow should this initial release solve? | Book appointments, Manage customers, Take payments | - | discovery | 23.5 | 0 |
| 2 | A sports clinic booking application for direct patients | sports clinic booking application for direct patients: that gives me a clear picture. What essential building blocks must be ready on day one for users? | User login & profiles, In-app payments, Push notifications, Search & discovery, Not sure yet | - | discovery | 6165.7 | 0 |
| 3 | User login & profiles | User login & profiles gives us a solid foundation for the first release. Added User login & profiles — any other features for the launch, or ready to continue? | Continue to next step →, + User login & profiles, + In-app payments, + Push notifications, Ready with this list | - | discovery | 30.5 | 0 |
| 4 | Continue to next step → | What should each of User login & profiles do in the first version? | That's enough | - | discovery | 25.2 | 0 |
| 5 | iOS and Android | Channels and UX: Flutter. Core flow: User login & profiles. Backend and APIs: Node.js + PostgreSQL. Who is the first person this should work well for? | Consumers, Business users, Internal team | shape | discovery | 18.5 | 0 |
| 6 | 1–3 months | Targeting 1 to 3 months gives us a defined delivery window. Will the first release need integrations with existing databases, auth providers, or third-party APIs? | None on day one, Payments, CRM | - | discovery | 18.8 | 0 |
| 7 | $15–40k | What is your role on the project when architecture and delivery decisions are made? | Founder / exec, Product or ops, Manager, Student / intern | - | discovery | 17.4 | 0 |
| 8 | Founder / exec | Here's what I understood: a mobile app - sports clinic booking application for direct patients. Platforms: iOS and Android. Features: User login & profiles. Timeline: 1 to 3 months. Budget: $15k to $40k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$32,000–$40,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 23.6 | 0 |

#### Scenario S8: Out-of-order answers (the old S3 script)

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 14.7 | 0 |
| 1 | I have an app idea | Tell me what your app does in a sentence or two — who is it for and what's the core workflow? | Mobile app, Web platform, AI product, UI/UX design | - | discovery | 3942.0 | 1 |
| 2 | A marketplace for local farmers | A two-sided marketplace architecture will need dedicated flows for farmer inventory management and buyer discovery. Which core capabilities or features are essential for the launch? | User authentication, Payment checkout, Admin dashboard, Analytics & reports, Not sure yet | - | discovery | 3743.6 | 1 |
| 3 | Web and mobile | Supporting both web and cross-platform mobile will ensure wide accessibility for buyers and farmers alike. Which core capabilities or features are essential for the launch? | User login & profiles, In-app payments, Push notifications, Search & discovery, Not sure yet | - | discovery | 4143.1 | 1 |
| 4 | Produce catalog, Stripe checkout, farmer payouts, direct chat | Channels and UX: Flutter. Core flow: Produce catalog, Stripe checkout, Farmer payouts. Backend and APIs: Node.js + PostgreSQL. When would you like the initial version in users' hands? | ASAP, 1–3 months, 3–6 months, Flexible | shape | discovery | 5427.9 | 1 |
| 5 | 3 to 6 months | A three to six month timeframe allows adequate runway for multi-platform development and payments integration testing. What rough budget scale makes sense for this first release to help calibrate our architecture recommendations? | Still exploring, Under $15k, $15–40k, $40–80k, $80k+ | - | discovery | 4423.2 | 1 |
| 6 | $40k to $80k | This scope aligns well with planning the multi-platform marketplace architecture. Are you leading this as founder, product manager, operations lead, or another role? | Founder / exec, Product or ops, Manager, Student / intern | - | discovery | 4723.7 | 1 |
| 7 | Product lead | Here's what I understood: a mobile app - marketplace for local farmers. Platforms: web, iOS and Android. Features: Produce catalog, Stripe checkout, Farmer payouts, Direct chat. Timeline: 3 to 6 months. Budget: $40k to $80k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$41,000–$51,000 USD** over about **22 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 4898.7 | 1 |

*LLM Call Instrumentation (Turn, Purpose, Model, Wall ms, Thinking Tokens, Prompt Tokens, Output Tokens):*
| Turn | Purpose | Model | Wall ms | Thinking Tok | Prompt Tok | Output Tok |
|---|---|---|---|---|---|---|
| 1 | extractor | gemini-3.8-flash | 3877.6 | 0 | 906 | 151 |
| 2 | extractor | gemini-3.8-flash | 3678.4 | 0 | 906 | 163 |
| 3 | extractor | gemini-3.8-flash | 4079.4 | 0 | 948 | 165 |
| 4 | extractor | gemini-3.8-flash | 5346.2 | 0 | 993 | 205 |
| 5 | extractor | gemini-3.8-flash | 4356.2 | 0 | 1039 | 195 |
| 6 | extractor | gemini-3.8-flash | 4654.3 | 0 | 1063 | 203 |
| 7 | extractor | gemini-3.8-flash | 4776.2 | 0 | 1092 | 205 |

#### Scenario S9: First message is only a budget: 'my budget is $40k to $80k'

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 26.3 | 0 |
| 1 | my budget is $40k to $80k | Understood, that budget range provides a solid baseline for planning the scope and architecture. What primary problem or user workflow should this initial release solve? | Book appointments, Manage customers, Take payments | - | discovery | 4146.4 | 1 |
| 2 | Mobile app | Understood, updating the target platform focus to a mobile application. What primary problem or user workflow should this initial release solve? | Book appointments, Manage customers, Take payments | - | discovery | 3662.9 | 1 |
| 3 | An on-demand tutor marketplace | Designing an on-demand tutor marketplace involves structuring dual-sided matching, real-time scheduling, and seamless communication workflows. What essential building blocks must be ready on day one for users? | User login & profiles, In-app payments, Push notifications, Search & discovery, Not sure yet | - | discovery | 3890.0 | 1 |
| 4 | iOS and Android | What essential building blocks or capabilities do you envision for the initial release? | User login & profiles, In-app payments, Push notifications, Search & discovery, Not sure yet, Not sure, suggest | - | discovery | 4178.3 | 1 |
| 5 | Matching algorithm, in-app messaging, tutor reviews | Channels and UX: Flutter. Core flow: Matching algorithm, In-app messaging, Tutor reviews. Backend and APIs: Node.js + PostgreSQL. Any systems this needs to talk to on day one? | None on day one, Payments, CRM | shape | discovery | 4010.9 | 1 |
| 6 | 1 to 3 months | A 1 to 3 month target provides a focused window for architecting and delivering the core mobile tutor marketplace. What is your role on the project when architecture and delivery decisions are made? | Founder / exec, Product or ops, Manager, Student / intern | - | discovery | 3807.6 | 1 |
| 7 | Founder | Here's what I understood: a mobile app - on-demand tutor marketplace. Platforms: iOS and Android. Features: Matching algorithm, In-app messaging, Tutor reviews. Timeline: 1 to 3 months. Budget: $40k to $80k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$38,000–$47,500 USD** over about **22 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 4733.8 | 1 |

*LLM Call Instrumentation (Turn, Purpose, Model, Wall ms, Thinking Tokens, Prompt Tokens, Output Tokens):*
| Turn | Purpose | Model | Wall ms | Thinking Tok | Prompt Tok | Output Tok |
|---|---|---|---|---|---|---|
| 1 | extractor | gemini-3.8-flash | 4070.9 | 0 | 913 | 167 |
| 2 | extractor | gemini-3.8-flash | 3599.3 | 0 | 964 | 157 |
| 3 | extractor | gemini-3.8-flash | 3816.0 | 0 | 987 | 181 |
| 4 | extractor | gemini-3.8-flash | 4109.0 | 0 | 1017 | 181 |
| 5 | extractor | gemini-3.8-flash | 3923.6 | 0 | 1024 | 216 |
| 6 | extractor | gemini-3.8-flash | 3731.8 | 0 | 1063 | 207 |
| 7 | extractor | gemini-3.8-flash | 4660.7 | 0 | 1087 | 206 |

#### Scenario S10: Starter 'I have an app idea' -> 'a booking app for barbers' -> 'web and mobile'

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 18.2 | 0 |
| 1 | I have an app idea | Developing a new application starts with defining its core functionality and platform requirements. What core business outcome or user experience should this first launch deliver? | Book appointments, Manage customers, Take payments | - | discovery | 4837.8 | 1 |
| 2 | a booking app for barbers | Focusing on booking app for barbers: clear priority. Which core capabilities or features are essential for the launch? | User login & profiles, In-app payments, Push notifications, Search & discovery, Not sure yet | - | discovery | 6345.0 | 0 |
| 3 | web and mobile | Supporting both web and mobile will ensure broad accessibility for both barbers and clients across devices. Which core capabilities or features are essential for the launch? | User login & profiles, In-app payments, Push notifications, Search & discovery, Not sure yet | - | discovery | 2721.1 | 1 |
| 4 | Appointment scheduling, barber portfolio, customer SMS alerts, loyalty points, payment processing | Channels and UX: Flutter. Core flow: Appointment scheduling, barber portfolio, customer SMS alerts. Backend and APIs: Node.js + PostgreSQL. Who is the first person this should work well for? | Consumers, Business users, Internal team | shape | discovery | 6167.1 | 0 |
| 5 | 1–3 months | Working toward 1 to 3 months sets the development pace. Will the first release need integrations with existing databases, auth providers, or third-party APIs? | None on day one, Payments, CRM | - | discovery | 25.4 | 0 |
| 6 | $15–40k | What is your role on the project when architecture and delivery decisions are made? | Founder / exec, Product or ops, Manager, Student / intern | - | discovery | 21.1 | 0 |
| 7 | Founder / exec | Here's what I understood: a mobile app - booking app for barbers. Platforms: web, iOS and Android. Features: Appointment scheduling, barber portfolio, customer SMS alerts, loyalty points, and 1 more. Timeline: 1 to 3 months. Budget: $15k to $40k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$29,500–$37,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 19.6 | 0 |

*LLM Call Instrumentation (Turn, Purpose, Model, Wall ms, Thinking Tokens, Prompt Tokens, Output Tokens):*
| Turn | Purpose | Model | Wall ms | Thinking Tok | Prompt Tok | Output Tok |
|---|---|---|---|---|---|---|
| 1 | extractor | gemini-3.8-flash | 4772.5 | 0 | 906 | 153 |
| 3 | extractor | gemini-3.8-flash | 2652.5 | 0 | 948 | 164 |

## Fast Flow: In-Process Deterministic Stub (Offline / Fallback)

### 1. QA Checks Summary Table (Complete QA-2 + QA-3 Validation)

| Scenario | Title | Opener | Max 2Sent/320c | No Placeholders | Platform Casing | No Mid-Word Cut | No Verbatim Repeat | Shape Card (S7) | Brief Match | Recap Exact | No Recap Reps | Objection Valid | No Guard Pre-Est | No Dup Bot | Est Once | Banned Strings | Latency & Calls | Turns to Est |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **S1** | Long comprehensive initia... | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 2 |
| **S2** | Starter chip 'I'm just ex... | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 7 |
| **S3** | Starter chip 'I have an a... | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 6 |
| **S4** | Seven-feature list in one... | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 4 |
| **S5** | Hinglish: 'mujhe ek deliv... | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 3 |
| **S6** | Post-estimate technical q... | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 5 |
| **S7** | Natural chip path: Mobile... | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 7 |
| **S8** | Out-of-order answers (the... | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 6 |
| **S9** | First message is only a b... | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 5 |
| **S10** | Starter 'I have an app id... | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 6 |

### 2. Scenario Latency & Call Statistics

| Scenario | Turns | Median (s) | p95 (s) | Max (s) | Max Calls/Turn | Pass/Fail |
|---|---|---|---|---|---|---|
| **S1** | 3 | 0.02s | 0.02s | 0.02s | 0 | ✓ PASS |
| **S2** | 8 | 0.02s | 0.02s | 0.02s | 0 | ✓ PASS |
| **S3** | 7 | 0.02s | 0.02s | 0.02s | 0 | ✓ PASS |
| **S4** | 5 | 0.02s | 0.02s | 0.02s | 0 | ✓ PASS |
| **S5** | 4 | 0.02s | 0.02s | 0.02s | 0 | ✓ PASS |
| **S6** | 11 | 0.02s | 0.53s | 0.53s | 0 | ✓ PASS |
| **S7** | 8 | 0.02s | 0.02s | 0.02s | 0 | ✓ PASS |
| **S8** | 7 | 0.02s | 0.02s | 0.02s | 0 | ✓ PASS |
| **S9** | 7 | 0.02s | 0.03s | 0.03s | 0 | ✓ PASS |
| **S10** | 7 | 0.02s | 0.02s | 0.02s | 0 | ✓ PASS |

### 3. Full Turn-by-Turn Transcripts & LLM Instrumentation

#### Scenario S1: Long comprehensive initial message with platforms, features, budget, and timeline

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 13.4 | 0 |
| 1 | We want it on both iOS and Android. For the first release we just need login, calendar booking, and push notifications. Budget around $25k to $35k, 2 to 3 months. | Channels and UX: Flutter. Core flow: login, calendar booking, push notifications. Backend and APIs: Node.js + PostgreSQL. What should this first version actually do for people? | Book appointments, Manage customers, Take payments | shape | discovery | 22.4 | 0 |
| 2 | I am building a sports clinic booking application for direct patients. | Here's what I understood: a mobile app - sports clinic booking application for direct patients. Platforms: iOS and Android. Features: login, calendar booking, push notifications. Timeline: 1 to 3 months. Budget: around $25k to $35k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$32,000–$40,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 17.7 | 0 |
| 3 | I am the founder and technical decision maker. | Noted — having the founder or exec perspective helps keep delivery aligned. What would you like to explore next? | Book a call, See the MVP, See sample projects, Talk to a human | - | discovery | 18.6 | 0 |

#### Scenario S2: Starter chip 'I'm just exploring costs'

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 13.4 | 0 |
| 1 | I'm just exploring costs | Happy to help you explore costs. What are you thinking of building: a mobile app, a web platform, AI, or design? | Mobile app, Web platform, AI product, UI/UX design | - | discovery | 18.8 | 0 |
| 2 | Mobile app | iOS and Android, noted. What core business outcome or user experience should this first launch deliver? | Book appointments, Manage customers, Take payments | - | discovery | 20.7 | 0 |
| 3 | Field service and asset tracking | Focusing on Field service and asset tracking: clear priority. What is your target launch horizon for getting this first release live? | ASAP, 1–3 months, 3–6 months, Flexible | - | discovery | 19.7 | 0 |
| 4 | iOS and Android | Is there a target milestone or launch timeframe you have in mind? | ASAP, 1–3 months, 3–6 months, Flexible, Not sure yet, Not sure, suggest | - | discovery | 23.2 | 0 |
| 5 | Offline data collection, barcode scanning, GPS tracking | Channels and UX: Flutter. Core flow: Offline data collection, barcode scanning, GPS tracking. Backend and APIs: Node.js + PostgreSQL. A rough ballpark helps me size this, no commitment — which budget range makes sense? | Still exploring, Under $15k, $15–40k, $40–80k, $80k+ | shape | discovery | 21.7 | 0 |
| 6 | 1 to 3 months | What rough budget scale makes sense for this first release to help calibrate our architecture recommendations? | Still exploring, Under $15k, $15–40k, $40–80k, $80k+ | - | discovery | 18.1 | 0 |
| 7 | $40k to $80k | Here's what I understood: a mobile app - Field service and asset tracking. Platforms: iOS and Android. Features: Offline data collection, barcode scanning, GPS tracking. Timeline: flexible timing. Budget: $40k to $80k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$29,500–$37,000 USD** over about **16 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band is above this first-pass range, so there is room to add scope. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 22.7 | 0 |
| 8 | Founder | Noted — having the founder or exec perspective helps keep delivery aligned. What would you like to explore next? | Book a call, See the MVP, See sample projects, Talk to a human | - | discovery | 17.8 | 0 |

#### Scenario S3: Starter chip 'I have an app idea' -> 'A marketplace for local farmers'

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 14.4 | 0 |
| 1 | I have an app idea | Tell me what your app does in a sentence or two — who is it for and what's the core workflow? | Mobile app, Web platform, AI product, UI/UX design | - | discovery | 20.7 | 0 |
| 2 | A marketplace for local farmers | Focusing on marketplace for local farmers: clear priority. Where will your target users primarily access this application — in a browser or on mobile devices? | Web, API | - | discovery | 23.4 | 0 |
| 3 | Web and mobile | Targeting web, iOS and Android sets our technical architecture. What is your target launch horizon for getting this first release live? | ASAP, 1–3 months, 3–6 months, Flexible | - | discovery | 17.3 | 0 |
| 4 | Produce catalog, Stripe checkout, farmer payouts, direct chat | Channels and UX: Flutter. Core flow: Produce catalog, Stripe checkout, farmer payouts. Backend and APIs: Node.js + PostgreSQL. When would you like the initial version in users' hands? | ASAP, 1–3 months, 3–6 months, Flexible | shape | discovery | 22.3 | 0 |
| 5 | 3 to 6 months | Targeting 3 to 6 months gives us a defined delivery window. Which investment range should I size this initial build against for squad composition and architecture? | Still exploring, Under $15k, $15–40k, $40–80k, $80k+ | - | discovery | 18.7 | 0 |
| 6 | $40k to $80k | Here's what I understood: a mobile app - marketplace for local farmers. Platforms: web, iOS and Android. Features: Produce catalog, Stripe checkout, farmer payouts, direct chat. Timeline: 3 to 6 months. Budget: $40k to $80k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$38,000–$47,500 USD** over about **22 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 22.7 | 0 |
| 7 | Product lead | Noted — having the product or ops lead perspective helps keep delivery aligned. What would you like to explore next? | Book a call, See the MVP, See sample projects, Talk to a human | - | discovery | 20.5 | 0 |

#### Scenario S4: Seven-feature list in one message (triggers Scope Coach)

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 13.3 | 0 |
| 1 | I want a web app for clinic management. Features: patient booking, telemedicine video, prescriptions, billing, lab results, doctor scheduling, insurance verification. | Channels and UX: Next.js. Core flow: patient booking, telemedicine video, prescriptions. Backend and APIs: Node.js + PostgreSQL. When would you like the initial version in users' hands? | ASAP, 1–3 months, 3–6 months, Flexible | shape | discovery | 21.5 | 0 |
| 2 | Web application | Is there a target milestone or launch timeframe you have in mind? | ASAP, 1–3 months, 3–6 months, Flexible, Not sure yet, Not sure, suggest | - | discovery | 19.7 | 0 |
| 3 | 1 to 3 months | Working toward 1 to 3 months sets the development pace. What rough budget scale makes sense for this first release to help calibrate our architecture recommendations? | Still exploring, Under $15k, $15–40k, $40–80k, $80k+ | - | discovery | 18.6 | 0 |
| 4 | $40k to $80k | Here's what I understood: a web application - for clinic management. Platforms: web. Features: patient booking, telemedicine video, prescriptions, billing, and 3 more. Timeline: 1 to 3 months. Budget: $40k to $80k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$19,000–$24,000 USD** over about **8 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  This range assumes the Core scope; a list this long will likely need more, and the team can size it precisely. | Show the Core cut, Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 22.8 | 0 |
| 5 | Founder | Noted, I have updated your project brief. What would you like to explore next? | Book a call, See the MVP, See sample projects, Talk to a human | - | discovery | 23.1 | 0 |

#### Scenario S5: Hinglish: 'mujhe ek delivery app chahiye, iOS aur Android dono, 3 mahine me'

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 14.6 | 0 |
| 1 | mujhe ek delivery app chahiye, iOS aur Android dono, 3 mahine me | Focusing on mujhe ek delivery app chahiye, iOS aur Android: clear priority. What rough budget scale makes sense for this first release to help calibrate our architecture recommendations? | Still exploring, Under $15k, $15–40k, $40–80k, $80k+ | - | discovery | 17.6 | 0 |
| 2 | Live order tracking, customer ratings, driver assignment | Channels and UX: Flutter. Core flow: Live order tracking, customer ratings, driver assignment. Backend and APIs: Node.js + PostgreSQL. A rough ballpark helps me size this, no commitment — which budget range makes sense? | Still exploring, Under $15k, $15–40k, $40–80k, $80k+ | shape | discovery | 16.9 | 0 |
| 3 | $15k to $40k | Here's what I understood: a mobile app - mujhe ek delivery app chahiye. Platforms: iOS and Android. Features: Live order tracking, customer ratings, driver assignment. Timeline: 1 to 3 months. Budget: $15k to $40k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$29,500–$37,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 17.7 | 0 |
| 4 | Founder | Noted — having the founder or exec perspective helps keep delivery aligned. What would you like to explore next? | Book a call, See the MVP, See sample projects, Talk to a human | - | discovery | 18.0 | 0 |

#### Scenario S6: Post-estimate technical questions, calendar slot booking, and post-booking ack

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 14.5 | 0 |
| 1 | We need a cross-platform mobile app for iOS and Android. | Targeting iOS and Android sets our technical architecture. What primary problem or user workflow should this initial release solve? | Book appointments, Manage customers, Take payments | - | discovery | 19.5 | 0 |
| 2 | Fitness coaching app with workout logger and push notifications. | Channels and UX: Flutter. Core flow: workout logger, push notifications. Backend and APIs: Node.js + PostgreSQL. When would you like the initial version in users' hands? | ASAP, 1–3 months, 3–6 months, Flexible | shape | discovery | 20.8 | 0 |
| 3 | Workout tracking, user profiles, video demonstrations | What is your target launch horizon for getting this first release live? | ASAP, 1–3 months, 3–6 months, Flexible | - | discovery | 15.9 | 0 |
| 4 | 1 to 3 months | Targeting 1 to 3 months gives us a defined delivery window. Which investment range should I size this initial build against for squad composition and architecture? | Still exploring, Under $15k, $15–40k, $40–80k, $80k+ | - | discovery | 19.4 | 0 |
| 5 | $15k to $40k | Here's what I understood: a mobile app - Fitness coaching app. Platforms: iOS and Android. Features: workout logger, push notifications. Timeline: 1 to 3 months. Budget: $15k to $40k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$29,500–$37,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 23.4 | 0 |
| 6 | Founder | Noted — having the founder or exec perspective helps keep delivery aligned. What would you like to explore next? | Book a call, See the MVP, See sample projects, Talk to a human | - | discovery | 22.3 | 0 |
| 7 | Do you use Flutter? | Our engineering team can go into detail on those specific technical requirements on a discovery call. | Book a meeting, See similar work | - | fallback | 18.8 | 0 |
| 8 | Which cloud do you use? | We can dive deeper into that architecture and technical setup during a quick discovery call. | Book a meeting, See similar work | - | fallback | 20.2 | 0 |
| 9 | Can you guarantee 4 weeks? | Our engineering team can go into detail on those specific technical requirements on a discovery call. | Book a meeting, See similar work | - | fallback | 20.1 | 0 |
| 10 | Friday Oct 16, 3:00 PM UTC | You're booked for Fri Oct 16, 20:30 IST — Demo booking: no calendar invite is sent until Google Calendar is connected. Reply with your work email so the invite has somewhere to go. | Can I reschedule?, See similar work | booking | booking | 529.4 | 0 |
| 11 | cool thanks | You're all set for Fri Oct 16, 20:30 IST. The team will see this whole conversation, so you won't need to repeat anything. | What is on the agenda?, Can I reschedule the time? | - | ack | 25.0 | 0 |

#### Scenario S7: Natural chip path: Mobile app, goal text, feature chips, platform chip, timeline chip, budget chip, role chip

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 15.8 | 0 |
| 1 | Mobile app | mobile app, understood. What core business outcome or user experience should this first launch deliver? | Book appointments, Manage customers, Take payments | - | discovery | 19.7 | 0 |
| 2 | A sports clinic booking application for direct patients | Focusing on sports clinic booking application for direct patients: clear priority. Which platforms should we target for the first launch — web, iOS, Android, or cross-platform mobile? | iOS, Android, iOS and Android | - | discovery | 19.2 | 0 |
| 3 | User login & profiles | User login & profiles gives us a solid foundation for the first release. Where will your target users primarily access this application — in a browser or on mobile devices? | iOS, Android, iOS and Android | - | discovery | 18.1 | 0 |
| 4 | Continue to next step → | Where would your target audience primarily use this — on mobile devices or in a web browser? | iOS, Android, iOS and Android, Not sure yet, Not sure, suggest | - | discovery | 19.2 | 0 |
| 5 | iOS and Android | Channels and UX: Flutter. Core flow: User login & profiles. Backend and APIs: Node.js + PostgreSQL. When would you like the initial version in users' hands? | ASAP, 1–3 months, 3–6 months, Flexible | shape | discovery | 17.4 | 0 |
| 6 | 1–3 months | Working toward 1 to 3 months sets the development pace. Which investment range should I size this initial build against for squad composition and architecture? | Still exploring, Under $15k, $15–40k, $40–80k, $80k+ | - | discovery | 23.2 | 0 |
| 7 | $15–40k | Here's what I understood: a mobile app - sports clinic booking application for direct patients. Platforms: iOS and Android. Features: User login & profiles. Timeline: 1 to 3 months. Budget: $15k to $40k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$32,000–$40,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 19.9 | 0 |
| 8 | Founder / exec | Noted — having the founder or exec perspective helps keep delivery aligned. What would you like to explore next? | Book a call, See the MVP, See sample projects, Talk to a human | - | discovery | 18.6 | 0 |

#### Scenario S8: Out-of-order answers (the old S3 script)

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 13.5 | 0 |
| 1 | I have an app idea | Tell me what your app does in a sentence or two — who is it for and what's the core workflow? | Mobile app, Web platform, AI product, UI/UX design | - | discovery | 19.8 | 0 |
| 2 | A marketplace for local farmers | marketplace for local farmers: that gives me a clear picture. Which platforms should we target for the first launch — web, iOS, Android, or cross-platform mobile? | Web, API | - | discovery | 18.0 | 0 |
| 3 | Web and mobile | web, iOS and Android, noted. What is your target launch horizon for getting this first release live? | ASAP, 1–3 months, 3–6 months, Flexible | - | discovery | 19.3 | 0 |
| 4 | Produce catalog, Stripe checkout, farmer payouts, direct chat | Channels and UX: Flutter. Core flow: Produce catalog, Stripe checkout, farmer payouts. Backend and APIs: Node.js + PostgreSQL. When would you like the initial version in users' hands? | ASAP, 1–3 months, 3–6 months, Flexible | shape | discovery | 17.2 | 0 |
| 5 | 3 to 6 months | Targeting 3 to 6 months gives us a defined delivery window. Which investment range should I size this initial build against for squad composition and architecture? | Still exploring, Under $15k, $15–40k, $40–80k, $80k+ | - | discovery | 23.7 | 0 |
| 6 | $40k to $80k | Here's what I understood: a mobile app - marketplace for local farmers. Platforms: web, iOS and Android. Features: Produce catalog, Stripe checkout, farmer payouts, direct chat. Timeline: 3 to 6 months. Budget: $40k to $80k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$38,000–$47,500 USD** over about **22 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 21.9 | 0 |
| 7 | Product lead | Noted — having the product or ops lead perspective helps keep delivery aligned. What would you like to explore next? | Book a call, See the MVP, See sample projects, Talk to a human | - | discovery | 17.5 | 0 |

#### Scenario S9: First message is only a budget: 'my budget is $40k to $80k'

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 15.4 | 0 |
| 1 | my budget is $40k to $80k | What core business outcome or user experience should this first launch deliver? | Book appointments, Manage customers, Take payments | - | discovery | 20.9 | 0 |
| 2 | Mobile app | Targeting iOS and Android sets our technical architecture. What primary problem or user workflow should this initial release solve? | Book appointments, Manage customers, Take payments | - | discovery | 19.2 | 0 |
| 3 | An on-demand tutor marketplace | Focusing on on-demand tutor marketplace: clear priority. What timeframe are you aiming for to get this initial software product into users' hands? | ASAP, 1–3 months, 3–6 months, Flexible | - | discovery | 20.3 | 0 |
| 4 | iOS and Android | Is there a target milestone or launch timeframe you have in mind? | ASAP, 1–3 months, 3–6 months, Flexible, Not sure yet, Not sure, suggest | - | discovery | 23.4 | 0 |
| 5 | Matching algorithm, in-app messaging, tutor reviews | Here's what I understood: a mobile app - on-demand tutor marketplace. Platforms: iOS and Android. Features: Matching algorithm, in-app messaging, tutor reviews. Timeline: flexible timing. Budget: my budget is $40k to $80k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$38,000–$47,500 USD** over about **25 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 26.6 | 0 |
| 6 | 1 to 3 months | Noted, I have updated your project brief. What would you like to explore next? | Book a call, See the MVP, See sample projects, Talk to a human | - | discovery | 21.0 | 0 |
| 7 | Founder | Noted — having the founder or exec perspective helps keep delivery aligned. What would you like to explore next? | Book a call, See the MVP, See sample projects, Talk to a human | - | discovery | 21.2 | 0 |

#### Scenario S10: Starter 'I have an app idea' -> 'a booking app for barbers' -> 'web and mobile'

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 15.0 | 0 |
| 1 | I have an app idea | Tell me what your app does in a sentence or two — who is it for and what's the core workflow? | Mobile app, Web platform, AI product, UI/UX design | - | discovery | 19.9 | 0 |
| 2 | a booking app for barbers | booking app for barbers: that gives me a clear picture. Which platforms should we target for the first launch — web, iOS, Android, or cross-platform mobile? | Web, API | - | discovery | 20.1 | 0 |
| 3 | web and mobile | web, iOS and Android, noted. What timeframe are you aiming for to get this initial software product into users' hands? | ASAP, 1–3 months, 3–6 months, Flexible | - | discovery | 22.9 | 0 |
| 4 | Appointment scheduling, barber portfolio, customer SMS alerts, loyalty points, payment processing | Channels and UX: Flutter. Core flow: Appointment scheduling, barber portfolio, customer SMS alerts. Backend and APIs: Node.js + PostgreSQL. When would you like the initial version in users' hands? | ASAP, 1–3 months, 3–6 months, Flexible | shape | discovery | 19.6 | 0 |
| 5 | 1–3 months | Working toward 1 to 3 months sets the development pace. Which investment range should I size this initial build against for squad composition and architecture? | Still exploring, Under $15k, $15–40k, $40–80k, $80k+ | - | discovery | 20.6 | 0 |
| 6 | $15–40k | Here's what I understood: a mobile app - booking app for barbers. Platforms: web, iOS and Android. Features: Appointment scheduling, barber portfolio, customer SMS alerts, loyalty points, and 1 more. Timeline: 1 to 3 months. Budget: $15k to $40k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$29,500–$37,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 20.3 | 0 |
| 7 | Founder / exec | Noted — having the founder or exec perspective helps keep delivery aligned. What would you like to explore next? | Book a call, See the MVP, See sample projects, Talk to a human | - | discovery | 21.5 | 0 |

## Fast Flow: Live LLM Evaluation (Primary Provider: gemini-3.8-flash)

### 1. QA Checks Summary Table (Complete QA-2 + QA-3 Validation)

| Scenario | Title | Opener | Max 2Sent/320c | No Placeholders | Platform Casing | No Mid-Word Cut | No Verbatim Repeat | Shape Card (S7) | Brief Match | Recap Exact | No Recap Reps | Objection Valid | No Guard Pre-Est | No Dup Bot | Est Once | Banned Strings | Latency & Calls | Turns to Est |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **S1** | Long comprehensive initia... | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 2 |
| **S2** | Starter chip 'I'm just ex... | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | 5 |
| **S3** | Starter chip 'I have an a... | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 6 |
| **S4** | Seven-feature list in one... | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | 4 |
| **S5** | Hinglish: 'mujhe ek deliv... | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | 3 |
| **S6** | Post-estimate technical q... | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 5 |
| **S7** | Natural chip path: Mobile... | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 7 |
| **S8** | Out-of-order answers (the... | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 6 |
| **S9** | First message is only a b... | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 5 |
| **S10** | Starter 'I have an app id... | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 6 |

### 2. Scenario Latency & Call Statistics

| Scenario | Turns | Median (s) | p95 (s) | Max (s) | Max Calls/Turn | Pass/Fail |
|---|---|---|---|---|---|---|
| **S1** | 3 | 3.18s | 4.65s | 4.65s | 1 | ✓ PASS |
| **S2** | 8 | 4.01s | 4.71s | 4.71s | 1 | ✗ FAIL |
| **S3** | 7 | 3.80s | 5.80s | 5.80s | 1 | ✓ PASS |
| **S4** | 5 | 4.40s | 4.87s | 4.87s | 1 | ✗ FAIL |
| **S5** | 4 | 4.16s | 5.54s | 5.54s | 1 | ✗ FAIL |
| **S6** | 11 | 2.97s | 5.44s | 5.44s | 1 | ✓ PASS |
| **S7** | 8 | 0.02s | 3.90s | 3.90s | 1 | ✓ PASS |
| **S8** | 7 | 2.90s | 4.42s | 4.42s | 1 | ✓ PASS |
| **S9** | 7 | 3.25s | 5.12s | 5.12s | 1 | ✓ PASS |
| **S10** | 7 | 2.57s | 4.69s | 4.69s | 1 | ✓ PASS |

### 3. Full Turn-by-Turn Transcripts & LLM Instrumentation

#### Scenario S1: Long comprehensive initial message with platforms, features, budget, and timeline

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 12.5 | 0 |
| 1 | We want it on both iOS and Android. For the first release we just need login, calendar booking, and push notifications. Budget around $25k to $35k, 2 to 3 months. | Channels and UX: Flutter. Core flow: Login, Calendar booking, Push notifications. Backend and APIs: Node.js + PostgreSQL. What should this first version actually do for people? | Book appointments, Manage customers, Take payments | shape | discovery | 4649.9 | 1 |
| 2 | I am building a sports clinic booking application for direct patients. | Here's what I understood: a mobile app - Sports clinic booking application for direct patients. Platforms: iOS and Android. Features: Login, Calendar booking, Push notifications. Timeline: 1 to 3 months. Budget: around $25k to $35k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$32,000–$40,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 3179.6 | 1 |
| 3 | I am the founder and technical decision maker. | Noted — having the founder or exec perspective helps keep delivery aligned. What would you like to explore next? | Book a call, See the MVP, See sample projects, Talk to a human | - | discovery | 24.2 | 0 |

*LLM Call Instrumentation (Turn, Purpose, Model, Wall ms, Thinking Tokens, Prompt Tokens, Output Tokens):*
| Turn | Purpose | Model | Wall ms | Thinking Tok | Prompt Tok | Output Tok |
|---|---|---|---|---|---|---|
| 1 | extractor | gemini-3.8-flash | 4585.8 | 0 | 945 | 212 |
| 2 | extractor | gemini-3.8-flash | 3112.5 | 0 | 1051 | 168 |

#### Scenario S2: Starter chip 'I'm just exploring costs'

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 19.6 | 0 |
| 1 | I'm just exploring costs | Understood, exploring preliminary costs helps shape the scope and feasibility early on. What core business outcome or user experience should this first launch deliver? | Book appointments, Manage customers, Take payments | - | discovery | 4155.7 | 1 |
| 2 | Mobile app | Understood, updating the target platform focus to a mobile application. What core business outcome or user experience should this first launch deliver? | Book appointments, Manage customers, Take payments | - | discovery | 2939.4 | 1 |
| 3 | Field service and asset tracking | Channels and UX: Flutter. Core flow: Asset tracking, Field service management. Backend and APIs: Node.js + PostgreSQL. When would you like the initial version in users' hands? | ASAP, 1–3 months, 3–6 months, Flexible | shape | discovery | 3870.0 | 1 |
| 4 | iOS and Android | Is there a target milestone or launch timeframe you have in mind? | ASAP, 1–3 months, 3–6 months, Flexible, Not sure yet, Not sure, suggest | - | discovery | 4173.1 | 1 |
| 5 | Offline data collection, barcode scanning, GPS tracking | Here's what I understood: a mobile app - Field service and asset tracking. Platforms: iOS and Android. Features: Asset tracking, Field service management, Offline data collection, Barcode scanning, and 1 more. Timeline: flexible timing. Budget: just exploring costs. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$29,500–$37,000 USD** over about **16 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 2954.0 | 1 |
| 6 | 1 to 3 months | Noted, I have updated your project brief. What would you like to explore next? | Book a call, See the MVP, See sample projects, Talk to a human | - | discovery | 3683.9 | 1 |
| 7 | $40k to $80k | Noted, I have updated your project brief. What would you like to explore next? | Book a call, See the MVP, See sample projects, Talk to a human | - | discovery | 4707.6 | 1 |
| 8 | Founder | Noted — having the founder or exec perspective helps keep delivery aligned. What would you like to explore next? | Book a call, See the MVP, See sample projects, Talk to a human | - | discovery | 4186.7 | 1 |

*LLM Call Instrumentation (Turn, Purpose, Model, Wall ms, Thinking Tokens, Prompt Tokens, Output Tokens):*
| Turn | Purpose | Model | Wall ms | Thinking Tok | Prompt Tok | Output Tok |
|---|---|---|---|---|---|---|
| 1 | extractor | gemini-3.8-flash | 4073.1 | 0 | 907 | 156 |
| 2 | extractor | gemini-3.8-flash | 2878.9 | 0 | 955 | 152 |
| 3 | extractor | gemini-3.8-flash | 3783.9 | 0 | 977 | 181 |
| 4 | extractor | gemini-3.8-flash | 4084.6 | 0 | 1028 | 162 |
| 5 | extractor | gemini-3.8-flash | 2889.3 | 0 | 1034 | 201 |
| 6 | extractor | gemini-3.8-flash | 3609.7 | 0 | 1067 | 206 |
| 7 | extractor | gemini-3.8-flash | 4633.7 | 0 | 1071 | 171 |
| 8 | synth | gemini-3.8-flash | 4115.0 | 0 | 98 | 80 |

#### Scenario S3: Starter chip 'I have an app idea' -> 'A marketplace for local farmers'

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 18.1 | 0 |
| 1 | I have an app idea | Tell me what your app does in a sentence or two — who is it for and what's the core workflow? | Mobile app, Web platform, AI product, UI/UX design | - | discovery | 5795.4 | 1 |
| 2 | A marketplace for local farmers | Building a two-sided marketplace for local farmers involves multi-vendor catalog management and transaction workflows. Which platforms should we target for the first launch — web, iOS, Android, or cross-platform mobile? | Web, API | - | discovery | 2914.0 | 1 |
| 3 | Web and mobile | Supporting both web and cross-platform mobile interfaces provides a unified experience across devices. What timeframe are you aiming for to get this initial software product into users' hands? | ASAP, 1–3 months, 3–6 months, Flexible | - | discovery | 3800.7 | 1 |
| 4 | Produce catalog, Stripe checkout, farmer payouts, direct chat | Channels and UX: Flutter. Core flow: Produce catalog, Stripe checkout, Farmer payouts. Backend and APIs: Node.js + PostgreSQL. When would you like the initial version in users' hands? | ASAP, 1–3 months, 3–6 months, Flexible | shape | discovery | 4321.9 | 1 |
| 5 | 3 to 6 months | A three to six month window gives sufficient runway for developing and testing both the core marketplace flows and payment mechanics. Which investment range should I size this initial build against for squad composition and architecture? | Still exploring, Under $15k, $15–40k, $40–80k, $80k+ | - | discovery | 3506.6 | 1 |
| 6 | $40k to $80k | Here's what I understood: a mobile app - marketplace for local farmers. Platforms: web, iOS and Android. Features: Produce catalog, Stripe checkout, Farmer payouts, Direct chat. Timeline: 3 to 6 months. Budget: $40k to $80k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$41,000–$51,000 USD** over about **22 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 3807.5 | 1 |
| 7 | Product lead | Noted — having the product or ops lead perspective helps keep delivery aligned. What would you like to explore next? | Book a call, See the MVP, See sample projects, Talk to a human | - | discovery | 23.9 | 0 |

*LLM Call Instrumentation (Turn, Purpose, Model, Wall ms, Thinking Tokens, Prompt Tokens, Output Tokens):*
| Turn | Purpose | Model | Wall ms | Thinking Tok | Prompt Tok | Output Tok |
|---|---|---|---|---|---|---|
| 1 | extractor | gemini-3.8-flash | 5730.7 | 0 | 906 | 153 |
| 2 | extractor | gemini-3.8-flash | 2847.7 | 0 | 906 | 166 |
| 3 | extractor | gemini-3.8-flash | 3730.7 | 0 | 948 | 163 |
| 4 | extractor | gemini-3.8-flash | 4254.2 | 0 | 999 | 225 |
| 5 | extractor | gemini-3.8-flash | 3434.4 | 0 | 1039 | 163 |
| 6 | extractor | gemini-3.8-flash | 3734.3 | 0 | 1063 | 212 |

#### Scenario S4: Seven-feature list in one message (triggers Scope Coach)

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 18.0 | 0 |
| 1 | I want a web app for clinic management. Features: patient booking, telemedicine video, prescriptions, billing, lab results, doctor scheduling, insurance verification. | Channels and UX: Next.js. Core flow: patient booking, telemedicine video, prescriptions. Backend and APIs: Node.js + PostgreSQL. When would you like the initial version in users' hands? | ASAP, 1–3 months, 3–6 months, Flexible | shape | discovery | 4403.7 | 1 |
| 2 | Web application | Is there a target milestone or launch timeframe you have in mind? | ASAP, 1–3 months, 3–6 months, Flexible, Not sure yet, Not sure, suggest | - | discovery | 4575.1 | 1 |
| 3 | 1 to 3 months | A one to three month target aligns with delivering core workflow modules through rapid iterative sprints. Which investment range should I size this initial build against for squad composition and architecture? | Still exploring, Under $15k, $15–40k, $40–80k, $80k+ | - | discovery | 4873.5 | 1 |
| 4 | $40k to $80k | Here's what I understood: a web application - Clinic management with telemedicine, scheduling, and billing capabilities. Platforms: web. Features: patient booking, telemedicine video, prescriptions, billing, and 3 more. Timeline: 1 to 3 months. Budget: $40k to $80k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$20,500–$25,500 USD** over about **8 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  This range assumes the Core scope; a list this long will likely need more, and the team can size it precisely. | Show the Core cut, Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 4335.3 | 1 |
| 5 | Founder | Noted, I have updated your project brief. What would you like to explore next? | Book a call, See the MVP, See sample projects, Talk to a human | - | discovery | 24.8 | 0 |

*LLM Call Instrumentation (Turn, Purpose, Model, Wall ms, Thinking Tokens, Prompt Tokens, Output Tokens):*
| Turn | Purpose | Model | Wall ms | Thinking Tok | Prompt Tok | Output Tok |
|---|---|---|---|---|---|---|
| 1 | extractor | gemini-3.8-flash | 4331.8 | 0 | 931 | 245 |
| 2 | extractor | gemini-3.8-flash | 4509.7 | 0 | 1055 | 155 |
| 3 | extractor | gemini-3.8-flash | 4812.1 | 0 | 1058 | 229 |
| 4 | extractor | gemini-3.8-flash | 4249.4 | 0 | 1087 | 260 |

#### Scenario S5: Hinglish: 'mujhe ek delivery app chahiye, iOS aur Android dono, 3 mahine me'

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 19.5 | 0 |
| 1 | mujhe ek delivery app chahiye, iOS aur Android dono, 3 mahine me | Channels and UX: Flutter. Core flow: delivery tracking or ordering. Backend and APIs: Node.js + PostgreSQL. A rough ballpark helps me size this, no commitment — which budget range makes sense? | Still exploring, Under $15k, $15–40k, $40–80k, $80k+ | shape | discovery | 3342.2 | 1 |
| 2 | Live order tracking, customer ratings, driver assignment | Real-time dispatching, driver assignment logic, and rating mechanisms will require a resilient WebSocket infrastructure and background location handling. Which investment range should I size this initial build against for squad composition and architecture? | Still exploring, Under $15k, $15–40k, $40–80k, $80k+ | - | discovery | 5536.1 | 1 |
| 3 | $15k to $40k | Here's what I understood: a mobile app - delivery app. Platforms: iOS and Android. Features: delivery tracking or ordering, Live order tracking, customer ratings, driver assignment. Timeline: 1 to 3 months. Budget: $15k to $40k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$29,500–$37,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 4975.1 | 1 |
| 4 | Founder | Noted — having the founder or exec perspective helps keep delivery aligned. What would you like to explore next? | Book a call, See the MVP, See sample projects, Talk to a human | - | discovery | 2762.7 | 1 |

*LLM Call Instrumentation (Turn, Purpose, Model, Wall ms, Thinking Tokens, Prompt Tokens, Output Tokens):*
| Turn | Purpose | Model | Wall ms | Thinking Tok | Prompt Tok | Output Tok |
|---|---|---|---|---|---|---|
| 1 | extractor | gemini-3.8-flash | 3278.1 | 0 | 918 | 184 |
| 2 | extractor | gemini-3.8-flash | 5456.2 | 0 | 1010 | 197 |
| 3 | extractor | gemini-3.8-flash | 4904.5 | 0 | 1045 | 207 |
| 4 | synth | gemini-3.8-flash | 2689.7 | 0 | 90 | 65 |

#### Scenario S6: Post-estimate technical questions, calendar slot booking, and post-booking ack

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 18.8 | 0 |
| 1 | We need a cross-platform mobile app for iOS and Android. | Developing a cross-platform mobile application targeting iOS and Android allows for a unified codebase and consistent user experience across devices. What core business outcome or user experience should this first launch deliver? | Book appointments, Manage customers, Take payments | - | discovery | 3871.8 | 1 |
| 2 | Fitness coaching app with workout logger and push notifications. | Channels and UX: Flutter. Core flow: Fitness coaching, Workout logger, Push notifications. Backend and APIs: Node.js + PostgreSQL. When would you like the initial version in users' hands? | ASAP, 1–3 months, 3–6 months, Flexible | shape | discovery | 5444.1 | 1 |
| 3 | Workout tracking, user profiles, video demonstrations | Captured the workout tracking, profile management, and video demonstration requirements. What is your target launch horizon for getting this first release live? | ASAP, 1–3 months, 3–6 months, Flexible | - | discovery | 4083.5 | 1 |
| 4 | 1 to 3 months | A one to three month timeline allows for an iterative build and thorough testing across both iOS and Android platforms. Which investment range should I size this initial build against for squad composition and architecture? | Still exploring, Under $15k, $15–40k, $40–80k, $80k+ | - | discovery | 2967.2 | 1 |
| 5 | $15k to $40k | Here's what I understood: a mobile app - Fitness coaching app with workout logger and push notifications. Platforms: iOS and Android. Features: Fitness coaching, Workout logger, Push notifications, Workout tracking, and 2 more. Timeline: 1 to 3 months. Budget: $15k to $40k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$29,500–$37,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 3545.9 | 1 |
| 6 | Founder | Noted — having the founder or exec perspective helps keep delivery aligned. What would you like to explore next? | Book a call, See the MVP, See sample projects, Talk to a human | - | discovery | 26.8 | 0 |
| 7 | Do you use Flutter? | We build modern web, mobile, and cloud solutions using frameworks like React, Node.js, Python, Flutter, and native cloud services on AWS, GCP, and Azure. | Book a meeting, See similar work | - | faq | 2764.1 | 0 |
| 8 | Which cloud do you use? | We help you weigh tradeoffs; Flutter or React Native works exceptionally well for fast time-to-market, while native Swift/Kotlin suits high-performance hardware needs. | Book a meeting, See similar work | - | faq | 4912.6 | 1 |
| 9 | Can you guarantee 4 weeks? | The timeline assumes a small senior team. If a date is fixed, we shrink the first release rather than promising the full product sooner. | Book a meeting, See similar work | - | objection | 1127.5 | 0 |
| 10 | Friday Oct 16, 3:00 PM UTC | You're booked for Fri Oct 16, 20:30 IST — Demo booking: no calendar invite is sent until Google Calendar is connected. Reply with your work email so the invite has somewhere to go. | Can I reschedule?, See similar work | booking | booking | 574.1 | 0 |
| 11 | cool thanks | You're all set for Fri Oct 16, 20:30 IST. The team will see this whole conversation, so you won't need to repeat anything. | What is on the agenda?, Can I reschedule the time? | - | ack | 22.8 | 0 |

*LLM Call Instrumentation (Turn, Purpose, Model, Wall ms, Thinking Tokens, Prompt Tokens, Output Tokens):*
| Turn | Purpose | Model | Wall ms | Thinking Tok | Prompt Tok | Output Tok |
|---|---|---|---|---|---|---|
| 1 | extractor | gemini-3.8-flash | 3789.6 | 0 | 914 | 167 |
| 2 | extractor | gemini-3.8-flash | 5370.3 | 0 | 963 | 179 |
| 3 | extractor | gemini-3.8-flash | 4020.0 | 0 | 1021 | 190 |
| 4 | extractor | gemini-3.8-flash | 2896.8 | 0 | 1050 | 205 |
| 5 | extractor | gemini-3.8-flash | 3476.9 | 0 | 1074 | 165 |
| 8 | synth | gemini-3.8-flash | 2920.7 | 0 | 115 | 74 |

#### Scenario S7: Natural chip path: Mobile app, goal text, feature chips, platform chip, timeline chip, budget chip, role chip

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 20.4 | 0 |
| 1 | Mobile app | Focusing on mobile app: noted. What core business outcome or user experience should this first launch deliver? | Book appointments, Manage customers, Take payments | - | discovery | 22.5 | 0 |
| 2 | A sports clinic booking application for direct patients | A dedicated booking system tailored for sports clinic patients requires clear scheduling flows and patient management architecture. Which platforms should we target for the first launch — web, iOS, Android, or cross-platform mobile? | iOS, Android, iOS and Android | - | discovery | 2419.4 | 1 |
| 3 | User login & profiles | appointment booking, User login & profiles gives us a solid foundation for the first release. Where will your target users primarily access this application — in a browser or on mobile devices? | iOS, Android, iOS and Android | - | discovery | 23.0 | 0 |
| 4 | Continue to next step → | Where would your target audience primarily use this — on mobile devices or in a web browser? | iOS, Android, iOS and Android, Not sure yet, Not sure, suggest | - | discovery | 23.7 | 0 |
| 5 | iOS and Android | Channels and UX: Flutter. Core flow: appointment booking, User login & profiles. Backend and APIs: Node.js + PostgreSQL. When would you like the initial version in users' hands? | ASAP, 1–3 months, 3–6 months, Flexible | shape | discovery | 25.3 | 0 |
| 6 | 1–3 months | Targeting 1 to 3 months gives us a defined delivery window. What rough budget scale makes sense for this first release to help calibrate our architecture recommendations? | Still exploring, Under $15k, $15–40k, $40–80k, $80k+ | - | discovery | 19.4 | 0 |
| 7 | $15–40k | Here's what I understood: a mobile app - sports clinic booking application for direct patients. Platforms: iOS and Android. Features: appointment booking, User login & profiles. Timeline: 1 to 3 months. Budget: $15k to $40k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$32,000–$40,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 26.8 | 0 |
| 8 | Founder / exec | Noted — having the founder or exec perspective helps keep delivery aligned. What would you like to explore next? | Book a call, See the MVP, See sample projects, Talk to a human | - | discovery | 3904.8 | 1 |

*LLM Call Instrumentation (Turn, Purpose, Model, Wall ms, Thinking Tokens, Prompt Tokens, Output Tokens):*
| Turn | Purpose | Model | Wall ms | Thinking Tok | Prompt Tok | Output Tok |
|---|---|---|---|---|---|---|
| 2 | extractor | gemini-3.8-flash | 2355.8 | 0 | 932 | 168 |
| 8 | synth | gemini-3.8-flash | 3830.4 | 0 | 94 | 84 |

#### Scenario S8: Out-of-order answers (the old S3 script)

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 21.6 | 0 |
| 1 | I have an app idea | Understood, developing a custom application starts with defining the target platform and core user workflow. What core business outcome or user experience should this first launch deliver? | Book appointments, Manage customers, Take payments | - | discovery | 2601.5 | 1 |
| 2 | A marketplace for local farmers | A two-sided marketplace architecture will help connect local growers directly with buyers. Which platforms should we target for the first launch — web, iOS, Android, or cross-platform mobile? | iOS, Android, iOS and Android | - | discovery | 4419.7 | 1 |
| 3 | Web and mobile | Targeting both web and mobile will ensure broad reach across desktop and mobile devices for the marketplace. What is your target launch horizon for getting this first release live? | ASAP, 1–3 months, 3–6 months, Flexible | - | discovery | 3381.5 | 1 |
| 4 | Produce catalog, Stripe checkout, farmer payouts, direct chat | Channels and UX: Flutter. Core flow: Produce catalog, Stripe checkout, Farmer payouts. Backend and APIs: Node.js + PostgreSQL. When would you like the initial version in users' hands? | ASAP, 1–3 months, 3–6 months, Flexible | shape | discovery | 2802.5 | 1 |
| 5 | 3 to 6 months | A three to six month delivery window provides adequate runway for architecting both mobile platforms alongside the payment and chat workflows. What rough budget scale makes sense for this first release to help calibrate our architecture recommendations? | Still exploring, Under $15k, $15–40k, $40–80k, $80k+ | - | discovery | 2895.7 | 1 |
| 6 | $40k to $80k | Here's what I understood: a mobile app - marketplace for local farmers. Platforms: web, iOS and Android. Features: Produce catalog, Stripe checkout, Farmer payouts, Direct chat. Timeline: 3 to 6 months. Budget: $40k to $80k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$41,000–$51,000 USD** over about **22 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 2938.6 | 1 |
| 7 | Product lead | Noted — having the product or ops lead perspective helps keep delivery aligned. What would you like to explore next? | Book a call, See the MVP, See sample projects, Talk to a human | - | discovery | 30.6 | 0 |

*LLM Call Instrumentation (Turn, Purpose, Model, Wall ms, Thinking Tokens, Prompt Tokens, Output Tokens):*
| Turn | Purpose | Model | Wall ms | Thinking Tok | Prompt Tok | Output Tok |
|---|---|---|---|---|---|---|
| 1 | extractor | gemini-3.8-flash | 2534.8 | 0 | 906 | 157 |
| 2 | extractor | gemini-3.8-flash | 4338.1 | 0 | 929 | 160 |
| 3 | extractor | gemini-3.8-flash | 3312.9 | 0 | 959 | 166 |
| 4 | extractor | gemini-3.8-flash | 2727.1 | 0 | 1010 | 191 |
| 5 | extractor | gemini-3.8-flash | 2828.7 | 0 | 1045 | 199 |
| 6 | extractor | gemini-3.8-flash | 2857.7 | 0 | 1069 | 166 |

#### Scenario S9: First message is only a budget: 'my budget is $40k to $80k'

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 22.1 | 0 |
| 1 | my budget is $40k to $80k | Understood, that target range gives us a clear framework for defining architecture and release scope. What primary problem or user workflow should this initial release solve? | Book appointments, Manage customers, Take payments | - | discovery | 3289.7 | 1 |
| 2 | Mobile app | Understood, updating the target platform focus to a native or cross-platform mobile application architecture. What primary problem or user workflow should this initial release solve? | Book appointments, Manage customers, Take payments | - | discovery | 2799.1 | 1 |
| 3 | An on-demand tutor marketplace | Building a two-sided marketplace for on-demand tutoring requires robust matching algorithms, scheduling, and reliable communication channels. What is your target launch horizon for getting this first release live? | ASAP, 1–3 months, 3–6 months, Flexible | - | discovery | 5119.0 | 1 |
| 4 | iOS and Android | Is there a target milestone or launch timeframe you have in mind? | ASAP, 1–3 months, 3–6 months, Flexible, Not sure yet, Not sure, suggest | - | discovery | 2577.8 | 1 |
| 5 | Matching algorithm, in-app messaging, tutor reviews | Here's what I understood: a mobile app - on-demand tutor marketplace. Platforms: iOS and Android. Features: Matching algorithm, In-app messaging, Tutor reviews. Timeline: flexible timing. Budget: $40k to $80k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$38,000–$47,500 USD** over about **25 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 3256.0 | 1 |
| 6 | 1 to 3 months | Noted, I have updated your project brief. What would you like to explore next? | Book a call, See the MVP, See sample projects, Talk to a human | - | discovery | 3245.3 | 1 |
| 7 | Founder | Noted — having the founder or exec perspective helps keep delivery aligned. What would you like to explore next? | Book a call, See the MVP, See sample projects, Talk to a human | - | discovery | 28.1 | 0 |

*LLM Call Instrumentation (Turn, Purpose, Model, Wall ms, Thinking Tokens, Prompt Tokens, Output Tokens):*
| Turn | Purpose | Model | Wall ms | Thinking Tok | Prompt Tok | Output Tok |
|---|---|---|---|---|---|---|
| 1 | extractor | gemini-3.8-flash | 3207.1 | 0 | 913 | 168 |
| 2 | extractor | gemini-3.8-flash | 2725.7 | 0 | 964 | 163 |
| 3 | extractor | gemini-3.8-flash | 5043.9 | 0 | 987 | 180 |
| 4 | extractor | gemini-3.8-flash | 2512.0 | 0 | 1017 | 157 |
| 5 | extractor | gemini-3.8-flash | 3189.9 | 0 | 1024 | 203 |
| 6 | extractor | gemini-3.8-flash | 3186.2 | 0 | 1051 | 201 |

#### Scenario S10: Starter 'I have an app idea' -> 'a booking app for barbers' -> 'web and mobile'

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 18.5 | 0 |
| 1 | I have an app idea | Scoped development begins with mapping out the core user journey and target platform requirements. What core business outcome or user experience should this first launch deliver? | Book appointments, Manage customers, Take payments | - | discovery | 4692.8 | 1 |
| 2 | a booking app for barbers | A barber booking system requires structured scheduling workflows and calendar management for both service providers and clients. Which platforms should we target for the first launch — web, iOS, Android, or cross-platform mobile? | iOS, Android, iOS and Android | - | discovery | 2651.8 | 1 |
| 3 | web and mobile | Channels and UX: Flutter. Core flow: appointment booking. Backend and APIs: Node.js + PostgreSQL. When would you like the initial version in users' hands? | ASAP, 1–3 months, 3–6 months, Flexible | shape | discovery | 2569.9 | 1 |
| 4 | Appointment scheduling, barber portfolio, customer SMS alerts, loyalty points, payment processing | Captured the core feature set covering scheduling, SMS notifications, loyalty rewards, and secure payment processing. What timeframe are you aiming for to get this initial software product into users' hands? | ASAP, 1–3 months, 3–6 months, Flexible | - | discovery | 3087.1 | 1 |
| 5 | 1–3 months | Targeting 1 to 3 months gives us a defined delivery window. Which investment range should I size this initial build against for squad composition and architecture? | Still exploring, Under $15k, $15–40k, $40–80k, $80k+ | - | discovery | 24.3 | 0 |
| 6 | $15–40k | Here's what I understood: a mobile app - booking app for barbers. Platforms: web, iOS and Android. Features: appointment booking, Appointment scheduling, barber portfolio, customer SMS alerts, and 2 more. Timeline: 1 to 3 months. Budget: $15k to $40k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$32,000–$40,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 25.4 | 0 |
| 7 | Founder / exec | Noted — having the founder or exec perspective helps keep delivery aligned. What would you like to explore next? | Book a call, See the MVP, See sample projects, Talk to a human | - | discovery | 20.1 | 0 |

*LLM Call Instrumentation (Turn, Purpose, Model, Wall ms, Thinking Tokens, Prompt Tokens, Output Tokens):*
| Turn | Purpose | Model | Wall ms | Thinking Tok | Prompt Tok | Output Tok |
|---|---|---|---|---|---|---|
| 1 | extractor | gemini-3.8-flash | 4613.6 | 301 | 906 | 154 |
| 2 | extractor | gemini-3.8-flash | 2596.3 | 0 | 929 | 165 |
| 3 | extractor | gemini-3.8-flash | 2498.1 | 0 | 969 | 161 |
| 4 | extractor | gemini-3.8-flash | 3004.6 | 0 | 1038 | 231 |

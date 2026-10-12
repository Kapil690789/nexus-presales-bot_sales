# DEMO TRANSCRIPTS & QA CHECKS (QA-3 STRICT VALIDATION)

Generated: 2026-10-12 07:16:31 UTC
Primary model configured: `gemini-3.8-flash` (thinkingLevel: `low`)

## Section 1: In-Process Deterministic Stub (Offline / Fallback)

### 1. QA Checks Summary Table (QA-3 Strict Validation)

| Scenario | Title | Opener | Max 2Sent/320c | Brief Match | Recap Exact | No Recap Reps | Objection Valid | No Guard Pre-Est | No Dup Bot | Est Once | Banned Strings | Latency & Calls | Turns to Est |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **S1** | Long comprehensive initial m... | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 3 |
| **S2** | Starter chip 'I'm just explo... | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 8 |
| **S3** | Starter chip 'I have an app ... | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 7 |
| **S4** | Seven-feature list in one me... | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 4 |
| **S5** | Hinglish: 'mujhe ek delivery... | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 4 |
| **S6** | Post-estimate technical ques... | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 6 |
| **S7** | Natural chip path: Mobile ap... | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 8 |
| **S8** | Out-of-order answers (the ol... | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 7 |
| **S9** | First message is only a budg... | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 7 |
| **S10** | Starter 'I have an app idea'... | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 7 |

### 2. Scenario Latency & Call Statistics

| Scenario | Turns | Median (s) | p95 (s) | Max (s) | Max Calls/Turn | Pass/Fail |
|---|---|---|---|---|---|---|
| **S1** | 3 | 0.02s | 0.03s | 0.03s | 0 | ✓ PASS |
| **S2** | 8 | 0.02s | 0.02s | 0.02s | 0 | ✓ PASS |
| **S3** | 7 | 0.02s | 0.05s | 0.05s | 0 | ✓ PASS |
| **S4** | 5 | 0.02s | 0.03s | 0.03s | 0 | ✓ PASS |
| **S5** | 4 | 0.02s | 0.03s | 0.03s | 0 | ✓ PASS |
| **S6** | 11 | 0.02s | 0.69s | 0.69s | 0 | ✓ PASS |
| **S7** | 8 | 0.02s | 0.03s | 0.03s | 0 | ✓ PASS |
| **S8** | 7 | 0.02s | 0.02s | 0.02s | 0 | ✓ PASS |
| **S9** | 7 | 0.02s | 0.02s | 0.02s | 0 | ✓ PASS |
| **S10** | 7 | 0.02s | 0.03s | 0.03s | 0 | ✓ PASS |

### 3. Full Turn-by-Turn Transcripts & LLM Instrumentation

#### Scenario S1: Long comprehensive initial message with platforms, features, budget, and timeline

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 84.0 | 0 |
| 1 | We want it on both iOS and Android. For the first release we just need login, calendar booking, and push notifications. Budget around $25k to $35k, 2 to 3 months. | Here is the architectural shape: Flutter for Channels and UX, Core flow: Primary user journey on the agre, login, calendar booking, and Node.js + PostgreSQL for Backend and APIs. What should this first version actually do for people? | Book appointments, Manage customers, Take payments | shape | discovery | 30.1 | 0 |
| 2 | I am building a sports clinic booking application for direct patients. | sports clinic booking application for direct patients: that gives me a clear picture. Who will be using this first — direct consumers, business clients, or internal team members? | Consumers, Business users, Internal team | - | discovery | 19.8 | 0 |
| 3 | I am the founder and technical decision maker. | Here's what I understood: a mobile app - sports clinic booking application for direct patients. Platforms: iOS and Android. Features: login, calendar booking, push notifications. Timeline: 1 to 3 months. Budget: around $25k to $35k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$32,000–$40,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 24.2 | 0 |

#### Scenario S2: Starter chip 'I'm just exploring costs'

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 17.0 | 0 |
| 1 | I'm just exploring costs | Happy to help you explore costs. What are you thinking of building: a mobile app, a web platform, AI, or design? | Mobile app, Web platform, AI product, UI/UX design | - | discovery | 20.8 | 0 |
| 2 | Mobile app | iOS and Android, noted. What primary problem or user workflow should this initial release solve? | Book appointments, Manage customers, Take payments | - | discovery | 18.0 | 0 |
| 3 | Field service and asset tracking | Field service and asset tracking: that gives me a clear picture. Which core capabilities or features are essential for the launch? | User login & profiles, In-app payments, Push notifications, Search & discovery, Not sure yet | - | discovery | 19.3 | 0 |
| 4 | iOS and Android | What essential building blocks or capabilities do you envision for the initial release? | User login & profiles, In-app payments, Push notifications, Search & discovery, Not sure yet, Not sure, suggest | - | discovery | 17.7 | 0 |
| 5 | Offline data collection, barcode scanning, GPS tracking | Here is the architectural shape: Flutter for Channels and UX, Core flow: Field service and asset tracking, Offline data collection, barcode scanning, and Node.js + PostgreSQL for Backend and APIs. Who is the first person this should work well for? | Consumers, Business users, Internal team | shape | discovery | 20.9 | 0 |
| 6 | 1 to 3 months | Working toward 1 to 3 months sets the development pace. Will the first release need integrations with existing databases, auth providers, or third-party APIs? | None on day one, Payments, CRM | - | discovery | 24.5 | 0 |
| 7 | $40k to $80k | What is your role on the project when architecture and delivery decisions are made? | Founder / exec, Product or ops, Manager, Student / intern | - | discovery | 21.9 | 0 |
| 8 | Founder | Here's what I understood: a mobile app - Field service and asset tracking. Platforms: iOS and Android. Features: Offline data collection, barcode scanning, GPS tracking. Timeline: 1 to 3 months. Budget: $40k to $80k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$29,500–$37,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band is above this first-pass range, so there is room to add scope. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 20.4 | 0 |

#### Scenario S3: Starter chip 'I have an app idea' -> 'A marketplace for local farmers'

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 21.8 | 0 |
| 1 | I have an app idea | Tell me what your app does in a sentence or two — who is it for and what's the core workflow? | Mobile app, Web platform, AI product, UI/UX design | - | discovery | 23.7 | 0 |
| 2 | A marketplace for local farmers | Focusing on marketplace for local farmers: clear priority. What essential building blocks must be ready on day one for users? | User authentication, Payment checkout, Admin dashboard, Analytics & reports, Not sure yet | - | discovery | 54.5 | 0 |
| 3 | Web and mobile | Targeting web, iOS and Android sets our technical architecture. Which core capabilities or features are essential for the launch? | User login & profiles, In-app payments, Push notifications, Search & discovery, Not sure yet | - | discovery | 19.5 | 0 |
| 4 | Produce catalog, Stripe checkout, farmer payouts, direct chat | Here is the architectural shape: Flutter for Channels and UX, Core flow: marketplace for local farmers, Produce catalog, Stripe checkout, and Node.js + PostgreSQL for Backend and APIs. Who is the first person this should work well for? | Consumers, Business users, Internal team | shape | discovery | 17.8 | 0 |
| 5 | 3 to 6 months | Working toward 3 to 6 months sets the development pace. Are there any external services or APIs this must connect with on day one, like payments or CRM? | None on day one, Payments, CRM | - | discovery | 23.1 | 0 |
| 6 | $40k to $80k | Are you leading this as founder, product manager, operations lead, or another role? | Founder / exec, Product or ops, Manager, Student / intern | - | discovery | 19.7 | 0 |
| 7 | Product lead | Here's what I understood: a mobile app - marketplace for local farmers. Platforms: web, iOS and Android. Features: Produce catalog, Stripe checkout, farmer payouts, direct chat. Timeline: 3 to 6 months. Budget: $40k to $80k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$38,000–$47,500 USD** over about **22 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 24.6 | 0 |

#### Scenario S4: Seven-feature list in one message (triggers Scope Coach)

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 17.5 | 0 |
| 1 | I want a web app for clinic management. Features: patient booking, telemedicine video, prescriptions, billing, lab results, doctor scheduling, insurance verification. | Here is the architectural shape: Next.js for Channels and UX, Core flow: I want a web app for clinic mana, patient booking, telemedicine video, and Node.js + PostgreSQL for Backend and APIs. Who is the first person this should work well for? | Consumers, Business users, Internal team | shape | discovery | 27.1 | 0 |
| 2 | Web application | Who do you picture using this first — end consumers, business clients, or your own team? | Consumers, Business users, Internal team, Not sure yet, Not sure, suggest | - | discovery | 23.7 | 0 |
| 3 | 1 to 3 months | Targeting 1 to 3 months gives us a defined delivery window. Will the first release need integrations with existing databases, auth providers, or third-party APIs? | None on day one, Payments, CRM | - | discovery | 19.5 | 0 |
| 4 | $40k to $80k | Here's what I understood: a web application - for clinic management. Platforms: web. Features: patient booking, telemedicine video, prescriptions, billing, and 3 more. Timeline: 1 to 3 months. Budget: $40k to $80k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$19,000–$24,000 USD** over about **8 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  This range assumes the Core scope; a list this long will likely need more, and the team can size it precisely. | Show the Core cut, Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 20.5 | 0 |
| 5 | Founder | Noted, I have updated your project brief. What would you like to explore next? | Book a call, See the MVP, See sample projects, Talk to a human | - | discovery | 28.5 | 0 |

#### Scenario S5: Hinglish: 'mujhe ek delivery app chahiye, iOS aur Android dono, 3 mahine me'

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 17.6 | 0 |
| 1 | mujhe ek delivery app chahiye, iOS aur Android dono, 3 mahine me | Focusing on mujhe ek delivery app chahiye, iOS aur Android: clear priority. What essential building blocks must be ready on day one for users? | User login & profiles, In-app payments, Push notifications, Search & discovery, Not sure yet | - | discovery | 22.3 | 0 |
| 2 | Live order tracking, customer ratings, driver assignment | Here is the architectural shape: Flutter for Channels and UX, Core flow: mujhe ek delivery app chahiye, i, Live order tracking, customer ratings, and Node.js + PostgreSQL for Backend and APIs. Who is the first person this should work well for? | Consumers, Business users, Internal team | shape | discovery | 19.9 | 0 |
| 3 | $15k to $40k | Are there any external services or APIs this must connect with on day one, like payments or CRM? | None on day one, Payments, CRM | - | discovery | 19.5 | 0 |
| 4 | Founder | Here's what I understood: a mobile app - mujhe ek delivery app chahiye. Platforms: iOS and Android. Features: Live order tracking, customer ratings, driver assignment. Timeline: 1 to 3 months. Budget: $15k to $40k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$29,500–$37,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 34.8 | 0 |

#### Scenario S6: Post-estimate technical questions, calendar slot booking, and post-booking ack

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 14.8 | 0 |
| 1 | We need a cross-platform mobile app for iOS and Android. | Targeting iOS and Android sets our technical architecture. What primary problem or user workflow should this initial release solve? | Book appointments, Manage customers, Take payments | - | discovery | 19.7 | 0 |
| 2 | Fitness coaching app with workout logger and push notifications. | Here is the architectural shape: Flutter for Channels and UX, Core flow: Fitness coaching app, workout logger, push notifications, and Node.js + PostgreSQL for Backend and APIs. Who is the first person this should work well for? | Consumers, Business users, Internal team | shape | discovery | 18.2 | 0 |
| 3 | Workout tracking, user profiles, video demonstrations | Are there any external services or APIs this must connect with on day one, like payments or CRM? | None on day one, Payments, CRM | - | discovery | 21.2 | 0 |
| 4 | 1 to 3 months | Working toward 1 to 3 months sets the development pace. Which investment range should I size this initial build against for squad composition and architecture? | Still exploring, Under $15k, $15–40k, $40–80k, $80k+ | - | discovery | 18.5 | 0 |
| 5 | $15k to $40k | What is your role on the project when architecture and delivery decisions are made? | Founder / exec, Product or ops, Manager, Student / intern | - | discovery | 24.2 | 0 |
| 6 | Founder | Here's what I understood: a mobile app - Fitness coaching app. Platforms: iOS and Android. Features: workout logger, push notifications. Timeline: 1 to 3 months. Budget: $15k to $40k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$29,500–$37,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 23.1 | 0 |
| 7 | Do you use Flutter? | Our engineering team can go into detail on those specific technical requirements on a discovery call. | Book a meeting, See similar work | - | fallback | 31.9 | 0 |
| 8 | Which cloud do you use? | We can dive deeper into that architecture and technical setup during a quick discovery call. | Book a meeting, See similar work | - | fallback | 26.0 | 0 |
| 9 | Can you guarantee 4 weeks? | Our engineering team can go into detail on those specific technical requirements on a discovery call. | Book a meeting, See similar work | - | fallback | 28.9 | 0 |
| 10 | Friday Oct 16, 3:00 PM UTC | You're booked for Fri Oct 16, 20:30 IST — Demo booking: no calendar invite is sent until Google Calendar is connected. Reply with your work email so the invite has somewhere to go. | Can I reschedule?, See similar work | booking | booking | 686.3 | 0 |
| 11 | cool thanks | You're all set for Fri Oct 16, 20:30 IST. The team will see this whole conversation, so you won't need to repeat anything. | What is on the agenda?, Can I reschedule the time? | - | ack | 23.6 | 0 |

#### Scenario S7: Natural chip path: Mobile app, goal text, feature chips, platform chip, timeline chip, budget chip, role chip

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 19.2 | 0 |
| 1 | Mobile app | mobile app, understood. What core business outcome or user experience should this first launch deliver? | Book appointments, Manage customers, Take payments | - | discovery | 24.3 | 0 |
| 2 | A sports clinic booking application for direct patients | Focusing on sports clinic booking application for direct patients: clear priority. Which core capabilities or features are essential for the launch? | User login & profiles, In-app payments, Push notifications, Search & discovery, Not sure yet | - | discovery | 18.3 | 0 |
| 3 | User login & profiles | Focusing on User login & profiles establishes a clear core scope. Added User login & profiles — any other features for the launch, or ready to continue? | Continue to next step →, + User login & profiles, + In-app payments, + Push notifications, Ready with this list | - | discovery | 24.9 | 0 |
| 4 | Continue to next step → | What should each of User login & profiles do in the first version? | That's enough | - | discovery | 20.3 | 0 |
| 5 | iOS and Android | Here is the architectural shape: Flutter for Channels and UX, Core flow: A sports clinic booking applicat, User login & profiles, Primary user journey on the agre, and Node.js + PostgreSQL for Backend and APIs. Who is the first person this should work well for? | Consumers, Business users, Internal team | shape | discovery | 21.8 | 0 |
| 6 | 1–3 months | Working toward 1 to 3 months sets the development pace. Are there any external services or APIs this must connect with on day one, like payments or CRM? | None on day one, Payments, CRM | - | discovery | 25.1 | 0 |
| 7 | $15–40k | What is your role on the project when architecture and delivery decisions are made? | Founder / exec, Product or ops, Manager, Student / intern | - | discovery | 19.0 | 0 |
| 8 | Founder / exec | Here's what I understood: a mobile app - sports clinic booking application for direct patients. Platforms: iOS and Android. Features: User login & profiles. Timeline: 1 to 3 months. Budget: $15k to $40k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$32,000–$40,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 19.9 | 0 |

#### Scenario S8: Out-of-order answers (the old S3 script)

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 52.0 | 0 |
| 1 | I have an app idea | Tell me what your app does in a sentence or two — who is it for and what's the core workflow? | Mobile app, Web platform, AI product, UI/UX design | - | discovery | 21.9 | 0 |
| 2 | A marketplace for local farmers | Focusing on marketplace for local farmers: clear priority. What essential building blocks must be ready on day one for users? | User authentication, Payment checkout, Admin dashboard, Analytics & reports, Not sure yet | - | discovery | 19.5 | 0 |
| 3 | Web and mobile | web, iOS and Android, noted. What essential building blocks must be ready on day one for users? | User login & profiles, In-app payments, Push notifications, Search & discovery, Not sure yet | - | discovery | 17.1 | 0 |
| 4 | Produce catalog, Stripe checkout, farmer payouts, direct chat | Here is the architectural shape: Flutter for Channels and UX, Core flow: marketplace for local farmers, Produce catalog, Stripe checkout, and Node.js + PostgreSQL for Backend and APIs. Who is the first person this should work well for? | Consumers, Business users, Internal team | shape | discovery | 17.6 | 0 |
| 5 | 3 to 6 months | Targeting 3 to 6 months gives us a defined delivery window. Are there any external services or APIs this must connect with on day one, like payments or CRM? | None on day one, Payments, CRM | - | discovery | 23.7 | 0 |
| 6 | $40k to $80k | Are you leading this as founder, product manager, operations lead, or another role? | Founder / exec, Product or ops, Manager, Student / intern | - | discovery | 20.4 | 0 |
| 7 | Product lead | Here's what I understood: a mobile app - marketplace for local farmers. Platforms: web, iOS and Android. Features: Produce catalog, Stripe checkout, farmer payouts, direct chat. Timeline: 3 to 6 months. Budget: $40k to $80k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$38,000–$47,500 USD** over about **22 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 20.0 | 0 |

#### Scenario S9: First message is only a budget: 'my budget is $40k to $80k'

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 21.4 | 0 |
| 1 | my budget is $40k to $80k | What primary problem or user workflow should this initial release solve? | Book appointments, Manage customers, Take payments | - | discovery | 23.4 | 0 |
| 2 | Mobile app | Targeting iOS and Android sets our technical architecture. What core business outcome or user experience should this first launch deliver? | Book appointments, Manage customers, Take payments | - | discovery | 16.5 | 0 |
| 3 | An on-demand tutor marketplace | on-demand tutor marketplace: that gives me a clear picture. What essential building blocks must be ready on day one for users? | User login & profiles, In-app payments, Push notifications, Search & discovery, Not sure yet | - | discovery | 18.3 | 0 |
| 4 | iOS and Android | What essential building blocks or capabilities do you envision for the initial release? | User login & profiles, In-app payments, Push notifications, Search & discovery, Not sure yet, Not sure, suggest | - | discovery | 23.9 | 0 |
| 5 | Matching algorithm, in-app messaging, tutor reviews | Here is the architectural shape: Flutter for Channels and UX, Core flow: An on-demand tutor marketplace, Matching algorithm, in-app messaging, and Node.js + PostgreSQL for Backend and APIs. Who is the first person this should work well for? | Consumers, Business users, Internal team | shape | discovery | 21.4 | 0 |
| 6 | 1 to 3 months | Targeting 1 to 3 months gives us a defined delivery window. Are there any external services or APIs this must connect with on day one, like payments or CRM? | None on day one, Payments, CRM | - | discovery | 24.5 | 0 |
| 7 | Founder | Here's what I understood: a mobile app - on-demand tutor marketplace. Platforms: iOS and Android. Features: Matching algorithm, in-app messaging, tutor reviews. Timeline: 1 to 3 months. Budget: my budget is $40k to $80k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$38,000–$47,500 USD** over about **22 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 20.3 | 0 |

#### Scenario S10: Starter 'I have an app idea' -> 'a booking app for barbers' -> 'web and mobile'

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 20.3 | 0 |
| 1 | I have an app idea | Tell me what your app does in a sentence or two — who is it for and what's the core workflow? | Mobile app, Web platform, AI product, UI/UX design | - | discovery | 21.0 | 0 |
| 2 | a booking app for barbers | booking app for barbers: that gives me a clear picture. What essential building blocks must be ready on day one for users? | User authentication, Payment checkout, Admin dashboard, Analytics & reports, Not sure yet | - | discovery | 30.6 | 0 |
| 3 | web and mobile | Targeting web, iOS and Android sets our technical architecture. What essential building blocks must be ready on day one for users? | User login & profiles, In-app payments, Push notifications, Search & discovery, Not sure yet | - | discovery | 20.1 | 0 |
| 4 | Appointment scheduling, barber portfolio, customer SMS alerts, loyalty points, payment processing | Here is the architectural shape: Flutter for Channels and UX, Core flow: a booking app for barbers, Appointment scheduling, barber portfolio, and Node.js + PostgreSQL for Backend and APIs. Who is the first person this should work well for? | Consumers, Business users, Internal team | shape | discovery | 22.8 | 0 |
| 5 | 1–3 months | Working toward 1 to 3 months sets the development pace. Will the first release need integrations with existing databases, auth providers, or third-party APIs? | None on day one, Payments, CRM | - | discovery | 19.1 | 0 |
| 6 | $15–40k | Are you leading this as founder, product manager, operations lead, or another role? | Founder / exec, Product or ops, Manager, Student / intern | - | discovery | 20.1 | 0 |
| 7 | Founder / exec | Here's what I understood: a mobile app - booking app for barbers. Platforms: web, iOS and Android. Features: Appointment scheduling, barber portfolio, customer SMS alerts, loyalty points, and 1 more. Timeline: 1 to 3 months. Budget: $15k to $40k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$29,500–$37,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 22.1 | 0 |

## Section 2: Live LLM Evaluation (Primary Provider: gemini-3.8-flash)

### 1. QA Checks Summary Table (QA-3 Strict Validation)

| Scenario | Title | Opener | Max 2Sent/320c | Brief Match | Recap Exact | No Recap Reps | Objection Valid | No Guard Pre-Est | No Dup Bot | Est Once | Banned Strings | Latency & Calls | Turns to Est |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **S1** | Long comprehensive initial m... | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 3 |
| **S2** | Starter chip 'I'm just explo... | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 8 |
| **S3** | Starter chip 'I have an app ... | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | 7 |
| **S4** | Seven-feature list in one me... | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 4 |
| **S5** | Hinglish: 'mujhe ek delivery... | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 4 |
| **S6** | Post-estimate technical ques... | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 6 |
| **S7** | Natural chip path: Mobile ap... | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 8 |
| **S8** | Out-of-order answers (the ol... | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 7 |
| **S9** | First message is only a budg... | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | 7 |
| **S10** | Starter 'I have an app idea'... | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 7 |

### 2. Scenario Latency & Call Statistics

| Scenario | Turns | Median (s) | p95 (s) | Max (s) | Max Calls/Turn | Pass/Fail |
|---|---|---|---|---|---|---|
| **S1** | 3 | 3.26s | 3.38s | 3.38s | 1 | ✓ PASS |
| **S2** | 8 | 3.38s | 3.99s | 3.99s | 1 | ✓ PASS |
| **S3** | 7 | 3.13s | 10.66s | 10.66s | 1 | ✗ FAIL |
| **S4** | 5 | 3.01s | 3.94s | 3.94s | 1 | ✓ PASS |
| **S5** | 4 | 3.22s | 3.59s | 3.59s | 1 | ✓ PASS |
| **S6** | 11 | 2.81s | 4.14s | 4.14s | 1 | ✓ PASS |
| **S7** | 8 | 0.02s | 2.87s | 2.87s | 1 | ✓ PASS |
| **S8** | 7 | 2.95s | 4.03s | 4.03s | 1 | ✓ PASS |
| **S9** | 7 | 3.14s | 8.67s | 8.67s | 1 | ✗ FAIL |
| **S10** | 7 | 2.69s | 3.47s | 3.47s | 1 | ✓ PASS |

### 3. Full Turn-by-Turn Transcripts & LLM Instrumentation

#### Scenario S1: Long comprehensive initial message with platforms, features, budget, and timeline

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 21.6 | 0 |
| 1 | We want it on both iOS and Android. For the first release we just need login, calendar booking, and push notifications. Budget around $25k to $35k, 2 to 3 months. | Here is the architectural shape: Flutter for Channels and UX, Core flow: Primary user journey on the agre, login, calendar booking, and Node.js + PostgreSQL for Backend and APIs. What should this first version actually do for people? | Book appointments, Manage customers, Take payments | shape | discovery | 3065.3 | 1 |
| 2 | I am building a sports clinic booking application for direct patients. | A sports clinic scheduling platform tailored for patients aligns well with the planned calendar and mobile notification architecture. Are there any external services or APIs this must connect with on day one, like payments or CRM? | None on day one, Payments, CRM | - | discovery | 3377.9 | 1 |
| 3 | I am the founder and technical decision maker. | Here's what I understood: a mobile app - sports clinic booking application for direct patients. Platforms: iOS and Android. Features: login, calendar booking, push notifications. Timeline: 1 to 3 months. Budget: around $25k to $35k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$32,000–$40,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 3260.9 | 1 |

*LLM Call Instrumentation (Turn, Purpose, Model, Wall ms, Thinking Tokens, Prompt Tokens, Output Tokens):*
| Turn | Purpose | Model | Wall ms | Thinking Tok | Prompt Tok | Output Tok |
|---|---|---|---|---|---|---|
| 1 | extractor | gemini-3.8-flash | 3000.2 | 0 | 945 | 210 |
| 2 | extractor | gemini-3.8-flash | 3317.4 | 0 | 1048 | 215 |
| 3 | extractor | gemini-3.8-flash | 3188.8 | 0 | 1075 | 157 |

#### Scenario S2: Starter chip 'I'm just exploring costs'

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 17.5 | 0 |
| 1 | I'm just exploring costs | Understood, we can walk through ballpark ranges once the high-level scope and platform requirements are clearer. What core business outcome or user experience should this first launch deliver? | Book appointments, Manage customers, Take payments | - | discovery | 3142.6 | 1 |
| 2 | Mobile app | Understood, scoping this as a mobile application. What core business outcome or user experience should this first launch deliver? | Book appointments, Manage customers, Take payments | - | discovery | 3248.6 | 1 |
| 3 | Field service and asset tracking | Here is the architectural shape: Flutter for Channels and UX, Core flow: Field service and asset tracking, asset tracking, field service management, and Node.js + PostgreSQL for Backend and APIs. Any systems this needs to talk to on day one? | None on day one, Payments, CRM | shape | discovery | 3665.2 | 1 |
| 4 | iOS and Android | Will this connect with any outside systems, like payments, email, or a CRM? | None on day one, Payments, CRM, Not sure yet, Not sure, suggest | - | discovery | 2723.5 | 1 |
| 5 | Offline data collection, barcode scanning, GPS tracking | Supporting offline data synchronization alongside hardware-level barcode scanning and continuous GPS tracking requires robust local caching and background state management. What is your target launch horizon for getting this first release live? | ASAP, 1–3 months, 3–6 months, Flexible | - | discovery | 3515.9 | 1 |
| 6 | 1 to 3 months | A 1 to 3 month delivery window provides a solid target for scoping out the core offline and tracking features. Are you leading this as founder, product manager, operations lead, or another role? | Founder / exec, Product or ops, Manager, Student / intern | - | discovery | 2936.2 | 1 |
| 7 | $40k to $80k | That target range aligns well with delivering a robust multi-platform field application with offline and hardware-integrated capabilities. What is your role on the project when architecture and delivery decisions are made? | Founder / exec, Product or ops, Manager, Student / intern | - | discovery | 3993.0 | 1 |
| 8 | Founder | Here's what I understood: a mobile app - Field service and asset tracking. Platforms: iOS and Android. Features: asset tracking, field service management, Offline data collection, barcode scanning, and 1 more. Timeline: 1 to 3 months. Budget: $40k to $80k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$29,500–$37,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band is above this first-pass range, so there is room to add scope. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 3831.1 | 1 |

*LLM Call Instrumentation (Turn, Purpose, Model, Wall ms, Thinking Tokens, Prompt Tokens, Output Tokens):*
| Turn | Purpose | Model | Wall ms | Thinking Tok | Prompt Tok | Output Tok |
|---|---|---|---|---|---|---|
| 1 | extractor | gemini-3.8-flash | 3080.5 | 0 | 907 | 162 |
| 2 | extractor | gemini-3.8-flash | 3185.7 | 0 | 955 | 149 |
| 3 | extractor | gemini-3.8-flash | 3603.2 | 0 | 977 | 174 |
| 4 | extractor | gemini-3.8-flash | 2657.7 | 0 | 1029 | 161 |
| 5 | extractor | gemini-3.8-flash | 3444.3 | 0 | 1035 | 222 |
| 6 | extractor | gemini-3.8-flash | 2872.0 | 0 | 1063 | 164 |
| 7 | extractor | gemini-3.8-flash | 3921.0 | 0 | 1087 | 214 |
| 8 | extractor | gemini-3.8-flash | 3760.5 | 0 | 1088 | 211 |

#### Scenario S3: Starter chip 'I have an app idea' -> 'A marketplace for local farmers'

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 16.9 | 0 |
| 1 | I have an app idea | Tell me what your app does in a sentence or two — who is it for and what's the core workflow? | Mobile app, Web platform, AI product, UI/UX design | - | discovery | 2609.8 | 1 |
| 2 | A marketplace for local farmers | A local farmer marketplace requires establishing catalog management, order handling, and vendor workflows. What essential building blocks must be ready on day one for users? | User authentication, Payment checkout, Admin dashboard, Analytics & reports, Not sure yet | - | discovery | 2089.2 | 1 |
| 3 | Web and mobile | Targeting both web and mobile platforms will allow you to reach buyers and farmers across different devices. Which core capabilities or features are essential for the launch? | User login & profiles, In-app payments, Push notifications, Search & discovery, Not sure yet | - | discovery | 3128.4 | 1 |
| 4 | Produce catalog, Stripe checkout, farmer payouts, direct chat | Here is the architectural shape: Flutter for Channels and UX, Core flow: A marketplace for local farmers, Produce catalog, Stripe checkout, and Node.js + PostgreSQL for Backend and APIs. When would you like the initial version in users' hands? | ASAP, 1–3 months, 3–6 months, Flexible | shape | discovery | 3154.2 | 1 |
| 5 | 3 to 6 months | Targeting 3 to 6 months gives us a defined delivery window. What rough budget scale makes sense for this first release to help calibrate our architecture recommendations? | Still exploring, Under $15k, $15–40k, $40–80k, $80k+ | - | discovery | 10664.3 | 0 |
| 6 | $40k to $80k | This target window provides solid room to build the core marketplace features and cross-platform infrastructure. Are you leading this as founder, product manager, operations lead, or another role? | Founder / exec, Product or ops, Manager, Student / intern | - | discovery | 2650.4 | 1 |
| 7 | Product lead | Here's what I understood: a mobile app - marketplace for local farmers. Platforms: web, iOS and Android. Features: Produce catalog, Stripe checkout, Farmer payouts, Direct chat. Timeline: 3 to 6 months. Budget: $40k to $80k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$41,000–$51,000 USD** over about **22 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 3325.8 | 1 |

*LLM Call Instrumentation (Turn, Purpose, Model, Wall ms, Thinking Tokens, Prompt Tokens, Output Tokens):*
| Turn | Purpose | Model | Wall ms | Thinking Tok | Prompt Tok | Output Tok |
|---|---|---|---|---|---|---|
| 1 | extractor | gemini-3.8-flash | 2547.5 | 0 | 906 | 149 |
| 2 | extractor | gemini-3.8-flash | 2018.9 | 0 | 906 | 163 |
| 3 | extractor | gemini-3.8-flash | 3064.9 | 0 | 948 | 172 |
| 4 | extractor | gemini-3.8-flash | 3087.1 | 0 | 993 | 191 |
| 6 | extractor | gemini-3.8-flash | 2565.1 | 0 | 1063 | 168 |
| 7 | extractor | gemini-3.8-flash | 3261.6 | 0 | 1092 | 204 |

#### Scenario S4: Seven-feature list in one message (triggers Scope Coach)

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 18.6 | 0 |
| 1 | I want a web app for clinic management. Features: patient booking, telemedicine video, prescriptions, billing, lab results, doctor scheduling, insurance verification. | Here is the architectural shape: Next.js for Channels and UX, Core flow: Clinic management system with te, Patient booking, Telemedicine video, and Node.js + PostgreSQL for Backend and APIs. Any systems this needs to talk to on day one? | None on day one, Payments, CRM | shape | discovery | 3938.5 | 1 |
| 2 | Web application | Will this connect with any outside systems, like payments, email, or a CRM? | None on day one, Payments, CRM, Not sure yet, Not sure, suggest | - | discovery | 3008.8 | 1 |
| 3 | 1 to 3 months | A one-to-three-month timeline sets clear constraints for prioritizing the core clinical modules and integrations. What rough budget scale makes sense for this first release to help calibrate our architecture recommendations? | Still exploring, Under $15k, $15–40k, $40–80k, $80k+ | - | discovery | 2953.9 | 1 |
| 4 | $40k to $80k | Here's what I understood: a web application - Clinic management system with telemedicine, booking, and administrative workflows. Platforms: web. Features: Patient booking, Telemedicine video, Prescriptions, Billing, and 3 more. Timeline: 1 to 3 months. Budget: $40k to $80k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$19,000–$24,000 USD** over about **8 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  This range assumes the Core scope; a list this long will likely need more, and the team can size it precisely. | Show the Core cut, Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 3433.0 | 1 |
| 5 | Founder | Noted, I have updated your project brief. What would you like to explore next? | Book a call, See the MVP, See sample projects, Talk to a human | - | discovery | 21.2 | 0 |

*LLM Call Instrumentation (Turn, Purpose, Model, Wall ms, Thinking Tokens, Prompt Tokens, Output Tokens):*
| Turn | Purpose | Model | Wall ms | Thinking Tok | Prompt Tok | Output Tok |
|---|---|---|---|---|---|---|
| 1 | extractor | gemini-3.8-flash | 3877.3 | 0 | 931 | 244 |
| 2 | extractor | gemini-3.8-flash | 2934.4 | 0 | 1052 | 151 |
| 3 | extractor | gemini-3.8-flash | 2906.1 | 0 | 1055 | 165 |
| 4 | extractor | gemini-3.8-flash | 3375.2 | 0 | 1092 | 247 |

#### Scenario S5: Hinglish: 'mujhe ek delivery app chahiye, iOS aur Android dono, 3 mahine me'

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 18.0 | 0 |
| 1 | mujhe ek delivery app chahiye, iOS aur Android dono, 3 mahine me | Developing a cross-platform delivery app for iOS and Android within a three-month timeframe is a clear scope target. Which core capabilities or features are essential for the launch? | User login & profiles, In-app payments, Push notifications, Search & discovery, Not sure yet | - | discovery | 3166.4 | 1 |
| 2 | Live order tracking, customer ratings, driver assignment | Here is the architectural shape: Flutter for Channels and UX, Core flow: delivery app, Live order tracking, Customer ratings, and Node.js + PostgreSQL for Backend and APIs. Who is the first person this should work well for? | Consumers, Business users, Internal team | shape | discovery | 3280.5 | 1 |
| 3 | $15k to $40k | Targeting this investment range aligns well with phasing out initial delivery and tracking modules. Will the first release need integrations with existing databases, auth providers, or third-party APIs? | None on day one, Payments, CRM | - | discovery | 3588.8 | 1 |
| 4 | Founder | Here's what I understood: a mobile app - delivery app. Platforms: iOS and Android. Features: Live order tracking, Customer ratings, Driver assignment. Timeline: 1 to 3 months. Budget: $15k to $40k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$29,500–$37,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 3085.3 | 1 |

*LLM Call Instrumentation (Turn, Purpose, Model, Wall ms, Thinking Tokens, Prompt Tokens, Output Tokens):*
| Turn | Purpose | Model | Wall ms | Thinking Tok | Prompt Tok | Output Tok |
|---|---|---|---|---|---|---|
| 1 | extractor | gemini-3.8-flash | 3099.6 | 0 | 918 | 174 |
| 2 | extractor | gemini-3.8-flash | 3214.7 | 0 | 979 | 197 |
| 3 | extractor | gemini-3.8-flash | 3530.4 | 0 | 1020 | 193 |
| 4 | extractor | gemini-3.8-flash | 3017.4 | 0 | 1054 | 190 |

#### Scenario S6: Post-estimate technical questions, calendar slot booking, and post-booking ack

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 17.4 | 0 |
| 1 | We need a cross-platform mobile app for iOS and Android. | Developing a cross-platform mobile app targeting both iOS and Android ensures unified code maintenance and broad initial reach. What primary problem or user workflow should this initial release solve? | Book appointments, Manage customers, Take payments | - | discovery | 2536.4 | 1 |
| 2 | Fitness coaching app with workout logger and push notifications. | Here is the architectural shape: Flutter for Channels and UX, Core flow: Fitness coaching app with workou, Fitness coaching, Workout logger, and Node.js + PostgreSQL for Backend and APIs. Any systems this needs to talk to on day one? | None on day one, Payments, CRM | shape | discovery | 3785.6 | 1 |
| 3 | Workout tracking, user profiles, video demonstrations | Captured workout tracking, user profile management, and video demonstration capabilities for the core functionality. What is your target launch horizon for getting this first release live? | ASAP, 1–3 months, 3–6 months, Flexible | - | discovery | 2987.3 | 1 |
| 4 | 1 to 3 months | A one to three month timeline provides a focused window for delivering the core mobile application features. Which investment range should I size this initial build against for squad composition and architecture? | Still exploring, Under $15k, $15–40k, $40–80k, $80k+ | - | discovery | 3206.8 | 1 |
| 5 | $15k to $40k | This target allows us to properly size the initial release scope across both target mobile platforms. What is your role on the project when architecture and delivery decisions are made? | Founder / exec, Product or ops, Manager, Student / intern | - | discovery | 3447.7 | 1 |
| 6 | Founder | Here's what I understood: a mobile app - Fitness coaching app with workout logger and push notifications. Platforms: iOS and Android. Features: Fitness coaching, Workout logger, Push notifications, Workout tracking, and 2 more. Timeline: 1 to 3 months. Budget: $15k to $40k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$29,500–$37,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 2805.4 | 1 |
| 7 | Do you use Flutter? | We build modern web, mobile, and cloud solutions using frameworks like React, Node.js, Python, Flutter, and native cloud services on AWS, GCP, and Azure. | Book a meeting, See similar work | - | faq | 1397.2 | 0 |
| 8 | Which cloud do you use? | We help you weigh tradeoffs; Flutter or React Native works exceptionally well for fast time-to-market, while native Swift/Kotlin suits high-performance hardware needs. | Book a meeting, See similar work | - | faq | 4144.5 | 1 |
| 9 | Can you guarantee 4 weeks? | The timeline assumes a small senior team. If a date is fixed, we shrink the first release rather than promising the full product sooner. | Book a meeting, See similar work | - | objection | 756.8 | 0 |
| 10 | Friday Oct 16, 3:00 PM UTC | You're booked for Fri Oct 16, 20:30 IST — Demo booking: no calendar invite is sent until Google Calendar is connected. Reply with your work email so the invite has somewhere to go. | Can I reschedule?, See similar work | booking | booking | 580.3 | 0 |
| 11 | cool thanks | You're all set for Fri Oct 16, 20:30 IST. The team will see this whole conversation, so you won't need to repeat anything. | What is on the agenda?, Can I reschedule the time? | - | ack | 22.4 | 0 |

*LLM Call Instrumentation (Turn, Purpose, Model, Wall ms, Thinking Tokens, Prompt Tokens, Output Tokens):*
| Turn | Purpose | Model | Wall ms | Thinking Tok | Prompt Tok | Output Tok |
|---|---|---|---|---|---|---|
| 1 | extractor | gemini-3.8-flash | 2474.9 | 0 | 914 | 165 |
| 2 | extractor | gemini-3.8-flash | 3711.2 | 0 | 963 | 201 |
| 3 | extractor | gemini-3.8-flash | 2916.8 | 0 | 1022 | 210 |
| 4 | extractor | gemini-3.8-flash | 3137.6 | 0 | 1050 | 162 |
| 5 | extractor | gemini-3.8-flash | 3399.6 | 0 | 1074 | 170 |
| 6 | extractor | gemini-3.8-flash | 2733.1 | 0 | 1102 | 211 |
| 8 | synth | gemini-3.8-flash | 2656.5 | 0 | 115 | 72 |

#### Scenario S7: Natural chip path: Mobile app, goal text, feature chips, platform chip, timeline chip, budget chip, role chip

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 17.4 | 0 |
| 1 | Mobile app | mobile app, understood. What core business outcome or user experience should this first launch deliver? | Book appointments, Manage customers, Take payments | - | discovery | 22.0 | 0 |
| 2 | A sports clinic booking application for direct patients | A dedicated patient booking platform will require secure scheduling workflows and reliable patient management. What should each of appointment booking do in the first version? | That's enough | - | discovery | 2867.8 | 1 |
| 3 | User login & profiles | appointment booking, User login & profiles gives us a solid foundation for the first release. How do you picture a visitor moving through the application from first screen to result (sketch it or skip)? | Skip for now | - | discovery | 22.4 | 0 |
| 4 | Continue to next step → | How do you envision someone signing up and using this from start to finish? | Skip for now, Not sure yet, Not sure, suggest | - | discovery | 22.6 | 0 |
| 5 | iOS and Android | Here is the architectural shape: Flutter for Channels and UX, Core flow: A sports clinic booking applicat, appointment booking, User login & profiles, and Node.js + PostgreSQL for Backend and APIs. Any systems this needs to talk to on day one? | None on day one, Payments, CRM | shape | discovery | 21.2 | 0 |
| 6 | 1–3 months | Working toward 1 to 3 months sets the development pace. Which investment range should I size this initial build against for squad composition and architecture? | Still exploring, Under $15k, $15–40k, $40–80k, $80k+ | - | discovery | 24.4 | 0 |
| 7 | $15–40k | What is your role on the project when architecture and delivery decisions are made? | Founder / exec, Product or ops, Manager, Student / intern | - | discovery | 18.0 | 0 |
| 8 | Founder / exec | Here's what I understood: a mobile app - sports clinic booking application for direct patients. Platforms: iOS and Android. Features: appointment booking, User login & profiles. Timeline: 1 to 3 months. Budget: $15k to $40k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$32,000–$40,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 18.1 | 0 |

*LLM Call Instrumentation (Turn, Purpose, Model, Wall ms, Thinking Tokens, Prompt Tokens, Output Tokens):*
| Turn | Purpose | Model | Wall ms | Thinking Tok | Prompt Tok | Output Tok |
|---|---|---|---|---|---|---|
| 2 | extractor | gemini-3.8-flash | 2810.4 | 0 | 932 | 166 |

#### Scenario S8: Out-of-order answers (the old S3 script)

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 14.5 | 0 |
| 1 | I have an app idea | Tell me what your app does in a sentence or two — who is it for and what's the core workflow? | Mobile app, Web platform, AI product, UI/UX design | - | discovery | 4032.3 | 1 |
| 2 | A marketplace for local farmers | Building a marketplace for local farmers typically requires dual-sided catalog management, order processing, and location-based discovery. Which core capabilities or features are essential for the launch? | User authentication, Payment checkout, Admin dashboard, Analytics & reports, Not sure yet | - | discovery | 2947.7 | 1 |
| 3 | Web and mobile | Targeting both web and mobile platforms ensures broad reach for farmers and consumers. Which core capabilities or features are essential for the launch? | User login & profiles, In-app payments, Push notifications, Search & discovery, Not sure yet | - | discovery | 2719.7 | 1 |
| 4 | Produce catalog, Stripe checkout, farmer payouts, direct chat | Here is the architectural shape: Flutter for Channels and UX, Core flow: marketplace for local farmers, Produce catalog, Stripe checkout, and Node.js + PostgreSQL for Backend and APIs. When would you like the initial version in users' hands? | ASAP, 1–3 months, 3–6 months, Flexible | shape | discovery | 3048.7 | 1 |
| 5 | 3 to 6 months | A three to six month window gives sufficient runway to implement cross-platform applications and the marketplace payout infrastructure properly. Which investment range should I size this initial build against for squad composition and architecture? | Still exploring, Under $15k, $15–40k, $40–80k, $80k+ | - | discovery | 2513.6 | 1 |
| 6 | $40k to $80k | This scope aligns well with standard development requirements for a multi-platform marketplace. Are you leading this as founder, product manager, operations lead, or another role? | Founder / exec, Product or ops, Manager, Student / intern | - | discovery | 3603.4 | 1 |
| 7 | Product lead | Here's what I understood: a mobile app - marketplace for local farmers. Platforms: web, iOS and Android. Features: Produce catalog, Stripe checkout, Farmer payouts, Direct chat. Timeline: 3 to 6 months. Budget: $40k to $80k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$41,000–$51,000 USD** over about **22 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 2907.7 | 1 |

*LLM Call Instrumentation (Turn, Purpose, Model, Wall ms, Thinking Tokens, Prompt Tokens, Output Tokens):*
| Turn | Purpose | Model | Wall ms | Thinking Tok | Prompt Tok | Output Tok |
|---|---|---|---|---|---|---|
| 1 | extractor | gemini-3.8-flash | 3957.8 | 250 | 906 | 23 |
| 2 | extractor | gemini-3.8-flash | 2881.1 | 0 | 906 | 167 |
| 3 | extractor | gemini-3.8-flash | 2652.6 | 0 | 947 | 162 |
| 4 | extractor | gemini-3.8-flash | 2976.9 | 0 | 992 | 216 |
| 5 | extractor | gemini-3.8-flash | 2448.5 | 0 | 1038 | 163 |
| 6 | extractor | gemini-3.8-flash | 3538.8 | 0 | 1062 | 168 |
| 7 | extractor | gemini-3.8-flash | 2835.5 | 36 | 1091 | 144 |

#### Scenario S9: First message is only a budget: 'my budget is $40k to $80k'

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 16.5 | 0 |
| 1 | my budget is $40k to $80k | Understood, that budget range provides a solid baseline for planning the scope and architecture. What core business outcome or user experience should this first launch deliver? | Book appointments, Manage customers, Take payments | - | discovery | 2599.7 | 1 |
| 2 | Mobile app | Understood, shifting the focus to a native or cross-platform mobile application build. What core business outcome or user experience should this first launch deliver? | Book appointments, Manage customers, Take payments | - | discovery | 2851.0 | 1 |
| 3 | An on-demand tutor marketplace | A two-sided marketplace for on-demand tutoring involves search, booking workflows, and real-time interaction capabilities. Which core capabilities or features are essential for the launch? | User login & profiles, In-app payments, Push notifications, Search & discovery, Not sure yet | - | discovery | 3138.9 | 1 |
| 4 | iOS and Android | What essential building blocks or capabilities do you envision for the initial release? | User login & profiles, In-app payments, Push notifications, Search & discovery, Not sure yet, Not sure, suggest | - | discovery | 8670.6 | 1 |
| 5 | Matching algorithm, in-app messaging, tutor reviews | Here is the architectural shape: Flutter for Channels and UX, Core flow: An on-demand tutor marketplace, Matching algorithm, in-app messaging, and Node.js + PostgreSQL for Backend and APIs. Any systems this needs to talk to on day one? | None on day one, Payments, CRM | shape | discovery | 3566.7 | 1 |
| 6 | 1 to 3 months | A 1 to 3 month target provides a clear timeframe to prioritize core architecture and delivery milestones. What is your role on the project when architecture and delivery decisions are made? | Founder / exec, Product or ops, Manager, Student / intern | - | discovery | 3402.5 | 1 |
| 7 | Founder | Here's what I understood: a mobile app - on-demand tutor marketplace. Platforms: iOS and Android. Features: Matching algorithm, in-app messaging, tutor reviews. Timeline: 1 to 3 months. Budget: $40k to $80k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$38,000–$47,500 USD** over about **22 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 2845.0 | 1 |

*LLM Call Instrumentation (Turn, Purpose, Model, Wall ms, Thinking Tokens, Prompt Tokens, Output Tokens):*
| Turn | Purpose | Model | Wall ms | Thinking Tok | Prompt Tok | Output Tok |
|---|---|---|---|---|---|---|
| 1 | extractor | gemini-3.8-flash | 2550.7 | 0 | 913 | 167 |
| 2 | extractor | gemini-3.8-flash | 2796.2 | 0 | 964 | 156 |
| 3 | extractor | gemini-3.8-flash | 3079.4 | 0 | 987 | 169 |
| 4 | extractor | gemini-3.8-flash | 8607.5 | 0 | 1017 | 159 |
| 5 | extractor | gemini-3.8-flash | 3502.5 | 0 | 1024 | 204 |
| 6 | extractor | gemini-3.8-flash | 3343.7 | 0 | 1063 | 161 |
| 7 | extractor | gemini-3.8-flash | 2781.8 | 0 | 1087 | 158 |

#### Scenario S10: Starter 'I have an app idea' -> 'a booking app for barbers' -> 'web and mobile'

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |
|---|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 15.6 | 0 |
| 1 | I have an app idea | Developing a custom application starts with defining its core functionality and platform requirements. What core business outcome or user experience should this first launch deliver? | Book appointments, Manage customers, Take payments | - | discovery | 2777.2 | 1 |
| 2 | a booking app for barbers | A barber booking application typically requires real-time scheduling, calendar synchronization, and service catalog management. What should each of appointment booking do in the first version? | That's enough | - | discovery | 2691.3 | 1 |
| 3 | web and mobile | Here is the architectural shape: Flutter for Channels and UX, Core flow: booking app for barbers, appointment booking, Primary user journey on the agre, and Node.js + PostgreSQL for Backend and APIs. Any systems this needs to talk to on day one? | None on day one, Payments, CRM | shape | discovery | 3465.9 | 1 |
| 4 | Appointment scheduling, barber portfolio, customer SMS alerts, loyalty points, payment processing | Incorporating payment processing and SMS alerts provides a robust transaction and notification workflow for client bookings. What is your target launch horizon for getting this first release live? | ASAP, 1–3 months, 3–6 months, Flexible | - | discovery | 3196.6 | 1 |
| 5 | 1–3 months | Targeting 1 to 3 months gives us a defined delivery window. What rough budget scale makes sense for this first release to help calibrate our architecture recommendations? | Still exploring, Under $15k, $15–40k, $40–80k, $80k+ | - | discovery | 24.6 | 0 |
| 6 | $15–40k | What is your role on the project when architecture and delivery decisions are made? | Founder / exec, Product or ops, Manager, Student / intern | - | discovery | 20.5 | 0 |
| 7 | Founder / exec | Here's what I understood: a mobile app - booking app for barbers. Platforms: web, iOS and Android. Features: appointment booking, Appointment scheduling, barber portfolio, customer SMS alerts, and 2 more. Timeline: 1 to 3 months. Budget: $15k to $40k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$32,000–$40,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 23.1 | 0 |

*LLM Call Instrumentation (Turn, Purpose, Model, Wall ms, Thinking Tokens, Prompt Tokens, Output Tokens):*
| Turn | Purpose | Model | Wall ms | Thinking Tok | Prompt Tok | Output Tok |
|---|---|---|---|---|---|---|
| 1 | extractor | gemini-3.8-flash | 2709.5 | 0 | 906 | 153 |
| 2 | extractor | gemini-3.8-flash | 2623.1 | 0 | 929 | 166 |
| 3 | extractor | gemini-3.8-flash | 3386.4 | 0 | 971 | 160 |
| 4 | extractor | gemini-3.8-flash | 3130.1 | 0 | 1033 | 222 |

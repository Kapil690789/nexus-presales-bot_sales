# DEMO TRANSCRIPTS & QA CHECKS (QA-2 VALIDATION)

Generated: 2026-10-11 17:50:10 UTC
Primary model configured: `gemini-3.8-flash`

## Section 1: In-Process Deterministic Stub (Offline / Fallback)

### 1. QA Checks Summary Table

| Scenario | Title | Opener (4+Human) | Bot <=2 Sent & <=320 Chars | No Placeholders | Platform Casing | No Mid-Word Cut | No Verbatim Repeat | Shape Card (S7) | Estimate Checked | Turns to Est |
|---|---|---|---|---|---|---|---|---|---|---|
| **S1** | Long comprehensive initial messa... | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 3 |
| **S2** | Starter chip 'I'm just exploring... | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 8 |
| **S3** | Starter chip 'I have an app idea... | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 7 |
| **S4** | Seven-feature list in one messag... | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 4 |
| **S5** | Hinglish: 'mujhe ek delivery app... | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | N/A |
| **S6** | Post-estimate technical question... | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 6 |
| **S7** | Natural chip path: Mobile app, g... | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 8 |
| **S8** | Out-of-order answers (the old S3... | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 7 |

### 2. Full Turn-by-Turn Transcripts

#### Scenario S1: Long comprehensive initial message with platforms, features, budget, and timeline

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) |
|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 83.1 |
| 1 | We want it on both iOS and Android. For the first release we just need login, calendar booking, and push notifications. Budget around $25k to $35k, 2 to 3 months. | iOS and Android, noted. What core business outcome or user experience should this first launch deliver? | Book appointments, Manage customers, Take payments | - | discovery | 28.2 |
| 2 | I am building a sports clinic booking application for direct patients. | Building a mobile app focused on sports clinic booking application for direct patients: clear priority. Which core capabilities or features are essential for the launch? | User login & profiles, In-app payments, Push notifications, Search & discovery, Not sure yet | - | discovery | 26.2 |
| 3 | I am the founder and technical decision maker. | Here's what I understood: a mobile app for sports clinic booking application for direct patients, on iOS and Android, aiming for 1 to 3 months with a budget of $15k to $40k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$29,500–$37,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 25.1 |

#### Scenario S2: Starter chip 'I'm just exploring costs'

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) |
|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 16.6 |
| 1 | I'm just exploring costs | Building a web application focused on just exploring costs: clear priority. Which core capabilities or features are essential for the launch? | User authentication, Payment checkout, Admin dashboard, Analytics & reports, Not sure yet | - | discovery | 36.8 |
| 2 | Mobile app | You mentioned a web app earlier, but mobile as the platform. Should we target web, mobile, or both? | Web app, Mobile app, Both web & mobile | - | discovery | 20.7 |
| 3 | Field service and asset tracking | Here is the architectural shape: Next.js for Channels and UX, Core user flows for the Core flow, and Node.js + PostgreSQL for Backend and APIs. Who is the first person this should work well for? | Consumers, Business users, Internal team | shape | discovery | 22.3 |
| 4 | iOS and Android | Will the first release need integrations with existing databases, auth providers, or third-party APIs? | None on day one, Payments, CRM | - | discovery | 29.6 |
| 5 | Offline data collection, barcode scanning, GPS tracking | What is your target launch horizon for getting this first release live? | ASAP, 1–3 months, 3–6 months, Flexible | - | discovery | 23.9 |
| 6 | 1 to 3 months | Targeting 1 to 3 months gives us a defined delivery window. Which investment range should I size this initial build against for squad composition and architecture? | Still exploring, Under $15k, $15–40k, $40–80k, $80k+ | - | discovery | 29.2 |
| 7 | $40k to $80k | Are you leading this as founder, product manager, operations lead, or another role? | Founder / exec, Product or ops, Manager, Student / intern | - | discovery | 21.0 |
| 8 | Founder | Here's what I understood: a web application for just exploring costs, on iOS and Android, with Field service, asset tracking, aiming for 1 to 3 months with a budget of $40k to $80k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$30,500–$38,000 USD** over about **22 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band is above this first-pass range, so there is room to add scope. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 21.6 |

#### Scenario S3: Starter chip 'I have an app idea' -> 'A marketplace for local farmers'

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) |
|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 15.2 |
| 1 | I have an app idea | Building a web application focused on I have an app idea: clear priority. What essential building blocks must be ready on day one for users? | User authentication, Payment checkout, Admin dashboard, Analytics & reports, Not sure yet | - | discovery | 24.4 |
| 2 | A marketplace for local farmers | Focusing on A marketplace for local farmers establishes a clear core scope. What should each of A marketplace for local farmers do in the first version? | That's enough | - | discovery | 23.9 |
| 3 | Web and mobile | Here is the architectural shape: Next.js for Channels and UX, Core user flows for the Core flow, and Node.js + PostgreSQL for Backend and APIs. Who is the first person this should work well for? | Consumers, Business users, Internal team | shape | discovery | 23.6 |
| 4 | Produce catalog, Stripe checkout, farmer payouts, direct chat | Are there any external services or APIs this must connect with on day one, like payments or CRM? | None on day one, Payments, CRM | - | discovery | 23.1 |
| 5 | 3 to 6 months | Targeting 3 to 6 months gives us a defined delivery window. Which investment range should I size this initial build against for squad composition and architecture? | Still exploring, Under $15k, $15–40k, $40–80k, $80k+ | - | discovery | 27.5 |
| 6 | $40k to $80k | Are you leading this as founder, product manager, operations lead, or another role? | Founder / exec, Product or ops, Manager, Student / intern | - | discovery | 19.7 |
| 7 | Product lead | Here's what I understood: a web application for I have an app idea, on web, iOS and Android, with A marketplace for local farmers, aiming for 3 to 6 months with a budget of $40k to $80k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$32,500–$40,500 USD** over about **22 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 22.1 |

#### Scenario S4: Seven-feature list in one message (triggers Scope Coach)

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) |
|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 14.4 |
| 1 | I want a web app for clinic management. Features: patient booking, telemedicine video, prescriptions, billing, lab results, doctor scheduling, insurance verification. | Targeting web sets our technical architecture. What core business outcome or user experience should this first launch deliver? | Book appointments, Manage customers, Take payments | - | discovery | 27.1 |
| 2 | Web application | Building a web application focused on Web application: clear priority. Which core capabilities or features are essential for the launch? | User authentication, Payment checkout, Admin dashboard, Analytics & reports, Not sure yet | - | discovery | 22.2 |
| 3 | 1 to 3 months | Here is the architectural shape: Next.js for Channels and UX, Core user flows for the Core flow, and Node.js + PostgreSQL for Backend and APIs. Who is the first person this should work well for? | Consumers, Business users, Internal team | shape | discovery | 18.5 |
| 4 | $40k to $80k | Here's what I understood: a web application for Web application, on web, aiming for 1 to 3 months with a budget of $40k to $80k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$19,000–$24,000 USD** over about **8 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band is above this first-pass range, so there is room to add scope. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 22.6 |
| 5 | Founder | Here's what I understood: a web application for Web application, on web, aiming for 1 to 3 months with a budget of $40k to $80k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$19,000–$24,000 USD** over about **8 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band is above this first-pass range, so there is room to add scope. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 19.9 |

#### Scenario S5: Hinglish: 'mujhe ek delivery app chahiye, iOS aur Android dono, 3 mahine me'

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) |
|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 14.4 |
| 1 | mujhe ek delivery app chahiye, iOS aur Android dono, 3 mahine me | Targeting iOS and Android sets our technical architecture. What primary problem or user workflow should this initial release solve? | Book appointments, Manage customers, Take payments | - | discovery | 23.5 |
| 2 | Live order tracking, customer ratings, driver assignment | A mobile app for Live order tracking, customer ratings, driver assignment: that gives me a clear picture. What essential building blocks must be ready on day one for users? | User login & profiles, In-app payments, Push notifications, Search & discovery, Not sure yet | - | discovery | 17.9 |
| 3 | $15k to $40k | Here is the architectural shape: Flutter for Channels and UX, Core user flows for the Core flow, and Node.js + PostgreSQL for Backend and APIs. Who is the first person this should work well for? | Consumers, Business users, Internal team | shape | discovery | 18.8 |
| 4 | Founder | Are there any external services or APIs this must connect with on day one, like payments or CRM? | None on day one, Payments, CRM | - | discovery | 18.2 |

#### Scenario S6: Post-estimate technical questions, calendar slot booking, and post-booking ack

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) |
|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 16.7 |
| 1 | We need a cross-platform mobile app for iOS and Android. | A mobile app for cross-platform mobile app for iOS and Android: that gives me a clear picture. Which core capabilities or features are essential for the launch? | User login & profiles, In-app payments, Push notifications, Search & discovery, Not sure yet | - | discovery | 18.5 |
| 2 | Fitness coaching app with workout logger and push notifications. | Here is the architectural shape: Flutter for Channels and UX, Core user flows for the Core flow, and Node.js + PostgreSQL for Backend and APIs. Who is the first person this should work well for? | Consumers, Business users, Internal team | shape | discovery | 20.9 |
| 3 | Workout tracking, user profiles, video demonstrations | Will the first release need integrations with existing databases, auth providers, or third-party APIs? | None on day one, Payments, CRM | - | discovery | 23.0 |
| 4 | 1 to 3 months | Working toward 1 to 3 months sets the development pace. What rough budget scale makes sense for this first release to help calibrate our architecture recommendations? | Still exploring, Under $15k, $15–40k, $40–80k, $80k+ | - | discovery | 20.8 |
| 5 | $15k to $40k | Are you leading this as founder, product manager, operations lead, or another role? | Founder / exec, Product or ops, Manager, Student / intern | - | discovery | 18.8 |
| 6 | Founder | Here's what I understood: a mobile app for cross-platform mobile app for iOS and Android, on iOS and Android, with Fitness coaching app with workout logger, push notifications, aiming for 1 to 3 months with a budget of $15k to $40k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$29,500–$37,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 24.3 |
| 7 | Do you use Flutter? | Based on what you've shared for 'We need a cross-platform mobile app for iOS and Android', our indicative range is **$29,500–$37,000 USD** over about 14 weeks. The best next step is a short discovery call with our engineering team to review your specific requirements. | Book a meeting, See similar work | - | fallback | 27.5 |
| 8 | Which cloud do you use? | Based on what you've shared for 'We need a cross-platform mobile app for iOS and Android', our indicative range is **$29,500–$37,000 USD** over about 14 weeks. The best next step is a short discovery call with our engineering team to review your specific requirements. | Book a meeting, See similar work | - | fallback | 22.6 |
| 9 | Can you guarantee 4 weeks? | Based on what you've shared for 'We need a cross-platform mobile app for iOS and Android', our indicative range is **$29,500–$37,000 USD** over about 14 weeks. The best next step is a short discovery call with our engineering team to review your specific requirements. | Book a meeting, See similar work | - | fallback | 19.3 |
| 10 | Friday Oct 16, 3:00 PM UTC | You're booked for Fri Oct 16, 20:30 IST — Demo booking: no calendar invite is sent until Google Calendar is connected. Reply with your work email so the invite has somewhere to go. | Startup, SMB, Mid-market, Enterprise | booking | booking | 1075.4 |
| 11 | cool thanks | You're all set for Fri Oct 16, 20:30 IST. The team will see this whole conversation, so you won't need to repeat anything. | What is on the agenda?, Can I reschedule the time? | - | ack | 24.2 |

#### Scenario S7: Natural chip path: Mobile app, goal text, feature chips, platform chip, timeline chip, budget chip, role chip

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) |
|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 21.0 |
| 1 | Mobile app | mobile app, understood. What primary problem or user workflow should this initial release solve? | Book appointments, Manage customers, Take payments | - | discovery | 23.1 |
| 2 | A sports clinic booking application for direct patients | A mobile app for sports clinic booking application for direct patients: that gives me a clear picture. What essential building blocks must be ready on day one for users? | User login & profiles, In-app payments, Push notifications, Search & discovery, Not sure yet | - | discovery | 18.3 |
| 3 | User login & profiles | Focusing on User login & profiles establishes a clear core scope. Added User login & profiles — any other features for the launch, or ready to continue? | Continue to next step →, + User login & profiles, + In-app payments, + Push notifications, Ready with this list | - | discovery | 19.9 |
| 4 | Continue to next step → | What should each of User login & profiles do in the first version? | That's enough | - | discovery | 22.2 |
| 5 | iOS and Android | Here is the architectural shape: Flutter for Channels and UX, Core user flows for the Core flow, and Node.js + PostgreSQL for Backend and APIs. Who is the first person this should work well for? | Consumers, Business users, Internal team | shape | discovery | 21.1 |
| 6 | 1–3 months | Targeting 1 to 3 months gives us a defined delivery window. Will the first release need integrations with existing databases, auth providers, or third-party APIs? | None on day one, Payments, CRM | - | discovery | 19.9 |
| 7 | $15–40k | What is your role on the project when architecture and delivery decisions are made? | Founder / exec, Product or ops, Manager, Student / intern | - | discovery | 18.4 |
| 8 | Founder / exec | Here's what I understood: a mobile app for sports clinic booking application for direct patients, on iOS and Android, with User login & profiles, aiming for 1 to 3 months with a budget of $15k to $40k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$32,000–$40,000 USD** over about **14 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 23.1 |

#### Scenario S8: Out-of-order answers (the old S3 script)

| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) |
|---|---|---|---|---|---|---|
| 0 | (Session Start) | Hi, I'm Alex, Nexus's AI project advisor. Tell me what you'd like to build in a sentence, or pick a starting point. | I have an app idea, I need a web platform, Add AI to my product, Just exploring costs, Talk to a human | - | discovery | 13.7 |
| 1 | I have an app idea | A web application for I have an app idea: that gives me a clear picture. Which core capabilities or features are essential for the launch? | User authentication, Payment checkout, Admin dashboard, Analytics & reports, Not sure yet | - | discovery | 24.1 |
| 2 | A marketplace for local farmers | A marketplace for local farmers gives us a solid foundation for the first release. What should each of A marketplace for local farmers do in the first version? | That's enough | - | discovery | 19.1 |
| 3 | Web and mobile | Here is the architectural shape: Next.js for Channels and UX, Core user flows for the Core flow, and Node.js + PostgreSQL for Backend and APIs. Who is the first person this should work well for? | Consumers, Business users, Internal team | shape | discovery | 20.6 |
| 4 | Produce catalog, Stripe checkout, farmer payouts, direct chat | Will the first release need integrations with existing databases, auth providers, or third-party APIs? | None on day one, Payments, CRM | - | discovery | 18.2 |
| 5 | 3 to 6 months | Working toward 3 to 6 months sets the development pace. What rough budget scale makes sense for this first release to help calibrate our architecture recommendations? | Still exploring, Under $15k, $15–40k, $40–80k, $80k+ | - | discovery | 19.5 |
| 6 | $40k to $80k | Are you leading this as founder, product manager, operations lead, or another role? | Founder / exec, Product or ops, Manager, Student / intern | - | discovery | 18.7 |
| 7 | Product lead | Here's what I understood: a web application for I have an app idea, on web, iOS and Android, with A marketplace for local farmers, aiming for 3 to 6 months with a budget of $40k to $80k. If anything is off, tell me and I'll update the estimate.  A first-pass indicative range for this scope is **$32,500–$40,500 USD** over about **22 weeks**. *Indicative range only, not a fixed quote.*  That's a first-pass range based on typical scope for this kind of project.  Your budget band overlaps this first-pass range. | Sharpen this estimate, See the MVP, See sample projects, Book a call, Talk to a human | estimate, architecture, mvp, portfolio | estimate | 26.4 |

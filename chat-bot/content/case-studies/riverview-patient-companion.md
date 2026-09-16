---
title: Riverview Clinic — patient companion app
case_id: clinic-mobile
service: mobile_app
industry: health
platforms: [ios, android]
stacks: [React Native, Node.js]
tags: [health, auth, mobile, hipaa, appointments]
outcome: HIPAA-aware companion app; no-show rate down 18% in the pilot cohort.
url: /work/riverview.html
status: published
nda_only: true
updated: 2026-01-19
---

## The problem

Riverview ran a network of outpatient clinics with a no-show rate high enough to be a
material revenue problem and a genuine care problem — the patients who missed
appointments were disproportionately the ones who most needed them. Reminders went out
by post and by an automated phone call that most patients never answered.

They wanted an app. What they needed first was to know whether their patients would
install one, which shaped how we sequenced the work.

## What we shipped

A companion app scoped tightly around the appointment:

- Upcoming appointments with location, clinician, and what to bring or avoid
  beforehand.
- Confirm, request a reschedule, or cancel, with the cancellation freeing the slot back
  into the clinic system immediately.
- Staged reminders at one week, two days, and three hours, with the timing
  configurable per clinic because the clinics disagreed about it.
- Post-visit summary and instructions, replacing a printed sheet that patients lost.
- Secure sign-in tied to the existing patient record, with no clinical data stored on
  the device.

## The stack and why

React Native, because the client's in-house team knew React and would take the app over
after launch. That mattered more than any performance argument, and the app has no
performance-sensitive surface.

Node.js for the integration layer, sitting between the app and the clinic management
system, which spoke HL7 and could not be modified. All patient data stayed in the
existing system of record; the integration layer held no clinical data at rest and
passed identifiers through rather than copying them.

## Working under HIPAA

Worth saying plainly, because it drove much of the schedule: we treated the compliance
work as design constraints from week one rather than a hardening phase at the end.
That meant no clinical data in logs or analytics, encryption in transit and at rest,
short-lived sessions with re-authentication for anything sensitive, an access audit
trail, and a data flow diagram reviewed with their compliance officer before we wrote
the integration. Their own security team ran the penetration test; we scoped and fixed
against its findings.

## What we cut from the MVP

- **Messaging with the care team.** The clinical governance work around asynchronous
  patient messaging was larger than the entire rest of the app.
- **Prescription and refill requests.** Deferred to a second phase.
- **Wearable and vitals integration.** Requested early, unconnected to no-shows.
- **Family and carer accounts.** Real need, significant consent modelling; phase two.

## The outcome

The pilot ran across three clinics. No-shows in the pilot cohort fell 18% over the
quarter, and reschedules moved from phone calls to the app, which took measurable load
off reception. The client's team took over the codebase four weeks after launch.

## The quote

"You told us in week two that messaging would double the project and would not move the
number we cared about. You were right, and we shipped a quarter earlier for it."
— Director of Operations, Riverview

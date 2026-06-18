# Roeung — Strategic Deployment and Commercialisation Plan

**Product:** Roeung (រឿង) — AI-powered oral history platform for diaspora families  
**Author:** Sea Family / Roeung Team  
**Date:** June 2026  
**Version:** 1.0

---

## Executive Summary

Roeung addresses a problem that is both urgent and irreversible: the living memory of displaced communities disappears when its bearers die. The product captures family oral histories via audio, transcribes and translates them with AI, and packages them into a bilingual digital family book — designed for families separated across countries and languages.

The commercialisation strategy positions Roeung as a self-serve SaaS product targeting diaspora families globally, with a freemium on-ramp and a subscription tier that covers ongoing AI processing costs. The roadmap moves from the current Sea family prototype through a structured pilot with 10–20 diaspora families, to a public launch, and ultimately to community-led expansion across language communities.

---

## Commercialisation Model

**Roeung will be a product sold via one-time purchase**, not a subscription, consulting service, or internal tool.

**Rationale:** The core value — AI transcription, translation, cultural flagging, and bilingual family book assembly — is repeatable and does not require bespoke delivery per customer. Families should feel they *own* their book, not rent access to it; a subscription creates anxiety that a missed payment could lock them out of their family's memories. The one-time purchase model removes that concern while a story credits system ensures that ongoing AI processing costs are covered per story processed. Licensing to organisations (e.g. cultural centres) is reserved for Phase 4 once the product is proven.

---

## Phase 1 — POC (Current State)

**Status:** Complete  
**Duration:** ~6 months (concluded ~June 2026)  
**Scope:** Single family (Sea family), private deployment

### What exists
- Working prototype deployed on Railway (backend + Redis) and Supabase (database + storage)
- Four complete user flows: Capture, AI Pipeline, Keeper Review, Book Reading
- Bilingual support (Khmer / English) across all flows
- AI pipeline: ElevenLabs transcription → Google Translate → GPT-4 cultural flagging → title generation → people tagging
- Mobile-first responsive design
- Two-tier auth (family token URL + Keeper email/password)
- GDPR-compliant consent logging and story deletion

### What is not yet built
- Multi-tenancy (each family gets isolated data)
- Subscription/billing layer
- Self-serve onboarding (currently requires manual setup)
- Monitoring, alerting, and SLA tooling
- Support infrastructure

### Phase 1 KPIs
| KPI | Target | Status |
|-----|--------|--------|
| Core flows functional end-to-end | All 4 flows | ✓ Complete |
| AI pipeline reliability | >90% of stories reach `awaiting_review` | Measure in pilot |
| Sea family stories published | ≥5 stories in the book | Track |
| Internal user satisfaction | Sea family Keepers rate experience ≥4/5 | Survey |

---

## Phase 2 — Pilot (Limited Rollout and Validation)

**Duration:** 3 months (July–September 2026)  
**Goal:** Validate product-market fit with 10–20 diaspora families outside the Sea family; measure willingness to pay; identify onboarding friction.

### Key Activities

**Product (months 1–2)**
- Build multi-tenancy: each family gets an isolated `families` row, storage bucket prefix, and access token
- Build self-serve signup: a Keeper creates a family account, names chapters, invites family members by sharing the family URL
- Add basic billing using Stripe (free tier + paid tier; no credit card required for free)
- Instrument analytics (PostHog or equivalent) to track story submission rate, pipeline completion rate, Keeper review time, and book reads
- Add email notifications for Keepers when stories enter `awaiting_review`

**Go-to-Market (months 1–3)**
- Recruit 10–20 pilot families through direct outreach to Cambodian, Vietnamese, Somali, and Ukrainian diaspora community networks and Facebook groups — communities where oral history loss is acute and well-documented
- Offer pilot families free access in exchange for structured feedback (bi-weekly 30-minute calls)
- Document 3–5 "hero stories" (with family permission) to use as public-facing social proof

**Milestones**
- Month 1: Multi-tenancy live; first external family onboarded
- Month 2: Billing live; 10 families active
- Month 3: Pilot debrief complete; pricing validated

### Phase 2 KPIs
| KPI | Target |
|-----|--------|
| Pilot families onboarded | ≥10 |
| Stories submitted by pilot families | ≥30 total |
| AI pipeline success rate | ≥95% reach `awaiting_review` |
| Keeper review completion rate | ≥70% of submitted stories reach `published` within 2 weeks |
| Families willing to pay at proposed price | ≥60% of pilot cohort |
| Net Promoter Score | ≥40 |

---

## Phase 3 — Full Deployment (Public Launch)

**Duration:** 3 months (October–December 2026)  
**Goal:** Open Roeung to the public; reach first 100 paying families; establish repeatable acquisition channels.

### Key Activities

**Product hardening (pre-launch)**
- Security audit and penetration test (audio files and family data are sensitive)
- Expand language support beyond Khmer/English: add Arabic, Somali, Ukrainian, Vietnamese as AI pipeline targets (Google Translate and ElevenLabs Scribe already support these)
- Build a "family health" dashboard for Keepers: stories pending, pipeline queue status, member activity
- Add printed book export (PDF) as a paid feature — this was deferred from Phase 1 and is a natural upgrade hook
- Set up status page, error alerting (Sentry/Railway logs), and on-call rotation

**Go-to-Market**
- Public launch on Product Hunt and Hacker News "Show HN"
- Partnerships with 3–5 diaspora community organisations (Cambodian American community centres, Ukrainian cultural organisations, etc.) who promote to their members in exchange for a community discount code
- Content marketing: publish 2–3 long-form pieces on oral history loss in diaspora communities, seeded into relevant subreddits, newsletters, and LinkedIn
- SEO targeting: "preserve family stories", "oral history app", "bilingual family memories"

**Pricing Model**

Roeung uses a **one-time purchase + story credits** model. Think of it like buying a camera and then purchasing film rolls as you need them: the family book is yours permanently, and credits are consumed only when a story is processed through the AI pipeline.

This model fits Roeung's emotional proposition — families should feel they *own* their book, not rent it — while ensuring that ongoing AI processing costs (ElevenLabs, OpenAI, Google Translate) are covered each time a story is submitted. A 10-minute story costs approximately $0.30–0.50 to process end-to-end; credits are priced to cover this with margin.

**Base purchase (one-time)**

| Product | Price | Includes |
|---------|-------|----------|
| Roeung Family Book | $89 one-time | Unlimited Keepers, unlimited family members, unlimited chapters, PDF book export, lifetime book reading access, 10 story credits included |

**Story credit packs (one-time, never expire)**

| Pack | Price | Per-story cost |
|------|-------|----------------|
| Starter — 10 credits | $19 | $1.90/story |
| Family — 30 credits | $49 | $1.63/story |
| Archive — 100 credits | $129 | $1.29/story |

One credit = one story processed through the full AI pipeline (audio quality check → transcription → translation → cultural flagging → title generation → people tagging). Credits are deducted at submission and refunded if the story fails the audio quality check. Credits never expire.

**Milestones**
- Month 1: Public launch; 50 purchases
- Month 2: 25 additional purchases; first credit pack repurchases
- Month 3: 100 cumulative paying families; revenue ≥ $10,000

### Phase 3 KPIs
| KPI | Target |
|-----|--------|
| Base purchases (cumulative) | ≥100 |
| Credit pack repurchase rate | ≥40% of customers within 90 days |
| Average revenue per customer (year 1) | ≥$120 (base + at least one credit pack) |
| Cumulative revenue at end of Phase 3 | ≥$12,000 |
| AI pipeline uptime | ≥99.5% |
| Support ticket response time | ≤24 hours |

---

## Phase 4 — Scale and Expansion (Optional)

**Duration:** January 2027 onward  
**Goal:** Reach 1,000 paying families; explore institutional channels.

### Key Activities

- **Community referral programme:** families who refer 3 paying families get one free month — word-of-mouth is the most natural growth channel for a product built around family intimacy
- **Institutional licences:** offer white-label or bulk-seat licences to refugee resettlement organisations, diaspora community centres, and university oral history programmes — these buyers have budgets, motivated user bases, and existing trust with the communities Roeung serves
- **iOS and Android native apps:** the Capture flow (recording on mobile) is the most friction-sensitive part of the product; a native app with offline recording and background upload would meaningfully improve submission rates for families with unreliable internet (Cambodia, rural Germany)
- **Grant funding:** apply to NEH (National Endowment for the Humanities), Digital Preservation grants, and diaspora-focused foundations (e.g. Open Society) — not as a revenue model but to fund language expansion and community outreach that pure SaaS revenue may not cover early on

### Phase 4 KPIs
| KPI | Target |
|-----|--------|
| Paying families | ≥1,000 |
| Cumulative revenue | ≥$150,000 |
| Languages supported in AI pipeline | ≥8 |
| Institutional accounts | ≥5 |
| Stories published across all families | ≥5,000 |

---

## Timeline Summary

| Phase | Period | Key Milestone |
|-------|--------|---------------|
| Phase 1: POC | ~Jan–Jun 2026 | Sea family prototype live |
| Phase 2: Pilot | Jul–Sep 2026 | 10+ families; billing live; PMF validated |
| Phase 3: Launch | Oct–Dec 2026 | Public launch; 100 paying families |
| Phase 4: Scale | Jan 2027+ | 1,000 families; institutional channel open |

---

## Go-to-Market Strategy

### Target Customers

The primary buyer is a **diaspora family Keeper** — typically a second-generation adult (25–45 years old) living in the US, Germany, or Australia, who speaks English fluently, is tech-comfortable, and feels an urgent responsibility to capture their parents' or grandparents' memories before they are lost. They are motivated not by nostalgia but by grief prevention. They are the ones who will pay, set up the account, and drive adoption within their family.

The end users (family members who submit stories) are often older first-generation immigrants who may be less tech-fluent. The product's token-URL access model (no login required for submitters) is specifically designed to reduce their friction to zero.

### Sales Channel

**Direct / self-serve** is the primary channel. Roeung is not a B2B enterprise sale — families discover it, sign up, and onboard themselves. This keeps customer acquisition cost low and aligns with the product's intimate, personal nature.

Community partnerships (diaspora organisations, cultural centres) function as **warm referral channels**, not resellers. They share the product with their networks; Roeung offers community discount codes in return. No revenue share is required.

### Key Differentiator

Existing alternatives — Story Worth, Forever, Ancestry audio — are built for English-speaking families in Western contexts. None of them offer:
- Bilingual AI transcription and translation with cultural nuance flagging
- Support for non-Latin script languages (Khmer, Arabic) in both the processing pipeline and the book UI
- A Keeper review workflow that treats human oversight as a first-class feature, not an afterthought

Roeung's moat is its **cultural specificity**. It is not a generic oral history tool that happens to support multiple languages — it is built from the ground up for families whose stories exist in multiple languages, carry cultural references that literal translation will mangle, and involve members with wildly different levels of digital access. That specificity is hard to replicate at scale by a product designed for the mainstream.

---

## Stakeholder Communication Plan

### Stakeholder Groups

**1. Sea Family (Internal Pilot / Origin Story)**
What they need to know: the app will remain available to them; their data is private and will not be shared or used for training without consent; the product may evolve but their stories are safe.  
Who communicates: Ellen (product owner), directly, via family group chat and the Keeper dashboard.  
When: Before any Phase 2 changes; whenever data model changes affect existing stories.

**2. Pilot Families (Phase 2)**
What they need to know: they are early adopters helping shape the product; their feedback will directly influence features; their data is private; they have free access during the pilot.  
Who communicates: Product owner via onboarding email, bi-weekly check-in calls, and an optional feedback Slack/WhatsApp group.  
When: At signup; at 2-week and 4-week check-ins; at pilot close.

**3. Community Partners (Phase 3)**
What they need to know: what Roeung does, how their community members benefit, the discount offer, and that they are not endorsing a commercial product but facilitating access to a tool their members may find valuable.  
Who communicates: Product owner, via a partner brief (1-page PDF) and a follow-up call.  
When: 4 weeks before public launch; at launch; at 30- and 90-day marks.

**4. Paying Customers (Phase 3+)**
What they need to know: pricing, what they get, how to get support, any changes to the product or pricing, and how their data is protected.  
Who communicates: Automated onboarding emails (Stripe/product), in-app notifications for feature updates, direct email for any breaking changes or pricing changes.  
When: At signup; at major feature releases; at least 30 days' notice before any pricing change.

**5. Investors / Funders (Phase 4, if pursued)**
What they need to know: total addressable market (diaspora families globally; ~280M people living outside their country of birth), traction metrics, unit economics, and the cultural mission.  
Who communicates: Product owner / founder, via pitch deck and monthly investor update emails.  
When: At first fundraise; monthly thereafter.

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| AI pipeline costs exceed revenue at scale | Medium | High | Monitor cost-per-story; adjust pricing or compression before launch |
| ElevenLabs / OpenAI API pricing changes | Medium | Medium | Abstract AI providers behind service interfaces; maintain fallback options |
| Low Keeper review completion (stories pile up unreviewed) | Medium | High | In-app nudges; weekly digest email; redesign queue UX if pilot data shows backlog |
| Data breach or audio leak | Low | Critical | Security audit pre-launch; Supabase RLS; no PII in logs |
| Low credit pack repurchase rate | Medium | High | Monitor credit burn rate; in-app prompts when credits run low; ensure families feel value before credits are exhausted |
| Community resistance to AI handling sensitive family stories | Medium | Medium | Clear consent flow; explainability in Keeper UI; human review as a feature, not a footnote |

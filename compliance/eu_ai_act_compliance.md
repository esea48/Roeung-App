# EU AI Act Compliance Package
**System:** Roeung (រឿង) — Family Oral History Application  
**Version:** 1.0  
**Date:** 2026-06-18  
**Prepared by:** Sea Family Development Team  
**Regulation:** Regulation (EU) 2024/1689 of the European Parliament and of the Council (EU AI Act)

---

## 1. Risk Classification

**Classification: Limited Risk**

Roeung's AI system is classified as **Limited Risk** under the EU AI Act. The system is not a prohibited AI practice, does not fall within any Annex III high-risk category, and is not a General-Purpose AI (GPAI) model itself (though it deploys GPAI models as components). Its primary obligations arise under **Article 50** — transparency requirements for AI systems that generate content and interact with natural persons.

---

## 2. Classification Reasoning

The following walkthrough applies the EU AI Act's classification cascade step by step.

### Step 1: Prohibited AI Practices (Article 5) — Does Not Apply

Article 5 prohibits AI systems that: manipulate human behaviour through subliminal or deceptive techniques; exploit vulnerabilities of specific groups; perform social scoring by public authorities; conduct untargeted scraping of facial images; infer emotions in workplace or educational settings; perform biometric categorisation to infer sensitive attributes; or conduct real-time remote biometric identification in public spaces for law enforcement.

Roeung does none of these. It is a private family archive. It does not score, rank, or make consequential decisions about individuals. It does not perform biometric identification of any kind. **→ Prohibited practices: Not applicable.**

### Step 2: High-Risk AI Systems (Article 6 and Annex III) — Does Not Apply

Annex III lists eight areas of high-risk use. Each is assessed below.

**1. Biometric identification and categorisation:** Roeung processes voice recordings, but not for the purpose of identifying or verifying individuals. Transcription converts speech to text; it does not match voice prints to identities or categorise individuals by protected characteristics. → Not applicable.

**2. Critical infrastructure:** Roeung is a family archive application, not a component of water, energy, transport, or digital infrastructure. → Not applicable.

**3. Education and vocational training:** Roeung does not determine access to education, assess students, or evaluate learning outcomes. → Not applicable.

**4. Employment and workers management:** Roeung does not make or influence employment decisions. → Not applicable.

**5. Access to essential private and public services and benefits:** Roeung does not determine access to credit, insurance, healthcare, emergency services, or government benefits. → Not applicable.

**6. Law enforcement:** Roeung has no law enforcement function and is not used by law enforcement authorities. → Not applicable.

**7. Migration, asylum, and border control management:** Roeung has no function related to migration or border control. → Not applicable.

**8. Administration of justice and democratic processes:** Roeung does not influence judicial decisions, elections, or referenda. → Not applicable.

**→ High-risk classification: Not applicable.**

### Step 3: General-Purpose AI (GPAI) Model Obligations (Articles 51–56) — Partial Applicability

Roeung is not a GPAI model provider. However, Roeung **deploys** two GPAI models:

- **OpenAI GPT-4o-mini** — for translation (KH↔EN) and cultural flag review
- **OpenAI GPT-4** — for title generation and people name flagging

As a deployer of GPAI models, Roeung is subject to the deployer-level obligations in the Act (principally transparency and use-in-accordance-with-intended-purpose obligations). The GPAI provider obligations (technical documentation, transparency to downstream users, copyright policy, etc.) rest with OpenAI, not with Roeung.

**→ Roeung is a GPAI deployer, not a GPAI provider. Deployer obligations apply.**

### Step 4: Transparency Obligations (Article 50) — Applies

Article 50 requires that providers of AI systems intended to interact with natural persons inform those persons that they are interacting with an AI system. It also requires that providers of AI systems that generate synthetic content (text, audio, images) ensure that outputs are marked as AI-generated.

Roeung's AI pipeline generates:
- Transcripts of audio recordings (ElevenLabs Scribe v2)
- Translations of those transcripts (GPT-4o-mini)
- Title suggestions (GPT-4)
- Cultural flag explanations (GPT-4o-mini)
- People name detections (GPT-4)

These outputs are presented to Keepers during review and (after Keeper approval) to all family readers in the Book view. **Natural persons interact with AI-generated content.** Transparency obligations therefore apply.

**→ Limited Risk, Article 50 transparency obligations apply.**

### Step 5: Remaining Components — Minimal Risk

The audio quality scoring component (using `librosa` for RMS-based SNR computation) is a rule-based signal processing function, not an AI system as defined in Annex I of the Act (it does not use machine learning or statistical approaches to infer outputs). It is **out of scope** for the AI Act's AI system definition.

The consent gate, story status management, soft lock mechanism, and all CRUD operations are not AI systems. **→ Minimal risk / out of scope.**

---

## 3. Mandatory Requirements Summary (Limited Risk)

Limited Risk systems under Article 50 carry transparency obligations. Although Roeung is not classified as high-risk, the following subsections address the five requirement areas listed in the prompt — noting which are legally mandated and which are implemented voluntarily as best practice.

### 3.1 Data and Data Governance

**Legal mandate for Limited Risk:** Not explicitly required by Article 50 (these apply to high-risk systems under Article 10). Addressed here as a design best-practice and under GDPR, which co-applies.

**How Roeung addresses this:**

- **Consent before collection.** The consent gate (Screen 1.2) is a hard gate — no audio is recorded, no log entry is created, and no data is collected until the recorder explicitly confirms the narrator has agreed. This satisfies GDPR Article 6(1)(a) and reflects the spirit of the AI Act's data governance expectations.
- **Consent audit trail.** A `consent_log` row is created simultaneously with the `stories` row. Consent log rows are never deleted — even if the story is subsequently deleted via GDPR request. `consent_log.story_deleted_at` records that the content was removed while preserving the proof of consent.
- **Consent wording versioning.** All consent text is stored in the `consent_wording_versions` table, keyed by version identifier (e.g., `v1_recorded`). Any historical consent record can be reconstructed by joining `consent_log.consent_wording_key` to this table, without relying on git history.
- **Data minimisation.** The only personal data collected at capture time is: narrator name (verbatim, for consent), recorder name (plain text), device hint (user agent), and hashed IP address. Raw IP addresses are not stored.
- **Audio data.** Audio files are stored in Supabase Storage. On GDPR deletion, the storage object is deleted and `audio_files.storage_key` and `storage_url` are cleared. Files are never overwritten or replaced.
- **Write-once originals.** `transcript_segments.original_text` and `translation_segments.original_text` are set on creation and never updated. Keeper edits go to the separate `edited_text` field. This preserves the integrity of AI outputs as a data record.

**Gap:** No formal data processing agreement (DPA) with OpenAI is documented in the project materials. Before deployment in the EU, a DPA with OpenAI (as a data processor handling personal data in the form of voice transcripts) must be in place under GDPR Article 28.

### 3.2 Human Oversight Mechanisms

**Legal mandate for Limited Risk:** Not formally required by Article 50. Implemented by design.

**How Roeung addresses this:**

Roeung's Keeper review layer is a substantive human oversight mechanism, not a formality. No AI output is published to the family book without passing through a Keeper:

- Every story passes through `awaiting_review` → `in_review` → `published` — there is no automated publication path.
- Keepers can edit any AI-generated transcript segment or translation segment; original AI outputs are preserved in `original_text` for audit.
- Keepers choose from or override AI-generated title suggestions.
- Keepers resolve AI-detected people mentions (link or dismiss) independently of recorder-set tags.
- The translation confidence score and `translation_flagged` boolean are pre-set by AI but **Keeper-overridable in either direction** during review.
- A soft lock prevents two Keepers from editing the same story simultaneously, reducing the risk of conflicting overrides.
- At minimum 3 Keepers are required for succession, ensuring no single Keeper is a single point of failure.

The oversight model is structurally similar to a "human in the loop" architecture: AI generates candidate outputs; a human reviews, corrects, and makes the final publication decision.

### 3.3 Transparency and Information Obligations

**Legal mandate for Limited Risk:** Article 50 requires that natural persons interacting with AI systems are informed they are doing so. AI-generated content must be disclosed as such where it could be mistaken for authentic.

**How Roeung addresses this:**

**For Keepers (Flow 3):**
- The review interface presents transcripts, translations, title suggestions, cultural flags, and people detections explicitly as AI outputs. The Keeper review UI must use language that makes the AI origin of each section unambiguous (e.g., "AI Transcript," "AI Translation," "AI-suggested titles").
- Confidence scores (`translation_confidence_score`, `audio_quality_score`) are displayed per story and per paragraph, giving Keepers a quantified signal of AI reliability.

**For family readers (Flow 4):**
- The `⚠ Translation approximate` badge (visible to readers per Decision #3) provides a transparency signal when a Keeper has flagged uncertain translation quality.
- The story page includes a note: *"This translation may not capture all nuances."* This text should be extended to note that the translation was generated by AI and reviewed by a Keeper.
- The act of Keeper review and approval should be disclosed on story pages (e.g., "Reviewed and published by [Keeper name]") so readers know a human has verified the AI output.

**Gap (action required before deployment):**
1. A site-wide disclosure is needed informing all family members that AI is used in the transcription and translation pipeline. This could be a persistent footer note or an onboarding screen on first visit.
2. The story page should be updated to explicitly attribute translation to AI (e.g., "Translation generated by AI, reviewed by [Keeper name]").
3. AI-suggested titles that are accepted without modification should be noted as such, or the distinction between AI-suggested and Keeper-written titles should be retained in the UI.

### 3.4 Accuracy and Robustness Requirements

**Legal mandate for Limited Risk:** Not formally required by Article 50 (applies to high-risk systems under Article 15). Implemented by design.

**How Roeung addresses this:**

- **Audio quality gate.** Stories with audio quality scores below the configurable `AUDIO_QUALITY_THRESHOLD` are rejected before transcription begins, preventing low-quality inputs from propagating errors through the pipeline. The threshold is an environment variable, not hardcoded.
- **Translation confidence scoring.** Per-segment `confidence_score` (0.0–1.0) is generated by the LLM review pass and aggregated into a story-level `translation_confidence_score`. Stories below a threshold are pre-flagged for Keeper attention.
- **Cultural flag review pass.** A dedicated LLM pass reviews Google Translate outputs (now replaced with GPT-4o-mini per Decision #15) for culturally nuanced phrases, generating `cultural_flag_note` text. This directly addresses a known failure mode: accurate word-for-word translation of Khmer phrases that are culturally meaningless or misleading in English.
- **Pipeline failure handling.** If any pipeline step fails, the error is logged in `stories.processing_error` and `status` remains `'processing'` to allow retry. Stories do not silently move forward with partial AI outputs.
- **Idempotency concern (gap):** Pipeline retry logic should be designed to be idempotent — re-running a step that partially completed should not create duplicate `transcript_segments` or `translation_segments` rows. This is not yet explicitly addressed in the architecture and should be resolved before deployment.

### 3.5 Cybersecurity Considerations

**Legal mandate for Limited Risk:** Not formally required by Article 50. Addressed here as a deployment prerequisite.

**How Roeung addresses this:**

- **Access control.** Family members access the system via a secret token in the URL (`/f/{access_token}`). Keeper routes require JWT authentication (Supabase Auth). The two auth paths are never mixed — a valid family `access_token` does not grant access to Keeper routes.
- **No raw credentials in storage.** Keeper passwords are hashed with bcrypt or argon2. IP addresses in the consent log are hashed, not stored in plaintext.
- **API key management.** AI provider keys (OpenAI, ElevenLabs) are stored as environment variables and never committed to version control. A `.env.example` file documents required variables without values.
- **Supabase row-level security.** All data access should be scoped by `family_id` — every query filters on `family_id` to prevent cross-family data leakage. This should be enforced at the database level via Supabase RLS policies, not only at the application level.

**Gaps:**
1. The family access token (`families.access_token`) is a long-lived shared secret. A leaked token gives full read/record access to the family archive. Token rotation and per-device token mechanisms are explicitly deferred to Phase 2. The risk must be documented and accepted before Phase 1 deployment.
2. No rate limiting or abuse prevention is described for the audio submission endpoint. Malicious submissions could consume AI pipeline quota or storage. Rate limiting should be implemented before public deployment.
3. Supabase RLS policies are not yet specified. These should be defined and audited before deployment.

---

## 4. Conformity Assessment Summary

**System Name:** Roeung (រឿង)  
**System Version:** Phase 1  
**Provider:** Sea Family Development Team  
**Date of Assessment:** 2026-06-18  
**Assessor:** Internal (self-assessment; formal third-party assessment not required for Limited Risk)

### 4.1 What the System Does

Roeung is a private family oral history application designed for the Sea family, with members in the USA, Germany, and Cambodia. The system enables family members to record or upload audio stories in Khmer or English. An AI pipeline automatically transcribes the audio, translates the transcript between Khmer and English, generates title suggestions, flags culturally nuanced phrases, and detects names of people mentioned. The AI outputs are reviewed and curated by designated family members called Keepers, who correct errors, choose titles, and make the final decision to publish each story to a shared family book. Published stories can be read and listened to by all family members.

The AI pipeline is composed of the following models and services:

| Component | Provider / Model | Function |
|---|---|---|
| Speech transcription | ElevenLabs Scribe v2 | Converts audio to text with word-level timestamps |
| Translation | OpenAI GPT-4o-mini | Translates transcript segments KH↔EN |
| Cultural flag review | OpenAI GPT-4o-mini | Flags culturally nuanced phrases; generates explanatory notes |
| Title generation | OpenAI GPT-4 | Generates 3 title suggestions per story in KH and EN |
| People name detection | OpenAI GPT-4 | Detects names and family titles mentioned in the transcript |
| Audio quality scoring | librosa (Python, rule-based) | Computes RMS-based SNR score; gates pipeline entry |

The audio quality scoring component uses rule-based signal processing and is not an AI system under the EU AI Act's Annex I definition. The remaining five components constitute the AI system subject to this assessment.

### 4.2 Risk Class and Basis for Classification

**Risk class: Limited Risk**

Roeung is classified as Limited Risk on the following basis:

1. It is not a prohibited AI practice under Article 5.
2. It does not fall within any Annex III high-risk category. In particular, while it processes voice recordings, it does not perform biometric identification, categorisation, or verification — it converts speech to text for archival purposes within a closed, consented family group.
3. It is not a General-Purpose AI model (it is a deployer of GPAI models).
4. It generates AI-produced text content (transcripts, translations, titles, cultural notes) that is presented to natural persons — Keepers during review and family members when reading published stories. This triggers transparency obligations under Article 50.

The system operates in a private, voluntary, and clearly non-consequential context. Users are family members who have chosen to participate. No decisions with legal or similarly significant effects on individuals are made by or based on the AI outputs.

### 4.3 Applicable Obligations and How the Design Addresses Them

**Article 50(1) — Transparency to persons interacting with AI systems**

Obligation: Providers of AI systems intended to interact with natural persons must ensure those persons are informed they are interacting with an AI system.

Design response: The Keeper review interface presents all AI outputs (transcripts, translations, titles, flags, name detections) in clearly labelled sections attributed to the AI pipeline. Confidence scores are displayed to communicate AI reliability. On the family book side, the `⚠ Translation approximate` badge and the "This translation may not capture all nuances" note on story pages provide a disclosure signal.

Status: Partially met. The Keeper interface design is compliant by intent. The family reader interface requires an explicit AI disclosure statement on story pages and a site-wide onboarding disclosure.

**Article 50(2) — Disclosure of AI-generated synthetic content**

Obligation: Providers of AI systems that generate synthetic audio, video, image, or text content shall ensure outputs are marked as artificially generated or manipulated.

Design response: Transcripts and translations are AI-generated text. They are labelled as AI outputs in the Keeper review UI. On the published story page, Keeper authorship of the curation decision is visible. The connection between the AI-generated translation and its AI origin is implied but not yet explicit in the reader UI.

Status: Partially met. An explicit "AI-generated translation, reviewed by [Keeper]" attribution is needed on published story pages.

**Deployer obligations for GPAI models (Article 25)**

Obligation: Deployers of GPAI models must use them in accordance with the provider's instructions, implement human oversight, and not use them for prohibited purposes.

Design response: OpenAI's usage policies are adhered to. GPT-4o-mini and GPT-4 are used for text translation, cultural review, title generation, and name extraction — all within scope of intended use. Human Keeper oversight is mandatory before any AI output is published.

Status: Met in design. A formal record of compliance with OpenAI's terms of service should be maintained.

### 4.4 Gaps and Remediation Plan

The following gaps exist as of the assessment date. All must be resolved before deployment to EU-resident family members.

| # | Gap | Article / Basis | Remediation | Priority |
|---|---|---|---|---|
| 1 | No explicit AI disclosure on published story pages for family readers | Art. 50(1), 50(2) | Add "AI-generated translation, reviewed by [Keeper name]" to story page template | High — required before deployment |
| 2 | No site-wide AI usage disclosure for family members (non-Keepers) | Art. 50(1) | Add onboarding screen or persistent footer disclosing AI use in pipeline | High — required before deployment |
| 3 | No documented Data Processing Agreement (DPA) with OpenAI | GDPR Art. 28 (co-applicable) | Execute DPA with OpenAI before processing any EU resident's voice data | High — required before deployment |
| 4 | Family access token is a long-lived shared secret with no rotation mechanism | Cybersecurity best practice | Document and accept the risk for Phase 1; implement per-device tokens in Phase 2 | Medium — document risk acceptance |
| 5 | Supabase Row-Level Security (RLS) policies not yet specified | Data governance | Define and test RLS policies scoped to `family_id` before deployment | High — required before deployment |
| 6 | No rate limiting on audio submission endpoint | Cybersecurity best practice | Implement rate limiting per IP or per access token before deployment | Medium — required before deployment |
| 7 | Pipeline retry logic not specified as idempotent | Accuracy / robustness | Specify and implement idempotent retry for each pipeline step to prevent duplicate records | Medium — required before deployment |
| 8 | AI-suggested titles not distinguished from Keeper-written titles in the reader UI | Art. 50(2) | Optionally note on story page whether title was AI-suggested or Keeper-written | Low — good practice, not legally mandated |

---

## 5. Technical Documentation Outline

*Note: For Limited Risk systems, the EU AI Act does not mandate the full technical documentation package required of High Risk systems under Article 11 and Annex IV. The outline below represents the documentation that would be produced as best practice and that would be required if the system's risk classification is ever reassessed.*

---

### Table of Contents — Roeung Technical Documentation Package

**Section 1: System Overview**
1.1 Purpose and use case description  
1.2 Intended users (Keepers; family members; narrators)  
1.3 Deployment context (private family use; EU, US, Cambodia)  
1.4 System architecture diagram  
1.5 AI components inventory (models, providers, versions, API endpoints)  
1.6 Non-AI components inventory  

**Section 2: AI Pipeline Technical Specification**
2.1 Audio quality scoring — algorithm description (librosa RMS/SNR), threshold configuration, rejection behaviour  
2.2 Transcription — ElevenLabs Scribe v2 API specification, language detection logic, segment schema, word-level timestamp format  
2.3 Translation — GPT-4o-mini API specification, system prompt (versioned), per-segment call structure, KH↔EN direction handling  
2.4 Cultural flag review — GPT-4o-mini API specification, system prompt (versioned), `cultural_flag` and `cultural_flag_note` schema  
2.5 Title generation — GPT-4 API specification, system prompt (versioned), bilingual output schema, `title_suggestions` table structure  
2.6 People name detection — GPT-4 API specification, system prompt (versioned), `ai_people_mentions` schema, resolution workflow  
2.7 Translation confidence scoring — scoring methodology, story-level aggregation, `translation_flagged` threshold  
2.8 Pipeline orchestration — ARQ job queue configuration, step ordering, failure handling, retry logic, idempotency guarantees  

**Section 3: Data Governance**
3.1 Data flow diagram (from audio capture through publication)  
3.2 Personal data inventory — data elements, legal basis (GDPR), retention period, deletion procedure  
3.3 Consent mechanism — consent gate design, wording versioning, `consent_log` schema, pre-submission vs. post-submission deletion paths  
3.4 GDPR deletion procedure — step-by-step: audio deletion, content clearing, `consent_log` retention, `deletion_requests` workflow  
3.5 Data Processing Agreements — OpenAI (GPT-4, GPT-4o-mini), ElevenLabs (Scribe v2), Supabase  
3.6 Write-once invariants — `original_text` fields; `consent_log` append-only policy  

**Section 4: Human Oversight**
4.1 Keeper role definition and responsibilities  
4.2 Keeper review workflow (story status flow diagram)  
4.3 Keeper override capabilities — editable fields, overridable AI decisions  
4.4 Soft lock mechanism — heartbeat specification, timeout, release procedure  
4.5 Succession policy — minimum Keeper count (3), Keeper provisioning and deactivation  

**Section 5: Transparency Measures**
5.1 AI disclosures in the Keeper review interface — labelling spec per UI section  
5.2 AI disclosures in the family book — story page attribution, translation note, `⚠ Translation approximate` badge  
5.3 Site-wide AI usage disclosure — onboarding screen or footer text (versioned)  
5.4 Consent wording — full text (English and Khmer) for `v1_recorded` and `v1_uploaded`  

**Section 6: Security**
6.1 Authentication design — family access token (URL-based); Keeper JWT (Supabase Auth)  
6.2 Authorisation model — auth path separation; `family_id` scoping  
6.3 Supabase RLS policy specifications  
6.4 Secret management — environment variable inventory; `.env.example`; API key rotation policy  
6.5 Rate limiting specification — audio submission endpoint; Keeper API endpoints  
6.6 Known risks and accepted residual risk — family access token longevity (Phase 1)  

**Section 7: Accuracy and Robustness**
7.1 Audio quality threshold — current value, rationale, review cadence  
7.2 Translation confidence threshold — current value, rationale, review cadence  
7.3 Known AI failure modes — Khmer cultural phrase loss; mixed-language segment handling; homonym resolution  
7.4 Monitoring and incident response — pipeline error logging, `processing_error` field, retry triggers, Keeper escalation path  
7.5 Model version policy — procedure for updating ElevenLabs, OpenAI model versions; regression testing approach  

**Section 8: Compliance Records**
8.1 EU AI Act risk classification record (this document)  
8.2 GDPR Records of Processing Activities (RoPA)  
8.3 Data Processing Agreements (executed copies)  
8.4 AI provider terms of service compliance records  
8.5 Gap remediation log — tracking closure of items in Section 4.4  
8.6 Incident log — any processing errors, data breaches, or user complaints  

---

*This document should be reviewed and updated before any material change to the AI pipeline, model versions, data flows, or user base. Next scheduled review: prior to Phase 2 development.*

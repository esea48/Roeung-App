# GDPR Documentation — Roeung (រឿង) Family Oral History App

**Version:** 1.0  
**Date:** 2026-06-18  
**Controller:** Sea Family (private, non-commercial)  
**Scope:** All users globally (USA, Germany, Cambodia). GDPR compliance is applied uniformly as the most stringent applicable standard.

---

## 1. Data Flow Map

The table below traces every category of personal data through the system, from source to destination.

| Data Category | Source | Stored In | Processed By | Sent To |
|---|---|---|---|---|
| Narrator name (verbatim) | Consent gate (self-entered) | PostgreSQL (`stories`, `consent_log`) | FastAPI backend | None |
| Recorder name (self-reported) | Consent gate | PostgreSQL (`stories`) | FastAPI backend | None |
| Audio recording | Family member's device | Supabase Storage (blob) | ElevenLabs Scribe v2 (transcription) | ElevenLabs |
| Transcript text | AI pipeline | PostgreSQL (`transcript_segments`) | Google Translate API, OpenAI GPT-4 | Google, OpenAI |
| Translation text | AI pipeline | PostgreSQL (`translation_segments`) | OpenAI GPT-4 (cultural review) | OpenAI |
| People mentioned in audio | AI pipeline | PostgreSQL (`ai_people_mentions`) | FastAPI backend | None |
| IP address (hashed) | HTTP request headers | PostgreSQL (`consent_log`) | FastAPI backend (hashing only) | None |
| Device/browser hint | HTTP User-Agent header | PostgreSQL (`consent_log`) | FastAPI backend | None |
| Keeper email + password hash | Keeper onboarding | PostgreSQL (`keepers`) | Supabase Auth | None |
| Consent wording shown | System-generated | PostgreSQL (`consent_wording_versions`) | FastAPI backend | None |
| Deletion requests | Family member self-submission | PostgreSQL (`deletion_requests`) | Keeper (human review) | None |

**Data flow summary (narrative):**

A family member opens the private family link (`/f/{access_token}`) on their device. They enter a narrator name and recorder name on the consent gate, consent to the terms, and either record audio directly in the browser or upload an audio file. The audio is uploaded to Supabase Storage (hosted on AWS S3). The FastAPI backend queues an AI pipeline job via ARQ/Redis. The pipeline sends the audio to ElevenLabs for transcription, sends the resulting text to Google Translate for initial translation, then sends the translation to OpenAI GPT-4 for cultural review. All AI outputs are stored in PostgreSQL (hosted on Supabase). A Keeper reviews and edits the transcript and translation via an authenticated web interface. Upon publication, the processed story is readable by all family members via the private family link. No data is sent to advertising networks, analytics providers, or any party other than those listed above.

---

## 2. Processing Activities Register

### 2.1 Consent and Identity Data

| Field | Detail |
|---|---|
| **What data** | Narrator name (verbatim text), recorder name (text), timestamp of consent, consent wording version shown |
| **Purpose** | Establish and record informed consent before capturing personal audio; audit trail for compliance |
| **Legal basis** | **Consent** (GDPR Art. 6(1)(a)) — family member actively taps a consent gate before any recording begins |
| **Retention** | `consent_log` rows are retained **indefinitely** even after story deletion — this is the legal record that consent was obtained. `stories.narrator_name_raw` is cleared on GDPR deletion but the `consent_log` row persists. |
| **Third-party recipients** | None |

### 2.2 Audio Recordings

| Field | Detail |
|---|---|
| **What data** | Raw audio file (voice recording of a family member narrating personal and family history, potentially including names, dates, locations, health information, and accounts of historical trauma) |
| **Purpose** | Primary content of the family archive; enables transcription and publication |
| **Legal basis** | **Consent** (GDPR Art. 6(1)(a)) — consent gate explicitly covers audio capture and AI processing |
| **Retention** | Retained for the lifetime of the family archive. Deleted from Supabase Storage on GDPR deletion request (storage key and URL cleared from `audio_files`). Audio files are never overwritten; on deletion the object is removed and the DB fields are cleared. |
| **Third-party recipients** | **ElevenLabs** (transcription) — audio is transmitted to the ElevenLabs Scribe v2 API. See Section 5. |

### 2.3 Transcripts and Translations

| Field | Detail |
|---|---|
| **What data** | Word-for-word transcription of audio content in Khmer and/or English; translation into the other language; per-segment confidence scores; cultural flag notes |
| **Purpose** | Enable bilingual reading and listening; support Keeper review and correction |
| **Legal basis** | **Consent** (GDPR Art. 6(1)(a)) — consent covers AI processing including transcription and translation |
| **Retention** | Retained for the lifetime of the family archive. Original AI text (`original_text`) is write-once. On GDPR deletion, the parent story record is cleared; transcript and translation segments are cascade-deleted with the story. |
| **Third-party recipients** | **Google Cloud Translation API** (initial translation pass); **OpenAI GPT-4** (cultural review pass). See Section 5. |

### 2.4 AI-Detected People Mentions

| Field | Detail |
|---|---|
| **What data** | Names of individuals detected in the audio transcript (e.g., "Grandfather Sok", "Uncle Rith") |
| **Purpose** | Help Keepers tag family members to stories; build the relational index of the family archive |
| **Legal basis** | **Consent** (GDPR Art. 6(1)(a)) — consent covers AI processing; **Legitimate interests** (GDPR Art. 6(1)(f)) for third parties mentioned — processing names of others mentioned in oral history is necessary for the core purpose of the archive and is unlikely to harm the named individuals, who are family members |
| **Retention** | Retained with the story. Deleted when the story is GDPR-deleted. |
| **Third-party recipients** | **OpenAI GPT-4** (people flagging step of AI pipeline). Names are extracted from transcript text sent to OpenAI. See Section 5. |

### 2.5 Keeper Account Data

| Field | Detail |
|---|---|
| **What data** | Keeper name, email address, bcrypt/argon2 password hash |
| **Purpose** | Authenticate Keepers; attribute editorial decisions (approvals, edits, publications) to specific Keepers |
| **Legal basis** | **Contract** (GDPR Art. 6(1)(b)) — Keepers have an agreed role in the family archive that requires identity and authentication |
| **Retention** | Retained while the Keeper account is active. Soft-disabled (`is_active = false`) rather than deleted to preserve attribution on historical edits. Hard deletion on explicit request. |
| **Third-party recipients** | **Supabase** (PostgreSQL hosting and Auth layer — Phase 2 migration planned). See Section 5. |

### 2.6 Network Metadata (IP Address and User Agent)

| Field | Detail |
|---|---|
| **What data** | Hashed IP address (one-way hash; original IP is not stored); HTTP User-Agent string (device/browser hint) |
| **Purpose** | Fraud and abuse detection; consent audit integrity (shows consent came from a real device request) |
| **Legal basis** | **Legitimate interests** (GDPR Art. 6(1)(f)) — storing a one-way hash (not the raw IP) is the minimum necessary to preserve audit integrity without retaining directly identifiable network data |
| **Retention** | Retained with `consent_log` indefinitely (same rationale as consent data). |
| **Third-party recipients** | None — hashing is performed by the FastAPI backend before any storage. |

### 2.7 Deletion Requests

| Field | Detail |
|---|---|
| **What data** | Self-reported name of requester, optional reason text, timestamp |
| **Purpose** | Facilitate and audit GDPR deletion rights; create a Keeper-facing workflow |
| **Legal basis** | **Legal obligation** (GDPR Art. 6(1)(c)) — processing is necessary to comply with the right to erasure (Art. 17) |
| **Retention** | Retained indefinitely as an audit record of rights-request handling. |
| **Third-party recipients** | None |

---

## 3. Data Protection Impact Assessment (DPIA)

**Processing activity assessed:** AI pipeline processing of audio recordings — transcription, translation, and people-mention extraction — via third-party APIs (ElevenLabs, Google, OpenAI).

This was selected as the highest-risk processing activity because it involves: (a) transmission of sensitive personal audio containing family trauma narratives to external processors; (b) automated extraction of third-party names; (c) processing of special-category-adjacent content (accounts of political persecution, violence, and death under the Khmer Rouge).

### 3.1 Description of the Processing

When a family member submits an audio recording, the ARQ worker pipeline automatically:

1. Runs an audio quality check.
2. Sends the audio file to ElevenLabs Scribe v2 for speech-to-text transcription.
3. Sends the transcript text to Google Cloud Translation API for translation between Khmer and English.
4. Sends both the transcript and translation to OpenAI GPT-4 to review cultural phrases and detect names of people mentioned.
5. Stores all outputs in PostgreSQL on Supabase.

No human reviews the data before it reaches these third-party processors. The processing is fully automated until the Keeper review stage.

### 3.2 Necessity and Proportionality Assessment

**Necessity:** The core purpose of Roeung is to make Khmer-language oral histories accessible to family members across three countries, many of whom do not speak Khmer fluently. Transcription and translation are not optional enhancements — they are what makes the archive meaningful to English-speaking family members. Name detection is used to surface connections between stories, which is a primary archival value. AI processing is the only feasible way to do this at the scale of a private family archive without a dedicated professional translation team.

**Proportionality:** The data sent to third-party APIs is limited to what is necessary. IP addresses are hashed before storage. Audio is sent to ElevenLabs for transcription only; the transcript (text) is then sent onwards — audio is not sent to Google or OpenAI. Data minimisation is applied at each pipeline step.

**Alternative considered:** Human-only transcription and translation. This is disproportionately expensive and slow for a private family archive and would not reduce risk meaningfully, since the same content would need to be shared with human translators.

### 3.3 Risks to Data Subjects

| Risk | Likelihood | Severity | Notes |
|---|---|---|---|
| Audio content shared with third-party processors without explicit understanding | Medium | High | Family members may not appreciate that their voice recordings are sent to US-based AI companies. Consent wording must make this explicit. |
| Content describing Khmer Rouge-era trauma processed by commercial AI | Low | High | Narratives may include accounts of violence, persecution, and death. Mishandling or breach at a processor could cause distress or reputational harm. |
| Names of third parties (mentioned individuals) sent to OpenAI without their consent | Medium | Medium | Family members mentioned in stories have not individually consented to having their names processed by OpenAI. |
| Data breach at a third-party processor | Low | High | Audio and transcript content is sensitive; a breach at ElevenLabs, Google, or OpenAI could expose family trauma narratives. |
| Unauthorised access via leaked family access token | Medium | High | The family link (`/f/{access_token}`) is the only authentication for non-Keeper members; a leaked link gives read/record access. |
| Retention of consent log after data deletion creates a partial re-identification risk | Low | Low | The consent log retains a name and timestamp even after story deletion, by design. This is a deliberate legal trade-off (consent audit) and the log contains no audio or transcript. |

### 3.4 Mitigation Measures

| Risk | Mitigation |
|---|---|
| Insufficient consent transparency | Consent wording (v1, stored in `consent_wording_versions`) must explicitly name ElevenLabs, Google, and OpenAI as processors, describe what data each receives, and state where data is stored geographically. Consent is version-controlled so wording shown at any historical point is reconstructible. |
| Khmer Rouge-era content at third parties | Data Processing Agreements (DPAs) executed with ElevenLabs, Google, and OpenAI before go-live. Processor contracts must prohibit use of submitted data for model training without separate opt-in. |
| Third-party names in AI pipeline | Cultural context noted in consent wording: "Stories may mention other family members by name; those names may be processed as part of the AI transcription." This provides a reasonable basis under legitimate interests for incidental third-party name processing within a closed family archive. |
| Third-party data breach | DPAs in place; use of TLS in transit; no audio retained at processors beyond the API call (verify via processor documentation). Audit processor data retention policies annually. |
| Leaked family access token | Token rotation mechanism to be implemented in Phase 2. For Phase 1: token is shared only via direct family communication, not posted publicly. Keepers should be advised to treat it like a password. |
| Consent log re-identification | The consent log stores a first name or name string only — not enough for re-identification without the audio. Risk assessed as low. |

### 3.5 Residual Risk Rating

**Overall residual risk: Medium.**

The primary residual risk is the transmission of sensitive family narratives — including accounts of Khmer Rouge-era trauma — to US-based commercial AI processors. This risk cannot be fully eliminated while AI processing remains central to the product. It is mitigated by: explicit consent, contractual safeguards (DPAs), data minimisation, and the closed/private nature of the archive. The risk is accepted by the Sea family as controller on the basis that the archival purpose is significant and the alternative (no digitisation) forecloses family access to these histories entirely.

---

## 4. Data Subject Rights

All data subjects (narrators, recorders, family members mentioned in stories) have the following rights under GDPR. The table below describes how Roeung implements each.

| Right | Implementation |
|---|---|
| **Right of access (Art. 15)** | Family members may request a copy of their personal data by contacting a Keeper. Keepers can export story content, consent log entries, and tags for a named individual. No automated self-service portal in Phase 1 — handled manually by Keeper. |
| **Right to erasure (Art. 17)** | Implemented via the `deletion_requests` workflow. Any family member can submit a deletion request post-publication (via the app or directly to a Keeper). On approval: audio is deleted from Supabase Storage; story content fields are cleared; `stories.status` is set to `'deleted'` (terminal). The `consent_log` row is **retained** with `story_deleted_at` set — this is a deliberate exception permitted under Art. 17(3)(e) (legal claims) and Art. 17(3)(b) (legal obligation to retain consent evidence). Pre-submission: recorder can delete their own recording at any time before submitting; hard-delete of story and audio, `consent_log` retained with `pre_submission_deleted_at`. |
| **Right to rectification (Art. 16)** | Keepers can correct transcript and translation text via the review interface (`edited_text` fields). Family member names in the roster (`family_members`) can be corrected by Keepers. Direct rectification by non-Keeper family members is handled via a Keeper request in Phase 1. |
| **Right to data portability (Art. 20)** | Keepers can export story content (transcript, translation, audio file URL) for a given subject on request. No automated export format in Phase 1; manual JSON or document export by Keeper. |
| **Right to object (Art. 21)** | Where processing is on the basis of legitimate interests (network metadata, third-party people mentions), data subjects may object. Objections are handled manually by Keepers and result in removal of the specific data. For consent-based processing, withdrawal of consent achieves the equivalent outcome via the erasure request workflow. |
| **Right to withdraw consent (Art. 7(3))** | Equivalent to a deletion request. Family members may contact a Keeper at any time to withdraw consent and request deletion of their story. Withdrawal does not affect lawfulness of processing prior to withdrawal. |
| **Right not to be subject to automated decision-making (Art. 22)** | No automated decisions with legal or similarly significant effects are made. AI outputs (transcripts, translations, quality scores) are all subject to Keeper human review before publication. Rejected stories (failed audio quality check) are surfaced to Keepers, who can decide whether to request re-recording. |

---

## 5. Third-Party Data Transfers

### 5.1 Supabase (PostgreSQL + Storage)

| Field | Detail |
|---|---|
| **What data is sent** | All structured data (stories, transcripts, translations, family member records, consent logs, etc.); audio files in blob storage |
| **Purpose** | Database hosting and file storage |
| **Legal mechanism** | Supabase offers a Data Processing Agreement (DPA) and is subject to EU Standard Contractual Clauses (SCCs) for data transfers to the USA |
| **Data location** | Supabase is US-based. Storage region should be configured to EU (Frankfurt / `eu-central-1`) for EU data subjects where possible. Confirm region selection before go-live. |
| **Retention at processor** | Data retained until deleted by controller (Roeung). Supabase does not independently retain deleted data beyond standard backup windows (configurable). |

### 5.2 ElevenLabs (Transcription)

| Field | Detail |
|---|---|
| **What data is sent** | Raw audio files (voice recordings) |
| **Purpose** | Automatic speech-to-text transcription via ElevenLabs Scribe v2 API |
| **Legal mechanism** | ElevenLabs DPA / Standard Contractual Clauses (SCCs). Verify that ElevenLabs' current DPA covers the Scribe API before go-live. |
| **Data location** | ElevenLabs is US-based. Confirm whether audio is processed and retained in the EU or USA. Request a data residency commitment if available. |
| **Retention at processor** | Verify ElevenLabs' API data retention policy. Consent wording should accurately reflect whether audio is retained post-processing. Contract should prohibit training data use. |

### 5.3 Google Cloud Translation API

| Field | Detail |
|---|---|
| **What data is sent** | Transcript text (the output of ElevenLabs transcription — text only, no audio) |
| **Purpose** | Initial Khmer↔English translation |
| **Legal mechanism** | Google Cloud Data Processing Addendum (DPA), which incorporates SCCs for international transfers. Google Cloud Translation API is covered by Google Cloud's GDPR commitments. |
| **Data location** | Google Cloud; data processing region can be specified. Use `europe-west` region for EU compliance where possible. |
| **Retention at processor** | Google Cloud Translation API does not retain input/output data for training by default (confirm via Google's current DPA). Data is processed transiently per the API call. |

### 5.4 OpenAI (Cultural Review and People Flagging)

| Field | Detail |
|---|---|
| **What data is sent** | Transcript text and initial translation text (for cultural flag review); transcript text (for people mention detection) |
| **Purpose** | Cultural phrase identification and confidence scoring; detection of family member names mentioned in stories |
| **Legal mechanism** | OpenAI Data Processing Agreement (DPA), available for API customers. Includes SCCs for EU–US transfers. |
| **Data location** | OpenAI processes data in the USA. SCCs are the transfer mechanism. |
| **Retention at processor** | OpenAI's API usage policy states that API data is not used for training by default. Confirm via the executed DPA. Request zero-retention mode if available and appropriate. |
| **Special considerations** | Stories submitted to Roeung may include accounts of political persecution, violence, and death. While this content is not classified as special category data under GDPR Art. 9 in the strict sense (it is historical testimony, not health or biometric data), it is sensitive in nature. The DPA with OpenAI should include a clause prohibiting use of this data for any purpose other than the API call response. |

### 5.5 Railway (Backend Hosting)

| Field | Detail |
|---|---|
| **What data is sent** | All data flows through the FastAPI backend hosted on Railway (application tier only — persistent data lives in Supabase) |
| **Purpose** | Backend compute and API hosting |
| **Legal mechanism** | Railway DPA / SCCs. Railway is US-based. |
| **Data location** | USA. Railway region selection should target the region closest to users. Persistent data is in Supabase (see 5.1). |
| **Retention at processor** | Application logs may contain personal data (e.g., request parameters with names). Ensure Railway log retention is configured to a short window (e.g., 30 days) and logs do not include audio content or raw transcript text. |

---

## 6. Pre-Launch Checklist

The following items must be completed before the app is made available to family members:

- [ ] Execute Data Processing Agreements with ElevenLabs, Google Cloud, OpenAI, Supabase, and Railway
- [ ] Confirm ElevenLabs data retention policy for the Scribe v2 API; update consent wording if audio is retained post-call
- [ ] Configure Supabase Storage region to EU (`eu-central-1`) where feasible
- [ ] Review and finalise consent wording in `consent_wording_versions` — wording must name all third-party processors
- [ ] Confirm Google Cloud Translation API region is set to `europe-west`
- [ ] Configure Railway log retention to ≤ 30 days; ensure logs do not contain audio or transcript content
- [ ] Appoint a point of contact for data subject rights requests (a named Keeper)
- [ ] Document the family access token distribution method and instruct Keepers to treat it as a secret

# Use Case Definition Document
## Roeung (រឿង) — AI-Powered Family Oral History Platform

---

## 1. Business Problem Statement

**Problem:** Oral histories from elderly family members — especially those who lived through the Khmer Rouge genocide and subsequent diaspora — are disappearing as those individuals age and pass away. These stories exist primarily in spoken Khmer and are inaccessible to younger generations who may not speak the language fluently, and to family members dispersed across multiple countries.

**Who it affects:** The Sea family, with members in the United States, Germany, and Cambodia. The same problem applies broadly to any diaspora family whose elder generation carries stories in a non-dominant language.

**Core pain points:**
- Stories are told once, in conversation, and never preserved
- Language barriers prevent intergenerational transmission (Khmer-speaking elders, English-dominant younger members)
- No accessible, culturally sensitive tool exists for structured family oral history archiving
- Family members in different time zones cannot coordinate a manual transcription and translation effort

---

## 2. Company / Project Profile

| Attribute | Detail |
|---|---|
| **Type** | Private family project (non-commercial) |
| **Scale** | Startup / early-stage: single family, small user base (~10–30 members) |
| **Industry** | Cultural preservation / personal heritage tech |
| **Operational state** | Pre-launch; in active development (Phase 1) |
| **Geographic spread** | USA, Germany, Cambodia |
| **Languages** | Khmer (ភាសាខ្មែរ) and English |
| **Primary constraint** | Non-technical family members must be able to use it without training |

---

## 3. Proposed AI Solution

Roeung uses an **AI processing pipeline** that runs automatically after a family member submits an audio recording. The pipeline performs the following steps in sequence:

### 3a. What the AI Does

| Step | AI Task | Type |
|---|---|---|
| Audio quality check | Scores recording for clarity and usability | Classification |
| Transcription | Converts spoken Khmer or English audio to text with word-level timestamps | Generative (speech-to-text) |
| Translation | Produces a first-pass translation from Khmer to English (or vice versa) | Generative (sequence-to-sequence) |
| Cultural flag review | Identifies translation segments that carry cultural nuance, idiom, or historically sensitive content requiring human review | Classification + Generation |
| Title generation | Suggests three candidate titles for the story in both Khmer and English | Generative |
| People detection | Identifies names of family members mentioned in the story | Named Entity Recognition (NER) |
| Confidence scoring | Aggregates per-segment confidence into a story-level score; flags stories for priority Keeper review | Aggregation / Scoring |

### 3b. AI Systems Involved

- **ElevenLabs Scribe v2** — transcription (speech-to-text)
- **Google Cloud Translation API** — first-pass translation (neural MT)
- **GPT-4 / Claude API** — cultural flag review, title generation, people flagging (generative LLM)

### 3c. Human-in-the-Loop

The AI output is never published directly. Designated family **Keepers** review every story — reading AI-generated transcripts and translations, resolving flagged cultural segments, confirming or correcting detected family member tags, and selecting a final title — before approving publication to the shared family book.

---

## 4. Key Stakeholders

| Stakeholder | Role | Relationship to AI |
|---|---|---|
| **Story submitters** (family members) | Record and upload audio stories | Trigger the AI pipeline; never interact with AI output directly |
| **Keepers** | Designated family reviewers with edit and publish authority | Primary consumers of AI output; correct and approve before publication |
| **Readers** (all family members) | Access the published family book | Benefit from AI-translated and curated content |
| **Ellen Sea** (project owner) | Product decision-maker; configures thresholds and Keeper permissions | Controls AI quality thresholds and pipeline configuration |
| **AI service providers** | ElevenLabs, Google Cloud, OpenAI/Anthropic | Provide underlying model capabilities |

---

## 5. Success Criteria

### Measurable Outcome 1 — Translation Accuracy (Keeper Correction Rate)
**Target:** Keepers edit fewer than 30% of AI-generated translation segments per story before approving.

**Measurement:** Track the ratio of `translation_segments` where `edited_text IS NOT NULL` (Keeper made a correction) versus total segments, per published story. Average across the first 20 published stories.

**Rationale:** A correction rate above 30% indicates the AI translation is not saving meaningful time and may be introducing errors that require close reading of every line.

---

### Measurable Outcome 2 — Story Preservation Rate (Time to Published)
**Target:** At least 80% of submitted stories reach `status = 'published'` within 7 days of submission.

**Measurement:** For each story where `status = 'published'`, compute `published_at - submitted_at`. Track the percentage where this interval is ≤ 7 days, over a rolling 30-day window.

**Rationale:** The AI pipeline's value is reducing the manual effort bottleneck. If stories stall in the review queue, the system is not achieving its preservation goal — elder family members continue to be at risk of passing before their stories are captured and shared.

---

### Measurable Outcome 3 — Audio Rejection Rate (Quality Signal Accuracy)
**Target:** Fewer than 10% of stories are rejected at the audio quality check step, and no story that passes the quality check is later flagged by a Keeper as unintelligible.

**Measurement:** Track `status = 'rejected'` rate from the audio quality step. For approved stories, collect Keeper feedback on audio clarity (binary: usable / not usable).

**Rationale:** The threshold must be calibrated correctly — too strict wastes valid recordings; too lenient sends unprocessable audio through the expensive transcription step.

---

## 6. Out-of-Scope Boundaries

The following are explicitly excluded from Phase 1 of this solution:

| Out of scope | Reason |
|---|---|
| **Family tree / genealogy features** | Separate product surface; added complexity without core preservation value in Phase 1 |
| **Image or video upload** | Audio-first scope; media handling adds storage and processing complexity |
| **Email or push notifications** | Keeper workflow relies on direct access; notifications deferred to Phase 2 |
| **User accounts for non-Keeper family members** | Token-based URL access is sufficient; account management adds friction for non-technical users |
| **Offline mode** | Requires significant engineering investment; internet access assumed for all target users |
| **Printed / exported book** | Physical or PDF export is a Phase 2 feature |
| **Automatic AI publication without Keeper review** | AI output is never published directly — human review is a non-negotiable invariant |
| **Real-time translation during recording** | Transcription and translation run post-submission, not live |
| **Support for languages other than Khmer and English** | Scoped to the Sea family's languages in Phase 1 |

---

*Document version: 1.0 — June 2026*
*Project: Roeung (រឿង) — Sea Family Oral History Archive*

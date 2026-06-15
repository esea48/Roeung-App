# Roeung (រឿង) — Phase 1 UX Flows
**Version:** 0.2  
**Date:** 2026-06-15  
**Scope:** End-to-end — Record → AI Processing → Keeper Review → Book Reading

---

## Overview

Four connected flows make up the Phase 1 experience:

1. **Recording** (mobile-first) — any family member records a story
2. **AI Processing** (background) — automated transcription, translation, titling
3. **Keeper Review** (desktop-optimised, mobile-responsive) — designated curators approve and publish
4. **Book Reading** (desktop + mobile) — family reads, listens, and is prompted to contribute

---

## Flow 1: Capture (Mobile-First)

**Actors:** Any family member  
**Access:** Via private family link — no login required  
**Two paths:** Live recording or audio file upload — both share the same consent, tag, confirm, and sent screens.

### Screens

#### 1.1 Home
- Two equal capture options: "Record a Story" and "Upload Audio"
- Scrollable list of recently published stories (read-only preview)
- Language toggle (EN / KH) persisted per device

#### 1.2 Consent Gate *(shared by both paths, wording differs)*
- Hard gate — shown before mic opens or file picker appears
- **Live recording wording:** *"We're about to record [Name]'s story. They have agreed to be recorded and for this story to be shared with the family."*
- **Upload wording:** *"The person in this recording agreed to have it shared with the family."*
- Single tap: "Yes, they've agreed" — logs narrator name + timestamp (GDPR)
- Recorder can cancel here with nothing started

#### 1.3a Live Recording *(Record path)*
- Animated waveform gives live feedback that the mic is active
- Running timer (MM:SS) — max 60 minutes
- Single large "Stop" button — no other controls to confuse
- Auto-save every few seconds locally, stitched on upload (protects against drops, locks, battery loss)
- Discard option (requires confirm) to start over
- **Edge case:** Background noise warning shown if levels exceed threshold *(open Q: define threshold)*

#### 1.3b Upload Audio *(Upload path)*
- File picker: accepts mp3, m4a, wav — up to 500MB
- File name and duration shown after selection for confirmation
- Option to pick a different file before continuing
- Upload begins in background once confirmed; progress indicator shown

#### 1.4 Quick Tag *(shared by both paths)*
- Chips of known family member names (pre-populated from seed data)
- Tap chips to select — "people mentioned in this story"
- "Someone else" opens a simple free-text field
- "Skip for now" allowed — Keeper can tag during review
- **Principle:** No categories, dates, or other metadata at capture time. Capture first, organise later.

#### 1.5 Confirm & Send *(shared by both paths)*
- Playback option so the Recorder can preview before submitting
- Summary shown: duration, names tagged, capture method (recorded / uploaded)
- "Delete recording" button available — no request process, just direct deletion before submission
- GDPR deletion request (with history log) only applies after a story has been sent to Keepers
- Tapping "Send to Keepers" submits — consent was already logged at 1.2

#### 1.6 Sent Confirmation *(shared by both paths)*
- Warm success state: *"Your story is with the Keepers 🙏"*
- Estimated review time shown if known
- Prompt to capture another story or return home

---

## Flow 2: AI Processing (Background, Automated)

**Trigger:** Audio file submitted  
**Output:** Story card packaged for Keeper review queue

### Steps

#### 2.1 Transcription
- Auto-detect language (Khmer / English / mixed)
- Model: Whisper or equivalent, Khmer-tuned
- Transcript stored with word-level timestamps for audio sync
- Raw transcript preserved and never overwritten — edits tracked separately
- **Open Q:** Minimum audio quality threshold before pipeline proceeds vs. returning to narrator

#### 2.2 Translation
- Khmer → English and English → Khmer both generated in full
- Cultural phrases flagged where direct translation may lose meaning
- **Open Q:** Translation model selection — Khmer quality is a known risk

#### 2.3 Title Generation
- 3 title suggestions surfaced to Keeper (they pick or write their own)
- Titles generated in both EN and KH
- Tone calibrated: story-like, not summary-like (e.g. *"The Flood of '79"* not *"Story about flooding"*)

#### 2.4 People Flagging
- AI detects names and family titles mentioned in the audio (e.g. "Grandfather Sok", "Aunt Maly")
- These are surfaced separately from the Recorder's tags — Keeper manually links them to known family members
- Distinct from Recorder tags: Recorder tags = who the story is *about*; AI flags = who is *mentioned* by name
- Unlinked names held as free text until Keeper resolves them

#### 2.5 Quality Scoring
- Translation confidence score attached per paragraph
- Low-confidence paragraphs highlighted in Keeper review UI
- `⚠ Translation needs review` flag set if overall score below threshold
- Audio quality score captured (background noise, clipping)

#### 2.6 Keeper Queue Entry
- Story packaged: audio + transcript + translation + title suggestions + Recorder tags + AI people flags + confidence scores
- Keepers notified via in-app badge *(Phase 2: email)*
- Any Keeper can claim the review; first to open it soft-locks it (*"Ellen Sea is reviewing"*)

---

## Flow 3: Keeper Review (Desktop-Optimised)

**Actors:** Designated Keepers (minimum 3 for succession)  
**Access:** Authenticated web app — optimised for desktop, works on mobile

### Screens

#### 3.1 Review Queue
- Card per story: narrator name, duration, date recorded, language, tag preview
- `⚠` badge on stories with low translation confidence
- Claimed stories shown as locked with reviewer name
- Default sort: newest first; sort option available (oldest first for chronological backlog clearing)
- Filter by: narrator, language, flag status

#### 3.2 Story Review
- Audio player with waveform; transcript scrolls in sync (click paragraph to jump)
- Side-by-side bilingual transcript — KH left, EN right (or toggled)
- Editable text fields for transcript and translation corrections *(edits tracked, raw preserved)*
- Title picker: choose from 3 AI suggestions or type a custom title (in both languages)
- Tag editor: confirm or edit Recorder's name chips, add more
- **People linker:** AI-flagged names shown as a separate list — Keeper links each to a known family member or dismisses as free text
- Translation quality flag toggle: `⚠ Translation approximate` (visible to readers)

#### 3.3 Decision Point
Keeper chooses one of:
- **Approve** — AI output is good; publish directly
- **Publish with flag** — story goes live marked "Translation approximate" (visible to readers)
- **Archive privately** — story is preserved but not published to the book

*"Return to narrator" dropped from MVP — too awkward in a family context. Keepers edit what they have or archive.*

#### 3.4 Publish
- One-click "Publish to Book" button
- Optional: assign to a chapter (or leave uncategorised)
- Translation quality flag carried through to book view if set
- Publish is **reversible** — Keeper can unpublish and re-edit at any time

#### 3.5 Live Confirmation
- Story immediately appears in the book
- Narrator sees *"Your story is live!"* in-app notification *(email in Phase 2)*
- Keeper sees confirmation + direct link to the published story

---

## Flow 4: Book Reading (Desktop + Mobile)

**Actors:** All family members  
**Access:** Via private family link — no login required

### Screens

#### 4.1 Book Home
- Cover-style landing: family name, decorative Khmer motif
- Chapters listed as "shelves" — default chapters for this family:
  - *Life Before the War*
  - *The Khmer Rouge Period*
  - *Migration & Resettlement*
  - *(Uncategorised)* — stories not yet assigned to a chapter
- "Recently added" strip at the top for new stories
- Global EN / KH toggle — persists for session

#### 4.2 Chapter View
- Story cards: title, narrator, duration, language badge
- Sort options: newest first (default) or narrative chronology (Keeper-set)
- `⚠ Translation approximate` badge visible to readers on applicable cards

#### 4.3 Story Page
- Full bilingual text — EN and KH shown side-by-side or toggled (user preference)
- Narrator name and date recorded shown prominently
- Translation quality note if flagged: *"This translation may not capture all nuances"*
- Tags link to other stories mentioning the same people
- Prev / Next story navigation within chapter

#### 4.4 Listen Mode
- Audio player with sentence-level highlight sync in transcript
- Playback speed control: 0.75×, 1×, 1.25×
- Can read EN text while listening to original KH audio simultaneously

#### 4.5 Record Yours CTA
- Surfaces after reading a story: *"Do you have a memory like this?"*
- Deep-links to the recording flow, optionally pre-filling the same people tags
- Only shown on mobile (where recording is available)

---

## Open Questions (Inherited from PRD v0.3)

| # | Question | Flow affected |
|---|---|---|
| 1 | Khmer translation quality — which model? | AI Processing (2.2) |
| 2 | Background noise threshold for rejection | Capture (1.3a), AI Processing (2.5) |
| 3 | ~~Interview prompt guide — show before/during recording?~~ **Closed: no prompt guide. Fully freeform.** | Capture (1.3a) |
| 4 | Deceased member design treatment | Book (4.3), Tag (1.4) |
| 5 | ~~Consent wording for uploads~~ **Closed: past-tense wording for upload path** — *"The person in this recording agreed to have it shared with the family."* Live recording path keeps present-tense wording. | Capture (1.2, 1.3b) |

---

## Out of Scope (Phase 2)

- Family tree integration
- Recipes, image upload with AI captions, photo gallery
- Email notifications
- User login / account creation
- Offline mode
- Printed book export

---

*Next: Convert flows to wireframes, define data model, or resolve open questions.*

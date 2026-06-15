# Roeung (រឿង) — Key Design Decisions
**Version:** 0.1  
**Date:** 2026-06-15  
**Scope:** Decisions made during Phase 1 UX flow and wireframe session

---

## 1. Consent gate is a hard gate before anything starts

**Decision:** Show the consent screen before the microphone opens or the file picker appears. Nothing is recorded, uploaded, or logged until the user taps "Yes, they've agreed."

**Why:** GDPR requires consent to be given freely before data collection — not buried after. Placing it first also makes the intent clear to the recorder: this step is about the narrator's rights, not a formality. Cancelling at the consent screen leaves no trace.

---

## 2. Consent wording differs between live recording and upload

**Decision:**
- Live recording: present tense — *"We're about to record [Name]'s story. They have agreed to be recorded and for this story to be shared with the family."*
- Upload: past tense — *"The person in this recording agreed to have it shared with the family."*

**Why:** The tenses reflect reality. For live recording, the narrator is present and consent is being given in the moment. For uploads, the recording already exists — the narrator agreed at some earlier point. Using present tense for an upload would be inaccurate and could create a false consent record.

---

## 3. Translation flag is visible to readers

**Decision:** The "Translation approximate" flag, when set by a Keeper, is shown to readers on the story page. (PRD v0.3 originally said it would be invisible to readers.)

**Why:** Hiding the flag would mislead readers into treating an uncertain translation as authoritative. For a family preserving oral histories across languages, transparency about translation quality matters — especially for Khmer, where nuance and cultural context are frequently lost. Readers can decide how much weight to give the English text.

---

## 4. Review queue sorts newest-first by default, with an oldest-first option

**Decision:** Stories in the Keeper review queue appear newest-first by default. Keepers can switch to oldest-first.

**Why:** Newest-first keeps the queue feeling current and motivating — new contributions appear immediately. Oldest-first is available for Keepers who want to clear a chronological backlog (e.g., processing a batch of older family recordings). Both needs are real; defaulting to newest is the more common daily-use pattern.

---

## 5. Upload audio is a first-class capture path, not a secondary option

**Decision:** "Upload Audio" sits alongside "Record a Story" on the home screen with equal visual weight. Both paths share the same consent, tag, confirm, and sent screens — they branch only at screens 1.3a / 1.3b.

**Why:** Many families already have recordings — voicemails, WhatsApp voice notes, videos, old cassette rips. Treating upload as a second-class path would mean a significant portion of the family's existing stories can't enter the archive easily. Equal weighting reflects equal value.

---

## 6. Pre-submission deletion is direct — no request process

**Decision:** On the Confirm & Send screen, the "Delete recording" button triggers a simple confirmation dialog and then permanently deletes the audio. No GDPR deletion request, no log.

**Why:** Before a story is submitted to Keepers, it is entirely in the recorder's control. The GDPR deletion request process (with timestamp log) only applies once a story has been sent — at that point it becomes part of the family record. Pre-submission, the recorder is simply choosing not to submit, which requires no paper trail.

---

## 7. Narrator name is pre-selected on the Quick Tag screen

**Decision:** The narrator's name (established at the consent gate) is pre-ticked as a chip on the Quick Tag screen.

**Why:** The most common case is that a story is primarily *about* the narrator. Pre-ticking reduces friction without removing choice — the recorder can deselect it or add more people. It also reduces the risk of a story being submitted with no tags at all.

---

## 8. No capture-time metadata beyond people tags

**Decision:** The Quick Tag screen asks only "who is this story about?" — no categories, chapters, dates, or other metadata at capture time.

**Why:** Adding friction at capture time risks the recorder abandoning the flow before submitting. The Keeper, who has more context and time, is better placed to handle organisation. The principle: *capture first, organise later*.

---

## 9. "Return to narrator" was dropped from Keeper decisions

**Decision:** Keepers have three options only: Approve, Publish with flag, Archive privately. "Return to narrator" (sending the story back for re-recording) was removed.

**Why:** In a family context, "return to narrator" is socially awkward. Telling a grandparent their story was rejected and asking them to re-record it is unlikely to happen in practice. Keepers can edit what they have (transcript corrections, title changes) or archive privately if the recording isn't suitable. The option would have been unused and would have added UI complexity for no real gain.

---

## 10. Two separate people-tagging systems, kept visually distinct

**Decision:** Recorder tags (who the story is *about*, chosen at Quick Tag) and AI-detected people (names *mentioned* in the audio) are treated as separate systems in the Keeper review UI — shown in different sections, with different affordances.

**Why:** Conflating the two would create confusion. A story about Grandfather Sokha might mention Uncle Virak, the French customer next door, and a local politician — none of whom the story is *about*. The Keeper needs to treat these differently: confirming narrator tags vs. deciding whether to link or dismiss incidentally mentioned names.

---

## 11. Keeper review UI is responsive — desktop primary, mobile works too

**Decision:** The Keeper review interface is designed desktop-first (sidebar nav, side-by-side bilingual transcript). On mobile, the transcript collapses to KH / EN tabs, the decision bar simplifies to Approve + ··· (secondary actions in a bottom sheet), and all fields stack vertically.

**Why:** Curation work — reading, editing, comparing transcripts — is genuinely better on a larger screen. But Keepers shouldn't be blocked if they want to process a story from their phone. "Desktop primary, mobile works too" acknowledges the primary use case without making mobile impossible.

---

## 12. Soft lock on Keeper review — first to open it locks it

**Decision:** When a Keeper opens a story for review, it is soft-locked to them. Other Keepers see *"Ellen Sea is reviewing"* and cannot open it.

**Why:** With a minimum of 3 Keepers, two people could easily open the same story simultaneously and make conflicting edits. The soft lock prevents this without a complex merge workflow. "Soft" means the lock expires after a timeout (timeout duration is still an open question) so stories don't get permanently blocked if a Keeper steps away.

---

## 13. All flows are desktop and mobile — no flow is screen-size exclusive

**Decision:** Every flow must work on both desktop and mobile. Primary experience per flow: Capture is mobile-primary (that's where recording happens); Keeper Review is desktop-primary (curation work suits a larger screen, but mobile must work); Book Reading is equal desktop and mobile.

**Why:** Family members are spread across three countries with different device habits. Restricting any flow to a single screen size would exclude parts of the family. The previous framing of Capture as "Mobile" and Keeper Review as "Desktop" described primary use cases, not exclusions.

---

## Open Questions (not yet closed)

| # | Question | Flow affected |
|---|---|---|
| 1 | Khmer translation model — which one? Quality is a known risk. | AI Processing (2.2) |
| 2 | Background noise threshold — at what level does the app warn / reject? | Capture (1.3a), AI Processing (2.5) |
| 4 | Deceased family members — how are they indicated in tags and story pages? | Book (4.3), Tag (1.4) |
| — | Soft lock timeout — how long before a locked story becomes available again? | Keeper Review (3.1, 3.2) |

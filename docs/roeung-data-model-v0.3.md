# Roeung (រឿង) — Phase 1 Data Model
**Version:** 0.3  
**Date:** 2026-06-15  
**Scope:** Phase 1 — Sea family only, all four flows

---

## Stack Decisions

These choices were made before the model was designed and shape every table.

| Decision | Choice | Rationale |
|---|---|---|
| Database | PostgreSQL (relational) | Well-defined entities, cross-entity queries (stories ↔ people ↔ chapters) |
| Multi-family | `family_id` on every entity now | Avoids a painful schema migration when second family onboards |
| Family roster | Keeper-managed live table | Chip list always reflects current members; handles births, deaths, marriages without developer involvement |
| Audio storage | Blob storage (S3/GCS) + DB URL | DB stores the key/URL; raw bytes live in cloud object storage |
| Translation pipeline | Hybrid: Google Translate API + GPT-4/Claude | Google for KH coverage; LLM pass for `cultural_flag` and `cultural_flag_note` generation |
| Keeper auth | Email/password (`password_hash` in DB) | Phase 1; migrate to auth provider in Phase 2 if needed |
| Consent wording storage | `consent_wording_versions` DB table | Self-contained audit trail; no reliance on git history to reconstruct wording shown |
| Tech stack | FastAPI + React/Vite + Supabase + ARQ + Railway | Python backend; Supabase for Postgres, storage, and auth; ARQ for AI pipeline jobs |
| Soft lock mechanism | Heartbeat — client pings every 5 min; lock expires 10 min after last ping | Lock releases automatically on tab close; requires a `/stories/:id/ping` endpoint |
| Deceased member display | † symbol next to name | e.g. "Grandfather Sokha †" — on chips and story pages |

---

## Entity Index

| Table | Owned by | Created when |
|---|---|---|
| `families` | System | Family is set up |
| `family_members` | Keeper | Added via settings screen |
| `keepers` | System admin | Keeper is provisioned |
| `consent_wording_versions` | System admin | Wording is created or updated |
| `stories` | System | Audio is submitted |
| `audio_files` | System | Audio is uploaded |
| `consent_log` | System | Consent gate is tapped |
| `story_tags` | Recorder / Keeper | Quick Tag screen or Keeper review |
| `transcript_segments` | AI | Transcription completes |
| `translation_segments` | AI | Translation completes |
| `title_suggestions` | AI | Title generation completes |
| `ai_people_mentions` | AI | People flagging completes |
| `keeper_locks` | System | Keeper opens a story for review |
| `chapters` | Keeper | Created/managed in settings |
| `deletion_requests` | Recorder / Narrator | GDPR request submitted post-publication |

---

## Flow 1: Capture

The Capture flow creates the foundational records. Everything else is derived from or linked to what's created here.

### What gets stored

**On page load (private family link)**

The family link (`/f/{access_token}`) authenticates the session. The `families.access_token` is checked — no cookie, no login. This is the only auth mechanism for non-Keeper family members.

> ⚠️ **Design decision — link security:** A leaked `access_token` gives full read/record access to the family archive. For Phase 1 this is acceptable (it's a small, trusted group). Plan for per-device tokens or link rotation in Phase 2.

**On consent gate tap**

Two records are created simultaneously:

1. A `stories` row is inserted with `status = 'submitted'` and all consent fields populated.
2. A `consent_log` row is inserted as an immutable audit record.

The `consent_log` is separate from `stories` intentionally — it must survive even if the story is later deleted via a GDPR request. The log proves consent was given; deleting it would be legally incorrect.

Fields populated at this step: `narrator_id`, `narrator_name_raw`, `recorder_name`, `capture_method`, `consent_given_at`, `consent_wording_key`.

> ⚠️ **Design decision — consent wording versioning:** The `consent_wording_key` (e.g., `'v1_recorded'`, `'v1_uploaded'`) records which version of the consent text was shown. The full wording text is stored in the `consent_wording_versions` table (see entity reference below), keyed by this string. This keeps the audit trail self-contained in the DB — no reliance on git history to reconstruct what was displayed years later.

> ⚠️ **Design decision — narrator vs. recorder:** The app distinguishes the narrator (the person the story is about, a family member) from the recorder (whoever is holding the phone). The narrator is a `family_members` row; the recorder is just a name string, since they may not be in the family roster. `narrator_id` is a FK; `recorder_name` is plain text.

**On audio upload (upload path) or recording stop (record path)**

An `audio_files` row is created pointing to the file in blob storage.

The UX doc specifies auto-save chunks that are stitched on upload. Individual chunks are not stored server-side — only the final stitched file is persisted. The `audio_files` row is created once the stitched upload is complete.

> ⚠️ **Design decision — one audio file per story (Phase 1):** Phase 1 stores one original per story. If multi-segment or multi-track support is needed later (e.g., interviewer + narrator on separate tracks), the `audio_files` table already supports multiple rows per `story_id` — `file_type` can be extended.

**On Quick Tag submission**

`story_tags` rows are created for each selected person. The narrator's tag is pre-created when the story is created (pre-ticked chip, per Decision #7 in the decisions doc), with `tagged_by = 'recorder'`.

Free-text "Someone else" entries create a `story_tags` row with `family_member_id = NULL` and the raw name in `name_raw`. Keepers can link these to `family_members` rows during review.

**On "Delete recording" (pre-submission)**

The `stories` row and `audio_files` row are hard-deleted. The `consent_log` row is **retained** but marked with a `pre_submission_deleted_at` timestamp. No GDPR process — this is the recorder choosing not to submit.

---

## Flow 2: AI Processing

The AI pipeline runs after submission and enriches the `stories` row. `status` progresses from `'submitted'` → `'processing'` → `'awaiting_review'` (or `'rejected'` if audio quality is below threshold).

### What gets stored

**Transcription (step 2.1)**

`transcript_segments` rows are created — one per utterance/paragraph. Each segment has:
- Start and end timestamps (millisecond precision) for audio sync
- The original AI text (`original_text`) — never overwritten
- A nullable `edited_text` for Keeper corrections
- Word-level timestamps stored as a JSONB column

> ⚠️ **Design decision — word-level timestamps as JSONB:** Word-level data is stored as `word_timestamps JSONB` (array of `{word, start_ms, end_ms}`) on the segment row rather than a separate `word_timestamps` table. This avoids tens of thousands of rows per story and is sufficient for sentence-level highlight sync in Listen Mode. If word-level querying across stories becomes a requirement, migrate to a separate table.

> ⚠️ **Design decision — edit tracking (Phase 1 simplification):** `original_text` and `edited_text` are stored on the same row. This captures the before/after for a single edit. If a Keeper edits, Keeper B edits again, the second edit overwrites `edited_text` with no history of Keeper A's version. For Phase 1 this is acceptable — these are family stories, not legal documents. Add an `edits` audit table in Phase 2 if version history is needed.

**Translation (step 2.2)**

`translation_segments` rows are created parallel to `transcript_segments`. Each has a FK back to its source `transcript_segment_id`.

Both directions are stored: KH→EN and EN→KH. For mixed-language stories, each segment is translated from its detected language into the other.

**Pipeline:** Google Translate API handles the initial translation (strong Khmer coverage). A second LLM pass (GPT-4 or Claude) reviews the output for cultural phrases and generates `cultural_flag_note` text where needed. The LLM also assigns the `confidence_score` per segment. An overall story-level `translation_confidence_score` is computed as the mean and written to `stories`.

**Title generation (step 2.3)**

Three `title_suggestions` rows are created per story — in both languages (6 rows total: 3 EN + 3 KH pairs, linked by `suggestion_index`).

> ⚠️ **Design decision — title storage:** The final chosen title lives in `stories.title_en` / `stories.title_kh`. Keepers can select a suggestion (setting `selected = true` on the suggestion rows) or type a custom title (no suggestion is marked selected). The suggestions table is preserved for potential AI training feedback.

**People flagging (step 2.4)**

`ai_people_mentions` rows are created for each name detected — family titles, given names, and combinations (e.g., "Grandfather Sok"). These are unlinked (`family_member_id = NULL`, `resolution_status = 'pending'`) until a Keeper resolves them.

> ⚠️ **Design decision — two people systems:** `story_tags` (recorder-set, who the story is *about*) and `ai_people_mentions` (AI-detected, who is *mentioned*) are separate tables with different semantics, per Decision #10 in the decisions doc. When a Keeper links an `ai_people_mention` to a `family_members` row, the system should also create a corresponding `story_tags` row with `tagged_by = 'keeper'` — so the resolved link surfaces in the story's tag list. This is the expected behavior but should be made explicit in the application logic.

**Quality scoring (step 2.5)**

`stories.audio_quality_score` and `stories.translation_confidence_score` are written. If `translation_confidence_score` is below a threshold (to be defined — open question), `stories.translation_flagged` is pre-set to `true` as a suggestion to the Keeper. The Keeper can override this in either direction.

> ⚠️ **Design decision — audio quality rejection:** Low-quality audio sets `stories.status = 'rejected'` and blocks the pipeline. `'rejected'` is included in the status enum. The rejection threshold (dB level, SNR, or similar) is still to be defined — the developer should make this a configurable constant, not a hardcoded value. A rejected story is surfaced to Keepers with the quality score so they can decide whether to request a re-recording outside the app.

**Status update**

Once all AI steps complete, `stories.status` is set to `'awaiting_review'`. Keeper in-app badge counts are driven by `SELECT COUNT(*) FROM stories WHERE family_id = ? AND status = 'awaiting_review'` — no separate notification table needed for Phase 1.

---

## Flow 3: Keeper Review

Keepers authenticate with email/password. They see only stories within their `family_id`.

### What gets stored

**On opening a story (soft lock)**

A `keeper_locks` row is inserted. Other Keepers see `status = 'in_review'` on the queue card and the locking Keeper's name (joined from `keepers`).

> ⚠️ **Design decision — soft lock heartbeat:** The client sends a `POST /stories/:id/ping` every 5 minutes while the Keeper has the story open. `expires_at` is extended by 10 minutes on each ping. A lock with `released_at IS NULL AND expires_at < NOW()` is considered expired and the story is available to other Keepers. The frontend should handle tab/window close by sending a final ping with a `release=true` flag to set `released_at` immediately (via `navigator.sendBeacon`).

**During review — edits**

Transcript edits: `transcript_segments.edited_text`, `edited_by`, `edited_at` are set.

Translation edits: `translation_segments.edited_text`, `edited_by`, `edited_at` are set.

The Keeper sets the final title: `stories.title_en` and `stories.title_kh`. If a suggestion was chosen, `title_suggestions.selected = true` is set on the matching rows.

People tags: Keeper can add `story_tags` rows, confirm existing recorder tags, or remove incorrect ones. For `ai_people_mentions` rows, Keeper sets `resolution_status` to `'linked'` (and sets `family_member_id`) or `'dismissed'`. Linking creates a new `story_tags` row.

Translation quality flag: Keeper can toggle `stories.translation_flagged`. This flag is visible to readers (per Decision #3 in the decisions doc).

**On decision (Approve / Publish with flag / Archive)**

| Decision | Status set to | Fields updated |
|---|---|---|
| Approve | `'published'` | `published_at`, `published_by`, `chapter_id` (optional) |
| Publish with flag | `'published'` | Same as above + `translation_flagged = true` |
| Archive privately | `'archived'` | `archived_at`, `archived_by` |

Publish is reversible. Unpublishing sets `status = 'unpublished'` and clears `published_at`. The story re-enters the Keeper's control and can be re-edited and re-published.

The `keeper_locks` row is released (`released_at` is set) when the Keeper submits a decision.

**GDPR deletion requests (post-publication)**

After a story is published, any family member can request deletion. A `deletion_requests` row is created. Keepers see and resolve it. On resolution:
- If `'deleted'`: audio file is removed from blob storage, story content is cleared, `stories.status` is set to a terminal `'deleted'` state. The `consent_log` row is retained with a note.
- If `'rejected'`: `deletion_requests.resolution = 'rejected'`, with a required `resolution_note`.

> ⚠️ **Design decision — consent log retention after deletion:** Even when a story is fully deleted, the `consent_log` row must be retained. It is the legal record that consent was given. Set `consent_log.story_deleted_at` to record when the content was removed, but do not delete the log row.

---

## Flow 4: Book Reading

No new rows are created during reading. This flow is entirely read-only for the database.

### What gets queried

**Book home (`/f/{access_token}/book`):** Fetches all `chapters` for the family ordered by `sort_order`, plus a "recently added" strip (`stories WHERE status = 'published' ORDER BY published_at DESC LIMIT 5`).

**Chapter view:** Fetches all `stories WHERE chapter_id = ? AND status = 'published'`. Default sort: `published_at DESC`. Narrative chronology: `chapter_sort_order ASC` (Keeper-set integer).

**Uncategorised shelf:** `stories WHERE chapter_id IS NULL AND status = 'published'`. This is a virtual shelf — no "Uncategorised" chapter row exists. The app constructs it from the NULL FK.

**Story page:** Fetches story + all `transcript_segments` + `translation_segments` (both directions) + `story_tags` (joined to `family_members` for names).

**Listen Mode (4.4):** The `word_timestamps` JSONB on each `transcript_segment` drives sentence-level highlight sync. The audio player seeks to `start_ms` of the relevant segment; the client highlights the segment text.

**"Record Yours" CTA (4.5):** Deep-links to the Capture flow with the current story's `story_tags` pre-populated. Tags are passed as query parameters (family member IDs) — no new DB write until the user actually submits a new story.

---

## Complete Entity Reference

### `consent_wording_versions`

Canonical record of every version of consent text ever shown. Append-only — never update or delete rows.

| Column | Type | Notes |
|---|---|---|
| `key` | TEXT PK | e.g. `'v1_recorded'`, `'v1_uploaded'` |
| `capture_method` | ENUM | `recorded`, `uploaded` |
| `language` | ENUM | `en`, `kh` — store both language versions |
| `text` | TEXT NOT NULL | Full wording shown on screen |
| `effective_from` | TIMESTAMPTZ NOT NULL | When this version became active |
| `superseded_at` | TIMESTAMPTZ | Set when a newer version replaces this one |

`consent_log.consent_wording_key` is a foreign key to `consent_wording_versions.key`. To reconstruct exactly what was shown for any historical consent record: `SELECT text FROM consent_wording_versions WHERE key = consent_log.consent_wording_key`.

---

### `families`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `name` | TEXT NOT NULL | Display name, e.g. "Sea Family" |
| `slug` | TEXT UNIQUE | URL-friendly, e.g. "sea-family" |
| `access_token` | TEXT UNIQUE NOT NULL | Secret in the private family link |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

---

### `family_members`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `family_id` | UUID FK → families | |
| `name_en` | TEXT NOT NULL | English name |
| `name_kh` | TEXT | Khmer name (nullable) |
| `is_deceased` | BOOLEAN DEFAULT false | |
| `deceased_date` | DATE | Full date — nullable; day/month may be unknown for older family members |
| `birth_year` | INTEGER | |
| `notes` | TEXT | Keeper-facing notes |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

> ⚠️ **Design decision — deceased member display:** Deceased members show as "Name †" (e.g. "Grandfather Sokha †") on tag chips and story pages. `deceased_date` is a full DATE; day and/or month may be unknown for older family members — the UI should handle partial dates gracefully (e.g. show year only when month/day are absent). Consider storing partial dates as the first of the month / first of January as a convention, with a separate `deceased_date_precision` field (`year`, `month`, `day`) so the display layer knows what to show.

---

### `keepers`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `family_id` | UUID FK → families | |
| `name` | TEXT NOT NULL | |
| `email` | TEXT UNIQUE NOT NULL | |
| `password_hash` | TEXT NOT NULL | bcrypt or argon2; Phase 1 email/password auth |
| `is_active` | BOOLEAN DEFAULT true | Soft-disable without deleting |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

> ⚠️ **Design decision — Keeper auth:** Phase 1 uses email/password. Use bcrypt or argon2 for `password_hash` — never plain text or MD5. If migrating to an auth provider later (Auth0, Supabase Auth, Clerk), `password_hash` would be replaced by an `external_auth_id`; structure the auth layer so this swap is localised.

---

### `stories`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `family_id` | UUID FK → families | |
| `status` | ENUM | `submitted`, `processing`, `awaiting_review`, `rejected`, `in_review`, `published`, `archived`, `unpublished`, `deleted` |
| `capture_method` | ENUM | `recorded`, `uploaded` |
| `narrator_id` | UUID FK → family_members | Nullable — narrator may not yet be in roster |
| `narrator_name_raw` | TEXT NOT NULL | Verbatim name from consent gate (audit) |
| `recorder_name` | TEXT | Who held the phone / submitted the upload |
| `consent_given_at` | TIMESTAMPTZ NOT NULL | |
| `consent_wording_key` | TEXT NOT NULL | e.g. `'v1_recorded'` — references canonical wording |
| `submitted_at` | TIMESTAMPTZ | |
| `language_detected` | ENUM | `kh`, `en`, `mixed` — set by AI |
| `audio_quality_score` | FLOAT | 0.0–1.0, set by AI |
| `translation_confidence_score` | FLOAT | 0.0–1.0, overall story score, set by AI |
| `translation_flagged` | BOOLEAN DEFAULT false | "Translation approximate" flag — visible to readers |
| `title_en` | TEXT | Set by Keeper |
| `title_kh` | TEXT | Set by Keeper |
| `chapter_id` | UUID FK → chapters | Nullable — NULL = Uncategorised |
| `chapter_sort_order` | INTEGER | Keeper-set for narrative chronology within chapter |
| `published_at` | TIMESTAMPTZ | |
| `published_by` | UUID FK → keepers | |
| `archived_at` | TIMESTAMPTZ | |
| `archived_by` | UUID FK → keepers | |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

> ⚠️ **Design decision — `status` is the single source of truth:** Do not duplicate story lifecycle state across multiple boolean columns (e.g., `is_published`, `is_archived`). The enum is the authority. All queries should filter on `status`.

---

### `audio_files`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `story_id` | UUID FK → stories | |
| `family_id` | UUID FK → families | Denormalised for access control queries |
| `storage_key` | TEXT NOT NULL | Object key in S3/GCS |
| `storage_url` | TEXT | CDN or presigned URL — may be generated on demand |
| `file_type` | ENUM | `original` (Phase 1 only) |
| `mime_type` | TEXT | `audio/mpeg`, `audio/mp4`, `audio/wav` |
| `duration_seconds` | INTEGER | |
| `file_size_bytes` | BIGINT | |
| `created_at` | TIMESTAMPTZ | |

---

### `consent_log`

Append-only. Never updated or deleted.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `story_id` | UUID FK → stories | Retained even after story deletion |
| `family_id` | UUID FK → families | |
| `narrator_name` | TEXT NOT NULL | Verbatim at time of consent |
| `capture_method` | ENUM | `recorded`, `uploaded` |
| `consent_wording_key` | TEXT NOT NULL | |
| `consented_at` | TIMESTAMPTZ NOT NULL | |
| `device_hint` | TEXT | User agent string |
| `ip_hash` | TEXT | Hashed (not raw) IP — GDPR compliance |
| `pre_submission_deleted_at` | TIMESTAMPTZ | Set if recorder deleted before submitting |
| `story_deleted_at` | TIMESTAMPTZ | Set if story was GDPR-deleted post-publication |

---

### `story_tags`

People associated with a story — either tagged by the recorder or confirmed/added by a Keeper.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `story_id` | UUID FK → stories | |
| `family_member_id` | UUID FK → family_members | Nullable — NULL for unresolved free-text names |
| `name_raw` | TEXT NOT NULL | Name as entered or resolved |
| `tagged_by` | ENUM | `recorder`, `keeper` |
| `created_at` | TIMESTAMPTZ | |

---

### `transcript_segments`

One row per utterance/paragraph in the original audio. Created by AI; editable by Keepers.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `story_id` | UUID FK → stories | |
| `language` | ENUM | `kh`, `en` — detected language of this segment |
| `segment_index` | INTEGER NOT NULL | Ordering within story |
| `start_ms` | INTEGER NOT NULL | Milliseconds from audio start |
| `end_ms` | INTEGER NOT NULL | |
| `original_text` | TEXT NOT NULL | Raw AI output — never updated |
| `edited_text` | TEXT | Keeper correction — NULL means unedited |
| `edited_by` | UUID FK → keepers | |
| `edited_at` | TIMESTAMPTZ | |
| `word_timestamps` | JSONB | Array of `{word, start_ms, end_ms}` for Listen Mode sync |
| `created_at` | TIMESTAMPTZ | |

---

### `translation_segments`

Parallel to `transcript_segments`. Stores AI-generated translations, editable by Keepers.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `story_id` | UUID FK → stories | |
| `transcript_segment_id` | UUID FK → transcript_segments | Source segment this translates |
| `source_language` | ENUM | `kh`, `en` |
| `target_language` | ENUM | `kh`, `en` |
| `segment_index` | INTEGER NOT NULL | Matches source segment index |
| `original_text` | TEXT NOT NULL | AI output — never updated |
| `edited_text` | TEXT | Keeper correction — NULL means unedited |
| `edited_by` | UUID FK → keepers | |
| `edited_at` | TIMESTAMPTZ | |
| `confidence_score` | FLOAT | Per-paragraph confidence (0.0–1.0) |
| `cultural_flag` | BOOLEAN DEFAULT false | AI flagged as culturally nuanced |
| `cultural_flag_note` | TEXT | AI explanation of the cultural phrase |
| `created_at` | TIMESTAMPTZ | |

---

### `title_suggestions`

AI-generated title options shown to Keeper during review.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `story_id` | UUID FK → stories | |
| `language` | ENUM | `kh`, `en` |
| `suggestion_index` | INTEGER | 1, 2, or 3 |
| `text` | TEXT NOT NULL | The suggested title |
| `selected` | BOOLEAN DEFAULT false | Set true if Keeper chose this suggestion |
| `created_at` | TIMESTAMPTZ | |

Note: `stories.title_en` and `stories.title_kh` hold the final title regardless of source (selected suggestion or custom). The suggestions table is for audit and AI improvement.

---

### `ai_people_mentions`

Names detected in the audio by the AI pipeline. Separate from recorder-set `story_tags`.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `story_id` | UUID FK → stories | |
| `name_raw` | TEXT NOT NULL | Name as detected (e.g. "Grandfather Sok") |
| `family_member_id` | UUID FK → family_members | NULL until Keeper links it |
| `resolution_status` | ENUM | `pending`, `linked`, `dismissed` |
| `resolved_by` | UUID FK → keepers | |
| `resolved_at` | TIMESTAMPTZ | |
| `created_at` | TIMESTAMPTZ | |

When a Keeper sets `resolution_status = 'linked'` and assigns `family_member_id`, the application should also create a `story_tags` row with `tagged_by = 'keeper'`. This is application logic, not a DB constraint, but should be documented for the developer.

---

### `keeper_locks`

Soft locks on stories under active Keeper review.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `story_id` | UUID UNIQUE FK → stories | One active lock per story |
| `keeper_id` | UUID FK → keepers | |
| `locked_at` | TIMESTAMPTZ NOT NULL | |
| `expires_at` | TIMESTAMPTZ NOT NULL | Duration TBD — see open question |
| `released_at` | TIMESTAMPTZ | NULL = still active |

A lock is considered active when `released_at IS NULL AND expires_at > NOW()`. The queue query should filter out expired locks and surface those stories as available.

> ⚠️ **Open question — lock timeout duration:** Recommend starting with 2 hours. If a heartbeat mechanism is implemented later, the client POSTs to a `/ping` endpoint every 5 minutes to extend `expires_at`; the lock expires 10 minutes after the last ping.

---

### `chapters`

Pre-seeded for the Sea family. Keepers can manage via a settings screen.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `family_id` | UUID FK → families | |
| `title_en` | TEXT NOT NULL | |
| `title_kh` | TEXT | |
| `sort_order` | INTEGER NOT NULL | Display order on Book Home |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

**Seed data for Sea family:**

| sort_order | title_en | title_kh |
|---|---|---|
| 1 | Life Before the War | *(to be provided)* |
| 2 | The Khmer Rouge Period | *(to be provided)* |
| 3 | Migration & Resettlement | *(to be provided)* |

Stories with `chapter_id IS NULL` appear in the "Uncategorised" virtual shelf — no chapter row needed.

---

### `deletion_requests`

Post-publication GDPR deletion requests, resolved by Keepers.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `story_id` | UUID FK → stories | |
| `family_id` | UUID FK → families | |
| `requested_by_name` | TEXT NOT NULL | Self-reported name of requester |
| `reason` | TEXT | Optional |
| `requested_at` | TIMESTAMPTZ NOT NULL | |
| `resolved_at` | TIMESTAMPTZ | |
| `resolved_by` | UUID FK → keepers | |
| `resolution` | ENUM | `deleted`, `rejected` |
| `resolution_note` | TEXT | Required if `rejected` |

---

## Story Status Flow

```
submitted
    ↓  (AI starts)
processing
    ├── rejected    (audio quality below threshold — surfaced to Keepers)
    ↓  (AI completes)
awaiting_review
    ↓  (Keeper opens)
in_review
    ↓  (Keeper decides)
    ├── published   (reversible → unpublished → back to in_review)
    ├── archived    (reversible → back to awaiting_review)
    └── deleted     (terminal — GDPR deletion, content cleared)
```

---

## Open Questions

| # | Question | Tables affected | Impact |
|---|---|---|---|
| — | Audio quality rejection threshold (numeric value) | `stories.audio_quality_score` | Developer should expose as a configurable env variable |
| — | Khmer chapter titles | `chapters` seed data | Needed before seeding the DB |
| — | `deceased_date_precision` field needed? | `family_members` | Whether to add `year`/`month`/`day` precision flag alongside `deceased_date` |

---

## What Is Explicitly Out of Scope (Phase 1)

- Family tree / relationship graph between `family_members`
- Image or video uploads
- Email notifications (no email sending infrastructure needed in Phase 1)
- User accounts for non-Keeper family members
- Offline mode / local storage
- Printed book export

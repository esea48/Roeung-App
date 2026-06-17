# Roeung (រឿង) — Project Brief for Claude Code

Roeung is a private family oral history app for the Sea family (members in USA, Germany, and Cambodia). Family members record or upload audio stories in Khmer or English. AI transcribes, translates, and packages them for review by designated Keepers, who publish them to a shared family book.

---

## Reference Documents

Read these before making structural decisions:

- `roeung-ux-flows-v0.2.md` — all four user flows in detail
- `roeung-decisions-v0.1.md` — closed product decisions with rationale
- `roeung-data-model-v0.3.md` — complete entity reference (canonical)
- `Roeung_PRD_v0.3_updated.docx` — full product requirements

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI (Python) |
| Frontend | React + Vite |
| Database | PostgreSQL via Supabase |
| File storage | Supabase Storage (audio files) |
| Keeper auth | Supabase Auth (email/password) |
| AI job queue | ARQ (async, built on Redis) |
| Hosting | Railway (backend + Redis; frontend via Vite build or Railway static) |
| Transcription | ElevenLabs Scribe v2 API |
| Translation | Google Cloud Translation API (first pass) + OpenAI GPT-4 (cultural flag review pass) |

---

## Project Structure

```
/
├── CLAUDE.md
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── api/                 # Route handlers (one file per domain)
│   │   │   ├── stories.py
│   │   │   ├── keepers.py
│   │   │   ├── family_members.py
│   │   │   └── chapters.py
│   │   ├── models/              # SQLModel table definitions
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── services/            # Business logic (no DB calls in routes)
│   │   │   ├── ai_pipeline.py   # Orchestrates ElevenLabs transcription + translation
│   │   │   ├── storage.py       # Supabase Storage interactions
│   │   │   └── locks.py         # Soft lock + heartbeat logic
│   │   └── workers/             # ARQ job definitions
│   │       └── pipeline.py      # transcribe → translate → title → flag
│   ├── alembic/                 # DB migrations
│   ├── requirements.txt
│   └── .env                     # Never commit — see .env.example
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── capture/         # Flow 1: record + upload
│   │   │   ├── keeper/          # Flow 3: review queue + story review
│   │   │   └── book/            # Flow 4: book home, chapter, story, listen
│   │   ├── components/
│   │   └── main.jsx
│   └── package.json
└── docs/                        # Reference docs (read-only)
```

---

## Auth Model (Two-Tier)

**Family members (no login):**
Access via a secret token in the URL: `/f/{access_token}`. The backend validates `families.access_token` on every request. No cookies, no sessions. This token grants access to Capture (Flow 1) and Book Reading (Flow 4).

**Keepers (authenticated):**
Email/password via Supabase Auth. JWT issued by Supabase, passed as `Authorization: Bearer <token>` on API requests. All Keeper routes must validate the JWT and confirm `keepers.family_id` matches the resource being accessed.

Never mix the two auth paths. A valid family `access_token` does not grant access to Keeper routes.

---

## Story Status Flow

```
submitted → processing → awaiting_review → in_review → published
                     ↘ rejected (audio quality)        ↘ archived
                                                        ↘ unpublished (→ back to in_review)
                                                        ↘ deleted (terminal, GDPR)
```

`stories.status` is the single source of truth. Never use boolean columns to duplicate lifecycle state.

---

## AI Pipeline (ARQ Workers)

Triggered when a story reaches `status = 'submitted'`. Steps run in order; each step updates `stories.status` to `'processing'` with a `processing_step` field (for progress display):

1. **Audio quality check** — score audio; if below threshold (configurable env var `AUDIO_QUALITY_THRESHOLD`), set `status = 'rejected'` and stop.
2. **Transcription** — ElevenLabs Scribe v2 API; create `transcript_segments` rows with word-level timestamps as JSONB.
3. **Translation** — Google Translate API (first pass); create `translation_segments` rows.
4. **Cultural flag review** — GPT-4/Claude API; update `translation_segments` with `cultural_flag`, `cultural_flag_note`, and `confidence_score` per segment.
5. **Title generation** — GPT-4/Claude; create 3 `title_suggestions` rows in both KH and EN.
6. **People flagging** — GPT-4/Claude; create `ai_people_mentions` rows for detected names.
7. **Scoring** — compute mean `confidence_score` across segments; write to `stories.translation_confidence_score`. Pre-set `stories.translation_flagged = true` if below threshold.
8. **Set status** — `status = 'awaiting_review'`.

If any step fails, log the error, set a `processing_error` field on the story, and leave `status = 'processing'` so a retry can be triggered.

---

## Invariants — Never Violate These

These are non-negotiable rules enforced in application logic (no DB constraints can fully cover them):

1. **`transcript_segments.original_text` and `translation_segments.original_text` are write-once.** Set on creation; never updated. Keeper edits go to `edited_text` only.

2. **`consent_log` rows are never deleted.** Not even during GDPR story deletion. Set `story_deleted_at` on the row to record that the content was removed, but retain the row.

3. **Linking an `ai_people_mentions` row to a `family_members` row must also create a `story_tags` row** with `tagged_by = 'keeper'`. These two writes must be atomic (wrap in a transaction).

4. **Audio files in Supabase Storage are never overwritten.** On GDPR deletion, delete the object from storage and clear the `audio_files.storage_key` and `storage_url` fields — do not replace with a new file.

5. **`stories.status` transitions must follow the allowed flow above.** Do not allow arbitrary status updates (e.g., jumping from `submitted` directly to `published`).

---

## Soft Lock (Heartbeat)

When a Keeper opens a story for review:
- Insert a `keeper_locks` row with `expires_at = NOW() + 10 minutes`.
- The frontend sends `POST /stories/:id/ping` every 5 minutes, extending `expires_at` by 10 minutes.
- On tab close, the frontend sends `POST /stories/:id/ping?release=true` via `navigator.sendBeacon` to set `released_at` immediately.
- A lock is active when `released_at IS NULL AND expires_at > NOW()`.
- The queue query must filter out expired locks.

---

## Responsive Design

All four flows must work on both desktop and mobile. Primary experience per flow:

| Flow | Primary | Mobile behaviour |
|---|---|---|
| Capture (Flow 1) | Mobile | Full experience — this is where most recording happens |
| AI Processing (Flow 2) | Background | No UI |
| Keeper Review (Flow 3) | Desktop | Transcript collapses to KH / EN tabs; decision bar simplifies to Approve + ··· bottom sheet; all fields stack vertically |
| Book Reading (Flow 4) | Desktop + Mobile | Bilingual view collapses to toggled tabs on mobile |

Every frontend component must be built responsive. Never build a desktop-only layout. Use a mobile-first CSS approach and enhance for larger screens.

---

## Bilingual Rules

- Both `title_en` and `title_kh` are stored on every story.
- Both `name_en` and `name_kh` are stored on every `family_members` row.
- Transcript and translation segments each carry a `language` field — do not assume a story is monolingual.
- The UI language toggle (EN/KH) is a client-side preference; both languages are always returned from the API.

---

## Deceased Family Members

Display as `"Name †"` (e.g. `"Grandfather Sokha †"`) on tag chips and story pages. `family_members.deceased_date` is a full DATE; day/month may be unknown for older members. Use a `deceased_date_precision` field (`year` | `month` | `day`) so the UI knows what to display.

---

## Seed Data (Sea Family)

Run once on first deploy:

**Chapters:**
| sort_order | title_en | title_kh |
|---|---|---|
| 1 | Life Before the War | *(to be provided)* |
| 2 | The Khmer Rouge Period | *(to be provided)* |
| 3 | Migration & Resettlement | *(to be provided)* |

**Family members:** To be provided separately before seeding.

**Consent wording (v1):**

| key | capture_method | language |
|---|---|---|
| `v1_recorded` | recorded | en + kh |
| `v1_uploaded` | uploaded | en + kh |

Full wording text is in `roeung-ux-flows-v0.2.md` section 1.2.

---

## Out of Scope (Phase 1)

Do not build: family tree, image/video upload, email notifications, user accounts for non-Keepers, offline mode, printed book export.

# Roeung (រឿង)

AI-powered oral history platform for the Sea family — preserving stories told in Khmer before they are lost.

Family members record or upload audio stories. An AI pipeline transcribes, translates, and flags them for cultural review. Designated **Keepers** review and approve each story before it appears in the shared bilingual family book.

---

## Why this exists

Elderly Sea family members who lived through the Khmer Rouge genocide and subsequent diaspora carry irreplaceable oral histories. They are primarily Khmer-speaking; younger family members are primarily English-speaking and spread across the USA, Germany, and Cambodia. Without intervention, these stories are told once in conversation and then lost.

Roeung makes it possible for a family member to press record on their phone, speak in Khmer, and have that story — transcribed, translated, and curated — available to every family member within days.

---

## Four user flows

| Flow | Who | What happens |
|------|-----|-------------|
| **Capture** | Any family member | Opens a private link, gives consent, records or uploads audio |
| **AI Pipeline** | Automated (background) | Transcribes → translates → flags cultural nuance → generates titles → tags people |
| **Keeper Review** | Designated reviewers | Reads AI output, corrects translation, resolves flags, approves for publication |
| **Book Reading** | All family members | Reads and listens to the bilingual family archive |

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI (Python) |
| Frontend | React 19 + Vite |
| Database | PostgreSQL via Supabase |
| File storage | Supabase Storage (audio files) |
| Auth | Supabase Auth (Keeper email/password) + family token URLs (submitters) |
| AI job queue | ARQ (async Redis-backed workers) |
| Transcription | ElevenLabs Scribe v2 |
| Translation | Google Cloud Translation API (first pass) |
| Cultural review / titles / people tagging | OpenAI GPT-4o-mini |
| Observability | LangSmith |
| Hosting | Railway (backend + Redis) + Supabase |

---

## Project structure

```
/
├── mvp/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── main.py              # FastAPI app entry point
│   │   │   ├── api/                 # Route handlers (stories, keepers, chapters, family members)
│   │   │   ├── models/              # SQLModel table definitions
│   │   │   ├── schemas/             # Pydantic request/response schemas
│   │   │   ├── services/            # Business logic (ai_pipeline, storage, locks)
│   │   │   └── workers/             # ARQ job definitions (pipeline.py)
│   │   ├── alembic/                 # Database migrations
│   │   ├── requirements.txt
│   │   └── .env.example
│   └── frontend/
│       ├── src/
│       │   ├── pages/
│       │   │   ├── capture/         # Flow 1: record + upload
│       │   │   ├── keeper/          # Flow 3: review queue + story review
│       │   │   └── book/            # Flow 4: book home, chapter, story, listen
│       │   └── components/
│       └── package.json
├── docs/
│   ├── prototypes/                  # High-fidelity HTML prototypes (open in browser)
│   ├── roeung-ux-flows-v0.2.md
│   ├── roeung-data-model-v0.3.md
│   └── roeung-decisions-v0.1.md
├── compliance/
│   ├── gdpr_documentation.md
│   └── eu_ai_act_compliance.md
├── strategic_plan.md
└── use_case_definition.md
```

---

## Auth model

**Family members (no account required)**
Access via a secret token in the URL: `/f/{access_token}`. Grants access to Capture and Book Reading only. No cookies, no sessions.

**Keepers (authenticated)**
Email/password via Supabase Auth. JWT passed as `Authorization: Bearer <token>` on all Keeper routes. Keeper routes verify the JWT and confirm `keepers.family_id` matches the resource.

---

## AI pipeline

Triggered automatically when a story is submitted. Steps run in order:

1. **Audio quality check** — scores recording; rejects below `AUDIO_QUALITY_THRESHOLD`
2. **Transcription** — ElevenLabs Scribe v2; produces word-level timestamps
3. **Translation** — Google Translate API (first pass)
4. **Cultural flag review** — GPT-4o-mini; flags segments with cultural nuance or idiom requiring human attention
5. **Title generation** — GPT-4o-mini; produces 3 candidate titles in Khmer and English
6. **People flagging** — GPT-4o-mini; detects family member names mentioned in the story
7. **Confidence scoring** — aggregates per-segment scores; pre-flags stories below threshold
8. **Status update** — sets `status = 'awaiting_review'`

AI output is **never published directly**. Every story passes through Keeper review before it reaches the family book.

---

## Story lifecycle

```
submitted → processing → awaiting_review → in_review → published
                     ↘ rejected (audio quality)        ↘ archived
                                                        ↘ unpublished
                                                        ↘ deleted (GDPR)
```

---

## Local setup

### Backend

```bash
cd mvp/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Fill in .env with your Supabase, OpenAI, Redis, and LangSmith credentials

# Run migrations
alembic upgrade head

# Seed Sea family data
python seed.py

# Start the API server
uvicorn app.main:app --reload

# Start the ARQ worker (separate terminal)
arq app.workers.pipeline.WorkerSettings
```

### Frontend

```bash
cd mvp/frontend
npm install

cp .env.example .env
# Set VITE_API_BASE_URL to point at the backend

npm run dev
```

The app runs at `http://localhost:5173`. The API runs at `http://localhost:8000`.

---

## Environment variables

See [mvp/backend/.env.example](mvp/backend/.env.example) for the full list. Required:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string (Supabase) |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Storage access |
| `SUPABASE_JWT_SECRET` | Verify Keeper JWTs |
| `REDIS_URL` | ARQ job queue |
| `OPENAI_API_KEY` | Cultural review, titles, people tagging |
| `LANGSMITH_API_KEY` | AI pipeline observability |

---

## Design prototypes

The [docs/prototypes/](docs/prototypes/) folder contains high-fidelity HTML prototypes — open them directly in a browser to see live interactions and the EN/KH toggle:

- **Roeung Capture.html** — record/upload flow
- **Roeung Keeper.html** — curator review workspace
- **Roeung Book.html** — family archive reading experience
- **Roeung Direction.html** — visual identity and design tokens

---

## Roadmap

| Phase | Period | Status |
|-------|--------|--------|
| Phase 1: POC (Sea family) | Jan–Jun 2026 | Complete |
| Phase 2: Pilot (10–20 diaspora families) | Jul–Sep 2026 | Upcoming |
| Phase 3: Public launch | Oct–Dec 2026 | Planned |
| Phase 4: Scale to 1,000+ families | Jan 2027+ | Planned |

See [strategic_plan.md](strategic_plan.md) for the full commercialisation plan, pricing model, and go-to-market strategy.

---

## Key documents

| Document | Purpose |
|----------|---------|
| [use_case_definition.md](use_case_definition.md) | Problem statement, AI system overview, success criteria |
| [strategic_plan.md](strategic_plan.md) | Commercialisation model, roadmap, pricing, go-to-market |
| [docs/roeung-ux-flows-v0.2.md](docs/roeung-ux-flows-v0.2.md) | All four user flows in detail |
| [docs/roeung-data-model-v0.3.md](docs/roeung-data-model-v0.3.md) | Complete entity reference (canonical) |
| [docs/roeung-decisions-v0.1.md](docs/roeung-decisions-v0.1.md) | Closed product decisions with rationale |
| [mvp/CLAUDE.md](mvp/CLAUDE.md) | Engineering brief for AI-assisted development |
| [compliance/gdpr_documentation.md](compliance/gdpr_documentation.md) | GDPR compliance |
| [compliance/eu_ai_act_compliance.md](compliance/eu_ai_act_compliance.md) | EU AI Act compliance |

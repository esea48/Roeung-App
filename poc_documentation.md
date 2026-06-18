# POC Documentation
## Roeung (រឿង) — AI Processing Pipeline

---

## 1. Tools Used and Why

| Tool | Version / Model | Role | Why this tool |
|---|---|---|---|
| **FastAPI** | latest | Backend API server | Async-native Python framework; plays well with ARQ's async job workers |
| **ARQ** | latest | Async job queue (Redis-backed) | Lightweight async worker that fits the pipeline's sequential step model without heavyweight infrastructure |
| **Redis** | any | Job queue broker | Required by ARQ; also used for soft lock state in Keeper review |
| **SQLModel + PostgreSQL** | latest | Relational data persistence | SQLModel merges SQLAlchemy + Pydantic — one model class serves as both ORM table and Pydantic schema |
| **Supabase Storage** | — | Audio file storage | Provides S3-compatible object storage with a signed URL API and integrates with Supabase Auth already used for Keepers |
| **ffmpeg** | system install | Audio format conversion | Browser audio recordings come in webm/mp4/ogg; librosa requires WAV; ffmpeg handles all browser formats reliably |
| **librosa** | latest | Audio quality scoring (SNR) | Provides signal processing utilities (RMS energy, duration) without requiring a cloud call for what is essentially a gate step |
| **ElevenLabs Scribe v2** | scribe_v2 | Speech-to-text transcription | Best-in-class Khmer transcription accuracy; returns word-level timestamps needed for segment alignment |
| **OpenAI GPT-4o-mini** | gpt-4o-mini | Translation, cultural flagging, title generation, people detection | Capable multilingual LLM with JSON mode; cost-effective for multiple inference passes per story |
| **LangSmith** | latest | Pipeline observability and tracing | Captures every LLM call (model, prompt, tokens, latency, outcome) per story; critical for debugging a multi-step pipeline |

---

## 2. What the POC Does — Step by Step

The pipeline is triggered automatically when a family member uploads audio and the story's status transitions to `submitted`. An ARQ worker picks up the `process_story` job and calls `run_pipeline(story_id)`.

### Step 0 — Submission
A family member submits a story through the Capture API (`POST /f/{access_token}/stories`), then uploads an audio file (`POST /f/{access_token}/stories/{id}/audio`). The API writes an `AudioFile` row with the Supabase Storage key and enqueues the ARQ job. Story status becomes `submitted`.

### Step 1 — Audio Quality Check
The audio file is downloaded from Supabase Storage and converted to WAV via ffmpeg. librosa computes a signal-to-noise ratio (SNR) score using RMS energy: signal power is the mean RMS², noise floor is the 10th-percentile RMS². The score is clipped to [0.0, 1.0] by normalising over 40 dB.

If the score falls below `AUDIO_QUALITY_THRESHOLD` (default 0.5), the story is marked `rejected` and the pipeline halts. Otherwise the score is written to `stories.audio_quality_score` and the pipeline continues.

### Step 2 — Transcription
The raw audio bytes are sent to the ElevenLabs Scribe v2 API with `timestamps_granularity=word`. The flat list of word objects returned by ElevenLabs is then segmented into sentence-level chunks by two heuristics: sentence-ending punctuation (`.`, `!`, `?`) and silence gaps longer than 1.5 seconds between words.

Each resulting segment is language-detected using a Khmer Unicode regex (`[ក-៿]`) — Khmer script presence → `Language.kh`, otherwise `Language.en`. Segments are written as `TranscriptSegment` rows with `original_text`, `start_ms`, `end_ms`, and word-level timestamps stored as JSONB. `stories.language_detected` is set to `kh`, `en`, or `mixed` based on the set of segment languages.

### Step 3 — Translation
For each `TranscriptSegment`, GPT-4o-mini produces a translation into the opposite language (Khmer → English, English → Khmer). The system prompt instructs the model to preserve cultural names, honorifics, and relational terms. Results are written as `TranslationSegment` rows with `original_text` set at creation and never modified (write-once invariant).

### Step 4 — Cultural Flag Review
All translation segments for the story are batched into a single GPT-4o-mini call (JSON mode). The model is given both the source text and the translation for each segment and returns, per segment: `cultural_flag` (boolean), `cultural_flag_note` (string or null), and `confidence_score` (0.0–1.0). These fields are written back to the `TranslationSegment` rows.

### Step 5 — Title Generation
The full transcript text (all segment `original_text` values joined) is sent to GPT-4o-mini. The model is asked to generate exactly 3 short, evocative title options, each with an English and a Khmer version. Results are written as `TitleSuggestion` rows (6 total: 3 suggestion indices × 2 languages).

### Step 6 — People Flagging
The full transcript is sent to GPT-4o-mini with a prompt to identify distinct named people. The model returns a list of names in the original script. Each name is written as an `AIPeopleMention` row; Keepers later link these to `FamilyMember` rows.

### Step 7 — Confidence Scoring
The mean `confidence_score` across all `TranslationSegment` rows for the story is computed and written to `stories.translation_confidence_score`. If the mean falls below `TRANSLATION_CONFIDENCE_THRESHOLD` (default 0.7), `stories.translation_flagged` is set to `true` so the story surfaces for priority Keeper review.

### Completion
Story status transitions to `awaiting_review`. `stories.processing_step` is cleared. Total LLM tokens consumed across all steps are written to `stories.pipeline_tokens_used`.

**Error handling:** if any step raises an exception, `stories.processing_error` is set to the error message and status remains `processing`, enabling a manual or automated retry. If a story is rejected at Step 1, no error is recorded — rejection is a clean stop, not a failure.

---

## 3. What AI Capability Is Demonstrated

| Capability | Where in pipeline | Model |
|---|---|---|
| **Speech-to-text** with word-level timestamps on a low-resource language (Khmer) | Step 2 — Transcription | ElevenLabs Scribe v2 |
| **Multilingual neural machine translation** (Khmer ↔ English), segment-level, with cultural preservation prompting | Step 3 — Translation | GPT-4o-mini |
| **Cultural nuance classification** — flagging translation segments where idiom or relational context may be lost | Step 4 — Cultural flag review | GPT-4o-mini |
| **Structured bilingual text generation** — producing 3 parallel KH/EN story titles from a transcript | Step 5 — Title generation | GPT-4o-mini |
| **Named entity recognition** in mixed-language text | Step 6 — People flagging | GPT-4o-mini |
| **Signal quality classification** using audio signal processing (no ML model required) | Step 1 — Audio quality check | librosa (SNR) |

The core demonstration is that a single audio file in Khmer can be fully processed — transcribed with timestamps, translated, flagged for cultural review, titled, and tagged with people — with no human involvement, producing outputs ready for efficient Keeper review in under 10 minutes.

---

## 4. Known Limitations of the POC vs. a Production System

**Translation quality**
The POC uses GPT-4o-mini for all translation. The production design calls for Google Cloud Translation API as a first-pass (lower latency, lower cost) with GPT-4 only for cultural review. This distinction matters at scale: a long story could incur significant token cost from using an LLM for every translation segment.

**Context window per segment**
Translation and cultural review are done segment by segment without cross-segment context. A sentence that only makes sense in the context of the previous sentence may be translated or flagged incorrectly. A document-level context window would improve accuracy.

**Cultural flag review — single batch call**
All translation segments are sent to GPT-4o-mini in one JSON call. For very long stories (many segments), this could exceed context limits or produce inconsistent results. A production system would chunk the batch.

**Language detection**
Language is detected per segment using a Khmer Unicode regex — fast and works well for clearly monolingual segments, but fails on mixed-script sentences or romanised Khmer. A proper language detection library (e.g. langdetect, fastText) would be more robust.

**Audio quality scoring**
The SNR heuristic using librosa RMS is a proxy metric, not a trained audio quality classifier. It may pass noisy recordings that happen to have a loud signal, or reject quiet but intelligible recordings. A production system would use a model trained on speech quality data.

**No retry orchestration**
When a step fails, the story is left in `status = 'processing'` with a `processing_error` field. There is no automatic retry scheduler in the POC — a retry must be triggered manually. A production system would implement exponential backoff with a retry count limit.

**No rate limiting or cost controls**
The pipeline calls external APIs (ElevenLabs, OpenAI) without per-family rate limiting or per-story cost caps. A production system would add safeguards to prevent runaway spend on malformed or unusually long submissions.

**Observability is optional**
LangSmith tracing is wired in but `LANGSMITH_API_KEY` is optional. In a production system, observability would be mandatory and alerting on pipeline failures would be configured.

**Tests use mocked AI services**
Unit tests replace `_transcribe`, `_check_audio_quality`, and `_chat_json` with fakes. The test suite validates pipeline logic and database state but does not verify the real behaviour of ElevenLabs or OpenAI calls. The smoke test script (`scripts/ai_pipeline_smoke.py`) covers real API integration but requires a staging deployment.

---

## 5. How to Reproduce / Run It Yourself

### Prerequisites

- Python 3.11+
- PostgreSQL (or a Supabase project)
- Redis (local or cloud)
- ffmpeg installed on your system (`brew install ffmpeg` on Mac)
- API keys for: ElevenLabs, OpenAI

### 1. Clone and install dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and fill in:
# DATABASE_URL, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_STORAGE_BUCKET
# OPENAI_API_KEY, ELEVENLABS_API_KEY (add this key — not in .env.example yet)
# REDIS_URL (default: redis://localhost:6379)
# Optional: LANGSMITH_API_KEY for pipeline tracing
```

### 3. Run database migrations

```bash
cd backend
alembic upgrade head
```

### 4. Seed the database (first time only)

```bash
python app/seed.py
```

### 5. Start the API server

```bash
uvicorn app.main:app --reload --port 8000
```

### 6. Start the ARQ pipeline worker

In a separate terminal:

```bash
cd backend
source venv/bin/activate
arq app.workers.pipeline.WorkerSettings
```

### 7. Submit a story and trigger the pipeline

```bash
# Step 1: Create a story (replace ACCESS_TOKEN with a valid families.access_token)
curl -X POST http://localhost:8000/f/ACCESS_TOKEN/stories \
  -H "Content-Type: application/json" \
  -d '{"capture_method": "uploaded", "narrator_name_raw": "Grandmother Sea", "recorder_name": "Ellen", "consent_wording_key": "v1_uploaded"}'

# Step 2: Upload audio (replace STORY_ID with the id from the response)
curl -X POST http://localhost:8000/f/ACCESS_TOKEN/stories/STORY_ID/audio \
  -F "file=@/path/to/your/audio.wav"

# Step 3: Poll for pipeline completion (requires Keeper JWT)
curl http://localhost:8000/keeper/stories/STORY_ID \
  -H "Authorization: Bearer KEEPER_JWT"
# Poll until "status" == "awaiting_review"
```

### 8. Run the smoke test (end-to-end against a running server)

```bash
cd backend
export SMOKE_FAMILY_ACCESS_TOKEN=your-token
export SMOKE_KEEPER_TOKEN=your-keeper-jwt
export SMOKE_AUDIO_PATH=/absolute/path/to/audio-fixture.wav
python scripts/ai_pipeline_smoke.py
```

The script creates a story, uploads the audio, polls until `awaiting_review`, and asserts that the response contains transcript segments and 3 bilingual title suggestions.

### 9. Run the unit tests

```bash
cd backend
pytest tests/ -v
```

Unit tests run fully offline — all AI service calls are replaced with in-process fakes. They validate pipeline step sequencing, database state, idempotent retries, rejection behaviour, and error recording.

---

*Document version: 1.0 — June 2026*
*Project: Roeung (រឿង) — Sea Family Oral History Archive*

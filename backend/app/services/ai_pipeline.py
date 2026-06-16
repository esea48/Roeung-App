"""Orchestrates the AI processing pipeline (CLAUDE.md "AI Pipeline (ARQ Workers)").

`run_pipeline` is the entrypoint the ARQ worker (`app.workers.pipeline`) calls
once a story reaches `status = 'submitted'`. Each step updates
`stories.processing_step` so the UI can show progress.

If a step raises, the error is recorded on `stories.processing_error` and
`status` is left as `'processing'` so a retry can pick up where it left off.
"""

import io
import json
import logging
import re
import uuid
from functools import lru_cache

import httpx
import librosa
import numpy as np
from openai import OpenAI
from sqlmodel import Session, delete, select

from app.core.config import get_settings
from app.db import engine
from app.models import (
    AIPeopleMention,
    AudioFile,
    Story,
    TitleSuggestion,
    TranscriptSegment,
    TranslationSegment,
)
from app.models.enums import Language, LanguageDetected, StoryStatus
from app.services.storage import download_audio_file

logger = logging.getLogger(__name__)

_KHMER_RE = re.compile(r"[ក-៿]")


class _StoryRejected(Exception):
    """Raised by a step to stop the pipeline without recording an error."""


async def run_pipeline(story_id: str) -> None:
    with Session(engine) as session:
        story = session.get(Story, uuid.UUID(story_id))
        if story is None:
            logger.error("process_story: story %s not found", story_id)
            return

        story.status = StoryStatus.processing
        story.processing_error = None
        session.add(story)
        session.commit()

        steps = [
            _check_audio_quality,
            _transcribe,
            _translate,
            _review_cultural_flags,
            _generate_titles,
            _flag_people,
            _score_translation,
        ]

        for step in steps:
            try:
                await step(session, story)
            except _StoryRejected:
                session.commit()
                return
            except Exception as exc:
                logger.exception(
                    "process_story: step %s failed for story %s", step.__name__, story_id
                )
                story.processing_error = str(exc)
                session.add(story)
                session.commit()
                return

        story.status = StoryStatus.awaiting_review
        story.processing_step = None
        session.add(story)
        session.commit()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


@lru_cache
def _openai_client() -> OpenAI:
    return OpenAI(api_key=get_settings().openai_api_key)


def _detect_language(text: str) -> Language:
    """Per-segment language detection via Khmer script presence.

    More reliable than trusting a single whole-file language from Whisper,
    since stories may switch between Khmer and English mid-recording.
    """
    return Language.kh if _KHMER_RE.search(text) else Language.en


def _get_audio_file(session: Session, story: Story) -> AudioFile:
    audio_file = session.exec(
        select(AudioFile).where(AudioFile.story_id == story.id)
    ).first()
    if audio_file is None or audio_file.storage_key is None:
        raise RuntimeError(f"No audio file available for story {story.id}")
    return audio_file


def _replace_story_rows(session: Session, model, story_id: uuid.UUID) -> None:
    """Delete any prior rows for a story before recreating them.

    The pipeline is retryable, so insertion steps need to be idempotent.
    Clearing a step's rows before re-adding them keeps retries from
    duplicating transcript, translation, title, or people rows.
    """
    session.exec(delete(model).where(model.story_id == story_id))


_GOOGLE_LANG = {"kh": "km"}  # internal code → BCP 47 code expected by Google
_WHISPER_LANG = {"kh": "km", "en": "en"}  # internal code → ISO 639-1 expected by Whisper


def _translate_text(text: str, source: Language, target: Language) -> str:
    settings = get_settings()
    src = _GOOGLE_LANG.get(source.value, source.value)
    tgt = _GOOGLE_LANG.get(target.value, target.value)
    response = httpx.post(
        "https://translation.googleapis.com/language/translate/v2",
        params={"key": settings.google_translate_api_key},
        json={"q": text, "source": src, "target": tgt, "format": "text"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["data"]["translations"][0]["translatedText"]


def _chat_json(*, system: str, user: str, schema_hint: str) -> dict:
    response = _openai_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": f"{system}\n\nRespond with JSON matching this shape: {schema_hint}",
            },
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------


def _to_wav_bytes(audio_bytes: bytes) -> bytes:
    """Convert any browser audio format (webm/mp4/ogg) to WAV via ffmpeg.

    Uses a temp file for input because webm requires seekable access that
    pipe:0 cannot provide.
    """
    import subprocess
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        result = subprocess.run(
            ["ffmpeg", "-i", tmp_path, "-f", "wav", "-ac", "1", "-y", "pipe:1"],
            capture_output=True,
        )
    finally:
        os.unlink(tmp_path)

    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg conversion failed: {result.stderr.decode()}")
    return result.stdout


async def _check_audio_quality(session: Session, story: Story) -> None:
    story.processing_step = "audio_quality_check"
    session.add(story)
    session.commit()

    audio_file = _get_audio_file(session, story)
    audio_bytes = download_audio_file(audio_file.storage_key)

    wav_bytes = _to_wav_bytes(audio_bytes)
    y, sr = librosa.load(io.BytesIO(wav_bytes), sr=None, mono=True)
    rms = librosa.feature.rms(y=y)[0]
    signal_power = float(np.mean(rms ** 2))
    noise_power = float(np.percentile(rms, 10) ** 2)
    snr_db = 10 * np.log10(signal_power / max(noise_power, 1e-10))
    score = float(np.clip(snr_db / 40.0, 0.0, 1.0))

    story.audio_quality_score = score
    if score < get_settings().audio_quality_threshold:
        story.status = StoryStatus.rejected
        session.add(story)
        session.commit()
        raise _StoryRejected()

    session.add(story)
    session.commit()


async def _transcribe(session: Session, story: Story) -> None:
    story.processing_step = "transcription"
    session.add(story)
    session.commit()

    audio_file = _get_audio_file(session, story)
    audio_bytes = download_audio_file(audio_file.storage_key)
    _replace_story_rows(session, TranscriptSegment, story.id)

    _MIME_TO_EXT = {
        "audio/webm": "webm", "audio/mp4": "mp4", "audio/mpeg": "mp3",
        "audio/ogg": "ogg", "audio/wav": "wav", "audio/flac": "flac",
        "audio/x-m4a": "m4a",
    }
    _WHISPER_EXTS = {"webm", "mp4", "mp3", "m4a", "mpeg", "mpga", "oga", "ogg", "wav", "flac"}
    raw_ext = audio_file.storage_key.rsplit(".", 1)[-1].lower() if "." in audio_file.storage_key else ""
    if raw_ext in _WHISPER_EXTS:
        extension = raw_ext
    else:
        base_mime = (audio_file.mime_type or "").split(";")[0].strip()
        extension = _MIME_TO_EXT.get(base_mime, "webm")

    whisper_lang = _WHISPER_LANG.get(story.audio_language.value) if story.audio_language else None
    transcription = _openai_client().audio.transcriptions.create(
        model="whisper-1",
        file=(f"audio.{extension}", audio_bytes, audio_file.mime_type or "application/octet-stream"),
        response_format="verbose_json",
        timestamp_granularities=["word", "segment"],
        **({"language": whisper_lang} if whisper_lang else {}),
    )

    words = [
        {"word": w.word, "start_ms": int(w.start * 1000), "end_ms": int(w.end * 1000)}
        for w in (transcription.words or [])
    ]

    detected_languages: set[Language] = set()
    for index, segment in enumerate(transcription.segments or []):
        start_ms = int(segment.start * 1000)
        end_ms = int(segment.end * 1000)
        text = segment.text.strip()
        language = _detect_language(text)
        detected_languages.add(language)
        segment_words = [w for w in words if start_ms <= w["start_ms"] < end_ms]

        session.add(
            TranscriptSegment(
                story_id=story.id,
                language=language,
                segment_index=index,
                start_ms=start_ms,
                end_ms=end_ms,
                original_text=text,
                word_timestamps=segment_words or None,
            )
        )

    if detected_languages == {Language.en}:
        story.language_detected = LanguageDetected.en
    elif detected_languages == {Language.kh}:
        story.language_detected = LanguageDetected.kh
    elif detected_languages:
        story.language_detected = LanguageDetected.mixed

    session.add(story)
    session.commit()


async def _translate(session: Session, story: Story) -> None:
    story.processing_step = "translation"
    session.add(story)
    session.commit()

    transcript_segments = session.exec(
        select(TranscriptSegment)
        .where(TranscriptSegment.story_id == story.id)
        .order_by(TranscriptSegment.segment_index)
    ).all()
    _replace_story_rows(session, TranslationSegment, story.id)

    for segment in transcript_segments:
        target_language = Language.en if segment.language == Language.kh else Language.kh
        translated_text = _translate_text(segment.original_text, segment.language, target_language)
        session.add(
            TranslationSegment(
                story_id=story.id,
                transcript_segment_id=segment.id,
                source_language=segment.language,
                target_language=target_language,
                segment_index=segment.segment_index,
                original_text=translated_text,
            )
        )

    session.commit()


async def _review_cultural_flags(session: Session, story: Story) -> None:
    story.processing_step = "cultural_flag_review"
    session.add(story)
    session.commit()

    translation_segments = session.exec(
        select(TranslationSegment)
        .where(TranslationSegment.story_id == story.id)
        .order_by(TranslationSegment.segment_index)
    ).all()
    if not translation_segments:
        return

    transcript_by_id = {
        t.id: t
        for t in session.exec(
            select(TranscriptSegment).where(TranscriptSegment.story_id == story.id)
        ).all()
    }

    items = [
        {
            "index": i,
            "source_text": transcript_by_id[segment.transcript_segment_id].original_text,
            "translated_text": segment.original_text,
        }
        for i, segment in enumerate(translation_segments)
    ]

    result = _chat_json(
        system=(
            "You review machine translations of Khmer family oral history "
            "stories for cultural nuance lost in translation. For each item, "
            "decide whether the translation loses important cultural, "
            "idiomatic, or relational meaning from the source text."
        ),
        user=json.dumps({"items": items}, ensure_ascii=False),
        schema_hint=(
            '{"results": [{"index": int, "cultural_flag": bool, '
            '"cultural_flag_note": str | null, "confidence_score": float}]} '
            "— confidence_score is 0.0-1.0, how confident you are the "
            "translation is accurate; cultural_flag_note explains the nuance "
            "when cultural_flag is true, otherwise null"
        ),
    )

    results_by_index = {r["index"]: r for r in result.get("results", [])}
    for i, segment in enumerate(translation_segments):
        review = results_by_index.get(i, {})
        segment.cultural_flag = bool(review.get("cultural_flag", False))
        segment.cultural_flag_note = review.get("cultural_flag_note")
        segment.confidence_score = float(review.get("confidence_score", 0.0))
        session.add(segment)

    session.commit()


async def _generate_titles(session: Session, story: Story) -> None:
    story.processing_step = "title_generation"
    session.add(story)
    session.commit()

    transcript_segments = session.exec(
        select(TranscriptSegment)
        .where(TranscriptSegment.story_id == story.id)
        .order_by(TranscriptSegment.segment_index)
    ).all()
    if not transcript_segments:
        return

    transcript_text = "\n".join(segment.original_text for segment in transcript_segments)
    _replace_story_rows(session, TitleSuggestion, story.id)

    result = _chat_json(
        system=(
            "You write short, evocative titles for a family oral history "
            "story, given its transcript. Generate exactly 3 distinct title "
            "options. Each option must give the same title concept in both "
            "English and Khmer."
        ),
        user=transcript_text,
        schema_hint='{"titles": [{"en": str, "kh": str}, ...]} (exactly 3 entries)',
    )

    for index, title in enumerate(result.get("titles", [])[:3], start=1):
        session.add(
            TitleSuggestion(
                story_id=story.id,
                language=Language.en,
                suggestion_index=index,
                text=title["en"],
            )
        )
        session.add(
            TitleSuggestion(
                story_id=story.id,
                language=Language.kh,
                suggestion_index=index,
                text=title["kh"],
            )
        )

    session.commit()


async def _flag_people(session: Session, story: Story) -> None:
    story.processing_step = "people_flagging"
    session.add(story)
    session.commit()

    transcript_segments = session.exec(
        select(TranscriptSegment)
        .where(TranscriptSegment.story_id == story.id)
        .order_by(TranscriptSegment.segment_index)
    ).all()
    if not transcript_segments:
        return

    transcript_text = "\n".join(segment.original_text for segment in transcript_segments)
    _replace_story_rows(session, AIPeopleMention, story.id)

    result = _chat_json(
        system=(
            "You identify people mentioned by name in a family oral history "
            "story transcript. List each distinct person, written exactly as "
            "they appear in the transcript (original language/script). Do not "
            "include the narrator unless they refer to themselves by name."
        ),
        user=transcript_text,
        schema_hint='{"names": [str, ...]}',
    )

    for name in result.get("names", []):
        name = name.strip()
        if name:
            session.add(AIPeopleMention(story_id=story.id, name_raw=name))

    session.commit()


async def _score_translation(session: Session, story: Story) -> None:
    story.processing_step = "scoring"
    session.add(story)
    session.commit()

    scores = session.exec(
        select(TranslationSegment.confidence_score).where(
            TranslationSegment.story_id == story.id,
            TranslationSegment.confidence_score.is_not(None),
        )
    ).all()

    if scores:
        mean_score = sum(scores) / len(scores)
        story.translation_confidence_score = mean_score
        story.translation_flagged = mean_score < get_settings().translation_confidence_threshold

    session.add(story)
    session.commit()

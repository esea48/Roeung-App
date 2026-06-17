"""Orchestrates the AI processing pipeline (CLAUDE.md "AI Pipeline (ARQ Workers)").

`run_pipeline` is the entrypoint the ARQ worker (`app.workers.pipeline`) calls
once a story reaches `status = 'submitted'`. Each step updates
`stories.processing_step` so the UI can show progress.

If a step raises, the error is recorded on `stories.processing_error` and
`status` is left as `'processing'` so a retry can pick up where it left off.
"""

import io
import json
import inspect
import logging
import re
import uuid
from functools import lru_cache
from time import perf_counter
from typing import Any

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
from app.services.langsmith import (
    finish_run,
    trace_pipeline_run,
    trace_pipeline_step,
    traced_llm_json,
)
from app.services.storage import download_audio_file

logger = logging.getLogger(__name__)

_KHMER_RE = re.compile(r"[ក-៿]")


def _enum_value(value: Any | None) -> str | None:
    if value is None:
        return None
    return getattr(value, "value", value)


class _StoryRejected(Exception):
    """Raised by a step to stop the pipeline without recording an error."""


async def _run_step(step, session: Session, story: Story, trace_parent: Any | None) -> None:
    """Call a step with optional tracing support.

    Older tests and ad-hoc monkeypatches may still provide step doubles that do
    not accept `trace_parent`, so we inspect the callable before passing it.
    """
    params = inspect.signature(step).parameters
    if "trace_parent" in params:
        await step(session, story, trace_parent=trace_parent)
    else:
        await step(session, story)


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
            ("audio_quality_check", _check_audio_quality),
            ("transcription", _transcribe),
            ("translation", _translate),
            ("cultural_flag_review", _review_cultural_flags),
            ("title_generation", _generate_titles),
            ("people_flagging", _flag_people),
            ("scoring", _score_translation),
        ]

        with trace_pipeline_run(story) as root_run:
            for step_name, step in steps:
                step_model = {
                    "audio_quality_check": "librosa-snr",
                    "transcription": "elevenlabs/scribe_v2",
                    "translation": "google-translate-v2",
                    "cultural_flag_review": "gpt-4o-mini",
                    "title_generation": "gpt-4o-mini",
                    "people_flagging": "gpt-4o-mini",
                    "scoring": "mean-confidence-score",
                }.get(step_name)
                source_language = _enum_value(getattr(story, "language_detected", None) or story.audio_language)
                step_started = perf_counter()
                with trace_pipeline_step(
                    root_run,
                    story,
                    step=step_name,
                    run_type="tool",
                    inputs={"story_id": str(story.id), "family_id": str(story.family_id)},
                    model=step_model,
                    source_language=source_language,
                    processing_step=step_name,
                ) as step_run:
                    try:
                        await _run_step(step, session, story, step_run)
                    except _StoryRejected:
                        finish_run(
                            step_run,
                            story,
                            step=step_name,
                            outcome="rejected",
                            model=step_model,
                            processing_step=step_name,
                            extra={"latency_ms": int((perf_counter() - step_started) * 1000)},
                        )
                        story.processing_step = None
                        session.add(story)
                        session.commit()
                        finish_run(
                            root_run,
                            story,
                            step="roeung.ai_pipeline",
                            outcome="rejected",
                            model="pipeline",
                            outputs={"status": StoryStatus.rejected.value},
                            processing_step=None,
                        )
                        return
                    except Exception as exc:
                        logger.exception(
                            "process_story: step %s failed for story %s", step.__name__, story_id
                        )
                        story.processing_error = str(exc)
                        session.add(story)
                        session.commit()
                        finish_run(
                            step_run,
                            story,
                            step=step_name,
                            outcome="error",
                            model=step_model,
                            processing_step=step_name,
                            error=str(exc),
                            extra={
                                "latency_ms": int((perf_counter() - step_started) * 1000),
                                "error_type": type(exc).__name__,
                            },
                        )
                        finish_run(
                            root_run,
                            story,
                            step="roeung.ai_pipeline",
                            outcome="error",
                            model="pipeline",
                            error=str(exc),
                            outputs={"status": StoryStatus.processing.value},
                        )
                        return
                    else:
                        finish_run(
                            step_run,
                            story,
                            step=step_name,
                            outcome="success",
                            model=step_model,
                            processing_step=step_name,
                            extra={"latency_ms": int((perf_counter() - step_started) * 1000)},
                        )

            story.status = StoryStatus.awaiting_review
            story.processing_step = None
            session.add(story)
            session.commit()
            finish_run(
                root_run,
                story,
                step="roeung.ai_pipeline",
                outcome="success",
                model="pipeline",
                outputs={"status": StoryStatus.awaiting_review.value},
                processing_step=None,
            )


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


@lru_cache
def _openai_client() -> OpenAI:
    return OpenAI(api_key=get_settings().openai_api_key)


def _detect_language(text: str) -> Language:
    """Per-segment language detection via Khmer script presence.

    More reliable than trusting a single whole-file language from ElevenLabs,
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


_GOOGLE_LANG = {"kh": "km"}   # internal code → BCP 47 code expected by Google
_ELEVENLABS_LANG = {"kh": "km", "en": "en"}  # internal code → ISO 639-1 expected by ElevenLabs


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


def _chat_json(
    *,
    story: Story,
    parent_run: Any | None,
    step: str,
    system: str,
    user: str,
    schema_hint: str,
    source_language: str | None = None,
    target_language: str | None = None,
    processing_step: str | None = None,
) -> dict:
    def _call() -> dict:
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

    return traced_llm_json(
        parent_run,
        story,
        step=step,
        model="gpt-4o-mini",
        system=system,
        user=user,
        schema_hint=schema_hint,
        source_language=source_language,
        target_language=target_language,
        processing_step=processing_step,
        call_fn=_call,
    )


def _call_chat_json(
    *,
    story: Story,
    parent_run: Any | None,
    step: str,
    system: str,
    user: str,
    schema_hint: str,
    source_language: str | None = None,
    target_language: str | None = None,
    processing_step: str | None = None,
) -> dict:
    """Call `_chat_json` with tracing when the active implementation supports it.

    The test suite monkeypatches `_chat_json` with a simpler fake that only
    accepts the original three arguments. This adapter preserves that contract
    while letting the production implementation opt into tracing metadata.
    """
    params = inspect.signature(_chat_json).parameters
    if "story" in params:
        return _chat_json(
            story=story,
            parent_run=parent_run,
            step=step,
            system=system,
            user=user,
            schema_hint=schema_hint,
            source_language=source_language,
            target_language=target_language,
            processing_step=processing_step,
        )
    return _chat_json(system=system, user=user, schema_hint=schema_hint)


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


async def _check_audio_quality(
    session: Session, story: Story, *, trace_parent: Any | None = None
) -> None:
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


def _segment_elevenlabs_words(
    words: list[dict],
    pause_threshold: float = 1.5,
) -> list[tuple[int, int, str, list[dict]]]:
    """Group a flat ElevenLabs word list into sentence-level segments.

    Returns a list of (start_ms, end_ms, text, word_timestamps) tuples.
    Splits on sentence-ending punctuation or silence gaps longer than
    pause_threshold seconds.
    """
    _SENTENCE_END = frozenset(".!?")
    segments: list[tuple[int, int, str, list[dict]]] = []
    current_tokens: list[str] = []
    current_wts: list[dict] = []
    seg_start_ms: int | None = None
    seg_end_ms: int | None = None
    last_word_end: float | None = None

    def _field(item: Any, key: str, default: Any = None) -> Any:
        if isinstance(item, dict):
            return item.get(key, default)
        return getattr(item, key, default)

    for i, w in enumerate(words):
        wtype = _field(w, "type")
        wtext = _field(w, "text", _field(w, "word", ""))
        wstart = _field(w, "start")
        wend = _field(w, "end")

        if wtype is None and wtext:
            wtype = "word"

        if wtype == "audio_event":
            continue

        if wtype == "word":
            start_ms = int(wstart * 1000) if wstart is not None else None
            end_ms = int(wend * 1000) if wend is not None else None

            # Split on long pause before this word
            if last_word_end is not None and wstart is not None:
                if wstart - last_word_end > pause_threshold and current_tokens:
                    text = "".join(current_tokens).strip()
                    if text:
                        segments.append((seg_start_ms or 0, seg_end_ms or 0, text, current_wts))
                    current_tokens = []
                    current_wts = []
                    seg_start_ms = None
                    seg_end_ms = None

            if seg_start_ms is None and start_ms is not None:
                seg_start_ms = start_ms
            if end_ms is not None:
                seg_end_ms = end_ms
            if wend is not None:
                last_word_end = wend

            current_wts.append({
                "word": wtext,
                "start_ms": int(wstart * 1000) if wstart is not None else 0,
                "end_ms": int(wend * 1000) if wend is not None else 0,
            })

        current_tokens.append(wtext)

        # Split on sentence-ending punctuation
        if wtype == "word" and wtext.rstrip()[-1:] in _SENTENCE_END:
            text = "".join(current_tokens).strip()
            if text:
                segments.append((seg_start_ms or 0, seg_end_ms or 0, text, current_wts))
            current_tokens = []
            current_wts = []
            seg_start_ms = None
            seg_end_ms = None
            last_word_end = None

    if current_tokens:
        text = "".join(current_tokens).strip()
        if text:
            segments.append((seg_start_ms or 0, seg_end_ms or 0, text, current_wts))

    return segments


async def _transcribe(session: Session, story: Story, *, trace_parent: Any | None = None) -> None:
    story.processing_step = "transcription"
    session.add(story)
    session.commit()

    audio_file = _get_audio_file(session, story)
    audio_bytes = download_audio_file(audio_file.storage_key)
    _replace_story_rows(session, TranscriptSegment, story.id)

    filename = audio_file.storage_key.rsplit("/", 1)[-1] or "audio"
    mime = audio_file.mime_type or "application/octet-stream"
    lang_code = (
        _ELEVENLABS_LANG.get(story.audio_language.value) if story.audio_language else None
    )

    form: dict = {
        "model_id": (None, "scribe_v2"),
        "file": (filename, audio_bytes, mime),
        "timestamps_granularity": (None, "word"),
    }
    if lang_code:
        form["language_code"] = (None, lang_code)

    settings = get_settings()
    response = httpx.post(
        "https://api.elevenlabs.io/v1/speech-to-text",
        headers={"xi-api-key": settings.elevenlabs_api_key},
        files=form,
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()

    raw_words = data.get("words", [])
    segments = _segment_elevenlabs_words(raw_words)

    detected_languages: set[Language] = set()
    for index, (start_ms, end_ms, text, wts) in enumerate(segments):
        language = _detect_language(text)
        detected_languages.add(language)
        session.add(
            TranscriptSegment(
                story_id=story.id,
                language=language,
                segment_index=index,
                start_ms=start_ms,
                end_ms=end_ms,
                original_text=text,
                word_timestamps=wts or None,
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


async def _translate(session: Session, story: Story, *, trace_parent: Any | None = None) -> None:
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


async def _review_cultural_flags(
    session: Session, story: Story, *, trace_parent: Any | None = None
) -> None:
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

    result = _call_chat_json(
        story=story,
        parent_run=trace_parent,
        step="cultural_flag_review",
        processing_step="cultural_flag_review",
        source_language=_enum_value(getattr(story, "language_detected", None) or story.audio_language),
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


async def _generate_titles(
    session: Session, story: Story, *, trace_parent: Any | None = None
) -> None:
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

    result = _call_chat_json(
        story=story,
        parent_run=trace_parent,
        step="title_generation",
        processing_step="title_generation",
        source_language=_enum_value(getattr(story, "language_detected", None) or story.audio_language),
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


async def _flag_people(session: Session, story: Story, *, trace_parent: Any | None = None) -> None:
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

    result = _call_chat_json(
        story=story,
        parent_run=trace_parent,
        step="people_flagging",
        processing_step="people_flagging",
        source_language=_enum_value(getattr(story, "language_detected", None) or story.audio_language),
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


async def _score_translation(
    session: Session, story: Story, *, trace_parent: Any | None = None
) -> None:
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

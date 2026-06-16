import asyncio
import io
from types import SimpleNamespace

from fastapi import UploadFile
from sqlmodel import select

from app.api.keepers import get_story_detail
from app.api.stories import create_story, upload_story_audio
from app.models import AudioFile, TitleSuggestion, TranscriptSegment, TranslationSegment
from app.models.enums import AudioFileType, CaptureMethod, StoryStatus
from app.schemas.stories import StoryCreateRequest
from app.services import ai_pipeline
from app.services.ai_pipeline import run_pipeline


def _request_stub(host: str = "127.0.0.1", user_agent: str = "pytest") -> SimpleNamespace:
    return SimpleNamespace(headers={"user-agent": user_agent}, client=SimpleNamespace(host=host))


def _make_story(session, family, *, capture_method=CaptureMethod.uploaded, narrator_name="Grandmother Sea"):
    from app.models import FamilyMember

    family_member = FamilyMember(family_id=family.id, name_en=narrator_name, name_kh="ជីដូន")
    session.add(family_member)
    session.commit()
    session.refresh(family_member)

    story = create_story(
        StoryCreateRequest(
            capture_method=capture_method,
            narrator_id=family_member.id,
            narrator_name_raw=narrator_name,
            recorder_name="Recorder",
            consent_wording_key="v1_uploaded" if capture_method == CaptureMethod.uploaded else "v1_recorded",
        ),
        request=_request_stub(),
        family=family,
        session=session,
    )
    return story, family_member


def _make_audio_upload(name: str = "story.wav", content: bytes = b"audio-bytes") -> UploadFile:
    return UploadFile(file=io.BytesIO(content), filename=name)


def _make_fake_transcription():
    segment_0 = SimpleNamespace(start=0.0, end=1.2, text="សួស្តី")
    segment_1 = SimpleNamespace(start=1.2, end=2.4, text="Hello again")
    word_0 = SimpleNamespace(word="សួស្តី", start=0.0, end=1.2)
    word_1 = SimpleNamespace(word="Hello", start=1.2, end=1.8)
    word_2 = SimpleNamespace(word="again", start=1.8, end=2.4)
    return SimpleNamespace(segments=[segment_0, segment_1], words=[word_0, word_1, word_2])


def _patch_happy_path(monkeypatch):
    class FakeTranscriptions:
        def create(self, **kwargs):
            return _make_fake_transcription()

    class FakeAudio:
        transcriptions = FakeTranscriptions()

    class FakeClient:
        audio = FakeAudio()

    monkeypatch.setattr(ai_pipeline, "_openai_client", lambda: FakeClient())
    monkeypatch.setattr(ai_pipeline, "download_audio_file", lambda storage_key: b"fake-audio")
    monkeypatch.setattr(ai_pipeline, "_check_audio_quality", _fake_quality_step)
    monkeypatch.setattr(ai_pipeline, "_translate_text", lambda text, source, target: f"{text} ({source.value}->{target.value})")


async def _fake_quality_step(session, story):
    story.processing_step = "audio_quality_check"
    story.audio_quality_score = 0.9
    session.add(story)
    session.commit()


def _fake_chat_json_factory(*, fail_people_once: bool = False):
    state = {"people_calls": 0}

    def _fake_chat_json(*, system: str, user: str, schema_hint: str) -> dict:
        if "translation API" in system or "cultural nuance" in system:
            return {
                "results": [
                    {"index": 0, "cultural_flag": False, "cultural_flag_note": None, "confidence_score": 0.95},
                    {"index": 1, "cultural_flag": True, "cultural_flag_note": "Preserved nuance", "confidence_score": 0.9},
                ]
            }

        if "Generate exactly 3 distinct title options" in system:
            return {
                "titles": [
                    {"en": "Morning by the River", "kh": "ព្រឹកនៅជុំវិញទន្លេ"},
                    {"en": "Family Stories Return", "kh": "រឿងគ្រួសារត្រឡប់មកវិញ"},
                    {"en": "A Voice to Remember", "kh": "សំឡេងដែលគួរចងចាំ"},
                ]
            }

        if "identify people mentioned" in system:
            state["people_calls"] += 1
            if fail_people_once and state["people_calls"] == 1:
                raise RuntimeError("boom")
            return {"names": ["Sokha", "Maly"]}

        raise AssertionError(f"Unexpected system prompt: {system}")

    return _fake_chat_json


def test_upload_story_audio_persists_audio_and_enqueues_pipeline(session, family, monkeypatch):
    story, _ = _make_story(session, family)
    seen = []

    async def fake_enqueue(story_id):
        seen.append(story_id)

    monkeypatch.setattr("app.api.stories.upload_audio_file", lambda *args, **kwargs: "family/story/original.wav")
    monkeypatch.setattr("app.api.stories.enqueue_story_pipeline", fake_enqueue)

    result = asyncio.run(upload_story_audio(story.id, file=_make_audio_upload(), family=family, session=session))

    assert result.story_id == story.id
    assert result.storage_key == "family/story/original.wav"
    assert seen == [story.id]

    rows = session.exec(select(AudioFile).where(AudioFile.story_id == story.id)).all()
    assert len(rows) == 1
    assert rows[0].storage_key == "family/story/original.wav"


def test_run_pipeline_happy_path_creates_bilingual_title_options(session, family, keeper, monkeypatch):
    story, _ = _make_story(session, family)
    audio = AudioFile(
        story_id=story.id,
        family_id=family.id,
        storage_key="family/story/original.wav",
        file_type=AudioFileType.original,
        mime_type="audio/wav",
        file_size_bytes=1024,
    )
    session.add(audio)
    session.commit()

    _patch_happy_path(monkeypatch)
    monkeypatch.setattr(ai_pipeline, "_chat_json", _fake_chat_json_factory())

    asyncio.run(run_pipeline(str(story.id)))

    session.refresh(story)
    assert story.status == StoryStatus.awaiting_review
    assert story.processing_error is None
    assert story.audio_quality_score == 0.9
    assert story.translation_confidence_score == 0.925
    assert story.language_detected is not None

    transcript_rows = session.exec(
        select(TranscriptSegment).where(TranscriptSegment.story_id == story.id).order_by(TranscriptSegment.segment_index)
    ).all()
    translation_rows = session.exec(
        select(TranslationSegment).where(TranslationSegment.story_id == story.id).order_by(TranslationSegment.segment_index)
    ).all()
    title_rows = session.exec(
        select(TitleSuggestion).where(TitleSuggestion.story_id == story.id).order_by(TitleSuggestion.suggestion_index)
    ).all()

    assert len(transcript_rows) == 2
    assert [row.segment_index for row in transcript_rows] == [0, 1]
    assert len(translation_rows) == 2
    assert len(title_rows) == 6

    detail = get_story_detail(story.id, keeper=keeper, session=session)
    assert detail.status == StoryStatus.awaiting_review
    assert len(detail.title_suggestions) == 3
    assert [s.suggestion_index for s in detail.title_suggestions] == [1, 2, 3]
    assert all(s.title_en and s.title_kh for s in detail.title_suggestions)


def test_run_pipeline_records_error_when_transcription_fails(session, family, monkeypatch):
    story, _ = _make_story(session, family)
    audio = AudioFile(
        story_id=story.id,
        family_id=family.id,
        storage_key="family/story/original.wav",
        file_type=AudioFileType.original,
        mime_type="audio/wav",
        file_size_bytes=1024,
    )
    session.add(audio)
    session.commit()

    async def failing_transcribe(session_obj, story_obj):
        raise RuntimeError("transcription failed")

    monkeypatch.setattr(ai_pipeline, "_check_audio_quality", _fake_quality_step)
    monkeypatch.setattr(ai_pipeline, "_transcribe", failing_transcribe)

    asyncio.run(run_pipeline(str(story.id)))

    session.refresh(story)
    assert story.status == StoryStatus.processing
    assert story.processing_error == "transcription failed"


def test_run_pipeline_rejects_low_quality_audio(session, family, monkeypatch):
    story, _ = _make_story(session, family)
    audio = AudioFile(
        story_id=story.id,
        family_id=family.id,
        storage_key="family/story/original.wav",
        file_type=AudioFileType.original,
        mime_type="audio/wav",
        file_size_bytes=1024,
    )
    session.add(audio)
    session.commit()

    async def reject_quality(session_obj, story_obj):
        story_obj.processing_step = "audio_quality_check"
        story_obj.audio_quality_score = 0.1
        story_obj.status = StoryStatus.rejected
        session_obj.add(story_obj)
        session_obj.commit()
        raise ai_pipeline._StoryRejected()

    monkeypatch.setattr(ai_pipeline, "_check_audio_quality", reject_quality)

    asyncio.run(run_pipeline(str(story.id)))

    session.refresh(story)
    assert story.status == StoryStatus.rejected
    assert story.processing_error is None
    assert story.audio_quality_score == 0.1


def test_pipeline_retry_does_not_duplicate_title_rows(session, family, keeper, monkeypatch):
    story, _ = _make_story(session, family)
    audio = AudioFile(
        story_id=story.id,
        family_id=family.id,
        storage_key="family/story/original.wav",
        file_type=AudioFileType.original,
        mime_type="audio/wav",
        file_size_bytes=1024,
    )
    session.add(audio)
    session.commit()

    _patch_happy_path(monkeypatch)
    monkeypatch.setattr(ai_pipeline, "_chat_json", _fake_chat_json_factory(fail_people_once=True))

    asyncio.run(run_pipeline(str(story.id)))

    first_title_count = session.exec(
        select(TitleSuggestion).where(TitleSuggestion.story_id == story.id)
    ).all()
    assert len(first_title_count) == 6

    asyncio.run(run_pipeline(str(story.id)))

    session.refresh(story)
    assert story.status == StoryStatus.awaiting_review

    transcript_rows = session.exec(select(TranscriptSegment).where(TranscriptSegment.story_id == story.id)).all()
    translation_rows = session.exec(select(TranslationSegment).where(TranslationSegment.story_id == story.id)).all()
    title_rows = session.exec(select(TitleSuggestion).where(TitleSuggestion.story_id == story.id)).all()

    assert len(transcript_rows) == 2
    assert len(translation_rows) == 2
    assert len(title_rows) == 6

    detail = get_story_detail(story.id, keeper=keeper, session=session)
    assert len(detail.title_suggestions) == 3

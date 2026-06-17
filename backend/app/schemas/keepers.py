"""Request/response schemas for Keeper Review (CLAUDE.md Flow 3)."""

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from app.models.enums import (
    AudioFileType,
    CaptureMethod,
    Language,
    LanguageDetected,
    MentionResolutionStatus,
    StoryStatus,
    TaggedBy,
)


class LockInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    keeper_id: uuid.UUID
    keeper_name: str
    locked_at: datetime
    expires_at: datetime


class LockResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    story_id: uuid.UUID
    keeper_id: uuid.UUID
    locked_at: datetime
    expires_at: datetime
    released_at: Optional[datetime]


class QueueStoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: StoryStatus
    narrator_name_raw: str
    title_en: Optional[str]
    title_kh: Optional[str]
    language_detected: Optional[LanguageDetected]
    translation_flagged: bool
    translation_confidence_score: Optional[float]
    audio_quality_score: Optional[float]
    submitted_at: Optional[datetime]
    created_at: datetime
    lock: Optional[LockInfo] = None


class KeeperStoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: StoryStatus
    title_en: Optional[str]
    title_kh: Optional[str]
    translation_flagged: bool
    translation_confidence_score: Optional[float]
    chapter_id: Optional[uuid.UUID]
    chapter_sort_order: Optional[int]
    published_at: Optional[datetime]
    published_by: Optional[uuid.UUID]
    archived_at: Optional[datetime]
    archived_by: Optional[uuid.UUID]
    updated_at: datetime


class StoryUpdateRequest(BaseModel):
    title_en: Optional[str] = None
    title_kh: Optional[str] = None
    translation_flagged: Optional[bool] = None
    chapter_id: Optional[uuid.UUID] = None
    chapter_sort_order: Optional[int] = None
    transcript_edited: Optional[str] = None
    translation_edited: Optional[str] = None


class SegmentUpdateRequest(BaseModel):
    edited_text: str


class SegmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    story_id: uuid.UUID
    segment_index: int
    original_text: str
    edited_text: Optional[str]
    edited_by: Optional[uuid.UUID]
    edited_at: Optional[datetime]


class PublishRequest(BaseModel):
    # Approve = leave as-is; Publish with flag = set translation_flagged = true
    # (CLAUDE.md / Decision: "Approve" vs "Publish with flag").
    translation_flagged: Optional[bool] = None


class PeopleLinkRequest(BaseModel):
    family_member_id: uuid.UUID


class MentionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    story_id: uuid.UUID
    name_raw: str
    family_member_id: Optional[uuid.UUID]
    resolution_status: MentionResolutionStatus
    resolved_by: Optional[uuid.UUID]
    resolved_at: Optional[datetime]


class PublishedStoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: StoryStatus
    narrator_name_raw: str
    title_en: Optional[str]
    title_kh: Optional[str]
    language_detected: Optional[LanguageDetected]
    translation_flagged: bool
    published_at: Optional[datetime]
    created_at: datetime


class ArchivedStoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: StoryStatus
    narrator_name_raw: str
    title_en: Optional[str]
    title_kh: Optional[str]
    archived_at: Optional[datetime]
    created_at: datetime


class StatsResponse(BaseModel):
    awaiting_review: int
    flagged: int


class TranscriptSegmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    story_id: uuid.UUID
    language: Language
    segment_index: int
    start_ms: int
    end_ms: int
    original_text: str
    edited_text: Optional[str]
    edited_by: Optional[uuid.UUID]
    edited_at: Optional[datetime]
    word_timestamps: Optional[Any]


class TranslationSegmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    story_id: uuid.UUID
    transcript_segment_id: uuid.UUID
    source_language: Language
    target_language: Language
    segment_index: int
    original_text: str
    edited_text: Optional[str]
    edited_by: Optional[uuid.UUID]
    edited_at: Optional[datetime]
    confidence_score: Optional[float]
    cultural_flag: bool
    cultural_flag_note: Optional[str]


class TitleSuggestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    suggestion_index: int
    title_en: str
    title_kh: Optional[str] = None
    selected: bool


class StoryTagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    story_id: uuid.UUID
    family_member_id: Optional[uuid.UUID]
    name_raw: str
    tagged_by: TaggedBy


class AudioFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    storage_url: Optional[str]
    mime_type: Optional[str]
    duration_seconds: Optional[int]
    file_size_bytes: Optional[int]


class ChapterCreate(BaseModel):
    title_en: str


class ChapterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title_en: str
    title_kh: Optional[str]
    sort_order: int


class KeeperStoryDetailResponse(BaseModel):
    """Full story payload for the keeper review screen (StoryReview.jsx)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: StoryStatus
    capture_method: CaptureMethod
    narrator_name_raw: str
    language_detected: Optional[LanguageDetected]
    audio_quality_score: Optional[float]
    title_en: Optional[str]
    title_kh: Optional[str]
    translation_flagged: bool
    translation_confidence_score: Optional[float]
    chapter_id: Optional[uuid.UUID]
    chapter_sort_order: Optional[int]
    submitted_at: Optional[datetime]
    published_at: Optional[datetime]
    published_by: Optional[uuid.UUID]
    archived_at: Optional[datetime]
    archived_by: Optional[uuid.UUID]
    updated_at: datetime

    transcript_edited: Optional[str] = None
    translation_edited: Optional[str] = None

    audio_file: Optional[AudioFileResponse] = None
    transcript_segments: list[TranscriptSegmentResponse] = []
    translation_segments: list[TranslationSegmentResponse] = []
    title_suggestions: list[TitleSuggestionResponse] = []
    ai_people_mentions: list[MentionResponse] = []
    story_tags: list[StoryTagResponse] = []
    lock: Optional[LockInfo] = None

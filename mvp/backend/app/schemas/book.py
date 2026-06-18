"""Request/response schemas for Book Reading (CLAUDE.md Flow 4)."""

import uuid
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict

from app.models.enums import DeceasedDatePrecision, Language
from app.models.segments import TranscriptSegment, TranslationSegment

SortOrder = Literal["newest", "chronological"]


class ChapterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title_en: str
    title_kh: Optional[str]
    sort_order: int


class StorySummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title_en: Optional[str]
    title_kh: Optional[str]
    narrator_name_raw: str
    chapter_id: Optional[uuid.UUID]
    chapter_sort_order: Optional[int]
    translation_flagged: bool
    published_at: Optional[datetime]
    duration_seconds: Optional[int] = None


class BookResponse(BaseModel):
    chapters: list[ChapterResponse]
    recent_stories: list[StorySummaryResponse]


class TranscriptSegmentResponse(BaseModel):
    id: uuid.UUID
    segment_index: int
    start_ms: int
    end_ms: int
    language: Language
    text: str
    word_timestamps: Optional[list] = None

    @classmethod
    def from_model(cls, segment: TranscriptSegment) -> "TranscriptSegmentResponse":
        return cls(
            id=segment.id,
            segment_index=segment.segment_index,
            start_ms=segment.start_ms,
            end_ms=segment.end_ms,
            language=segment.language,
            text=segment.edited_text if segment.edited_text is not None else segment.original_text,
            word_timestamps=segment.word_timestamps,
        )


class TranslationSegmentResponse(BaseModel):
    id: uuid.UUID
    segment_index: int
    source_language: Language
    target_language: Language
    text: str
    cultural_flag: bool
    cultural_flag_note: Optional[str] = None

    @classmethod
    def from_model(cls, segment: TranslationSegment) -> "TranslationSegmentResponse":
        return cls(
            id=segment.id,
            segment_index=segment.segment_index,
            source_language=segment.source_language,
            target_language=segment.target_language,
            text=segment.edited_text if segment.edited_text is not None else segment.original_text,
            cultural_flag=segment.cultural_flag,
            cultural_flag_note=segment.cultural_flag_note,
        )


class StoryTagResponse(BaseModel):
    id: uuid.UUID
    name_raw: str
    family_member_id: Optional[uuid.UUID]
    name_en: Optional[str] = None
    name_kh: Optional[str] = None
    is_deceased: bool = False
    deceased_date: Optional[date] = None
    deceased_date_precision: Optional[DeceasedDatePrecision] = None


class StoryDetailResponse(BaseModel):
    id: uuid.UUID
    title_en: Optional[str]
    title_kh: Optional[str]
    narrator_name_raw: str
    chapter_id: Optional[uuid.UUID]
    chapter_sort_order: Optional[int]
    translation_flagged: bool
    translation_confidence_score: Optional[float]
    published_at: Optional[datetime]
    audio_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    transcript_segments: list[TranscriptSegmentResponse]
    translation_segments: list[TranslationSegmentResponse]
    tags: list[StoryTagResponse]

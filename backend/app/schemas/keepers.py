"""Request/response schemas for Keeper Review (CLAUDE.md Flow 3)."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.enums import LanguageDetected, MentionResolutionStatus, StoryStatus


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

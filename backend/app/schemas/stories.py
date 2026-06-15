"""Request/response schemas for the Capture flow (CLAUDE.md Flow 1)."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, model_validator

from app.models.enums import AudioFileType, CaptureMethod, StoryStatus, TaggedBy


class StoryCreateRequest(BaseModel):
    capture_method: CaptureMethod
    # Narrator may not yet be in the family roster.
    narrator_id: Optional[uuid.UUID] = None
    # Verbatim name from the consent gate, for audit purposes.
    narrator_name_raw: str
    recorder_name: Optional[str] = None
    # Which consent_wording_versions row was shown at the consent gate.
    consent_wording_key: str
    # When the recorder tapped "Yes, they've agreed"; defaults to now.
    consented_at: Optional[datetime] = None


class StoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    family_id: uuid.UUID
    status: StoryStatus
    capture_method: CaptureMethod
    narrator_id: Optional[uuid.UUID]
    narrator_name_raw: str
    recorder_name: Optional[str]
    consent_given_at: datetime
    consent_wording_key: str
    submitted_at: Optional[datetime]
    created_at: datetime


class AudioFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    story_id: uuid.UUID
    file_type: AudioFileType
    mime_type: Optional[str]
    file_size_bytes: Optional[int]
    created_at: datetime


class StoryTagCreate(BaseModel):
    """One entry from the Quick Tag screen.

    Either `family_member_id` (a chip from the known roster) or `name_raw`
    (a free-text "Someone else" entry) must be set.
    """

    family_member_id: Optional[uuid.UUID] = None
    name_raw: Optional[str] = None

    @model_validator(mode="after")
    def _check_one_of(self) -> "StoryTagCreate":
        if self.family_member_id is None and not (self.name_raw and self.name_raw.strip()):
            raise ValueError("Either family_member_id or name_raw is required")
        return self


class StoryTagsCreateRequest(BaseModel):
    tags: list[StoryTagCreate]


class StoryTagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    story_id: uuid.UUID
    family_member_id: Optional[uuid.UUID]
    name_raw: str
    tagged_by: TaggedBy
    created_at: datetime

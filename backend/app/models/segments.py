import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from .common import timestamptz_field, utcnow, uuid_fk_field, uuid_pk_field
from .enums import Language


class TranscriptSegment(SQLModel, table=True):
    """One row per utterance/paragraph in the original audio.

    Created by the AI transcription step; `edited_text` is filled in by
    Keepers during review.

    WRITE-ONCE: `original_text` is set on creation and must never be
    updated afterwards (CLAUDE.md invariant #1). Keeper corrections go to
    `edited_text` only — enforce this in the service layer, since no DB
    constraint can express it.
    """

    __tablename__ = "transcript_segments"

    id: uuid.UUID = uuid_pk_field()
    story_id: uuid.UUID = uuid_fk_field("stories.id", nullable=False, index=True)

    # Detected language of this segment.
    language: Language = Field(
        sa_column=Column(SAEnum(Language, name="language"), nullable=False)
    )
    segment_index: int
    start_ms: int
    end_ms: int

    # WRITE-ONCE — raw AI output. Never update after creation.
    original_text: str
    edited_text: Optional[str] = None
    edited_by: Optional[uuid.UUID] = uuid_fk_field("keepers.id", nullable=True)
    edited_at: Optional[datetime] = timestamptz_field(nullable=True)

    # Array of {word, start_ms, end_ms} for Listen Mode highlight sync.
    word_timestamps: Optional[list] = Field(default=None, sa_column=Column(JSONB))

    created_at: datetime = timestamptz_field(
        nullable=False, default_factory=utcnow, server_default_now=True
    )


class TranslationSegment(SQLModel, table=True):
    """Translation of a `transcript_segments` row, parallel to it.

    Created by the AI translation + cultural flag review steps; editable
    by Keepers during review.

    WRITE-ONCE: `original_text` is set on creation and must never be
    updated afterwards (CLAUDE.md invariant #1). Keeper corrections go to
    `edited_text` only — enforce this in the service layer, since no DB
    constraint can express it.
    """

    __tablename__ = "translation_segments"

    id: uuid.UUID = uuid_pk_field()
    story_id: uuid.UUID = uuid_fk_field("stories.id", nullable=False, index=True)
    transcript_segment_id: uuid.UUID = uuid_fk_field(
        "transcript_segments.id", nullable=False, index=True
    )

    source_language: Language = Field(
        sa_column=Column(SAEnum(Language, name="language"), nullable=False)
    )
    target_language: Language = Field(
        sa_column=Column(SAEnum(Language, name="language"), nullable=False)
    )
    # Matches the source segment's segment_index.
    segment_index: int

    # WRITE-ONCE — AI output. Never update after creation.
    original_text: str
    edited_text: Optional[str] = None
    edited_by: Optional[uuid.UUID] = uuid_fk_field("keepers.id", nullable=True)
    edited_at: Optional[datetime] = timestamptz_field(nullable=True)

    # Per-paragraph confidence (0.0-1.0), set by the cultural flag review step.
    confidence_score: Optional[float] = None
    cultural_flag: bool = Field(default=False)
    cultural_flag_note: Optional[str] = None

    created_at: datetime = timestamptz_field(
        nullable=False, default_factory=utcnow, server_default_now=True
    )

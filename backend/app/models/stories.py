import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, ForeignKey
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from .common import timestamptz_field, utcnow, uuid_fk_field, uuid_pk_field
from .enums import CaptureMethod, Language, LanguageDetected, StoryStatus


class Story(SQLModel, table=True):
    """A single recorded/uploaded family story and its lifecycle state.

    `status` is the single source of truth for lifecycle state (see
    CLAUDE.md Story Status Flow). Never add boolean columns that
    duplicate this — all queries should filter on `status`.
    """

    __tablename__ = "stories"

    id: uuid.UUID = uuid_pk_field()
    family_id: uuid.UUID = uuid_fk_field("families.id", nullable=False, index=True)

    status: StoryStatus = Field(
        sa_column=Column(SAEnum(StoryStatus, name="story_status"), nullable=False)
    )
    capture_method: CaptureMethod = Field(
        sa_column=Column(SAEnum(CaptureMethod, name="capture_method"), nullable=False)
    )

    # Narrator may not yet be in the family roster at submission time.
    narrator_id: Optional[uuid.UUID] = uuid_fk_field("family_members.id", nullable=True)
    # Verbatim narrator name from the consent gate, for audit purposes.
    narrator_name_raw: str
    # Who held the phone / submitted the upload; not necessarily a family member.
    recorder_name: Optional[str] = None

    consent_given_at: datetime = timestamptz_field(nullable=False)
    consent_wording_key: str = Field(
        sa_column=Column(ForeignKey("consent_wording_versions.key"), nullable=False)
    )

    submitted_at: Optional[datetime] = timestamptz_field(nullable=True)

    # Set by the recorder at capture time; passed to Whisper to improve accuracy.
    audio_language: Optional[Language] = Field(
        default=None,
        sa_column=Column(SAEnum(Language, name="language")),
    )

    # Set by the AI pipeline.
    language_detected: Optional[LanguageDetected] = Field(
        default=None,
        sa_column=Column(SAEnum(LanguageDetected, name="language_detected")),
    )
    audio_quality_score: Optional[float] = None
    translation_confidence_score: Optional[float] = None
    # "Translation approximate" flag, visible to readers.
    translation_flagged: bool = Field(default=False)

    # Set by the AI pipeline while `status = 'processing'`, for progress display.
    processing_step: Optional[str] = None
    # Set if an AI pipeline step fails; status stays 'processing' so a retry can run.
    processing_error: Optional[str] = None

    # Keeper's full edited transcript/translation (story-level; set in review UI).
    transcript_edited: Optional[str] = None
    translation_edited: Optional[str] = None

    title_en: Optional[str] = None
    title_kh: Optional[str] = None

    # NULL = Uncategorised (virtual shelf, no chapter row).
    chapter_id: Optional[uuid.UUID] = uuid_fk_field("chapters.id", nullable=True)
    # Keeper-set ordering for narrative chronology within a chapter.
    chapter_sort_order: Optional[int] = None

    published_at: Optional[datetime] = timestamptz_field(nullable=True)
    published_by: Optional[uuid.UUID] = uuid_fk_field("keepers.id", nullable=True)

    archived_at: Optional[datetime] = timestamptz_field(nullable=True)
    archived_by: Optional[uuid.UUID] = uuid_fk_field("keepers.id", nullable=True)

    created_at: datetime = timestamptz_field(
        nullable=False, default_factory=utcnow, server_default_now=True
    )
    updated_at: datetime = timestamptz_field(
        nullable=False, default_factory=utcnow, server_default_now=True, onupdate_now=True
    )

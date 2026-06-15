import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, ForeignKey
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from .common import timestamptz_field, uuid_fk_field, uuid_pk_field
from .enums import CaptureMethod, Language


class ConsentWordingVersion(SQLModel, table=True):
    """Canonical record of every version of consent text ever shown.

    Append-only — never update or delete rows. `consent_log.consent_wording_key`
    references `key` so historical consent records can be reconstructed exactly.
    """

    __tablename__ = "consent_wording_versions"

    key: str = Field(primary_key=True)
    capture_method: CaptureMethod = Field(
        sa_column=Column(SAEnum(CaptureMethod, name="capture_method"), nullable=False)
    )
    language: Language = Field(
        sa_column=Column(SAEnum(Language, name="language"), nullable=False)
    )
    text: str

    effective_from: datetime = timestamptz_field(nullable=False)
    superseded_at: Optional[datetime] = timestamptz_field(nullable=True)


class ConsentLog(SQLModel, table=True):
    """Immutable audit record of consent given at story submission.

    Rows are never deleted — not even during GDPR story deletion. On
    deletion, `story_deleted_at` is set instead to record that the
    associated story's content was removed.
    """

    __tablename__ = "consent_log"

    id: uuid.UUID = uuid_pk_field()
    story_id: uuid.UUID = uuid_fk_field("stories.id", nullable=False, index=True)
    family_id: uuid.UUID = uuid_fk_field("families.id", nullable=False, index=True)

    narrator_name: str
    capture_method: CaptureMethod = Field(
        sa_column=Column(SAEnum(CaptureMethod, name="capture_method"), nullable=False)
    )
    consent_wording_key: str = Field(
        sa_column=Column(ForeignKey("consent_wording_versions.key"), nullable=False)
    )
    consented_at: datetime = timestamptz_field(nullable=False)

    device_hint: Optional[str] = None
    # Hashed (not raw) IP address — GDPR compliance.
    ip_hash: Optional[str] = None

    # Set if the recorder deleted the recording before submitting (no GDPR process).
    pre_submission_deleted_at: Optional[datetime] = timestamptz_field(nullable=True)
    # Set if the story was GDPR-deleted post-publication. The row itself is retained.
    story_deleted_at: Optional[datetime] = timestamptz_field(nullable=True)

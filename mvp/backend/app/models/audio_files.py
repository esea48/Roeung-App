import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Column
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from .common import timestamptz_field, utcnow, uuid_fk_field, uuid_pk_field
from .enums import AudioFileType


class AudioFile(SQLModel, table=True):
    """The audio asset for a story, stored in Supabase Storage.

    `storage_key` / `storage_url` are nullable because GDPR deletion clears
    them in place (per CLAUDE.md invariant #4: audio files are never
    overwritten — the object is deleted from storage and these fields are
    cleared, not replaced with a new file).
    """

    __tablename__ = "audio_files"

    id: uuid.UUID = uuid_pk_field()
    story_id: uuid.UUID = uuid_fk_field("stories.id", nullable=False, index=True)
    # Denormalised for access-control queries.
    family_id: uuid.UUID = uuid_fk_field("families.id", nullable=False, index=True)

    storage_key: Optional[str] = None
    storage_url: Optional[str] = None

    file_type: AudioFileType = Field(
        sa_column=Column(SAEnum(AudioFileType, name="audio_file_type"), nullable=False)
    )
    mime_type: Optional[str] = None
    duration_seconds: Optional[int] = None
    file_size_bytes: Optional[int] = Field(default=None, sa_column=Column(BigInteger))

    created_at: datetime = timestamptz_field(
        nullable=False, default_factory=utcnow, server_default_now=True
    )

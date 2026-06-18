import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from .common import timestamptz_field, uuid_fk_field, uuid_pk_field
from .enums import DeletionResolution


class DeletionRequest(SQLModel, table=True):
    """A post-publication GDPR deletion request, resolved by Keepers.

    On resolution:
    - `'deleted'`: audio is removed from storage (see `AudioFile`),
      the story's content is cleared, and `stories.status` is set to the
      terminal `'deleted'` state. The matching `consent_log` row is
      retained with `story_deleted_at` set (CLAUDE.md invariant #2).
    - `'rejected'`: `resolution_note` is required.
    """

    __tablename__ = "deletion_requests"

    id: uuid.UUID = uuid_pk_field()
    story_id: uuid.UUID = uuid_fk_field("stories.id", nullable=False, index=True)
    family_id: uuid.UUID = uuid_fk_field("families.id", nullable=False, index=True)

    # Self-reported name of the requester.
    requested_by_name: str
    reason: Optional[str] = None
    requested_at: datetime = timestamptz_field(nullable=False)

    resolved_at: Optional[datetime] = timestamptz_field(nullable=True)
    resolved_by: Optional[uuid.UUID] = uuid_fk_field("keepers.id", nullable=True)
    resolution: Optional[DeletionResolution] = Field(
        default=None,
        sa_column=Column(SAEnum(DeletionResolution, name="deletion_resolution")),
    )
    # Required if resolution = 'rejected'.
    resolution_note: Optional[str] = None

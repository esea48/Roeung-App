import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from .common import timestamptz_field, utcnow, uuid_fk_field, uuid_pk_field
from .enums import MentionResolutionStatus


class AIPeopleMention(SQLModel, table=True):
    """A name detected in a story's audio by the AI pipeline.

    Separate from recorder-set `story_tags` — this is who the AI thinks is
    *mentioned*, not who the recorder said the story is *about*.

    When a Keeper sets `resolution_status = 'linked'` and assigns
    `family_member_id`, the application must also create a `story_tags`
    row with `tagged_by = 'keeper'` (CLAUDE.md invariant #3) — these two
    writes must be wrapped in a transaction. This is application logic,
    not enforced by the database.
    """

    __tablename__ = "ai_people_mentions"

    id: uuid.UUID = uuid_pk_field()
    story_id: uuid.UUID = uuid_fk_field("stories.id", nullable=False, index=True)

    name_raw: str
    family_member_id: Optional[uuid.UUID] = uuid_fk_field("family_members.id", nullable=True)

    resolution_status: MentionResolutionStatus = Field(
        default=MentionResolutionStatus.pending,
        sa_column=Column(
            SAEnum(MentionResolutionStatus, name="mention_resolution_status"), nullable=False
        ),
    )
    resolved_by: Optional[uuid.UUID] = uuid_fk_field("keepers.id", nullable=True)
    resolved_at: Optional[datetime] = timestamptz_field(nullable=True)

    created_at: datetime = timestamptz_field(
        nullable=False, default_factory=utcnow, server_default_now=True
    )

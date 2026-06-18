import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from .common import timestamptz_field, utcnow, uuid_fk_field, uuid_pk_field
from .enums import TaggedBy


class StoryTag(SQLModel, table=True):
    """A person associated with a story.

    `family_member_id` is NULL for unresolved free-text "Someone else"
    entries; Keepers can link these to `family_members` during review.

    Per CLAUDE.md invariant #3: linking an `ai_people_mentions` row to a
    `family_members` row must also create a row here with
    `tagged_by = 'keeper'`, atomically with that update.
    """

    __tablename__ = "story_tags"

    id: uuid.UUID = uuid_pk_field()
    story_id: uuid.UUID = uuid_fk_field("stories.id", nullable=False, index=True)
    family_member_id: Optional[uuid.UUID] = uuid_fk_field("family_members.id", nullable=True)

    name_raw: str
    tagged_by: TaggedBy = Field(
        sa_column=Column(SAEnum(TaggedBy, name="tagged_by"), nullable=False)
    )

    created_at: datetime = timestamptz_field(
        nullable=False, default_factory=utcnow, server_default_now=True
    )

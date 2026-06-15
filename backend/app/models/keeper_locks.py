import uuid
from datetime import datetime
from typing import Optional

from .common import timestamptz_field, uuid_fk_field, uuid_pk_field
from sqlmodel import SQLModel


class KeeperLock(SQLModel, table=True):
    """A soft lock on a story under active Keeper review.

    A lock is active when `released_at IS NULL AND expires_at > NOW()`.
    The review queue query must filter out expired locks. Per the
    heartbeat mechanism (CLAUDE.md): the frontend pings
    `POST /stories/:id/ping` every 5 minutes to extend `expires_at` by
    10 minutes, and sends a final ping with `release=true` via
    `navigator.sendBeacon` on tab close to set `released_at` immediately.
    """

    __tablename__ = "keeper_locks"

    id: uuid.UUID = uuid_pk_field()
    # One active lock per story.
    story_id: uuid.UUID = uuid_fk_field("stories.id", nullable=False, unique=True, index=True)
    keeper_id: uuid.UUID = uuid_fk_field("keepers.id", nullable=False)

    locked_at: datetime = timestamptz_field(nullable=False)
    expires_at: datetime = timestamptz_field(nullable=False)
    # NULL = still active.
    released_at: Optional[datetime] = timestamptz_field(nullable=True)

import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from .common import timestamptz_field, utcnow, uuid_pk_field


class Family(SQLModel, table=True):
    __tablename__ = "families"

    id: uuid.UUID = uuid_pk_field()
    name: str
    slug: Optional[str] = Field(default=None, unique=True, index=True)
    access_token: str = Field(unique=True, index=True)

    created_at: datetime = timestamptz_field(
        nullable=False, default_factory=utcnow, server_default_now=True
    )
    updated_at: datetime = timestamptz_field(
        nullable=False, default_factory=utcnow, server_default_now=True, onupdate_now=True
    )

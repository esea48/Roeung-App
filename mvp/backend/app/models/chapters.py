import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from .common import timestamptz_field, utcnow, uuid_fk_field, uuid_pk_field


class Chapter(SQLModel, table=True):
    __tablename__ = "chapters"

    id: uuid.UUID = uuid_pk_field()
    family_id: uuid.UUID = uuid_fk_field("families.id", nullable=False, index=True)

    title_en: str
    title_kh: Optional[str] = None
    sort_order: int = Field(default=0)

    created_at: datetime = timestamptz_field(
        nullable=False, default_factory=utcnow, server_default_now=True
    )
    updated_at: datetime = timestamptz_field(
        nullable=False, default_factory=utcnow, server_default_now=True, onupdate_now=True
    )

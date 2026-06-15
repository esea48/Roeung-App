import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from .common import timestamptz_field, utcnow, uuid_fk_field, uuid_pk_field


class Keeper(SQLModel, table=True):
    __tablename__ = "keepers"

    id: uuid.UUID = uuid_pk_field()
    family_id: uuid.UUID = uuid_fk_field("families.id", nullable=False, index=True)

    name: str
    email: str = Field(unique=True, index=True)
    # bcrypt or argon2 hash — never store plain text or MD5.
    password_hash: str
    is_active: bool = Field(default=True)

    created_at: datetime = timestamptz_field(
        nullable=False, default_factory=utcnow, server_default_now=True
    )
    updated_at: datetime = timestamptz_field(
        nullable=False, default_factory=utcnow, server_default_now=True, onupdate_now=True
    )

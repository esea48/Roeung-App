import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from .common import timestamptz_field, utcnow, uuid_fk_field, uuid_pk_field
from .enums import RelationshipType


class FamilyRelationship(SQLModel, table=True):
    __tablename__ = "family_relationships"

    id: uuid.UUID = uuid_pk_field()
    family_id: uuid.UUID = uuid_fk_field("families.id", nullable=False, index=True)
    member_id: uuid.UUID = uuid_fk_field("family_members.id", nullable=False, index=True)
    related_member_id: uuid.UUID = uuid_fk_field("family_members.id", nullable=False, index=True)
    relationship_type: RelationshipType = Field(
        sa_column=Column(SAEnum(RelationshipType, name="relationship_type"), nullable=False)
    )
    created_by: Optional[uuid.UUID] = uuid_fk_field("keepers.id", nullable=True)
    created_at: datetime = timestamptz_field(
        nullable=False, default_factory=utcnow, server_default_now=True
    )

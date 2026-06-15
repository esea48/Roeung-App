import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Column
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from .common import timestamptz_field, utcnow, uuid_fk_field, uuid_pk_field
from .enums import DeceasedDatePrecision


class FamilyMember(SQLModel, table=True):
    __tablename__ = "family_members"

    id: uuid.UUID = uuid_pk_field()
    family_id: uuid.UUID = uuid_fk_field("families.id", nullable=False, index=True)

    name_en: str
    name_kh: Optional[str] = None

    is_deceased: bool = Field(default=False)
    # Full date; day/month may be unknown for older family members.
    # `deceased_date_precision` tells the UI how much of this date to display
    # (e.g. "year" -> show year only, per CLAUDE.md deceased member display rules).
    deceased_date: Optional[date] = None
    deceased_date_precision: Optional[DeceasedDatePrecision] = Field(
        default=None,
        sa_column=Column(SAEnum(DeceasedDatePrecision, name="deceased_date_precision")),
    )

    birth_year: Optional[int] = None
    notes: Optional[str] = None

    created_at: datetime = timestamptz_field(
        nullable=False, default_factory=utcnow, server_default_now=True
    )
    updated_at: datetime = timestamptz_field(
        nullable=False, default_factory=utcnow, server_default_now=True, onupdate_now=True
    )

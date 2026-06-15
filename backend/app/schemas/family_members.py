"""Request/response schemas for the family members roster."""

import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.enums import DeceasedDatePrecision


class FamilyMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name_en: str
    name_kh: Optional[str]
    is_deceased: bool
    deceased_date: Optional[date]
    deceased_date_precision: Optional[DeceasedDatePrecision]

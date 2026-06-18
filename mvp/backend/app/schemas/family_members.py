"""Request/response schemas for the family members roster and family tree."""

import uuid
from datetime import date
from typing import Optional, List

from pydantic import BaseModel, ConfigDict

from app.models.enums import DeceasedDatePrecision, Gender, RelationshipType


class FamilyMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name_en: str
    name_kh: Optional[str]
    is_deceased: bool
    deceased_date: Optional[date]
    deceased_date_precision: Optional[DeceasedDatePrecision]
    gender: Optional[Gender]
    birth_year: Optional[int]
    notes: Optional[str]
    is_tree_member: bool
    position_col: Optional[int] = None
    position_row: Optional[int] = None


# ── Tree schemas ──────────────────────────────────────────────────────────────

class RelationshipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    member_id: uuid.UUID
    related_member_id: uuid.UUID
    relationship_type: RelationshipType


class StoryMentionResponse(BaseModel):
    id: uuid.UUID
    title_en: Optional[str]
    title_kh: Optional[str]
    narrator_name_raw: Optional[str]


class MemberStoriesResponse(BaseModel):
    member: FamilyMemberResponse
    stories: List[StoryMentionResponse]


class TreeResponse(BaseModel):
    placed: List[FamilyMemberResponse]
    unplaced: List[FamilyMemberResponse]
    relationships: List[RelationshipResponse]


class MemberCreate(BaseModel):
    name_en: str
    name_kh: Optional[str] = None
    gender: Optional[Gender] = None
    birth_year: Optional[int] = None
    is_deceased: bool = False
    deceased_date: Optional[date] = None
    deceased_date_precision: Optional[DeceasedDatePrecision] = None
    notes: Optional[str] = None
    anchor_member_id: Optional[uuid.UUID] = None
    relationship_type: Optional[RelationshipType] = None


class MemberUpdate(BaseModel):
    name_en: Optional[str] = None
    name_kh: Optional[str] = None
    gender: Optional[Gender] = None
    birth_year: Optional[int] = None
    is_deceased: Optional[bool] = None
    deceased_date: Optional[date] = None
    deceased_date_precision: Optional[DeceasedDatePrecision] = None
    notes: Optional[str] = None
    position_col: Optional[int] = None
    position_row: Optional[int] = None


class RelationshipCreate(BaseModel):
    member_id: uuid.UUID
    related_member_id: uuid.UUID
    relationship_type: RelationshipType

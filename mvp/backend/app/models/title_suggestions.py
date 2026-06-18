import uuid
from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from .common import timestamptz_field, utcnow, uuid_fk_field, uuid_pk_field
from .enums import Language


class TitleSuggestion(SQLModel, table=True):
    """An AI-generated title option shown to the Keeper during review.

    `stories.title_en` / `stories.title_kh` hold the final chosen title
    regardless of source (a selected suggestion or a custom Keeper-typed
    title). This table is retained for audit and AI improvement.
    """

    __tablename__ = "title_suggestions"

    id: uuid.UUID = uuid_pk_field()
    story_id: uuid.UUID = uuid_fk_field("stories.id", nullable=False, index=True)

    language: Language = Field(
        sa_column=Column(SAEnum(Language, name="language"), nullable=False)
    )
    # 1, 2, or 3 — pairs with the same index in the other language.
    suggestion_index: int
    text: str
    selected: bool = Field(default=False)

    created_at: datetime = timestamptz_field(
        nullable=False, default_factory=utcnow, server_default_now=True
    )

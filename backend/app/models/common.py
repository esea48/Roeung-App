"""Shared column helpers for SQLModel table definitions.

Every table uses UUID primary keys and UUID foreign keys backed by the
native Postgres UUID type, and TIMESTAMPTZ for all timestamps. These
helpers keep that consistent without repeating SQLAlchemy `Column(...)`
boilerplate in every model file.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Column, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def uuid_pk_field() -> Any:
    """Primary key column: UUID, generated client-side by default."""
    return Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True),
    )


def uuid_fk_field(
    target: str,
    *,
    nullable: bool = False,
    index: bool = False,
    unique: bool = False,
    default: Optional[uuid.UUID] = None,
) -> Any:
    """Foreign key column referencing another table's UUID id."""
    return Field(
        default=default,
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey(target),
            nullable=nullable,
            index=index,
            unique=unique,
        ),
    )


def timestamptz_field(
    *,
    nullable: bool = True,
    default: Optional[datetime] = None,
    default_factory: Optional[Any] = None,
    server_default_now: bool = False,
    onupdate_now: bool = False,
) -> Any:
    """A TIMESTAMPTZ column."""
    column_kwargs: dict = {}
    if server_default_now:
        column_kwargs["server_default"] = func.now()
    if onupdate_now:
        column_kwargs["onupdate"] = func.now()

    field_kwargs: dict = {"sa_column": Column(DateTime(timezone=True), nullable=nullable, **column_kwargs)}
    if default_factory is not None:
        field_kwargs["default_factory"] = default_factory
    else:
        field_kwargs["default"] = default

    return Field(**field_kwargs)

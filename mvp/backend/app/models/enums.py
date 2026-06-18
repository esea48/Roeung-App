"""Enum types shared across SQLModel table definitions.

Each enum maps to a native Postgres ENUM type. Where the same enum is
reused across multiple tables (e.g. `Language`), the SQLAlchemy `Enum`
type is given the same `name=` in each column definition so Postgres
reuses a single type rather than creating duplicates.
"""

from enum import Enum


class CaptureMethod(str, Enum):
    recorded = "recorded"
    uploaded = "uploaded"


class Language(str, Enum):
    en = "en"
    kh = "kh"


class LanguageDetected(str, Enum):
    kh = "kh"
    en = "en"
    mixed = "mixed"


class StoryStatus(str, Enum):
    submitted = "submitted"
    processing = "processing"
    awaiting_review = "awaiting_review"
    rejected = "rejected"
    in_review = "in_review"
    published = "published"
    archived = "archived"
    unpublished = "unpublished"
    deleted = "deleted"


class AudioFileType(str, Enum):
    original = "original"


class TaggedBy(str, Enum):
    recorder = "recorder"
    keeper = "keeper"


class DeceasedDatePrecision(str, Enum):
    year = "year"
    month = "month"
    day = "day"


class MentionResolutionStatus(str, Enum):
    pending = "pending"
    linked = "linked"
    dismissed = "dismissed"


class DeletionResolution(str, Enum):
    deleted = "deleted"
    rejected = "rejected"


class RelationshipType(str, Enum):
    parent = "parent"
    child = "child"
    spouse = "spouse"
    sibling = "sibling"


class Gender(str, Enum):
    male = "male"
    female = "female"
    other = "other"
    unknown = "unknown"

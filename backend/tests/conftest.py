import os
import secrets
import uuid
from datetime import datetime, timezone

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ["SUPABASE_JWT_SECRET"] = "test-supabase-jwt-secret-at-least-32-bytes-long"

from sqlalchemy.dialects.postgresql import JSONB  # noqa: E402
from sqlalchemy.ext.compiler import compiles  # noqa: E402
from sqlmodel import Session, SQLModel, create_engine  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.models import (  # noqa: E402
    AIPeopleMention,
    Chapter,
    Family,
    FamilyMember,
    Keeper,
    KeeperLock,
    Story,
    StoryTag,
    TranscriptSegment,
    TranslationSegment,
)
from app.models.enums import CaptureMethod, StoryStatus  # noqa: E402

get_settings.cache_clear()


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    """Tests run against SQLite, which has no JSONB type — map it to JSON."""
    return "JSON"


@pytest.fixture()
def session():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(
        engine,
        tables=[
            Family.__table__,
            Keeper.__table__,
            FamilyMember.__table__,
            Chapter.__table__,
            Story.__table__,
            KeeperLock.__table__,
            StoryTag.__table__,
            AIPeopleMention.__table__,
            TranscriptSegment.__table__,
            TranslationSegment.__table__,
        ],
    )
    with Session(engine) as session:
        yield session


@pytest.fixture()
def family(session: Session) -> Family:
    family = Family(name="Sea Family", slug="sea-family", access_token=secrets.token_urlsafe(32))
    session.add(family)
    session.commit()
    session.refresh(family)
    return family


@pytest.fixture()
def keeper(session: Session, family: Family) -> Keeper:
    keeper = Keeper(
        id=uuid.uuid4(),
        family_id=family.id,
        name="Ellen Sea",
        email="ellen@example.com",
        password_hash="not-a-real-hash",
        is_active=True,
    )
    session.add(keeper)
    session.commit()
    session.refresh(keeper)
    return keeper


@pytest.fixture()
def other_keeper(session: Session, family: Family) -> Keeper:
    keeper = Keeper(
        id=uuid.uuid4(),
        family_id=family.id,
        name="Sokha Sea",
        email="sokha@example.com",
        password_hash="not-a-real-hash",
        is_active=True,
    )
    session.add(keeper)
    session.commit()
    session.refresh(keeper)
    return keeper


@pytest.fixture()
def story(session: Session, family: Family) -> Story:
    story = Story(
        family_id=family.id,
        status=StoryStatus.awaiting_review,
        capture_method=CaptureMethod.recorded,
        narrator_name_raw="Grandmother Sea",
        consent_given_at=datetime.now(timezone.utc),
        consent_wording_key="v1_recorded",
        submitted_at=datetime.now(timezone.utc),
    )
    session.add(story)
    session.commit()
    session.refresh(story)
    return story

import os
import secrets
import uuid
from datetime import datetime, timezone

import pytest

from sqlalchemy.dialects.postgresql import JSONB  # noqa: E402
from sqlalchemy.ext.compiler import compiles  # noqa: E402
from sqlmodel import Session, SQLModel, create_engine  # noqa: E402

from app.core.config import get_settings  # noqa: E402

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SUPABASE_JWT_SECRET"] = "test-supabase-jwt-secret-at-least-32-bytes-long"
os.environ["REDIS_URL"] = "redis://localhost:6379"
os.environ["SUPABASE_URL"] = "http://localhost"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "test-service-role-key"
os.environ["OPENAI_API_KEY"] = ""
os.environ["GOOGLE_TRANSLATE_API_KEY"] = ""
from app.core import config as app_config  # noqa: E402

app_config.Settings.database_url = "sqlite://"
app_config.Settings.supabase_jwt_secret = os.environ["SUPABASE_JWT_SECRET"]
app_config.Settings.redis_url = os.environ["REDIS_URL"]
app_config.Settings.supabase_url = os.environ["SUPABASE_URL"]
app_config.Settings.supabase_service_role_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
app_config.Settings.openai_api_key = os.environ["OPENAI_API_KEY"]
app_config.Settings.google_translate_api_key = os.environ["GOOGLE_TRANSLATE_API_KEY"]
get_settings.cache_clear()

import app.db as app_db  # noqa: E402
from app.services import ai_pipeline as ai_pipeline_service  # noqa: E402
from app.models import (  # noqa: E402
    AIPeopleMention,
    Chapter,
    ConsentLog,
    ConsentWordingVersion,
    DeletionRequest,
    Family,
    FamilyMember,
    Keeper,
    KeeperLock,
    Story,
    StoryTag,
    AudioFile,
    TitleSuggestion,
    TranscriptSegment,
    TranslationSegment,
)
from app.models.enums import CaptureMethod, Language, StoryStatus  # noqa: E402

get_settings.cache_clear()


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    """Tests run against SQLite, which has no JSONB type — map it to JSON."""
    return "JSON"


@pytest.fixture()
def session(monkeypatch):
    engine = create_engine("sqlite://")
    monkeypatch.setattr(app_db, "engine", engine)
    monkeypatch.setattr(ai_pipeline_service, "engine", engine)
    SQLModel.metadata.create_all(
        engine,
        tables=[
            Family.__table__,
            Keeper.__table__,
            FamilyMember.__table__,
            Chapter.__table__,
            ConsentWordingVersion.__table__,
            ConsentLog.__table__,
            Story.__table__,
            AudioFile.__table__,
            KeeperLock.__table__,
            StoryTag.__table__,
            AIPeopleMention.__table__,
            TranscriptSegment.__table__,
            TranslationSegment.__table__,
            TitleSuggestion.__table__,
            DeletionRequest.__table__,
        ],
    )
    with Session(engine) as session:
        session.add_all(
            [
                ConsentWordingVersion(
                    key="v1_recorded",
                    capture_method=CaptureMethod.recorded,
                    language=Language.en,
                    text="Recorded consent",
                    effective_from=datetime.now(timezone.utc),
                ),
                ConsentWordingVersion(
                    key="v1_uploaded",
                    capture_method=CaptureMethod.uploaded,
                    language=Language.en,
                    text="Uploaded consent",
                    effective_from=datetime.now(timezone.utc),
                ),
            ]
        )
        session.commit()
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

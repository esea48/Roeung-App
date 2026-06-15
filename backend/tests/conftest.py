import os
import secrets
import uuid

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ["SUPABASE_JWT_SECRET"] = "test-supabase-jwt-secret-at-least-32-bytes-long"

from sqlmodel import Session, SQLModel, create_engine  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.models import Family, Keeper  # noqa: E402

get_settings.cache_clear()


@pytest.fixture()
def session():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine, tables=[Family.__table__, Keeper.__table__])
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

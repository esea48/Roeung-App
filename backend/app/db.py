"""Database engine and session dependency."""

from typing import Iterator

from sqlmodel import Session, create_engine

from app.core.config import get_settings

engine = create_engine(get_settings().database_url)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session

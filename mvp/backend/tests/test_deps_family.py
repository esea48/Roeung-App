import pytest
from fastapi import HTTPException
from sqlmodel import Session

from app.api.deps import get_family
from app.models import Family


def test_get_family_returns_family_for_valid_token(session: Session, family: Family):
    result = get_family(access_token=family.access_token, session=session)

    assert result.id == family.id


def test_get_family_raises_403_for_unknown_token(session: Session, family: Family):
    with pytest.raises(HTTPException) as exc_info:
        get_family(access_token="not-a-real-token", session=session)

    assert exc_info.value.status_code == 403


def test_get_family_raises_403_for_empty_token(session: Session, family: Family):
    with pytest.raises(HTTPException) as exc_info:
        get_family(access_token="", session=session)

    assert exc_info.value.status_code == 403

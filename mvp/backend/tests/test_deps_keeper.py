import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlmodel import Session

from app.api.deps import get_current_keeper, verify_keeper_family
from app.core.config import get_settings
from app.models import Family, Keeper

SECRET = "test-supabase-jwt-secret-at-least-32-bytes-long"


def _credentials(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def _make_token(sub: str, *, secret: str = SECRET, expires_delta=timedelta(hours=1), audience="authenticated") -> str:
    payload = {
        "sub": sub,
        "aud": audience,
        "exp": datetime.now(timezone.utc) + expires_delta,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def test_settings_uses_test_secret():
    assert get_settings().supabase_jwt_secret == SECRET


def test_get_current_keeper_returns_keeper_for_valid_token(session: Session, keeper: Keeper):
    token = _make_token(str(keeper.id))

    result = get_current_keeper(credentials=_credentials(token), session=session)

    assert result.id == keeper.id


def test_get_current_keeper_raises_401_for_missing_credentials(session: Session):
    with pytest.raises(HTTPException) as exc_info:
        get_current_keeper(credentials=None, session=session)

    assert exc_info.value.status_code == 401


def test_get_current_keeper_raises_401_for_bad_signature(session: Session, keeper: Keeper):
    token = _make_token(str(keeper.id), secret="wrong-secret")

    with pytest.raises(HTTPException) as exc_info:
        get_current_keeper(credentials=_credentials(token), session=session)

    assert exc_info.value.status_code == 401


def test_get_current_keeper_raises_401_for_expired_token(session: Session, keeper: Keeper):
    token = _make_token(str(keeper.id), expires_delta=timedelta(hours=-1))

    with pytest.raises(HTTPException) as exc_info:
        get_current_keeper(credentials=_credentials(token), session=session)

    assert exc_info.value.status_code == 401


def test_get_current_keeper_raises_401_for_wrong_audience(session: Session, keeper: Keeper):
    token = _make_token(str(keeper.id), audience="other")

    with pytest.raises(HTTPException) as exc_info:
        get_current_keeper(credentials=_credentials(token), session=session)

    assert exc_info.value.status_code == 401


def test_get_current_keeper_raises_401_for_non_uuid_subject(session: Session):
    token = _make_token("not-a-uuid")

    with pytest.raises(HTTPException) as exc_info:
        get_current_keeper(credentials=_credentials(token), session=session)

    assert exc_info.value.status_code == 401


def test_get_current_keeper_raises_403_for_unknown_keeper(session: Session):
    token = _make_token(str(uuid.uuid4()))

    with pytest.raises(HTTPException) as exc_info:
        get_current_keeper(credentials=_credentials(token), session=session)

    assert exc_info.value.status_code == 403


def test_get_current_keeper_raises_403_for_inactive_keeper(session: Session, keeper: Keeper):
    keeper.is_active = False
    session.add(keeper)
    session.commit()

    token = _make_token(str(keeper.id))

    with pytest.raises(HTTPException) as exc_info:
        get_current_keeper(credentials=_credentials(token), session=session)

    assert exc_info.value.status_code == 403


def test_verify_keeper_family_passes_for_matching_family(keeper: Keeper, family: Family):
    verify_keeper_family(keeper, family.id)


def test_verify_keeper_family_raises_403_for_mismatched_family(keeper: Keeper):
    with pytest.raises(HTTPException) as exc_info:
        verify_keeper_family(keeper, uuid.uuid4())

    assert exc_info.value.status_code == 403

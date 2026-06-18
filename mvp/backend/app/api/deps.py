"""Shared FastAPI dependencies for the two auth paths.

See CLAUDE.md "Auth Model (Two-Tier)":

- Family members access Capture (Flow 1) and Book Reading (Flow 4) via a
  secret `access_token` in the URL path: `/f/{access_token}/...`.
- Keepers authenticate with a Supabase Auth JWT passed as
  `Authorization: Bearer <token>`.

The two paths are never mixed: a valid family `access_token` does not grant
access to Keeper routes, and vice versa.
"""

import uuid
from functools import lru_cache
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select

from app.core.config import get_settings
from app.db import get_session
from app.models import Family, Keeper

_bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def _get_jwks_client() -> jwt.PyJWKClient:
    settings = get_settings()
    return jwt.PyJWKClient(f"{settings.supabase_url}/auth/v1/.well-known/jwks.json")


def get_family(access_token: str, session: Session = Depends(get_session)) -> Family:
    """Resolve the `Family` for the `access_token` in the URL path.

    Raises 403 if no family matches the token. A non-matching token is
    treated the same as a missing one — never reveal whether a token format
    is "close" to valid.
    """
    family = session.exec(select(Family).where(Family.access_token == access_token)).first()
    if family is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid access token")
    return family


def get_current_keeper(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    session: Session = Depends(get_session),
) -> Keeper:
    """Resolve the `Keeper` for the Supabase JWT in the `Authorization` header.

    Raises 401 if the header is missing or the token is invalid/expired.
    Raises 403 if the token is valid but no active keeper matches its
    subject claim.

    Supabase projects may use HS256 or ES256 depending on project settings.
    We use PyJWKClient to fetch the correct public key from the JWKS endpoint,
    which handles both algorithms and key rotation automatically.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    settings = get_settings()
    try:
        jwks_client = _get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(credentials.credentials)
        payload = jwt.decode(
            credentials.credentials,
            signing_key.key,
            algorithms=["HS256", "ES256", "RS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError:
        try:
            payload = jwt.decode(
                credentials.credentials,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
            )
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    subject = payload.get("sub")
    try:
        keeper_id = uuid.UUID(subject)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    keeper = session.get(Keeper, keeper_id)
    if keeper is None or not keeper.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Keeper not found")

    return keeper


def verify_keeper_family(keeper: Keeper, family_id: uuid.UUID) -> None:
    """Confirm `keeper` belongs to `family_id`.

    Call this from routes once the target resource's `family_id` is known
    (e.g. after loading a story), to enforce that a keeper can only act on
    resources belonging to their own family.

    Raises 403 on mismatch.
    """
    if keeper.family_id != family_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

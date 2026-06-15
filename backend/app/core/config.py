"""Application configuration loaded from environment variables."""

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    database_url: str = os.environ["DATABASE_URL"]

    # Secret used by Supabase Auth to sign JWTs (HS256). Used to verify the
    # `Authorization: Bearer <token>` header on Keeper routes.
    supabase_jwt_secret: str = os.environ["SUPABASE_JWT_SECRET"]


@lru_cache
def get_settings() -> Settings:
    return Settings()

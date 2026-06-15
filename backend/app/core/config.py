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

    # Supabase Storage — audio file uploads (CLAUDE.md "File storage").
    supabase_url: str = os.environ["SUPABASE_URL"]
    supabase_service_role_key: str = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    supabase_storage_bucket: str = os.environ.get("SUPABASE_STORAGE_BUCKET", "audio")

    # Redis connection for the ARQ AI pipeline job queue (CLAUDE.md "AI job queue").
    redis_url: str = os.environ["REDIS_URL"]

    # Below this audio quality score, the pipeline sets status = 'rejected'
    # and stops (CLAUDE.md "AI Pipeline (ARQ Workers)" step 1).
    audio_quality_threshold: float = float(os.environ.get("AUDIO_QUALITY_THRESHOLD", "0.5"))


@lru_cache
def get_settings() -> Settings:
    return Settings()

"""Application configuration loaded from environment variables."""

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv(override=True)


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

    # OpenAI — Whisper transcription and GPT-4 review/generation steps.
    openai_api_key: str = os.environ.get("OPENAI_API_KEY") or os.environ.get("openai_api_key", "")

    # Google Cloud Translation API (v2, key-based) — first-pass translation.
    google_translate_api_key: str = (
        os.environ.get("GOOGLE_TRANSLATE_API_KEY") or os.environ.get("google_api_key", "")
    )

    # Below this mean translation confidence score, the pipeline sets
    # stories.translation_flagged = true (CLAUDE.md "AI Pipeline" step 7).
    translation_confidence_threshold: float = float(
        os.environ.get("TRANSLATION_CONFIDENCE_THRESHOLD", "0.7")
    )

    # Allowed browser origin for CORS. In production set to the deployed
    # frontend URL; defaults to Vite's local dev port.
    frontend_origin: str = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")


@lru_cache
def get_settings() -> Settings:
    return Settings()

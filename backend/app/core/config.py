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

    # ElevenLabs — Scribe v2 transcription.
    elevenlabs_api_key: str = os.environ.get("ELEVENLABS_API_KEY", "")

    # OpenAI — GPT-4 cultural review, title generation, people flagging steps.
    openai_api_key: str = os.environ.get("OPENAI_API_KEY") or os.environ.get("openai_api_key", "")

    # LangSmith observability for the AI pipeline.
    langsmith_api_key: str = os.environ.get("LANGSMITH_API_KEY", "")
    langsmith_api_url: str = (
        os.environ.get("LANGSMITH_ENDPOINT")
        or os.environ.get("LANGCHAIN_ENDPOINT")
        or ""
    )
    langsmith_project_name: str = (
        os.environ.get("LANGSMITH_PROJECT")
        or os.environ.get("LANGCHAIN_PROJECT")
        or "roeung-ai"
    )
    langsmith_tracing_v2: bool = os.environ.get("LANGSMITH_TRACING_V2", "").lower() == "true"

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

"""ARQ job definitions for the AI processing pipeline.

The Capture API enqueues `process_story` once a story's audio has been
uploaded (CLAUDE.md "AI Pipeline (ARQ Workers)" — triggered when a story
reaches `status = 'submitted'`). The actual pipeline steps live in
`app.services.ai_pipeline`.
"""

import uuid

from arq import create_pool
from arq.connections import RedisSettings

from app.core.config import get_settings
from app.services.ai_pipeline import run_pipeline


async def process_story(ctx, story_id: str) -> None:
    await run_pipeline(story_id)


async def enqueue_story_pipeline(story_id: uuid.UUID) -> None:
    """Push a `process_story` job onto the ARQ queue for `story_id`."""
    pool = await create_pool(RedisSettings.from_dsn(get_settings().redis_url))
    try:
        await pool.enqueue_job("process_story", str(story_id))
    finally:
        await pool.close()


class WorkerSettings:
    functions = [process_story]

    @staticmethod
    def redis_settings() -> RedisSettings:
        return RedisSettings.from_dsn(get_settings().redis_url)

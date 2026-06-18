"""ARQ job definitions for the AI processing pipeline.

The Capture API enqueues `process_story` once a story's audio has been
uploaded (CLAUDE.md "AI Pipeline (ARQ Workers)" — triggered when a story
reaches `status = 'submitted'`). The actual pipeline steps live in
`app.services.ai_pipeline`.
"""

import uuid

try:
    from arq import create_pool
    from arq.connections import RedisSettings
except ModuleNotFoundError:  # pragma: no cover - fallback for test environments without arq
    create_pool = None
    RedisSettings = None

from app.core.config import get_settings
from app.services.ai_pipeline import run_pipeline


async def process_story(ctx, story_id: str) -> None:
    await run_pipeline(story_id)


async def enqueue_story_pipeline(story_id: uuid.UUID) -> None:
    """Push a `process_story` job onto the ARQ queue for `story_id`."""
    if create_pool is None or RedisSettings is None:
        raise ModuleNotFoundError(
            "arq is required to enqueue pipeline jobs; install backend dependencies to use this module"
        )

    pool = await create_pool(RedisSettings.from_dsn(get_settings().redis_url))
    try:
        await pool.enqueue_job("process_story", str(story_id))
    finally:
        await pool.close()


if RedisSettings is not None:
    class WorkerSettings:
        functions = [process_story]
        redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
else:  # pragma: no cover - fallback for test environments without arq
    class WorkerSettings:
        functions = [process_story]
        redis_settings = None

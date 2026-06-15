"""Orchestrates the AI processing pipeline (CLAUDE.md "AI Pipeline (ARQ Workers)").

The step-by-step implementation (audio quality check, transcription,
translation, cultural flag review, title generation, people flagging,
scoring) is built out in a later phase. This module currently exposes the
entrypoint the ARQ worker calls so the Capture API can enqueue jobs.
"""


async def run_pipeline(story_id: str) -> None:
    raise NotImplementedError("AI pipeline steps are implemented in a later phase")

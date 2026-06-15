"""Orchestrates the AI processing pipeline (CLAUDE.md "AI Pipeline (ARQ Workers)").

`run_pipeline` is the entrypoint the ARQ worker (`app.workers.pipeline`) calls
once a story reaches `status = 'submitted'`. Each step below is a stub for
now — the real Whisper / Google Translate / GPT-4 calls are wired up in a
later phase. Each step updates `stories.processing_step` so the UI can show
progress, and sleeps briefly to simulate latency.

If a step raises, the error is recorded on `stories.processing_error` and
`status` is left as `'processing'` so a retry can pick up where it left off.
"""

import asyncio
import logging
import uuid

from sqlmodel import Session

from app.db import engine
from app.models import Story
from app.models.enums import StoryStatus

logger = logging.getLogger(__name__)

# Simulated per-step latency for stubbed pipeline steps.
STEP_SLEEP_SECONDS = 1


class _StoryRejected(Exception):
    """Raised by a step to stop the pipeline without recording an error."""


async def run_pipeline(story_id: str) -> None:
    with Session(engine) as session:
        story = session.get(Story, uuid.UUID(story_id))
        if story is None:
            logger.error("process_story: story %s not found", story_id)
            return

        story.status = StoryStatus.processing
        story.processing_error = None
        session.add(story)
        session.commit()

        steps = [
            _check_audio_quality,
            _transcribe,
            _translate,
            _review_cultural_flags,
            _generate_titles,
            _flag_people,
            _score_translation,
        ]

        for step in steps:
            try:
                await step(session, story)
            except _StoryRejected:
                session.commit()
                return
            except Exception as exc:
                logger.exception(
                    "process_story: step %s failed for story %s", step.__name__, story_id
                )
                story.processing_error = str(exc)
                session.add(story)
                session.commit()
                return

        story.status = StoryStatus.awaiting_review
        story.processing_step = None
        session.add(story)
        session.commit()


async def _check_audio_quality(session: Session, story: Story) -> None:
    story.processing_step = "audio_quality_check"
    session.add(story)
    session.commit()
    await asyncio.sleep(STEP_SLEEP_SECONDS)

    # TODO: score the story's audio file and compare against
    # AUDIO_QUALITY_THRESHOLD. If below threshold, set
    # story.audio_quality_score, story.status = StoryStatus.rejected,
    # and raise _StoryRejected() to stop the pipeline here.


async def _transcribe(session: Session, story: Story) -> None:
    story.processing_step = "transcription"
    session.add(story)
    session.commit()
    await asyncio.sleep(STEP_SLEEP_SECONDS)

    # TODO: call the Whisper API on the story's audio file and create
    # `transcript_segments` rows with word-level timestamps as JSONB.
    # Also set story.language_detected.


async def _translate(session: Session, story: Story) -> None:
    story.processing_step = "translation"
    session.add(story)
    session.commit()
    await asyncio.sleep(STEP_SLEEP_SECONDS)

    # TODO: call the Google Cloud Translation API (first pass) for each
    # `transcript_segments` row and create matching `translation_segments`
    # rows.


async def _review_cultural_flags(session: Session, story: Story) -> None:
    story.processing_step = "cultural_flag_review"
    session.add(story)
    session.commit()
    await asyncio.sleep(STEP_SLEEP_SECONDS)

    # TODO: call GPT-4/Claude on each `translation_segments` row and update
    # `cultural_flag`, `cultural_flag_note`, and `confidence_score`.


async def _generate_titles(session: Session, story: Story) -> None:
    story.processing_step = "title_generation"
    session.add(story)
    session.commit()
    await asyncio.sleep(STEP_SLEEP_SECONDS)

    # TODO: call GPT-4/Claude to generate 3 title suggestions and create
    # `title_suggestions` rows in both KH and EN.


async def _flag_people(session: Session, story: Story) -> None:
    story.processing_step = "people_flagging"
    session.add(story)
    session.commit()
    await asyncio.sleep(STEP_SLEEP_SECONDS)

    # TODO: call GPT-4/Claude to detect names mentioned in the transcript
    # and create `ai_people_mentions` rows.


async def _score_translation(session: Session, story: Story) -> None:
    story.processing_step = "scoring"
    session.add(story)
    session.commit()
    await asyncio.sleep(STEP_SLEEP_SECONDS)

    # TODO: compute the mean `confidence_score` across `translation_segments`
    # and write it to story.translation_confidence_score. Set
    # story.translation_flagged = True if it's below threshold.

"""Capture flow (Flow 1) story endpoints.

All routes are scoped to a family via the `/f/{access_token}` access-token
path, per CLAUDE.md "Auth Model (Two-Tier)". `access_token` is resolved to
a `Family` by the `get_family` dependency.
"""

import hashlib
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, Response, UploadFile, status
from sqlmodel import Session, select

from app.api.deps import get_family
from app.db import get_session
from app.models import AudioFile, ConsentLog, ConsentWordingVersion, Family, FamilyMember, Story, StoryTag
from app.models.common import utcnow
from app.models.enums import AudioFileType, StoryStatus, TaggedBy
from app.schemas.stories import (
    AudioFileResponse,
    StoryCreateRequest,
    StoryResponse,
    StoryTagResponse,
    StoryTagsCreateRequest,
)
from app.services.storage import delete_audio_file, upload_audio_file
from app.services.ai_pipeline import run_pipeline

router = APIRouter(prefix="/f/{access_token}/stories", tags=["stories"])


async def enqueue_story_pipeline(story_id: str) -> None:
    """Background-task wrapper for the ARQ pipeline entrypoint.

    Keeping this wrapper makes it easy to monkeypatch in tests and keeps the
    route code readably explicit about the task it queues.
    """
    await run_pipeline(str(story_id))


def _get_family_story(session: Session, family: Family, story_id: uuid.UUID) -> Story:
    story = session.get(Story, story_id)
    if story is None or story.family_id != family.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found")
    return story


def _hash_ip(request: Request) -> Optional[str]:
    if request.client is None:
        return None
    return hashlib.sha256(request.client.host.encode()).hexdigest()


@router.post("", response_model=StoryResponse, status_code=status.HTTP_201_CREATED)
def create_story(
    payload: StoryCreateRequest,
    request: Request,
    family: Family = Depends(get_family),
    session: Session = Depends(get_session),
) -> Story:
    """Consent gate tap (1.2): create the story and its consent log atomically.

    Also pre-tags the narrator on the Quick Tag screen (Decision #7).
    """
    wording = session.get(ConsentWordingVersion, payload.consent_wording_key)
    if wording is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown consent_wording_key"
        )

    if payload.narrator_id is not None:
        narrator = session.get(FamilyMember, payload.narrator_id)
        if narrator is None or narrator.family_id != family.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown narrator_id"
            )

    consented_at = payload.consented_at or utcnow()

    story = Story(
        family_id=family.id,
        status=StoryStatus.submitted,
        capture_method=payload.capture_method,
        narrator_id=payload.narrator_id,
        narrator_name_raw=payload.narrator_name_raw,
        recorder_name=payload.recorder_name,
        audio_language=payload.audio_language,
        consent_given_at=consented_at,
        consent_wording_key=payload.consent_wording_key,
        submitted_at=consented_at,
    )
    session.add(story)
    session.flush()

    session.add(
        ConsentLog(
            story_id=story.id,
            family_id=family.id,
            narrator_name=payload.narrator_name_raw,
            capture_method=payload.capture_method,
            consent_wording_key=payload.consent_wording_key,
            consented_at=consented_at,
            device_hint=request.headers.get("user-agent"),
            ip_hash=_hash_ip(request),
        )
    )

    # Pre-ticked narrator chip on the Quick Tag screen.
    session.add(
        StoryTag(
            story_id=story.id,
            family_member_id=payload.narrator_id,
            name_raw=payload.narrator_name_raw,
            tagged_by=TaggedBy.recorder,
        )
    )

    session.commit()
    session.refresh(story)
    return story


@router.post("/{story_id}/audio", response_model=AudioFileResponse, status_code=status.HTTP_201_CREATED)
async def upload_story_audio(
    story_id: uuid.UUID,
    background_tasks: BackgroundTasks = None,
    file: UploadFile = File(...),
    family: Family = Depends(get_family),
    session: Session = Depends(get_session),
) -> AudioFile:
    """Stitched upload complete (1.3a/1.3b): store the audio and start the AI pipeline."""
    story = _get_family_story(session, family, story_id)

    if story.status != StoryStatus.submitted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Audio can only be added to a submitted story",
        )

    # Retry case: a previous attempt may have uploaded the file but failed before
    # the pipeline started. Skip re-uploading (invariant #4: never overwrite) and
    # just re-trigger the pipeline.
    existing = session.exec(select(AudioFile).where(AudioFile.story_id == story.id)).first()
    if existing is not None:
        await file.read()  # consume the request body
        if background_tasks is None:
            await enqueue_story_pipeline(story.id)
        else:
            background_tasks.add_task(enqueue_story_pipeline, story.id)
        return existing

    content = await file.read()
    storage_key = upload_audio_file(family.id, story.id, file.filename or "audio", content, file.content_type)

    audio = AudioFile(
        story_id=story.id,
        family_id=family.id,
        storage_key=storage_key,
        file_type=AudioFileType.original,
        mime_type=file.content_type,
        file_size_bytes=len(content),
    )
    session.add(audio)
    session.commit()
    session.refresh(audio)

    if background_tasks is None:
        await enqueue_story_pipeline(story.id)
    else:
        background_tasks.add_task(enqueue_story_pipeline, story.id)

    return audio


@router.post("/{story_id}/tags", response_model=list[StoryTagResponse], status_code=status.HTTP_201_CREATED)
def create_story_tags(
    story_id: uuid.UUID,
    payload: StoryTagsCreateRequest,
    family: Family = Depends(get_family),
    session: Session = Depends(get_session),
) -> list[StoryTag]:
    """Quick Tag submission (1.4): tag people the story is about."""
    story = _get_family_story(session, family, story_id)

    existing = session.exec(select(StoryTag).where(StoryTag.story_id == story.id)).all()
    existing_member_ids = {t.family_member_id for t in existing if t.family_member_id is not None}
    existing_names = {t.name_raw for t in existing if t.family_member_id is None}

    created: list[StoryTag] = []
    for tag in payload.tags:
        if tag.family_member_id is not None:
            if tag.family_member_id in existing_member_ids:
                continue
            member = session.get(FamilyMember, tag.family_member_id)
            if member is None or member.family_id != family.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown family_member_id"
                )
            name_raw = member.name_en
            existing_member_ids.add(tag.family_member_id)
        else:
            name_raw = tag.name_raw.strip()  # type: ignore[union-attr]
            if not name_raw or name_raw in existing_names:
                continue
            existing_names.add(name_raw)

        story_tag = StoryTag(
            story_id=story.id,
            family_member_id=tag.family_member_id,
            name_raw=name_raw,
            tagged_by=TaggedBy.recorder,
        )
        session.add(story_tag)
        created.append(story_tag)

    session.commit()
    for story_tag in created:
        session.refresh(story_tag)
    return created


@router.delete("/{story_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_story(
    story_id: uuid.UUID,
    family: Family = Depends(get_family),
    session: Session = Depends(get_session),
) -> Response:
    """"Delete recording" (1.5), pre-submission only: hard-delete the story.

    The `consent_log` row is retained with `pre_submission_deleted_at` set
    (CLAUDE.md invariant #2 / Decision #6) — there is no GDPR process here,
    the recorder is simply choosing not to submit.
    """
    story = _get_family_story(session, family, story_id)

    if story.status != StoryStatus.submitted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only a story that has not started processing can be deleted this way",
        )

    audio_files = session.exec(select(AudioFile).where(AudioFile.story_id == story.id)).all()
    for audio in audio_files:
        if audio.storage_key:
            delete_audio_file(audio.storage_key)
        session.delete(audio)

    for tag in session.exec(select(StoryTag).where(StoryTag.story_id == story.id)).all():
        session.delete(tag)

    consent_log = session.exec(select(ConsentLog).where(ConsentLog.story_id == story.id)).first()
    if consent_log is not None:
        consent_log.pre_submission_deleted_at = utcnow()
        session.add(consent_log)

    session.delete(story)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

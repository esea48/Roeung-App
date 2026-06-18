"""Book Reading endpoints (CLAUDE.md Flow 4).

All routes are read-only and scoped to a family via the `/f/{access_token}`
access-token path, per CLAUDE.md "Auth Model (Two-Tier)". Only `published`
stories are visible here — anything still in review, archived, unpublished,
or deleted is never returned.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, col, select
from sqlmodel.sql.expression import SelectOfScalar

from app.api.deps import get_family
from app.db import get_session
from app.services.storage import get_signed_url
from app.models import (
    AudioFile,
    Chapter,
    Family,
    FamilyMember,
    Story,
    StoryTag,
    TranscriptSegment,
    TranslationSegment,
)
from app.models.enums import AudioFileType, StoryStatus
from app.schemas.book import (
    BookResponse,
    ChapterResponse,
    SortOrder,
    StoryDetailResponse,
    StorySummaryResponse,
    StoryTagResponse,
    TranscriptSegmentResponse,
    TranslationSegmentResponse,
)

router = APIRouter(prefix="/f/{access_token}", tags=["book"])

RECENT_STORIES_LIMIT = 5


def _sorted_published_stories(query: SelectOfScalar[Story], sort: SortOrder) -> SelectOfScalar[Story]:
    if sort == "chronological":
        return query.order_by(Story.chapter_sort_order.asc().nulls_last(), Story.published_at.asc())
    return query.order_by(Story.published_at.desc())


def _audio_by_story(session: Session, story_ids: list[uuid.UUID]) -> dict[uuid.UUID, AudioFile]:
    """Fetch original audio files for a list of story IDs, keyed by story_id."""
    if not story_ids:
        return {}
    rows = session.exec(
        select(AudioFile)
        .where(col(AudioFile.story_id).in_(story_ids))
        .where(AudioFile.file_type == AudioFileType.original)
    ).all()
    return {af.story_id: af for af in rows}


def _story_summary(story: Story, audio: AudioFile | None = None) -> StorySummaryResponse:
    return StorySummaryResponse(
        id=story.id,
        title_en=story.title_en,
        title_kh=story.title_kh,
        narrator_name_raw=story.narrator_name_raw,
        chapter_id=story.chapter_id,
        chapter_sort_order=story.chapter_sort_order,
        translation_flagged=story.translation_flagged,
        published_at=story.published_at,
        duration_seconds=audio.duration_seconds if audio else None,
    )


@router.get("/book", response_model=BookResponse)
def get_book(
    family: Family = Depends(get_family),
    session: Session = Depends(get_session),
) -> BookResponse:
    """Book Home (4.1): chapters plus the 5 most recently published stories."""
    chapters = session.exec(
        select(Chapter).where(Chapter.family_id == family.id).order_by(Chapter.sort_order.asc())
    ).all()

    recent_stories = session.exec(
        select(Story)
        .where(Story.family_id == family.id)
        .where(Story.status == StoryStatus.published)
        .order_by(Story.published_at.desc())
        .limit(RECENT_STORIES_LIMIT)
    ).all()

    audio_map = _audio_by_story(session, [s.id for s in recent_stories])

    return BookResponse(
        chapters=[ChapterResponse.model_validate(c) for c in chapters],
        recent_stories=[_story_summary(s, audio_map.get(s.id)) for s in recent_stories],
    )


@router.get("/chapters/{chapter_id}/stories", response_model=list[StorySummaryResponse])
def get_chapter_stories(
    chapter_id: uuid.UUID,
    sort: SortOrder = Query("newest"),
    family: Family = Depends(get_family),
    session: Session = Depends(get_session),
) -> list[StorySummaryResponse]:
    """Chapter view (4.2): published stories in a chapter."""
    chapter = session.get(Chapter, chapter_id)
    if chapter is None or chapter.family_id != family.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found")

    query = (
        select(Story)
        .where(Story.family_id == family.id)
        .where(Story.chapter_id == chapter.id)
        .where(Story.status == StoryStatus.published)
    )
    stories = session.exec(_sorted_published_stories(query, sort)).all()
    audio_map = _audio_by_story(session, [s.id for s in stories])
    return [_story_summary(s, audio_map.get(s.id)) for s in stories]


@router.get("/book/uncategorised", response_model=list[StorySummaryResponse])
def get_uncategorised_stories(
    sort: SortOrder = Query("newest"),
    family: Family = Depends(get_family),
    session: Session = Depends(get_session),
) -> list[StorySummaryResponse]:
    """Uncategorised shelf (4.2): published stories with no chapter assigned."""
    query = (
        select(Story)
        .where(Story.family_id == family.id)
        .where(Story.chapter_id.is_(None))
        .where(Story.status == StoryStatus.published)
    )
    stories = session.exec(_sorted_published_stories(query, sort)).all()
    audio_map = _audio_by_story(session, [s.id for s in stories])
    return [_story_summary(s, audio_map.get(s.id)) for s in stories]


@router.get("/stories/{story_id}", response_model=StoryDetailResponse)
def get_story(
    story_id: uuid.UUID,
    family: Family = Depends(get_family),
    session: Session = Depends(get_session),
) -> StoryDetailResponse:
    """Story page (4.3): full bilingual transcript, translations, and tags."""
    story = session.get(Story, story_id)
    if story is None or story.family_id != family.id or story.status != StoryStatus.published:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found")

    transcript_segments = session.exec(
        select(TranscriptSegment)
        .where(TranscriptSegment.story_id == story.id)
        .order_by(TranscriptSegment.segment_index.asc())
    ).all()

    translation_segments = session.exec(
        select(TranslationSegment)
        .where(TranslationSegment.story_id == story.id)
        .order_by(TranslationSegment.segment_index.asc())
    ).all()

    tag_rows = session.exec(
        select(StoryTag, FamilyMember)
        .where(StoryTag.story_id == story.id)
        .join(FamilyMember, FamilyMember.id == StoryTag.family_member_id, isouter=True)
    ).all()

    audio_file = session.exec(
        select(AudioFile)
        .where(AudioFile.story_id == story.id)
        .where(AudioFile.file_type == AudioFileType.original)
        .limit(1)
    ).first()

    tags = []
    for tag, member in tag_rows:
        tags.append(
            StoryTagResponse(
                id=tag.id,
                name_raw=tag.name_raw,
                family_member_id=tag.family_member_id,
                name_en=member.name_en if member else None,
                name_kh=member.name_kh if member else None,
                is_deceased=member.is_deceased if member else False,
                deceased_date=member.deceased_date if member else None,
                deceased_date_precision=member.deceased_date_precision if member else None,
            )
        )

    return StoryDetailResponse(
        id=story.id,
        title_en=story.title_en,
        title_kh=story.title_kh,
        narrator_name_raw=story.narrator_name_raw,
        chapter_id=story.chapter_id,
        chapter_sort_order=story.chapter_sort_order,
        translation_flagged=story.translation_flagged,
        translation_confidence_score=story.translation_confidence_score,
        published_at=story.published_at,
        audio_url=get_signed_url(audio_file.storage_key) if audio_file and audio_file.storage_key else None,
        duration_seconds=audio_file.duration_seconds if audio_file else None,
        transcript_segments=[TranscriptSegmentResponse.from_model(s) for s in transcript_segments],
        translation_segments=[TranslationSegmentResponse.from_model(s) for s in translation_segments],
        tags=tags,
    )

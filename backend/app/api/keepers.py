"""Keeper Review endpoints (CLAUDE.md Flow 3).

All routes are scoped to the authenticated Keeper via the Supabase JWT
(`get_current_keeper`), per CLAUDE.md "Auth Model (Two-Tier)". Every route
that loads a story confirms it belongs to the Keeper's family via
`verify_keeper_family` before returning or mutating anything.
"""

import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, select

from app.api.deps import get_current_keeper, verify_keeper_family
from app.services.storage import delete_audio_file, get_signed_url
from app.db import get_session
from app.models import (
    AIPeopleMention,
    AudioFile,
    Chapter,
    ConsentLog,
    Family,
    FamilyMember,
    Keeper,
    KeeperLock,
    Story,
    StoryTag,
    TitleSuggestion,
    TranscriptSegment,
    TranslationSegment,
)
from app.models.common import utcnow
from app.models.enums import MentionResolutionStatus, StoryStatus, TaggedBy
from app.models.enums import Language
from app.schemas.family_members import FamilyMemberResponse
from app.schemas.keepers import (
    ArchivedStoryResponse,
    AudioFileResponse,
    ChapterCreate,
    ChapterResponse,
    KeeperStoryDetailResponse,
    KeeperStoryResponse,
    LockInfo,
    LockResponse,
    MentionResponse,
    PeopleLinkRequest,
    PublishRequest,
    PublishedStoryResponse,
    QueueStoryResponse,
    SegmentResponse,
    SegmentUpdateRequest,
    StatsResponse,
    StoryTagResponse,
    StoryUpdateRequest,
    TitleSuggestionResponse,
    TranscriptSegmentResponse,
    TranslationSegmentResponse,
)

router = APIRouter(prefix="/keeper", tags=["keeper"])

LOCK_DURATION_MINUTES = 10


def _get_keeper_story(session: Session, keeper: Keeper, story_id: uuid.UUID) -> Story:
    story = session.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found")
    verify_keeper_family(keeper, story.family_id)
    return story


@router.get("/family-token")
def get_family_token(
    keeper: Keeper = Depends(get_current_keeper),
    session: Session = Depends(get_session),
):
    """Return the family access token so a Keeper can navigate to the capture flow."""
    family = session.get(Family, keeper.family_id)
    if family is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Family not found")
    return {"access_token": family.access_token}


@router.get("/queue", response_model=list[QueueStoryResponse])
def get_review_queue(
    keeper: Keeper = Depends(get_current_keeper),
    session: Session = Depends(get_session),
) -> list[QueueStoryResponse]:
    """Review Queue (3.1): stories awaiting or under review, newest first.

    A story's `lock` is included only if it has an active soft lock
    (`released_at IS NULL AND expires_at > NOW()`), per CLAUDE.md "Soft Lock
    (Heartbeat)".
    """
    stories = session.exec(
        select(Story)
        .where(Story.family_id == keeper.family_id)
        .where(Story.status.in_([StoryStatus.awaiting_review, StoryStatus.in_review]))
        .order_by(Story.submitted_at.desc())
    ).all()

    locks_by_story: dict[uuid.UUID, LockInfo] = {}
    if stories:
        now = utcnow()
        rows = session.exec(
            select(KeeperLock, Keeper)
            .join(Keeper, Keeper.id == KeeperLock.keeper_id)
            .where(KeeperLock.story_id.in_([s.id for s in stories]))
            .where(KeeperLock.released_at.is_(None))
            .where(KeeperLock.expires_at > now)
        ).all()
        for lock, lock_keeper in rows:
            locks_by_story[lock.story_id] = LockInfo(
                keeper_id=lock_keeper.id,
                keeper_name=lock_keeper.name,
                locked_at=lock.locked_at,
                expires_at=lock.expires_at,
            )

    results = []
    for story in stories:
        item = QueueStoryResponse.model_validate(story)
        item.lock = locks_by_story.get(story.id)
        results.append(item)
    return results


@router.post("/stories/{story_id}/lock", response_model=LockResponse)
def lock_story(
    story_id: uuid.UUID,
    keeper: Keeper = Depends(get_current_keeper),
    session: Session = Depends(get_session),
) -> KeeperLock:
    """Claim a story for review (2.6 / 3.1): soft-lock it for 10 minutes.

    If `status = 'awaiting_review'`, claiming it transitions the story to
    `'in_review'`. Raises 409 if another Keeper holds an active lock.
    """
    story = _get_keeper_story(session, keeper, story_id)

    now = utcnow()
    lock = session.exec(select(KeeperLock).where(KeeperLock.story_id == story.id)).first()

    if (
        lock is not None
        and lock.released_at is None
        and lock.expires_at > now
        and lock.keeper_id != keeper.id
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Story is locked by another keeper")

    expires_at = now + timedelta(minutes=LOCK_DURATION_MINUTES)
    if lock is None:
        lock = KeeperLock(story_id=story.id, keeper_id=keeper.id, locked_at=now, expires_at=expires_at)
    else:
        lock.keeper_id = keeper.id
        lock.locked_at = now
        lock.expires_at = expires_at
        lock.released_at = None
    session.add(lock)

    if story.status == StoryStatus.awaiting_review:
        story.status = StoryStatus.in_review
        session.add(story)
    # Published stories stay published — lock is acquired for editing without status change.

    session.commit()
    session.refresh(lock)
    return lock


@router.post("/stories/{story_id}/ping", response_model=LockResponse)
def ping_story_lock(
    story_id: uuid.UUID,
    release: bool = False,
    keeper: Keeper = Depends(get_current_keeper),
    session: Session = Depends(get_session),
) -> KeeperLock:
    """Heartbeat (CLAUDE.md "Soft Lock (Heartbeat)").

    Extends `expires_at` by 10 minutes, or — when `?release=true` (sent via
    `navigator.sendBeacon` on tab close) — sets `released_at` immediately.
    """
    story = _get_keeper_story(session, keeper, story_id)

    lock = session.exec(select(KeeperLock).where(KeeperLock.story_id == story.id)).first()
    if lock is None or lock.keeper_id != keeper.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active lock for this keeper")

    now = utcnow()
    if release:
        lock.released_at = now
    else:
        lock.expires_at = now + timedelta(minutes=LOCK_DURATION_MINUTES)

    session.add(lock)
    session.commit()
    session.refresh(lock)
    return lock


@router.patch("/stories/{story_id}", response_model=KeeperStoryResponse)
def update_story(
    story_id: uuid.UUID,
    payload: StoryUpdateRequest,
    keeper: Keeper = Depends(get_current_keeper),
    session: Session = Depends(get_session),
) -> Story:
    """Story Review edits (3.2): title, translation-flag, and chapter assignment."""
    story = _get_keeper_story(session, keeper, story_id)

    updates = payload.model_dump(exclude_unset=True)

    if "chapter_id" in updates and updates["chapter_id"] is not None:
        chapter = session.get(Chapter, updates["chapter_id"])
        if chapter is None or chapter.family_id != keeper.family_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown chapter_id")

    for field, value in updates.items():
        setattr(story, field, value)

    session.add(story)
    session.commit()
    session.refresh(story)
    return story


def _update_segment_impl(
    story_id: uuid.UUID,
    segment_id: uuid.UUID,
    payload: SegmentUpdateRequest,
    keeper: Keeper,
    session: Session,
):
    """Shared handler for transcript and translation segment corrections (3.2).

    Per CLAUDE.md invariant #1, `original_text` is write-once — corrections
    go to `edited_text` only.
    """
    story = _get_keeper_story(session, keeper, story_id)

    segment = session.get(TranscriptSegment, segment_id)
    if segment is None or segment.story_id != story.id:
        segment = session.get(TranslationSegment, segment_id)
        if segment is None or segment.story_id != story.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segment not found")

    segment.edited_text = payload.edited_text
    segment.edited_by = keeper.id
    segment.edited_at = utcnow()

    session.add(segment)
    session.commit()
    session.refresh(segment)
    return segment


@router.patch("/stories/{story_id}/transcript-segments/{segment_id}", response_model=SegmentResponse)
def update_transcript_segment(
    story_id: uuid.UUID,
    segment_id: uuid.UUID,
    payload: SegmentUpdateRequest,
    keeper: Keeper = Depends(get_current_keeper),
    session: Session = Depends(get_session),
):
    return _update_segment_impl(story_id, segment_id, payload, keeper, session)


@router.patch("/stories/{story_id}/translation-segments/{segment_id}", response_model=SegmentResponse)
def update_translation_segment(
    story_id: uuid.UUID,
    segment_id: uuid.UUID,
    payload: SegmentUpdateRequest,
    keeper: Keeper = Depends(get_current_keeper),
    session: Session = Depends(get_session),
):
    return _update_segment_impl(story_id, segment_id, payload, keeper, session)


@router.post("/stories/{story_id}/publish", response_model=KeeperStoryResponse)
def publish_story(
    story_id: uuid.UUID,
    payload: PublishRequest,
    keeper: Keeper = Depends(get_current_keeper),
    session: Session = Depends(get_session),
) -> Story:
    """Decision (3.3/3.4): Approve, or Publish with flag.

    Only a story under review can be published (CLAUDE.md Story Status Flow:
    `in_review -> published`).
    """
    story = _get_keeper_story(session, keeper, story_id)

    if story.status != StoryStatus.in_review:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Only a story in review can be published"
        )

    if payload.translation_flagged is not None:
        story.translation_flagged = payload.translation_flagged

    story.status = StoryStatus.published
    story.published_at = utcnow()
    story.published_by = keeper.id

    session.add(story)
    session.commit()
    session.refresh(story)
    return story


@router.post("/stories/{story_id}/archive", response_model=KeeperStoryResponse)
def archive_story(
    story_id: uuid.UUID,
    keeper: Keeper = Depends(get_current_keeper),
    session: Session = Depends(get_session),
) -> Story:
    """Decision (3.3): Archive privately.

    Allowed from `in_review` (archive instead of publishing) or `published`
    (CLAUDE.md Story Status Flow: `in_review -> archived`, `published -> archived`).
    """
    story = _get_keeper_story(session, keeper, story_id)

    if story.status not in (StoryStatus.awaiting_review, StoryStatus.in_review, StoryStatus.published):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Story cannot be archived from its current status"
        )

    story.status = StoryStatus.archived
    story.archived_at = utcnow()
    story.archived_by = keeper.id

    session.add(story)
    session.commit()
    session.refresh(story)
    return story


@router.post("/stories/{story_id}/unpublish", response_model=KeeperStoryResponse)
def unpublish_story(
    story_id: uuid.UUID,
    keeper: Keeper = Depends(get_current_keeper),
    session: Session = Depends(get_session),
) -> Story:
    """Unpublish (3.4): reversible — sends a published story back to review.

    CLAUDE.md Story Status Flow: `published -> unpublished (-> back to in_review)`.
    """
    story = _get_keeper_story(session, keeper, story_id)

    if story.status != StoryStatus.published:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Only a published story can be unpublished"
        )

    story.status = StoryStatus.in_review
    story.published_at = None
    story.published_by = None

    session.add(story)
    session.commit()
    session.refresh(story)
    return story


@router.get("/published", response_model=list[PublishedStoryResponse])
def get_published_stories(
    filter: str = "",
    sort: str = "newest",
    keeper: Keeper = Depends(get_current_keeper),
    session: Session = Depends(get_session),
) -> list[PublishedStoryResponse]:
    """Published stories list for the Keeper Published view."""
    query = (
        select(Story)
        .where(Story.family_id == keeper.family_id)
        .where(Story.status == StoryStatus.published)
    )
    if filter == "kh":
        query = query.where(Story.language_detected == "kh")
    elif filter == "en":
        query = query.where(Story.language_detected == "en")

    order = Story.published_at.asc() if sort == "oldest" else Story.published_at.desc()
    query = query.order_by(order)

    return session.exec(query).all()


@router.get("/archived", response_model=list[ArchivedStoryResponse])
def get_archived_stories(
    filter: str = "",
    sort: str = "newest",
    keeper: Keeper = Depends(get_current_keeper),
    session: Session = Depends(get_session),
) -> list[ArchivedStoryResponse]:
    """Archived stories list for the Keeper Archive view."""
    query = (
        select(Story)
        .where(Story.family_id == keeper.family_id)
        .where(Story.status == StoryStatus.archived)
    )
    if filter == "kh":
        query = query.where(Story.language_detected == "kh")
    elif filter == "en":
        query = query.where(Story.language_detected == "en")

    order = Story.archived_at.asc() if sort == "oldest" else Story.archived_at.desc()
    query = query.order_by(order)

    return session.exec(query).all()


@router.delete("/stories/{story_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_story(
    story_id: uuid.UUID,
    keeper: Keeper = Depends(get_current_keeper),
    session: Session = Depends(get_session),
) -> None:
    """GDPR deletion: removes audio, retains consent log, marks story as deleted.

    Per CLAUDE.md invariants:
    - #2: consent_log row is never deleted — story_deleted_at is set instead.
    - #4: audio files are never overwritten — object is deleted from storage and
      storage_key / storage_url fields are cleared.
    """
    story = _get_keeper_story(session, keeper, story_id)

    if story.status == StoryStatus.deleted:
        return  # Already deleted — idempotent

    audio_file = session.exec(
        select(AudioFile).where(AudioFile.story_id == story.id)
    ).first()
    if audio_file and audio_file.storage_key:
        try:
            delete_audio_file(audio_file.storage_key)
        except Exception:
            pass  # Storage deletion is best-effort; proceed with DB update
        audio_file.storage_key = None
        audio_file.storage_url = None
        session.add(audio_file)

    consent = session.exec(
        select(ConsentLog).where(ConsentLog.story_id == story.id)
    ).first()
    if consent:
        consent.story_deleted_at = utcnow()
        session.add(consent)

    story.status = StoryStatus.deleted
    session.add(story)
    session.commit()


@router.post("/stories/{story_id}/restore", response_model=KeeperStoryResponse)
def restore_story(
    story_id: uuid.UUID,
    keeper: Keeper = Depends(get_current_keeper),
    session: Session = Depends(get_session),
) -> Story:
    """Restore an archived story to its previous status.

    If `published_at` is set the story was previously published — restore to
    `published`. Otherwise restore to `in_review`.
    """
    story = _get_keeper_story(session, keeper, story_id)

    if story.status != StoryStatus.archived:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Only an archived story can be restored"
        )

    story.status = StoryStatus.published if story.published_at else StoryStatus.in_review
    story.archived_at = None
    story.archived_by = None

    session.add(story)
    session.commit()
    session.refresh(story)
    return story


@router.post("/stories/{story_id}/people-mentions/{mention_id}/link", response_model=MentionResponse)
def link_people_mention(
    story_id: uuid.UUID,
    mention_id: uuid.UUID,
    payload: PeopleLinkRequest,
    keeper: Keeper = Depends(get_current_keeper),
    session: Session = Depends(get_session),
) -> AIPeopleMention:
    """People linker (3.2): link an AI-flagged name to a family member.

    Per CLAUDE.md invariant #3, this also creates a `story_tags` row with
    `tagged_by = 'keeper'`, atomically with the mention update.
    """
    story = _get_keeper_story(session, keeper, story_id)

    mention = session.get(AIPeopleMention, mention_id)
    if mention is None or mention.story_id != story.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mention not found")

    member = session.get(FamilyMember, payload.family_member_id)
    if member is None or member.family_id != keeper.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown family_member_id")

    now = utcnow()
    mention.family_member_id = member.id
    mention.resolution_status = MentionResolutionStatus.linked
    mention.resolved_by = keeper.id
    mention.resolved_at = now
    session.add(mention)

    existing_tag = session.exec(
        select(StoryTag).where(
            StoryTag.story_id == story.id, StoryTag.family_member_id == member.id
        )
    ).first()
    if existing_tag is None:
        session.add(
            StoryTag(
                story_id=story.id,
                family_member_id=member.id,
                name_raw=member.name_en,
                tagged_by=TaggedBy.keeper,
            )
        )

    session.commit()
    session.refresh(mention)
    return mention


@router.post("/stories/{story_id}/people-mentions/{mention_id}/dismiss", response_model=MentionResponse)
def dismiss_people_mention(
    story_id: uuid.UUID,
    mention_id: uuid.UUID,
    keeper: Keeper = Depends(get_current_keeper),
    session: Session = Depends(get_session),
) -> AIPeopleMention:
    """Dismiss an AI-detected name mention (3.2): mark it as not a family member."""
    story = _get_keeper_story(session, keeper, story_id)

    mention = session.get(AIPeopleMention, mention_id)
    if mention is None or mention.story_id != story.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mention not found")

    now = utcnow()
    mention.resolution_status = MentionResolutionStatus.dismissed
    mention.resolved_by = keeper.id
    mention.resolved_at = now
    session.add(mention)
    session.commit()
    session.refresh(mention)
    return mention


@router.get("/stats", response_model=StatsResponse)
def get_stats(
    keeper: Keeper = Depends(get_current_keeper),
    session: Session = Depends(get_session),
) -> StatsResponse:
    """Badge counts for the keeper dashboard (KeeperContext.jsx)."""
    awaiting = session.exec(
        select(func.count(Story.id))
        .where(Story.family_id == keeper.family_id)
        .where(Story.status == StoryStatus.awaiting_review)
    ).one()

    flagged = session.exec(
        select(func.count(Story.id))
        .where(Story.family_id == keeper.family_id)
        .where(Story.status == StoryStatus.awaiting_review)
        .where(Story.translation_flagged == True)  # noqa: E712
    ).one()

    return StatsResponse(awaiting_review=awaiting, flagged=flagged)


@router.get("/stories/{story_id}", response_model=KeeperStoryDetailResponse)
def get_story_detail(
    story_id: uuid.UUID,
    keeper: Keeper = Depends(get_current_keeper),
    session: Session = Depends(get_session),
) -> KeeperStoryDetailResponse:
    """Full story detail for the review screen (StoryReview.jsx)."""
    story = _get_keeper_story(session, keeper, story_id)

    audio_file = session.exec(
        select(AudioFile).where(AudioFile.story_id == story.id)
    ).first()

    transcript_segments = session.exec(
        select(TranscriptSegment)
        .where(TranscriptSegment.story_id == story.id)
        .order_by(TranscriptSegment.segment_index)
    ).all()

    translation_segments = session.exec(
        select(TranslationSegment)
        .where(TranslationSegment.story_id == story.id)
        .order_by(TranslationSegment.segment_index)
    ).all()

    title_suggestions = session.exec(
        select(TitleSuggestion).where(TitleSuggestion.story_id == story.id)
        .order_by(TitleSuggestion.suggestion_index.asc(), TitleSuggestion.language.asc())
    ).all()

    ai_people_mentions = session.exec(
        select(AIPeopleMention).where(AIPeopleMention.story_id == story.id)
    ).all()

    story_tags = session.exec(
        select(StoryTag).where(StoryTag.story_id == story.id)
    ).all()

    now = utcnow()
    lock_row = session.exec(
        select(KeeperLock, Keeper)
        .join(Keeper, Keeper.id == KeeperLock.keeper_id)
        .where(KeeperLock.story_id == story.id)
        .where(KeeperLock.released_at.is_(None))
        .where(KeeperLock.expires_at > now)
    ).first()
    lock_info = None
    if lock_row:
        lock, lock_keeper = lock_row
        lock_info = LockInfo(
            keeper_id=lock_keeper.id,
            keeper_name=lock_keeper.name,
            locked_at=lock.locked_at,
            expires_at=lock.expires_at,
        )

    result = KeeperStoryDetailResponse.model_validate(story)
    if audio_file:
        audio_response = AudioFileResponse.model_validate(audio_file)
        if audio_file.storage_key and not audio_file.storage_url:
            audio_response.storage_url = get_signed_url(audio_file.storage_key)
        result.audio_file = audio_response
    else:
        result.audio_file = None
    result.transcript_segments = [TranscriptSegmentResponse.model_validate(s) for s in transcript_segments]
    result.translation_segments = [TranslationSegmentResponse.model_validate(s) for s in translation_segments]
    grouped_titles: dict[int, dict[str, object]] = {}
    for suggestion in title_suggestions:
        # Store bilingual options under the shared suggestion index.
        item = grouped_titles.setdefault(
            suggestion.suggestion_index,
            {"suggestion_index": suggestion.suggestion_index, "title_en": "", "title_kh": None, "selected": False},
        )
        if suggestion.language == Language.en:
            item["title_en"] = suggestion.text
        elif suggestion.language == Language.kh:
            item["title_kh"] = suggestion.text
        item["selected"] = bool(item["selected"]) or suggestion.selected

    result.title_suggestions = [
        TitleSuggestionResponse.model_validate(grouped_titles[index])
        for index in sorted(grouped_titles)
    ]
    result.ai_people_mentions = [MentionResponse.model_validate(m) for m in ai_people_mentions]
    result.story_tags = [StoryTagResponse.model_validate(t) for t in story_tags]
    result.lock = lock_info
    return result


@router.get("/family-members", response_model=list[FamilyMemberResponse])
def get_family_members(
    keeper: Keeper = Depends(get_current_keeper),
    session: Session = Depends(get_session),
) -> list[FamilyMember]:
    """Family roster for the people-mention linking dropdown (StoryReview.jsx)."""
    return session.exec(
        select(FamilyMember)
        .where(FamilyMember.family_id == keeper.family_id)
        .order_by(FamilyMember.name_en)
    ).all()


@router.get("/chapters", response_model=list[ChapterResponse])
def get_chapters(
    keeper: Keeper = Depends(get_current_keeper),
    session: Session = Depends(get_session),
) -> list[Chapter]:
    """Chapter list for the publish chapter-assignment dropdown (StoryReview.jsx)."""
    return session.exec(
        select(Chapter)
        .where(Chapter.family_id == keeper.family_id)
        .order_by(Chapter.sort_order)
    ).all()


@router.post("/chapters", response_model=ChapterResponse, status_code=status.HTTP_201_CREATED)
def create_chapter(
    body: ChapterCreate,
    keeper: Keeper = Depends(get_current_keeper),
    session: Session = Depends(get_session),
) -> Chapter:
    max_order = session.exec(
        select(func.max(Chapter.sort_order)).where(Chapter.family_id == keeper.family_id)
    ).first() or 0
    chapter = Chapter(
        family_id=keeper.family_id,
        title_en=body.title_en,
        sort_order=max_order + 1,
    )
    session.add(chapter)
    session.commit()
    session.refresh(chapter)
    return chapter


@router.delete("/chapters/{chapter_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chapter(
    chapter_id: uuid.UUID,
    keeper: Keeper = Depends(get_current_keeper),
    session: Session = Depends(get_session),
) -> None:
    chapter = session.get(Chapter, chapter_id)
    if chapter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found")
    if chapter.family_id != keeper.family_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    # Move assigned stories to uncategorised
    stories = session.exec(select(Story).where(Story.chapter_id == chapter_id)).all()
    for story in stories:
        story.chapter_id = None
        session.add(story)
    session.delete(chapter)
    session.commit()

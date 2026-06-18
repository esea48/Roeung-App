from datetime import timedelta

import pytest
from fastapi import HTTPException
from sqlmodel import Session

from app.api.keepers import (
    archive_story,
    link_people_mention,
    lock_story,
    ping_story_lock,
    publish_story,
    unpublish_story,
)
from app.models import AIPeopleMention, FamilyMember, KeeperLock, Story, StoryTag
from app.models.common import utcnow
from app.models.enums import MentionResolutionStatus, StoryStatus, TaggedBy
from app.schemas.keepers import PeopleLinkRequest, PublishRequest


# ---------------------------------------------------------------------------
# Locking
# ---------------------------------------------------------------------------


def test_lock_story_creates_lock_and_claims_awaiting_review(session: Session, keeper, story: Story):
    lock = lock_story(story.id, keeper=keeper, session=session)

    assert lock.story_id == story.id
    assert lock.keeper_id == keeper.id
    assert lock.released_at is None
    assert lock.expires_at > utcnow()

    session.refresh(story)
    assert story.status == StoryStatus.in_review


def test_lock_story_refresh_by_same_keeper_extends_expiry(session: Session, keeper, story: Story):
    first = lock_story(story.id, keeper=keeper, session=session)
    original_expiry = first.expires_at

    # Simulate time passing before the keeper re-opens the story.
    first.expires_at = utcnow() + timedelta(minutes=1)
    session.add(first)
    session.commit()

    second = lock_story(story.id, keeper=keeper, session=session)

    assert second.keeper_id == keeper.id
    assert second.expires_at > original_expiry - timedelta(minutes=9)
    assert second.expires_at > utcnow() + timedelta(minutes=9)


def test_lock_story_conflict_for_other_keeper_active_lock(session: Session, keeper, other_keeper, story: Story):
    lock_story(story.id, keeper=other_keeper, session=session)

    with pytest.raises(HTTPException) as exc_info:
        lock_story(story.id, keeper=keeper, session=session)

    assert exc_info.value.status_code == 409


def test_lock_story_succeeds_after_expired_lock(session: Session, keeper, other_keeper, story: Story):
    expired = KeeperLock(
        story_id=story.id,
        keeper_id=other_keeper.id,
        locked_at=utcnow() - timedelta(minutes=20),
        expires_at=utcnow() - timedelta(minutes=10),
    )
    session.add(expired)
    session.commit()

    lock = lock_story(story.id, keeper=keeper, session=session)

    assert lock.keeper_id == keeper.id
    assert lock.expires_at > utcnow()


def test_lock_story_succeeds_after_released_lock(session: Session, keeper, other_keeper, story: Story):
    released = KeeperLock(
        story_id=story.id,
        keeper_id=other_keeper.id,
        locked_at=utcnow() - timedelta(minutes=5),
        expires_at=utcnow() + timedelta(minutes=5),
        released_at=utcnow(),
    )
    session.add(released)
    session.commit()

    lock = lock_story(story.id, keeper=keeper, session=session)

    assert lock.keeper_id == keeper.id
    assert lock.released_at is None


# ---------------------------------------------------------------------------
# Ping / heartbeat
# ---------------------------------------------------------------------------


def test_ping_extends_lock_expiry(session: Session, keeper, story: Story):
    lock = lock_story(story.id, keeper=keeper, session=session)
    lock.expires_at = utcnow() + timedelta(minutes=1)
    session.add(lock)
    session.commit()

    refreshed = ping_story_lock(story.id, release=False, keeper=keeper, session=session)

    assert refreshed.expires_at > utcnow() + timedelta(minutes=9)
    assert refreshed.released_at is None


def test_ping_release_sets_released_at(session: Session, keeper, story: Story):
    lock_story(story.id, keeper=keeper, session=session)

    refreshed = ping_story_lock(story.id, release=True, keeper=keeper, session=session)

    assert refreshed.released_at is not None


def test_ping_without_lock_raises_404(session: Session, keeper, story: Story):
    with pytest.raises(HTTPException) as exc_info:
        ping_story_lock(story.id, release=False, keeper=keeper, session=session)

    assert exc_info.value.status_code == 404


def test_ping_with_other_keepers_lock_raises_404(session: Session, keeper, other_keeper, story: Story):
    lock_story(story.id, keeper=other_keeper, session=session)

    with pytest.raises(HTTPException) as exc_info:
        ping_story_lock(story.id, release=False, keeper=keeper, session=session)

    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Publish / archive / unpublish status transitions
# ---------------------------------------------------------------------------


def test_publish_requires_in_review(session: Session, keeper, story: Story):
    assert story.status == StoryStatus.awaiting_review

    with pytest.raises(HTTPException) as exc_info:
        publish_story(story.id, PublishRequest(), keeper=keeper, session=session)

    assert exc_info.value.status_code == 409


def test_publish_from_in_review_succeeds(session: Session, keeper, story: Story):
    story.status = StoryStatus.in_review
    session.add(story)
    session.commit()

    result = publish_story(story.id, PublishRequest(), keeper=keeper, session=session)

    assert result.status == StoryStatus.published
    assert result.published_at is not None
    assert result.published_by == keeper.id


def test_publish_with_flag_sets_translation_flagged(session: Session, keeper, story: Story):
    story.status = StoryStatus.in_review
    session.add(story)
    session.commit()

    result = publish_story(story.id, PublishRequest(translation_flagged=True), keeper=keeper, session=session)

    assert result.status == StoryStatus.published
    assert result.translation_flagged is True


def test_publish_already_published_raises_409(session: Session, keeper, story: Story):
    story.status = StoryStatus.published
    session.add(story)
    session.commit()

    with pytest.raises(HTTPException) as exc_info:
        publish_story(story.id, PublishRequest(), keeper=keeper, session=session)

    assert exc_info.value.status_code == 409


def test_archive_from_in_review_succeeds(session: Session, keeper, story: Story):
    story.status = StoryStatus.in_review
    session.add(story)
    session.commit()

    result = archive_story(story.id, keeper=keeper, session=session)

    assert result.status == StoryStatus.archived
    assert result.archived_at is not None
    assert result.archived_by == keeper.id


def test_archive_from_published_succeeds(session: Session, keeper, story: Story):
    story.status = StoryStatus.published
    session.add(story)
    session.commit()

    result = archive_story(story.id, keeper=keeper, session=session)

    assert result.status == StoryStatus.archived


def test_archive_from_awaiting_review_raises_409(session: Session, keeper, story: Story):
    assert story.status == StoryStatus.awaiting_review

    with pytest.raises(HTTPException) as exc_info:
        archive_story(story.id, keeper=keeper, session=session)

    assert exc_info.value.status_code == 409


def test_unpublish_from_published_returns_to_in_review(session: Session, keeper, story: Story):
    story.status = StoryStatus.published
    story.published_at = utcnow()
    story.published_by = keeper.id
    session.add(story)
    session.commit()

    result = unpublish_story(story.id, keeper=keeper, session=session)

    assert result.status == StoryStatus.in_review
    assert result.published_at is None
    assert result.published_by is None


def test_unpublish_from_in_review_raises_409(session: Session, keeper, story: Story):
    story.status = StoryStatus.in_review
    session.add(story)
    session.commit()

    with pytest.raises(HTTPException) as exc_info:
        unpublish_story(story.id, keeper=keeper, session=session)

    assert exc_info.value.status_code == 409


# ---------------------------------------------------------------------------
# People linking (invariant #3: atomic story_tags write)
# ---------------------------------------------------------------------------


def test_link_people_mention_creates_story_tag(session: Session, keeper, family, story: Story):
    member = FamilyMember(family_id=family.id, name_en="Grandfather Sokha")
    session.add(member)
    mention = AIPeopleMention(story_id=story.id, name_raw="Ta Sokha")
    session.add(mention)
    session.commit()
    session.refresh(member)
    session.refresh(mention)

    result = link_people_mention(
        story.id, mention.id, PeopleLinkRequest(family_member_id=member.id), keeper=keeper, session=session
    )

    assert result.resolution_status == MentionResolutionStatus.linked
    assert result.family_member_id == member.id
    assert result.resolved_by == keeper.id

    from sqlmodel import select

    tag = session.exec(
        select(StoryTag).where(StoryTag.story_id == story.id, StoryTag.family_member_id == member.id)
    ).first()
    assert tag is not None
    assert tag.tagged_by == TaggedBy.keeper
    assert tag.name_raw == "Grandfather Sokha"


def test_link_people_mention_unknown_family_member_raises_400(session: Session, keeper, story: Story):
    import uuid

    mention = AIPeopleMention(story_id=story.id, name_raw="Ta Sokha")
    session.add(mention)
    session.commit()
    session.refresh(mention)

    with pytest.raises(HTTPException) as exc_info:
        link_people_mention(
            story.id, mention.id, PeopleLinkRequest(family_member_id=uuid.uuid4()), keeper=keeper, session=session
        )

    assert exc_info.value.status_code == 400

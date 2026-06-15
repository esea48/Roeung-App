import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlmodel import Session

from app.api.book import get_book, get_chapter_stories, get_story, get_uncategorised_stories
from app.models import Chapter, Family, FamilyMember, Story, StoryTag, TranscriptSegment, TranslationSegment
from app.models.enums import CaptureMethod, DeceasedDatePrecision, Language, StoryStatus, TaggedBy


def _make_story(
    session: Session,
    family: Family,
    *,
    status: StoryStatus = StoryStatus.published,
    published_at: datetime | None = None,
    chapter_id: uuid.UUID | None = None,
    chapter_sort_order: int | None = None,
    title_en: str = "A Story",
) -> Story:
    story = Story(
        family_id=family.id,
        status=status,
        capture_method=CaptureMethod.recorded,
        narrator_name_raw="Grandmother Sea",
        consent_given_at=datetime.now(timezone.utc),
        consent_wording_key="v1_recorded",
        submitted_at=datetime.now(timezone.utc),
        title_en=title_en,
        chapter_id=chapter_id,
        chapter_sort_order=chapter_sort_order,
        published_at=published_at,
    )
    session.add(story)
    session.commit()
    session.refresh(story)
    return story


@pytest.fixture()
def chapter(session: Session, family: Family) -> Chapter:
    chapter = Chapter(family_id=family.id, title_en="Life Before the War", sort_order=1)
    session.add(chapter)
    session.commit()
    session.refresh(chapter)
    return chapter


# ---------------------------------------------------------------------------
# GET /f/{access_token}/book
# ---------------------------------------------------------------------------


def test_get_book_returns_chapters_and_recent_published_stories(session: Session, family: Family, chapter: Chapter):
    now = datetime.now(timezone.utc)
    published = _make_story(session, family, published_at=now, chapter_id=chapter.id)
    _make_story(session, family, status=StoryStatus.in_review, published_at=None)

    result = get_book(family=family, session=session)

    assert [c.id for c in result.chapters] == [chapter.id]
    assert [s.id for s in result.recent_stories] == [published.id]


def test_get_book_recent_stories_limited_to_five_and_newest_first(session: Session, family: Family):
    now = datetime.now(timezone.utc)
    stories = [
        _make_story(session, family, published_at=now - timedelta(days=i), title_en=f"Story {i}")
        for i in range(6)
    ]

    result = get_book(family=family, session=session)

    assert len(result.recent_stories) == 5
    assert result.recent_stories[0].id == stories[0].id  # most recently published


# ---------------------------------------------------------------------------
# GET /f/{access_token}/chapters/{id}/stories
# ---------------------------------------------------------------------------


def test_get_chapter_stories_only_returns_published_in_that_chapter(
    session: Session, family: Family, chapter: Chapter
):
    now = datetime.now(timezone.utc)
    in_chapter = _make_story(session, family, published_at=now, chapter_id=chapter.id)
    _make_story(session, family, status=StoryStatus.in_review, chapter_id=chapter.id)
    _make_story(session, family, published_at=now, chapter_id=None)

    result = get_chapter_stories(chapter.id, sort="newest", family=family, session=session)

    assert [s.id for s in result] == [in_chapter.id]


def test_get_chapter_stories_sort_chronological_uses_chapter_sort_order(
    session: Session, family: Family, chapter: Chapter
):
    now = datetime.now(timezone.utc)
    second = _make_story(session, family, published_at=now, chapter_id=chapter.id, chapter_sort_order=2)
    first = _make_story(session, family, published_at=now, chapter_id=chapter.id, chapter_sort_order=1)

    result = get_chapter_stories(chapter.id, sort="chronological", family=family, session=session)

    assert [s.id for s in result] == [first.id, second.id]


def test_get_chapter_stories_unknown_chapter_raises_404(session: Session, family: Family):
    with pytest.raises(HTTPException) as exc_info:
        get_chapter_stories(uuid.uuid4(), sort="newest", family=family, session=session)

    assert exc_info.value.status_code == 404


def test_get_chapter_stories_wrong_family_raises_404(session: Session, family: Family):
    other_family = Family(name="Other Family", slug="other-family", access_token="other-token")
    session.add(other_family)
    session.commit()
    session.refresh(other_family)

    other_chapter = Chapter(family_id=other_family.id, title_en="Other Chapter", sort_order=1)
    session.add(other_chapter)
    session.commit()
    session.refresh(other_chapter)

    with pytest.raises(HTTPException) as exc_info:
        get_chapter_stories(other_chapter.id, sort="newest", family=family, session=session)

    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# GET /f/{access_token}/book/uncategorised
# ---------------------------------------------------------------------------


def test_get_uncategorised_stories_returns_only_published_without_chapter(
    session: Session, family: Family, chapter: Chapter
):
    now = datetime.now(timezone.utc)
    uncategorised = _make_story(session, family, published_at=now, chapter_id=None)
    _make_story(session, family, published_at=now, chapter_id=chapter.id)
    _make_story(session, family, status=StoryStatus.in_review, chapter_id=None)

    result = get_uncategorised_stories(sort="newest", family=family, session=session)

    assert [s.id for s in result] == [uncategorised.id]


# ---------------------------------------------------------------------------
# GET /f/{access_token}/stories/{id}
# ---------------------------------------------------------------------------


def test_get_story_returns_segments_and_tags(session: Session, family: Family):
    story = _make_story(session, family, published_at=datetime.now(timezone.utc))

    transcript = TranscriptSegment(
        story_id=story.id,
        language=Language.kh,
        segment_index=0,
        start_ms=0,
        end_ms=1000,
        original_text="original kh",
        edited_text="edited kh",
    )
    session.add(transcript)
    session.commit()
    session.refresh(transcript)

    translation = TranslationSegment(
        story_id=story.id,
        transcript_segment_id=transcript.id,
        source_language=Language.kh,
        target_language=Language.en,
        segment_index=0,
        original_text="original en",
    )
    session.add(translation)

    member = FamilyMember(
        family_id=family.id,
        name_en="Grandfather Sokha",
        name_kh="௰",
        is_deceased=True,
        deceased_date_precision=DeceasedDatePrecision.year,
    )
    session.add(member)
    session.commit()
    session.refresh(member)

    session.add(
        StoryTag(story_id=story.id, family_member_id=member.id, name_raw="Grandfather Sokha", tagged_by=TaggedBy.keeper)
    )
    session.add(StoryTag(story_id=story.id, family_member_id=None, name_raw="Someone Else", tagged_by=TaggedBy.recorder))
    session.commit()

    result = get_story(story.id, family=family, session=session)

    assert result.id == story.id
    assert len(result.transcript_segments) == 1
    assert result.transcript_segments[0].text == "edited kh"  # edited_text preferred over original_text
    assert len(result.translation_segments) == 1
    assert result.translation_segments[0].text == "original en"  # falls back to original_text

    tag_by_name = {t.name_raw: t for t in result.tags}
    assert tag_by_name["Grandfather Sokha"].is_deceased is True
    assert tag_by_name["Grandfather Sokha"].name_en == "Grandfather Sokha"
    assert tag_by_name["Someone Else"].family_member_id is None


def test_get_story_not_published_raises_404(session: Session, family: Family):
    story = _make_story(session, family, status=StoryStatus.in_review, published_at=None)

    with pytest.raises(HTTPException) as exc_info:
        get_story(story.id, family=family, session=session)

    assert exc_info.value.status_code == 404


def test_get_story_wrong_family_raises_404(session: Session, family: Family):
    other_family = Family(name="Other Family", slug="other-family", access_token="other-token")
    session.add(other_family)
    session.commit()
    session.refresh(other_family)

    story = _make_story(session, other_family, published_at=datetime.now(timezone.utc))

    with pytest.raises(HTTPException) as exc_info:
        get_story(story.id, family=family, session=session)

    assert exc_info.value.status_code == 404

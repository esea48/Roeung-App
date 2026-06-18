"""Seed script — run once to populate dev/test data for the Sea family.

Usage:
    cd backend && source venv/bin/activate && python seed.py
"""

import uuid
from datetime import datetime, timezone

import bcrypt
from sqlmodel import Session, select, text

from app.db import engine
from app.models import FamilyMember, Keeper, Story
from app.models.enums import (
    CaptureMethod,
    DeceasedDatePrecision,
    LanguageDetected,
    StoryStatus,
)

FAMILY_ID = uuid.UUID("a30846e1-4b6f-4b02-8598-3075a736d5f5")
CHAPTER_IDS = {
    "before_war": uuid.UUID("2aab4df5-6873-4001-a453-1e24fb3f9f39"),
    "khmer_rouge": uuid.UUID("3844c9bc-33e2-4194-bd76-21c9fa279496"),
    "migration": uuid.UUID("6a4258b5-6e82-4913-8cab-14225bcb2498"),
}
CONSENT_KEY = "v1_recorded_en"

def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def seed_family_members(session: Session) -> dict[str, uuid.UUID]:
    members = [
        FamilyMember(
            family_id=FAMILY_ID,
            name_en="Grandfather Sokha",
            name_kh="ជីតា សុខា",
            is_deceased=True,
            deceased_date=None,
            deceased_date_precision=DeceasedDatePrecision.year,
            birth_year=1932,
        ),
        FamilyMember(
            family_id=FAMILY_ID,
            name_en="Grandmother Chanthou",
            name_kh="យាយ ចន្ទូ",
            is_deceased=True,
            deceased_date=None,
            deceased_date_precision=DeceasedDatePrecision.year,
            birth_year=1938,
        ),
        FamilyMember(
            family_id=FAMILY_ID,
            name_en="Dad (Rith Sea)",
            name_kh="ប៉ា រិទ្ធ សី",
            is_deceased=False,
            birth_year=1962,
        ),
        FamilyMember(
            family_id=FAMILY_ID,
            name_en="Mom (Srey Sea)",
            name_kh="ម៉ាក់ ស្រី សី",
            is_deceased=False,
            birth_year=1965,
        ),
        FamilyMember(
            family_id=FAMILY_ID,
            name_en="Ellen Sea",
            name_kh="អេឡិន សី",
            is_deceased=False,
            birth_year=1990,
        ),
    ]
    ids = {}
    for m in members:
        session.add(m)
        session.flush()
        ids[m.name_en] = m.id
        print(f"  + family member: {m.name_en}")
    return ids


def seed_keeper(session: Session) -> uuid.UUID:
    pw_hash = bcrypt.hashpw(b"keeperpass123", bcrypt.gensalt()).decode()
    keeper = Keeper(
        family_id=FAMILY_ID,
        name="Ellen Sea",
        email="ellen.v.sea@gmail.com",
        password_hash=pw_hash,
        is_active=True,
    )
    session.add(keeper)
    session.flush()
    print(f"  + keeper: {keeper.email} (password: keeperpass123)")
    return keeper.id


def seed_stories(session: Session, keeper_id: uuid.UUID, member_ids: dict[str, uuid.UUID]):
    now = utcnow()
    stories = [
        # Published stories for Flow 4 (Book Reading)
        Story(
            family_id=FAMILY_ID,
            status=StoryStatus.published,
            capture_method=CaptureMethod.recorded,
            narrator_id=member_ids["Grandfather Sokha"],
            narrator_name_raw="Grandfather Sokha",
            consent_given_at=now,
            consent_wording_key=CONSENT_KEY,
            submitted_at=now,
            language_detected=LanguageDetected.kh,
            title_en="Life in the Rice Fields",
            title_kh="ជីវិតនៅក្នុងស្រែ",
            chapter_id=CHAPTER_IDS["before_war"],
            chapter_sort_order=1,
            published_at=now,
            published_by=keeper_id,
            translation_confidence_score=0.87,
        ),
        Story(
            family_id=FAMILY_ID,
            status=StoryStatus.published,
            capture_method=CaptureMethod.recorded,
            narrator_id=member_ids["Grandmother Chanthou"],
            narrator_name_raw="Grandmother Chanthou",
            consent_given_at=now,
            consent_wording_key=CONSENT_KEY,
            submitted_at=now,
            language_detected=LanguageDetected.kh,
            title_en="Our Wedding in Phnom Penh",
            title_kh="ពិធីមង្គលការរបស់យើងនៅភ្នំពេញ",
            chapter_id=CHAPTER_IDS["before_war"],
            chapter_sort_order=2,
            published_at=now,
            published_by=keeper_id,
            translation_confidence_score=0.91,
        ),
        Story(
            family_id=FAMILY_ID,
            status=StoryStatus.published,
            capture_method=CaptureMethod.uploaded,
            narrator_id=member_ids["Dad (Rith Sea)"],
            narrator_name_raw="Dad",
            consent_given_at=now,
            consent_wording_key=CONSENT_KEY,
            submitted_at=now,
            language_detected=LanguageDetected.mixed,
            title_en="The Day We Left Battambang",
            title_kh="ថ្ងៃដែលយើងចាកចេញពីបាត់ដំបង",
            chapter_id=CHAPTER_IDS["khmer_rouge"],
            chapter_sort_order=1,
            published_at=now,
            published_by=keeper_id,
            translation_confidence_score=0.74,
            translation_flagged=True,
        ),
        Story(
            family_id=FAMILY_ID,
            status=StoryStatus.published,
            capture_method=CaptureMethod.recorded,
            narrator_id=member_ids["Mom (Srey Sea)"],
            narrator_name_raw="Mom",
            consent_given_at=now,
            consent_wording_key=CONSENT_KEY,
            submitted_at=now,
            language_detected=LanguageDetected.kh,
            title_en="Arriving in America",
            title_kh="មកដល់អាមេរិក",
            chapter_id=CHAPTER_IDS["migration"],
            chapter_sort_order=1,
            published_at=now,
            published_by=keeper_id,
            translation_confidence_score=0.89,
        ),
        # One story awaiting Keeper review (Flow 3)
        Story(
            family_id=FAMILY_ID,
            status=StoryStatus.awaiting_review,
            capture_method=CaptureMethod.recorded,
            narrator_id=member_ids["Dad (Rith Sea)"],
            narrator_name_raw="Dad",
            consent_given_at=now,
            consent_wording_key=CONSENT_KEY,
            submitted_at=now,
            language_detected=LanguageDetected.kh,
            title_en="Learning to Drive in Long Beach",
            title_kh="រៀនបើកបរនៅឡុងប៊ីច",
            chapter_id=CHAPTER_IDS["migration"],
            chapter_sort_order=2,
            translation_confidence_score=0.82,
        ),
    ]
    for s in stories:
        session.add(s)
        session.flush()
        print(f"  + story [{s.status}]: {s.title_en}")


def main():
    print("Seeding Sea family dev data...")
    with Session(engine) as session:
        # Skip if already seeded
        existing = session.exec(
            select(FamilyMember).where(FamilyMember.family_id == FAMILY_ID)
        ).first()
        if existing:
            print("Family members already exist — skipping. Run with --force to re-seed.")
            return

        print("\nFamily members:")
        member_ids = seed_family_members(session)

        print("\nKeeper:")
        keeper_id = seed_keeper(session)

        print("\nStories:")
        seed_stories(session, keeper_id, member_ids)

        session.commit()
        print("\nDone.")
        print(f"\nFamily access token: UDo21SAbFXlh71shQIUui--MEgqYH5Rd4SeZzDrCHPE")
        print(f"Keeper login:        ellen.v.sea@gmail.com / keeperpass123")


if __name__ == "__main__":
    main()

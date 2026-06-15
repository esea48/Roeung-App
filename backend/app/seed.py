"""Seed data for the Sea family.

Run once on first deploy (and safe to re-run — every insert is
idempotent, checking for an existing row before writing).

Usage:
    python -m app.seed
"""

import os
import secrets

from dotenv import load_dotenv
from sqlmodel import Session, create_engine, select

from app.models import Chapter, ConsentWordingVersion, Family
from app.models.common import utcnow
from app.models.enums import CaptureMethod, Language

FAMILY_SLUG = "sea-family"
FAMILY_NAME = "Sea Family"

CHAPTERS = [
    # title_kh values are placeholders pending translation.
    {"sort_order": 1, "title_en": "Life Before the War", "title_kh": None},  # TODO: Khmer title
    {"sort_order": 2, "title_en": "The Khmer Rouge Period", "title_kh": None},  # TODO: Khmer title
    {"sort_order": 3, "title_en": "Migration & Resettlement", "title_kh": None},  # TODO: Khmer title
]

CONSENT_WORDINGS = [
    {
        "key": "v1_recorded_en",
        "capture_method": CaptureMethod.recorded,
        "language": Language.en,
        "text": (
            "We're about to record [Name]'s story. They have agreed to be "
            "recorded and for this story to be shared with the family."
        ),
    },
    {
        "key": "v1_recorded_kh",
        "capture_method": CaptureMethod.recorded,
        "language": Language.kh,
        # TODO: Khmer translation of the recorded-consent wording.
        "text": "",
    },
    {
        "key": "v1_uploaded_en",
        "capture_method": CaptureMethod.uploaded,
        "language": Language.en,
        "text": "The person in this recording agreed to have it shared with the family.",
    },
    {
        "key": "v1_uploaded_kh",
        "capture_method": CaptureMethod.uploaded,
        "language": Language.kh,
        # TODO: Khmer translation of the upload-consent wording.
        "text": "",
    },
]


def seed_family(session: Session) -> Family:
    family = session.exec(select(Family).where(Family.slug == FAMILY_SLUG)).first()
    if family is None:
        family = Family(
            name=FAMILY_NAME,
            slug=FAMILY_SLUG,
            access_token=secrets.token_urlsafe(32),
        )
        session.add(family)
        session.commit()
        session.refresh(family)
        print(f"Created family '{FAMILY_NAME}' with access_token={family.access_token}")
    else:
        print(f"Family '{FAMILY_NAME}' already exists (id={family.id})")
    return family


def seed_chapters(session: Session, family: Family) -> None:
    for chapter_data in CHAPTERS:
        existing = session.exec(
            select(Chapter).where(
                Chapter.family_id == family.id,
                Chapter.sort_order == chapter_data["sort_order"],
            )
        ).first()
        if existing is None:
            session.add(Chapter(family_id=family.id, **chapter_data))
            print(f"Created chapter: {chapter_data['title_en']}")
        else:
            print(f"Chapter already exists: {existing.title_en}")
    session.commit()


def seed_consent_wordings(session: Session) -> None:
    for wording in CONSENT_WORDINGS:
        existing = session.exec(
            select(ConsentWordingVersion).where(ConsentWordingVersion.key == wording["key"])
        ).first()
        if existing is None:
            session.add(ConsentWordingVersion(effective_from=utcnow(), **wording))
            print(f"Created consent wording: {wording['key']}")
        else:
            print(f"Consent wording already exists: {wording['key']}")
    session.commit()


def main() -> None:
    load_dotenv()
    database_url = os.environ["DATABASE_URL"]
    engine = create_engine(database_url)

    with Session(engine) as session:
        family = seed_family(session)
        seed_chapters(session, family)
        seed_consent_wordings(session)


if __name__ == "__main__":
    main()

"""SQLModel table definitions.

Every model is imported here so that `SQLModel.metadata` is fully
populated for Alembic autogenerate.
"""

from .ai_people_mentions import AIPeopleMention
from .audio_files import AudioFile
from .chapters import Chapter
from .consent import ConsentLog, ConsentWordingVersion
from .deletion_requests import DeletionRequest
from .families import Family
from .family_members import FamilyMember
from .family_relationships import FamilyRelationship
from .keeper_locks import KeeperLock
from .keepers import Keeper
from .segments import TranscriptSegment, TranslationSegment
from .stories import Story
from .story_tags import StoryTag
from .title_suggestions import TitleSuggestion

__all__ = [
    "AIPeopleMention",
    "AudioFile",
    "Chapter",
    "ConsentLog",
    "ConsentWordingVersion",
    "DeletionRequest",
    "Family",
    "FamilyMember",
    "FamilyRelationship",
    "Keeper",
    "KeeperLock",
    "Story",
    "StoryTag",
    "TitleSuggestion",
    "TranscriptSegment",
    "TranslationSegment",
]

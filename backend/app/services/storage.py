"""Supabase Storage interactions for story audio files.

Per CLAUDE.md invariant #4: audio objects are never overwritten. Each
story gets a single object keyed by its `story_id` (Phase 1 stores one
original per story); GDPR deletion removes the object and clears
`audio_files.storage_key` / `storage_url` rather than replacing it.
"""

import uuid
from typing import Optional

from supabase import Client, create_client

from app.core.config import get_settings


def _client() -> Client:
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def upload_audio_file(
    family_id: uuid.UUID,
    story_id: uuid.UUID,
    filename: str,
    content: bytes,
    content_type: Optional[str],
) -> str:
    """Upload the original audio file and return its storage key."""
    settings = get_settings()
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    storage_key = f"{family_id}/{story_id}/original.{extension}"

    file_options = {"content-type": content_type} if content_type else None
    _client().storage.from_(settings.supabase_storage_bucket).upload(
        storage_key, content, file_options
    )
    return storage_key


def delete_audio_file(storage_key: str) -> None:
    """Remove an audio object from storage (GDPR / pre-submission deletion)."""
    settings = get_settings()
    _client().storage.from_(settings.supabase_storage_bucket).remove([storage_key])

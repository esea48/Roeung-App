"""Supabase Storage interactions for story audio files.

Per CLAUDE.md invariant #4: audio objects are never overwritten. Each
story gets a single object keyed by its `story_id` (Phase 1 stores one
original per story); GDPR deletion removes the object and clears
`audio_files.storage_key` / `storage_url` rather than replacing it.
"""

import uuid
from typing import Optional

try:
    from supabase import Client, create_client
except ModuleNotFoundError:  # pragma: no cover - fallback for test environments without supabase
    class _StorageBucketStub:
        def upload(self, *args, **kwargs):
            raise ModuleNotFoundError(
                "supabase is required for storage uploads; install backend dependencies to use this module"
            )

        def remove(self, *args, **kwargs):
            raise ModuleNotFoundError(
                "supabase is required for storage deletes; install backend dependencies to use this module"
            )

        def create_signed_url(self, storage_key: str, expires_in: int):
            return {"signedURL": f"stub://{storage_key}?expires_in={expires_in}"}

        def download(self, *args, **kwargs):
            raise ModuleNotFoundError(
                "supabase is required for storage downloads; install backend dependencies to use this module"
            )

    class _StorageStub:
        def from_(self, bucket: str) -> _StorageBucketStub:  # noqa: D401
            return _StorageBucketStub()

    class _ClientStub:
        storage = _StorageStub()

    Client = _ClientStub  # type: ignore[assignment]

    def create_client(*args, **kwargs):  # type: ignore[no-redef]
        return _ClientStub()

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


def get_signed_url(storage_key: str, expires_in: int = 3600) -> str:
    """Return a time-limited signed URL for a private storage object."""
    settings = get_settings()
    response = _client().storage.from_(settings.supabase_storage_bucket).create_signed_url(
        storage_key, expires_in
    )
    return response["signedURL"]


def download_audio_file(storage_key: str) -> bytes:
    """Download an audio object's bytes (used by the AI pipeline)."""
    settings = get_settings()
    return _client().storage.from_(settings.supabase_storage_bucket).download(storage_key)

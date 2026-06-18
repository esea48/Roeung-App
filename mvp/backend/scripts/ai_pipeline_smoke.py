"""Staging smoke test for the audio -> transcript -> title pipeline.

Run this against a staging deployment with real external services.
The script:
- creates a submitted story through the family capture API,
- uploads a curated audio fixture,
- waits for the AI pipeline to reach `awaiting_review`,
- verifies the Keeper detail payload contains transcript rows and 3
  bilingual title options.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@dataclass(frozen=True)
class SmokeConfig:
    api_base_url: str
    family_access_token: str
    keeper_token: str
    audio_path: Path
    narrator_name: str
    recorder_name: str
    consent_wording_key: str
    timeout_seconds: int
    poll_interval_seconds: float


def _env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None or not value.strip():
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def load_config(args: argparse.Namespace) -> SmokeConfig:
    audio_path = Path(args.audio_path or _env("SMOKE_AUDIO_PATH")).expanduser()
    if not audio_path.exists():
        raise SystemExit(f"Audio fixture not found: {audio_path}")

    return SmokeConfig(
        api_base_url=args.api_base_url or _env("SMOKE_API_BASE_URL", "http://localhost:8000"),
        family_access_token=args.family_access_token or _env("SMOKE_FAMILY_ACCESS_TOKEN"),
        keeper_token=args.keeper_token or _env("SMOKE_KEEPER_TOKEN"),
        audio_path=audio_path,
        narrator_name=args.narrator_name or os.environ.get("SMOKE_NARRATOR_NAME", "Smoke Test Narrator"),
        recorder_name=args.recorder_name or os.environ.get("SMOKE_RECORDER_NAME", "Smoke Test"),
        consent_wording_key=os.environ.get("SMOKE_CONSENT_WORDING_KEY", "v1_uploaded"),
        timeout_seconds=args.timeout_seconds or int(os.environ.get("SMOKE_TIMEOUT_SECONDS", "600")),
        poll_interval_seconds=args.poll_interval_seconds or float(os.environ.get("SMOKE_POLL_INTERVAL_SECONDS", "5")),
    )


def create_story(client: httpx.Client, config: SmokeConfig) -> uuid.UUID:
    payload = {
        "capture_method": "uploaded",
        "narrator_name_raw": config.narrator_name,
        "recorder_name": config.recorder_name,
        "consent_wording_key": config.consent_wording_key,
    }
    response = client.post(f"/f/{config.family_access_token}/stories", json=payload)
    response.raise_for_status()
    return uuid.UUID(response.json()["id"])


def upload_audio(client: httpx.Client, config: SmokeConfig, story_id: uuid.UUID) -> None:
    with config.audio_path.open("rb") as handle:
        files = {"file": (config.audio_path.name, handle, "audio/wav")}
        response = client.post(f"/f/{config.family_access_token}/stories/{story_id}/audio", files=files)
    response.raise_for_status()


def wait_for_review(client: httpx.Client, config: SmokeConfig, story_id: uuid.UUID) -> dict:
    deadline = time.monotonic() + config.timeout_seconds
    last_payload: dict | None = None

    while time.monotonic() < deadline:
        response = client.get(f"/keeper/stories/{story_id}")
        response.raise_for_status()
        payload = response.json()
        last_payload = payload

        status = payload.get("status")
        if status == "awaiting_review":
            return payload
        if status == "rejected":
            raise SystemExit(f"Pipeline rejected the story: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        if payload.get("processing_error"):
            raise SystemExit(f"Pipeline failed: {payload['processing_error']}")

        print(f"Waiting for pipeline... status={status} step={payload.get('processing_step')}")
        time.sleep(config.poll_interval_seconds)

    raise SystemExit(
        "Timed out waiting for the story to reach awaiting_review.\n"
        f"Last payload: {json.dumps(last_payload or {}, ensure_ascii=False, indent=2)}"
    )


def assert_pipeline_payload(payload: dict) -> None:
    transcript_segments = payload.get("transcript_segments") or []
    title_suggestions = payload.get("title_suggestions") or []

    if len(transcript_segments) == 0:
        raise SystemExit("Expected transcript segments, found none")
    if len(title_suggestions) != 3:
        raise SystemExit(f"Expected 3 title suggestions, found {len(title_suggestions)}")
    if [item.get("suggestion_index") for item in title_suggestions] != [1, 2, 3]:
        raise SystemExit("Title suggestions were not returned in index order")

    missing = [
        item for item in title_suggestions if not item.get("title_en") or not item.get("title_kh")
    ]
    if missing:
        raise SystemExit(f"Missing bilingual title text: {json.dumps(missing, ensure_ascii=False, indent=2)}")


def run(config: SmokeConfig) -> dict:
    with httpx.Client(base_url=config.api_base_url, timeout=30) as client:
        story_id = create_story(client, config)
        upload_audio(client, config, story_id)
        payload = wait_for_review(client, config, story_id)
        assert_pipeline_payload(payload)
        return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-base-url", default=None)
    parser.add_argument("--family-access-token", default=None)
    parser.add_argument("--keeper-token", default=None)
    parser.add_argument("--audio-path", default=None)
    parser.add_argument("--narrator-name", default=None)
    parser.add_argument("--recorder-name", default=None)
    parser.add_argument("--timeout-seconds", type=int, default=None)
    parser.add_argument("--poll-interval-seconds", type=float, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config = load_config(args)

    with httpx.Client(
        base_url=config.api_base_url,
        timeout=30,
        headers={"Authorization": f"Bearer {config.keeper_token}"},
    ) as keeper_client:
        with httpx.Client(base_url=config.api_base_url, timeout=30) as family_client:
            story_id = create_story(family_client, config)
            upload_audio(family_client, config, story_id)
            payload = wait_for_review(keeper_client, config, story_id)
            assert_pipeline_payload(payload)

    print(
        json.dumps(
            {
                "status": payload.get("status"),
                "story_id": payload.get("id"),
                "title_suggestions": payload.get("title_suggestions"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

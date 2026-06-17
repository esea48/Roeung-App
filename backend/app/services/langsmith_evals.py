"""Curated Roeung LangSmith eval examples and dataset sync helpers."""

from __future__ import annotations

from typing import Any

from langsmith import Client

from app.services.langsmith import get_client

DATASET_NAME = "Roeung AI Eval v1"


def roeung_eval_examples() -> list[dict[str, Any]]:
    """Return a small, curated set of Roeung-specific eval cases."""
    return [
        {
            "inputs": {
                "task": "cultural_flag_review",
                "source_language": "kh",
                "target_language": "en",
                "source_text": "ទឹកឡើងមកភ្លាមៗ ដោយគ្មានការព្រមាន។",
            },
            "outputs": {
                "expected_cultural_flag": False,
                "expected_note_contains": "",
            },
            "metadata": {
                "case": "khmer_river_warning",
                "theme": "cultural_nuance",
            },
        },
        {
            "inputs": {
                "task": "cultural_flag_review",
                "source_language": "kh",
                "target_language": "en",
                "source_text": "វាជារឿងចាស់ៗ តែអាចបន្តបានតាមសម័យនីមួយៗ។",
            },
            "outputs": {
                "expected_cultural_flag": True,
                "expected_note_contains": "nuance",
            },
            "metadata": {
                "case": "idiom_with_context",
                "theme": "cultural_nuance",
            },
        },
        {
            "inputs": {
                "task": "title_generation",
                "source_language": "mixed",
                "source_text": "I remember the flood came at dawn, then we moved to the stilt house.",
            },
            "outputs": {
                "expected_title_shape": "3_bilingual_options",
            },
            "metadata": {
                "case": "title_from_flood_story",
                "theme": "titles",
            },
        },
        {
            "inputs": {
                "task": "people_flagging",
                "source_language": "mixed",
                "source_text": "Grandfather Sok talked with Aunt Maly and Uncle Rith.",
            },
            "outputs": {
                "expected_names": ["Grandfather Sok", "Aunt Maly", "Uncle Rith"],
            },
            "metadata": {
                "case": "family_names",
                "theme": "people",
            },
        },
        {
            "inputs": {
                "task": "keeper_ground_truth",
                "source_language": "kh",
                "source_text": "កាលពីឆ្នាំ ១៩៧៩ យើងរត់ទៅផ្ទះលើជើងសសរ។",
            },
            "outputs": {
                "expected_translation_edited": True,
                "expected_flagged": True,
            },
            "metadata": {
                "case": "keeper_edited_translation",
                "theme": "human_review",
            },
        },
    ]


def sync_dataset(client: Client | None = None, *, dataset_name: str = DATASET_NAME) -> dict[str, Any]:
    """Create or refresh the Roeung eval dataset in LangSmith."""
    client = client or get_client()
    if client is None:
        raise RuntimeError("LangSmith is disabled; set LANGSMITH_API_KEY and LANGSMITH_TRACING_V2=true")

    dataset = client.read_dataset(dataset_name=dataset_name) if client.has_dataset(dataset_name) else None
    if dataset is None:
        dataset = client.create_dataset(
            dataset_name=dataset_name,
            description="Curated Roeung cases for AI pipeline regression testing.",
            metadata={"project": "roeung", "version": "v1"},
        )

    examples = roeung_eval_examples()
    existing_examples = list(client.list_examples(dataset_id=dataset.id))
    if existing_examples:
        client.delete_examples([example.id for example in existing_examples])
    client.create_examples(dataset_id=dataset.id, examples=examples)
    return {
        "dataset_id": str(dataset.id),
        "dataset_name": dataset.name,
        "example_count": len(examples),
    }

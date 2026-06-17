from __future__ import annotations

from uuid import UUID

from app.services import langsmith as langsmith_service
from app.services.langsmith_evals import roeung_eval_examples, sync_dataset


def test_langsmith_helpers_are_noop_without_env(session, family, story):
    langsmith_service.get_client.cache_clear()
    assert langsmith_service.is_enabled() is False

    with langsmith_service.trace_pipeline_run(story) as run:
        assert run is None

    with langsmith_service.trace_pipeline_step(None, story, step="title_generation") as run:
        assert run is None

    langsmith_service.record_feedback(
        trace_id=story.id,
        key="keeper_story_update",
        value={"story_id": str(story.id)},
    )


def test_roeung_eval_examples_cover_the_expected_cases():
    examples = roeung_eval_examples()

    assert len(examples) == 5
    assert {example["metadata"]["case"] for example in examples} == {
        "khmer_river_warning",
        "idiom_with_context",
        "title_from_flood_story",
        "family_names",
        "keeper_edited_translation",
    }
    assert all("task" in example["inputs"] for example in examples)
    assert all(
        any(key.startswith("expected") for key in example["outputs"])
        for example in examples
    )


def test_sync_dataset_refreshes_existing_examples(monkeypatch):
    created: dict[str, object] = {}
    deleted: list[UUID] = []

    class FakeExample:
        def __init__(self, example_id: str):
            self.id = UUID(example_id)

    class FakeDataset:
        def __init__(self) -> None:
            self.id = UUID("00000000-0000-0000-0000-000000000123")
            self.name = "Roeung AI Eval v1"

    class FakeClient:
        def has_dataset(self, dataset_name: str) -> bool:
            return True

        def read_dataset(self, dataset_name: str):
            return FakeDataset()

        def list_examples(self, dataset_id):
            return [FakeExample("00000000-0000-0000-0000-000000000111")]

        def delete_examples(self, example_ids, *, hard_delete: bool = False):
            deleted.extend(example_ids)

        def create_examples(self, *, dataset_id, examples):
            created["dataset_id"] = dataset_id
            created["examples"] = examples

    result = sync_dataset(client=FakeClient())

    assert result["dataset_name"] == "Roeung AI Eval v1"
    assert result["example_count"] == 5
    assert deleted == [UUID("00000000-0000-0000-0000-000000000111")]
    assert created["dataset_id"] == UUID("00000000-0000-0000-0000-000000000123")
    assert len(created["examples"]) == 5

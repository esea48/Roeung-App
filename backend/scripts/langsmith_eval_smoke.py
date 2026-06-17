"""Seed Roeung's LangSmith eval dataset and print a small smoke-test summary."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.langsmith_evals import DATASET_NAME, roeung_eval_examples, sync_dataset


def _env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None or not value.strip():
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-name", default=None)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    dataset_name = args.dataset_name or os.environ.get("LANGSMITH_DATASET_NAME", DATASET_NAME)

    # Fail fast with a clear message if the LangSmith SDK is not configured.
    _env("LANGSMITH_API_KEY")
    _env("LANGSMITH_TRACING_V2")

    examples = roeung_eval_examples()
    summary = {
        "dataset_name": dataset_name,
        "example_count": len(examples),
        "case_names": [example["metadata"]["case"] for example in examples],
    }

    if args.dry_run:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    result = sync_dataset(dataset_name=dataset_name)
    summary.update(result)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

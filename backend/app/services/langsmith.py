"""Optional LangSmith observability helpers for Roeung's AI pipeline."""

from __future__ import annotations

import contextlib
import logging
import time
from functools import lru_cache
from typing import Any, Iterator
from uuid import UUID

from langsmith import Client, trace

from app.core.config import get_settings

logger = logging.getLogger(__name__)

ROOT_TRACE_NAME = "roeung.ai_pipeline"


def _story_id(story: Any) -> str:
    return str(getattr(story, "id"))


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def _truncate_text(text: str, limit: int = 2000) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"...[truncated {len(text) - limit} chars]"


def _base_enabled() -> bool:
    settings = get_settings()
    return bool(settings.langsmith_tracing_v2 and settings.langsmith_api_key)


def is_enabled() -> bool:
    return _base_enabled()


def project_name() -> str:
    settings = get_settings()
    return settings.langsmith_project_name.strip() or "roeung-ai"


@lru_cache
def get_client() -> Client | None:
    if not is_enabled():
        return None

    settings = get_settings()
    kwargs: dict[str, Any] = {"api_key": settings.langsmith_api_key}
    if settings.langsmith_api_url.strip():
        kwargs["api_url"] = settings.langsmith_api_url.strip()
    return Client(**kwargs)


def pipeline_inputs(story: Any) -> dict[str, Any]:
    return {
        "story_id": _story_id(story),
        "family_id": str(getattr(story, "family_id", "")),
        "status": _enum_value(getattr(story, "status", None)),
        "capture_method": _enum_value(getattr(story, "capture_method", None)),
        "audio_language": _enum_value(getattr(story, "audio_language", None)),
    }


def step_metadata(
    story: Any,
    *,
    step: str,
    model: str | None = None,
    source_language: str | None = None,
    target_language: str | None = None,
    processing_step: str | None = None,
    outcome: str | None = None,
    latency_ms: int | None = None,
    error_type: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "story_id": _story_id(story),
        "family_id": str(getattr(story, "family_id", "")),
        "step": step,
        "model": model,
        "source_language": source_language,
        "target_language": target_language,
        "processing_step": processing_step,
        "outcome": outcome,
        "latency_ms": latency_ms,
        "error_type": error_type,
    }
    if extra:
        metadata.update(extra)
    return {key: value for key, value in metadata.items() if value is not None}


@contextlib.contextmanager
def trace_pipeline_run(story: Any) -> Iterator[Any | None]:
    client = get_client()
    if client is None:
        yield None
        return

    with trace(
        ROOT_TRACE_NAME,
        run_type="chain",
        run_id=_story_id(story),
        project_name=project_name(),
        client=client,
        inputs=pipeline_inputs(story),
        metadata=step_metadata(
            story,
            step=ROOT_TRACE_NAME,
            processing_step=_enum_value(getattr(story, "processing_step", None)),
            outcome="started",
        ),
    ) as run:
        yield run


@contextlib.contextmanager
def trace_pipeline_step(
    parent_run: Any | None,
    story: Any,
    *,
    step: str,
    run_type: str = "tool",
    inputs: dict[str, Any] | None = None,
    model: str | None = None,
    source_language: str | None = None,
    target_language: str | None = None,
    processing_step: str | None = None,
) -> Iterator[Any | None]:
    client = get_client()
    if client is None or parent_run is None:
        yield None
        return

    with trace(
        step,
        run_type=run_type,
        parent=parent_run,
        project_name=project_name(),
        client=client,
        inputs=inputs or {},
        metadata=step_metadata(
            story,
            step=step,
            model=model,
            source_language=source_language,
            target_language=target_language,
            processing_step=processing_step,
            outcome="started",
        ),
    ) as run:
        yield run


def finish_run(
    run: Any | None,
    story: Any,
    *,
    step: str,
    outcome: str,
    outputs: dict[str, Any] | None = None,
    model: str | None = None,
    source_language: str | None = None,
    target_language: str | None = None,
    processing_step: str | None = None,
    error: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    if run is None:
        return

    metadata = step_metadata(
        story,
        step=step,
        model=model,
        source_language=source_language,
        target_language=target_language,
        processing_step=processing_step,
        outcome=outcome,
        latency_ms=(extra or {}).get("latency_ms"),
        error_type=(extra or {}).get("error_type"),
        extra=extra,
    )
    run.end(outputs=outputs, error=error, metadata=metadata)


def _feedback_client() -> Client | None:
    return get_client()


def record_feedback(
    *,
    trace_id: UUID | str,
    key: str,
    value: Any | None = None,
    score: float | int | bool | None = None,
    comment: str | None = None,
    source_info: dict[str, Any] | None = None,
) -> None:
    client = _feedback_client()
    if client is None:
        return

    try:
        client.create_feedback(
            trace_id=str(trace_id),
            key=key,
            value=value,
            score=score,
            comment=comment,
            source_info=source_info,
        )
    except Exception:
        logger.exception("LangSmith feedback logging failed for key=%s trace_id=%s", key, trace_id)


def traced_llm_json(
    parent_run: Any | None,
    story: Any,
    *,
    step: str,
    model: str,
    system: str,
    user: str,
    schema_hint: str,
    source_language: str | None = None,
    target_language: str | None = None,
    processing_step: str | None = None,
    inputs_preview: dict[str, Any] | None = None,
    call_fn: Any,
) -> dict[str, Any]:
    """Run a JSON-producing LLM call under a LangSmith span when enabled."""
    client = get_client()
    trace_inputs = inputs_preview or {
        "system": system,
        "user_preview": _truncate_text(user),
        "schema_hint": schema_hint,
    }
    if client is None or parent_run is None:
        return call_fn()

    started = time.perf_counter()
    with trace(
        step,
        run_type="llm",
        parent=parent_run,
        project_name=project_name(),
        client=client,
        inputs=trace_inputs,
        metadata=step_metadata(
            story,
            step=step,
            model=model,
            source_language=source_language,
            target_language=target_language,
            processing_step=processing_step,
            outcome="started",
        ),
    ) as run:
        try:
            result = call_fn()
        except Exception as exc:
            finish_run(
                run,
                story,
                step=step,
                outcome="error",
                model=model,
                source_language=source_language,
                target_language=target_language,
                processing_step=processing_step,
                error=str(exc),
                extra={
                    "latency_ms": int((time.perf_counter() - started) * 1000),
                    "error_type": type(exc).__name__,
                },
            )
            raise

        finish_run(
            run,
            story,
            step=step,
            outcome="success",
            outputs=result,
            model=model,
            source_language=source_language,
            target_language=target_language,
            processing_step=processing_step,
            extra={"latency_ms": int((time.perf_counter() - started) * 1000)},
        )
        return result

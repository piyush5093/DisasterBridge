"""
Shared upsert logic for writing normalized event dicts into the
`disaster_events` collection — used by gdacs_ingestion.py,
usgs_ingestion.py, and ndma_ingestion.py so the actual Motor/Beanie
persistence code exists in exactly one place. Each source module still
owns its own `normalize_*` function (the field-mapping logic genuinely
differs per source), and just calls `upsert_normalized_events` once
normalization is done.

This is also where Day 5's "data normalization pipeline" milestone
naturally extends: a scheduled task can call each source's fetch +
normalize step and funnel everything through this one upsert path.
"""

from datetime import datetime, timezone
from typing import Any

from app.models.disaster_event import DisasterEvent
from app.schemas.disaster_event import IngestionResult


async def upsert_normalized_events(
    source: str,
    normalized_list: list[dict[str, Any]],
    *,
    total_fetched: int,
    skipped: int = 0,
    errors: list[str] | None = None,
) -> IngestionResult:
    """
    Upsert already-normalized event dicts (as produced by a source's
    `normalize_feature`/`normalize_alert`) keyed on
    (source, external_event_id, episode_id) — matching DisasterEvent's
    unique index. Existing documents are updated in place; new natural
    keys are inserted. Safe to call repeatedly (idempotent).
    """
    result = IngestionResult(
        source=source, fetched=total_fetched, created=0, updated=0, skipped=skipped, errors=list(errors or [])
    )

    for normalized in normalized_list:
        existing = await DisasterEvent.find_one(
            DisasterEvent.source == normalized["source"],
            DisasterEvent.external_event_id == normalized["external_event_id"],
            DisasterEvent.episode_id == normalized["episode_id"],
        )

        if existing:
            for key, value in normalized.items():
                setattr(existing, key, value)
            existing.updated_at = datetime.now(timezone.utc)
            await existing.save()
            result.updated += 1
        else:
            await DisasterEvent(**normalized).insert()
            result.created += 1

    return result

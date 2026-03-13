from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from django.conf import settings
from django.utils import timezone
from ninja.errors import HttpError

from core.api.schemas import EventCaptureSchema
from core.tasks import process_event_batch_task


@dataclass(frozen=True)
class NormalizedEvent:
    distinct_id: str
    event_name: str
    properties: dict[str, Any]
    event_uuid: UUID
    timestamp: datetime


def _normalize_timestamp(timestamp: datetime | None) -> datetime:
    if timestamp is None:
        return timezone.now()

    if timezone.is_naive(timestamp):
        return timezone.make_aware(timestamp, timezone.get_current_timezone())

    return timestamp


def _normalize_event(event: EventCaptureSchema) -> NormalizedEvent:
    return NormalizedEvent(
        distinct_id=event.distinct_id,
        event_name=event.event_name,
        properties=event.properties,
        event_uuid=event.event_uuid or uuid4(),
        timestamp=_normalize_timestamp(event.sent_at),
    )


def _serialize_event(event: NormalizedEvent) -> dict[str, Any]:
    return {
        "distinct_id": event.distinct_id,
        "event_name": event.event_name,
        "properties": event.properties,
        "event_uuid": str(event.event_uuid),
        "timestamp": event.timestamp.isoformat(),
    }


def enqueue_events(events: list[EventCaptureSchema]) -> int:
    if not events:
        raise HttpError(400, "events must contain at least one event")

    if len(events) > settings.MAX_CAPTURE_BATCH_SIZE:
        raise HttpError(
            400,
            f"batch size exceeds maximum of {settings.MAX_CAPTURE_BATCH_SIZE} events",
        )

    normalized = [_normalize_event(event) for event in events]
    process_event_batch_task.delay([_serialize_event(event) for event in normalized])

    return len(normalized)

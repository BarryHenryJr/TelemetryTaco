from datetime import datetime
from typing import Any
from uuid import UUID

from ninja import ModelSchema, Schema
from pydantic import Field

from core.models import Event


class EventCaptureSchema(Schema):
    distinct_id: str
    event_name: str
    properties: dict[str, Any] = Field(default_factory=dict)
    event_uuid: UUID | None = None
    sent_at: datetime | None = None


class EventBatchCaptureSchema(Schema):
    events: list[EventCaptureSchema]


class EventResponseSchema(ModelSchema):
    uuid: str

    class Meta:
        model = Event
        fields = [
            "id",
            "distinct_id",
            "event_name",
            "properties",
            "timestamp",
            "uuid",
            "created_at",
        ]

    @staticmethod
    def resolve_uuid(obj: Event) -> str:
        return str(obj.uuid)


class StatusResponse(Schema):
    status: str = "ok"


class BatchStatusResponse(StatusResponse):
    accepted: int


class InsightDataPoint(Schema):
    time: str
    count: int


class HealthStatusResponse(Schema):
    status: str
    database: str
    cache: str

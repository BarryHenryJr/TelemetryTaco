from datetime import timedelta
from typing import Any

from django.conf import settings
from django.db.models import Count
from django.db.models.functions import TruncMinute
from django.utils import timezone
from django_ratelimit.decorators import ratelimit
from ninja import ModelSchema, Router, Schema

from core.models import Event
from core.tasks import process_event_task

router = Router()


class EventSchema(Schema):
    """Pydantic schema for event capture endpoint."""

    distinct_id: str
    event_name: str
    properties: dict[str, Any] = {}


class EventResponseSchema(ModelSchema):
    """Pydantic schema for event response using ModelSchema."""

    uuid: str  # Override UUIDField to serialize as string

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
        """Convert UUID to string for serialization."""
        return str(obj.uuid)


class StatusResponse(Schema):
    """Response schema for successful event capture."""

    status: str = "ok"


class InsightDataPoint(Schema):
    """Schema for a single insight data point."""

    time: str
    count: int


@router.post("/capture", response=StatusResponse)
@ratelimit(key="ip", rate="1000/h", method="POST", block=True)
def capture_event(request, event: EventSchema) -> StatusResponse:
    """
    Capture event endpoint.

    Accepts event data and offloads it to Celery for async processing.
    Returns immediately with 200 OK to ensure low latency.

    Rate limited to 1000 requests per hour per IP address to prevent abuse.
    """
    # Convert Pydantic model to dict for Celery task
    # Using model_dump() for Pydantic v2 compatibility (replaces deprecated dict())
    event_data = event.model_dump()

    # Offload to Celery task asynchronously
    process_event_task.delay(event_data)

    # Return immediately without waiting for DB write
    return StatusResponse(status="ok")


@router.get("/events", response=list[EventResponseSchema])
@ratelimit(
    key="ip",
    rate="1000000/h" if settings.DEBUG else "10000/h",  # Very high limit in development
    method="GET",
    block=True,
)
def list_events(request, limit: int = 100):
    """
    List recent events endpoint.

    Returns the most recent events ordered by timestamp (descending).

    Rate limited to 300 requests per hour per IP address.
    """
    events = Event.objects.order_by("-timestamp")[:limit]
    # Django Ninja's ModelSchema will handle serialization automatically
    # The resolve_uuid method will convert UUID to string
    return list(events)


@router.get("/insights", response=list[InsightDataPoint])
@ratelimit(key="ip", rate="300/h", method="GET", block=True)
def get_insights(request, lookback_minutes: int = 60):
    """
    Get event insights endpoint.

    Returns aggregated event counts grouped by minute for the specified lookback period.
    Uses database-level aggregation for optimal performance.

    Args:
        lookback_minutes: Number of minutes to look back from now (default: 60)

    Returns:
        List of data points with time (HH:MM format) and count

    Rate limited to 300 requests per hour per IP address.
    """
    # Calculate the cutoff time
    cutoff_time = timezone.now() - timedelta(minutes=lookback_minutes)

    # Database-level aggregation: group by minute and count events
    # This is optimized as it happens entirely in the database
    aggregated = (
        Event.objects.filter(timestamp__gte=cutoff_time)
        .annotate(minute=TruncMinute("timestamp"))
        .values("minute")
        .annotate(count=Count("id"))
        .order_by("minute")
    )

    # Format the results
    result = []
    for item in aggregated:
        # Format time as HH:MM
        time_str = item["minute"].strftime("%H:%M")
        result.append({"time": time_str, "count": item["count"]})

    return result

from datetime import datetime

from django.conf import settings
from django_ratelimit.decorators import ratelimit
from ninja import Router
from ninja.errors import HttpError

from core.api.schemas import (
    BatchStatusResponse,
    EventBatchCaptureSchema,
    EventCaptureSchema,
    EventResponseSchema,
    HealthStatusResponse,
    InsightDataPoint,
    StatusResponse,
)
from core.selectors.events import get_insights, list_recent_events
from core.services.health import get_liveness_status, get_readiness_status
from core.services.ingestion import enqueue_events

router = Router()


@router.post("/capture", response=StatusResponse)
@ratelimit(key="ip", rate=settings.RATE_LIMIT_CAPTURE_EVENT, method="POST", block=True)
def capture_event(request, event: EventCaptureSchema) -> StatusResponse:
    enqueue_events([event])
    return StatusResponse(status="ok")


@router.post("/capture/batch", response=BatchStatusResponse)
@ratelimit(key="ip", rate=settings.RATE_LIMIT_CAPTURE_EVENT, method="POST", block=True)
def capture_event_batch(request, payload: EventBatchCaptureSchema) -> BatchStatusResponse:
    accepted = enqueue_events(payload.events)
    return BatchStatusResponse(status="ok", accepted=accepted)


@router.get("/events", response=list[EventResponseSchema])
@ratelimit(key="ip", rate=settings.RATE_LIMIT_LIST_EVENTS, method="GET", block=True)
def list_events(request, limit: int = 100, before: datetime | None = None):
    if limit < 1:
        raise HttpError(400, "limit must be greater than zero")

    return list_recent_events(limit=limit, before=before)


@router.get("/insights", response=list[InsightDataPoint])
@ratelimit(key="ip", rate=settings.RATE_LIMIT_GET_INSIGHTS, method="GET", block=True)
def get_event_insights(request, lookback_minutes: int = 60):
    if lookback_minutes < 1:
        raise HttpError(400, "lookback_minutes must be greater than zero")

    return get_insights(lookback_minutes=lookback_minutes)


@router.get("/health/live", response=HealthStatusResponse)
def liveness(request) -> HealthStatusResponse:
    return get_liveness_status()


@router.get("/health/ready", response=HealthStatusResponse)
def readiness(request) -> HealthStatusResponse:
    return get_readiness_status()

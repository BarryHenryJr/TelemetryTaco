from datetime import datetime, timedelta

from django.conf import settings
from django.db.models import Count
from django.db.models.functions import TruncMinute
from django.utils import timezone

from core.models import Event


def list_recent_events(*, limit: int, before: datetime | None = None) -> list[Event]:
    bounded_limit = min(limit, settings.MAX_EVENTS_LIMIT)
    queryset = Event.objects.order_by("-timestamp", "-id")

    if before is not None:
        queryset = queryset.filter(timestamp__lt=before)

    return list(queryset[:bounded_limit])


def get_insights(*, lookback_minutes: int) -> list[dict[str, int | str]]:
    bounded_lookback = min(lookback_minutes, settings.MAX_INSIGHTS_LOOKBACK_MINUTES)
    cutoff_time = timezone.now() - timedelta(minutes=bounded_lookback)

    aggregated = (
        Event.objects.filter(timestamp__gte=cutoff_time)
        .annotate(minute=TruncMinute("timestamp"))
        .values("minute")
        .annotate(count=Count("id"))
        .order_by("minute")
    )

    return [
        {
            "time": item["minute"].strftime("%H:%M"),
            "count": item["count"],
        }
        for item in aggregated
    ]


def purge_expired_events(*, now: datetime | None = None) -> int:
    if settings.EVENT_RETENTION_DAYS <= 0:
        return 0

    cutoff_time = (now or timezone.now()) - timedelta(days=settings.EVENT_RETENTION_DAYS)
    deleted_count, _ = Event.objects.filter(timestamp__lt=cutoff_time).delete()
    return deleted_count

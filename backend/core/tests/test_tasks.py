from datetime import timedelta
from uuid import uuid4

import pytest
from django.utils import timezone

from core.models import Event
from core.tasks import process_event_batch_task, process_event_task


@pytest.mark.django_db
def test_process_event_batch_task_ignores_duplicate_event_uuids():
    event_uuid = str(uuid4())
    payload = [
        {
            "distinct_id": "user-123",
            "event_name": "page_view",
            "event_uuid": event_uuid,
            "timestamp": timezone.now().isoformat(),
        },
        {
            "distinct_id": "user-123",
            "event_name": "page_view",
            "event_uuid": event_uuid,
            "timestamp": (timezone.now() - timedelta(minutes=1)).isoformat(),
        },
    ]

    processed_count = process_event_batch_task.run(payload)

    assert processed_count == 2
    assert Event.objects.count() == 1


@pytest.mark.django_db
def test_process_event_task_persists_single_event():
    event_uuid = str(uuid4())

    processed_count = process_event_task.run(
        {
            "distinct_id": "user-456",
            "event_name": "checkout_success",
            "event_uuid": event_uuid,
            "properties": {"total": 42},
            "timestamp": timezone.now().isoformat(),
        }
    )

    assert processed_count == 1
    stored_event = Event.objects.get()
    assert stored_event.distinct_id == "user-456"
    assert stored_event.event_name == "checkout_success"
    assert stored_event.properties == {"total": 42}
    assert str(stored_event.uuid) == event_uuid

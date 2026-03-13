from datetime import timedelta
from uuid import uuid4

import pytest
from django.utils import timezone

from core.models import Event
from core.tasks import process_event_batch_task


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

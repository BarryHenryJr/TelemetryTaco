import json
from unittest.mock import patch

from telemetry_taco import TelemetryTaco
from telemetry_taco.client import QueuedEvent


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return None

    def read(self):
        return b"{}"


def test_sdk_flushes_batched_events():
    requests = []

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        return FakeResponse()

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        client = TelemetryTaco(flush_interval=60, batch_size=10)
        client.capture("user-1", "page_view", {"path": "/"})
        client.capture("user-2", "checkout_success", {"total": 42})
        client.flush(timeout=2)
        client.close(timeout=2)

    assert len(requests) == 1
    request, timeout = requests[0]
    payload = json.loads(request.data.decode("utf-8"))
    assert timeout == 5.0
    assert len(payload["events"]) == 2
    assert all("event_uuid" in event for event in payload["events"])
    assert all("sent_at" in event for event in payload["events"])


def test_sdk_drop_oldest_policy_replaces_existing_item():
    client = TelemetryTaco(max_queue_size=1, queue_full_policy="drop_oldest", _start_worker=False)
    client._queue.put(  # type: ignore[attr-defined]
        QueuedEvent(
            distinct_id="user-1",
            event_name="page_view",
            properties={},
            event_uuid="first",
            sent_at="2026-01-01T00:00:00+0000",
        )
    )

    client._enqueue(  # type: ignore[attr-defined]
        QueuedEvent(
            distinct_id="user-2",
            event_name="signup_clicked",
            properties={},
            event_uuid="second",
            sent_at="2026-01-01T00:00:01+0000",
        )
    )

    queued = client._queue.get_nowait()  # type: ignore[attr-defined]
    client._queue.task_done()  # type: ignore[attr-defined]

    assert isinstance(queued, QueuedEvent)
    assert queued.event_uuid == "second"

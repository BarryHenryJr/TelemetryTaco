import json
import logging
import queue
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

logger = logging.getLogger("telemetry_taco")

QueueFullPolicy = Literal["block", "drop_newest", "drop_oldest"]
_STOP = object()


@dataclass(frozen=True)
class QueuedEvent:
    distinct_id: str
    event_name: str
    properties: dict[str, Any]
    event_uuid: str
    sent_at: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "distinct_id": self.distinct_id,
            "event_name": self.event_name,
            "properties": self.properties,
            "event_uuid": self.event_uuid,
            "sent_at": self.sent_at,
        }


class TelemetryTaco:
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        *,
        batch_size: int = 50,
        flush_interval: float = 1.0,
        max_queue_size: int = 1000,
        request_timeout: float = 5.0,
        max_retries: int = 2,
        queue_full_policy: QueueFullPolicy = "drop_newest",
        _start_worker: bool = True,
    ):
        self.base_url = base_url.rstrip("/")
        self.batch_url = f"{self.base_url}/api/capture/batch"
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.request_timeout = request_timeout
        self.max_retries = max_retries
        self.queue_full_policy = queue_full_policy

        self._queue: queue.Queue[QueuedEvent | object] = queue.Queue(maxsize=max_queue_size)
        self._flush_requested = threading.Event()
        self._closed = False
        self._worker = None
        if _start_worker:
            self._worker = threading.Thread(
                target=self._run_worker,
                name="telemetry-taco-worker",
                daemon=True,
            )
            self._worker.start()

    def capture(
        self,
        distinct_id: str,
        event_name: str,
        properties: dict[str, Any] | None = None,
    ) -> None:
        if self._closed:
            raise RuntimeError("TelemetryTaco client is closed")

        payload = QueuedEvent(
            distinct_id=distinct_id,
            event_name=event_name,
            properties=properties or {},
            event_uuid=str(uuid4()),
            sent_at=datetime.now(timezone.utc).isoformat(),
        )
        self._enqueue(payload)

    def flush(self, timeout: float | None = None) -> None:
        deadline = None if timeout in (None, 0) else time.monotonic() + timeout
        self._flush_requested.set()

        while self._queue.unfinished_tasks:
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError(
                    f"Timeout waiting for {self._queue.unfinished_tasks} event(s) to flush."
                )
            time.sleep(0.05)

        self._flush_requested.clear()

    def close(self, timeout: float | None = None) -> None:
        if self._closed:
            return

        self.flush(timeout=timeout)
        self._closed = True
        self._queue.put(_STOP)
        if self._worker is not None:
            self._worker.join(timeout=timeout)

    def __enter__(self) -> "TelemetryTaco":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def _enqueue(self, payload: QueuedEvent) -> None:
        if self.queue_full_policy == "block":
            self._queue.put(payload, timeout=self.request_timeout)
            return

        try:
            self._queue.put_nowait(payload)
        except queue.Full:
            if self.queue_full_policy == "drop_oldest":
                dropped = self._queue.get_nowait()
                if dropped is not _STOP:
                    self._queue.task_done()
                self._queue.put_nowait(payload)
                logger.warning("TelemetryTaco queue full; dropped oldest event.")
                return

            logger.warning("TelemetryTaco queue full; dropped newest event.")

    def _run_worker(self) -> None:
        batch: list[QueuedEvent] = []
        last_flush = time.monotonic()

        while True:
            try:
                item = self._queue.get(timeout=0.1)
            except queue.Empty:
                item = None

            if item is _STOP:
                self._queue.task_done()
                self._flush_batch(batch)
                return

            if isinstance(item, QueuedEvent):
                batch.append(item)

            should_flush = (
                len(batch) >= self.batch_size
                or (batch and time.monotonic() - last_flush >= self.flush_interval)
                or (batch and self._flush_requested.is_set())
            )

            if should_flush:
                self._flush_batch(batch)
                batch = []
                last_flush = time.monotonic()

    def _flush_batch(self, batch: list[QueuedEvent]) -> None:
        if not batch:
            return

        try:
            self._send_batch(batch)
        finally:
            for _ in batch:
                self._queue.task_done()

    def _send_batch(self, batch: list[QueuedEvent]) -> None:
        payload = {"events": [event.as_dict() for event in batch]}
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.batch_url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Content-Length": str(len(body)),
            },
            method="POST",
        )

        for attempt in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.request_timeout) as response:
                    response.read()
                return
            except urllib.error.HTTPError as exc:
                if 400 <= exc.code < 500:
                    logger.error(
                        "TelemetryTaco rejected event batch: %s %s",
                        exc.code,
                        exc.reason,
                    )
                    return
                if attempt >= self.max_retries:
                    logger.error(
                        "TelemetryTaco server error after retries: %s %s",
                        exc.code,
                        exc.reason,
                    )
                    return
            except urllib.error.URLError as exc:
                if attempt >= self.max_retries:
                    logger.warning("TelemetryTaco network error after retries: %s", exc.reason)
                    return

            time.sleep(min(0.25 * (attempt + 1), 1.0))

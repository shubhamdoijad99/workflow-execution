"""Wakes paused workflow executions when their resume time arrives.

One coordinator waits until the next deadline. It does not hold a worker for
each sleep, and worker threads return as soon as a workflow is paused.
"""

from __future__ import annotations

import heapq
import logging
import threading
import time
from collections.abc import Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class ResumeScheduler:
    def __init__(self, on_resume: Callable[[str], None]) -> None:
        self._on_resume = on_resume
        self._heap: list[tuple[float, int, str]] = []
        self._sequence = 0
        self._closed = False
        self._condition = threading.Condition()
        self._thread = threading.Thread(
            target=self._loop,
            name="workflow-resume",
            daemon=True,
        )
        self._thread.start()

    def schedule(self, resume_at: datetime, execution_id: str) -> None:
        when = resume_at.timestamp()
        with self._condition:
            if self._closed:
                return
            self._sequence += 1
            heapq.heappush(self._heap, (when, self._sequence, execution_id))
            self._condition.notify()

    def close(self) -> None:
        with self._condition:
            self._closed = True
            self._condition.notify_all()
        self._thread.join(timeout=2)

    def _loop(self) -> None:
        while True:
            with self._condition:
                while True:
                    if self._closed:
                        return
                    if not self._heap:
                        self._condition.wait()
                        continue
                    when, _sequence, execution_id = self._heap[0]
                    delay = when - time.time()
                    if delay > 0:
                        self._condition.wait(timeout=delay)
                        continue
                    heapq.heappop(self._heap)
                    break
            self._fire(execution_id)

    def _fire(self, execution_id: str) -> None:
        try:
            self._on_resume(execution_id)
        except Exception:
            logger.exception("failed to resume execution %s", execution_id)

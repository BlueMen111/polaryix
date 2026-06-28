from __future__ import annotations

import itertools
import logging
import queue
import threading
from concurrent.futures import Future
from dataclasses import dataclass, field
from typing import Any, Callable

from app.core.config.settings import settings

logger = logging.getLogger("polaryix.conversion_queue")


@dataclass(order=True)
class QueuedJob:
    sort_key: tuple[int, int]
    future: Future = field(compare=False)
    function: Callable[..., Any] = field(compare=False)
    args: tuple[Any, ...] = field(compare=False, default_factory=tuple)
    kwargs: dict[str, Any] = field(compare=False, default_factory=dict)


_counter = itertools.count()
_queue: "queue.PriorityQueue[QueuedJob]" = queue.PriorityQueue()
_workers: list[threading.Thread] = []
_started = False
_lock = threading.Lock()


def start_conversion_workers() -> None:
    global _started
    with _lock:
        if _started:
            return

        worker_count = max(int(settings.conversion_workers), 1)
        for index in range(worker_count):
            worker = threading.Thread(target=_worker_loop, name=f"polaryix-conversion-worker-{index + 1}", daemon=True)
            worker.start()
            _workers.append(worker)

        _started = True
        logger.info("Started %s conversion workers.", worker_count)


def _worker_loop() -> None:
    while True:
        job = _queue.get()
        try:
            if not job.future.set_running_or_notify_cancel():
                continue
            result = job.function(*job.args, **job.kwargs)
            job.future.set_result(result)
        except Exception as exc:  # pragma: no cover - covered by callers receiving exceptions
            job.future.set_exception(exc)
        finally:
            _queue.task_done()


def submit_conversion_job(function: Callable[..., Any], *args: Any, priority_level: int = 0, **kwargs: Any) -> Future:
    start_conversion_workers()
    future: Future = Future()
    # PriorityQueue sorts ascending; negate priority so Pro(100) is before Basic(50), then free(0).
    job = QueuedJob(sort_key=(-int(priority_level), next(_counter)), future=future, function=function, args=args, kwargs=kwargs)
    _queue.put(job)
    return future

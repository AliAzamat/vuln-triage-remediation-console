"""A minimal reliable queue on Redis. Enqueue pushes a job id; the worker BLPOPs it
and moves it to a processing list so a crash mid-job doesn't silently lose it."""
from __future__ import annotations

import json
import os
from typing import Any, Optional

import redis

_r = redis.Redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
                          decode_responses=True)

QUEUE_KEY = "scans:queued"
PROCESSING_KEY = "scans:processing"


def enqueue(job: dict[str, Any]) -> None:
    """Push a job onto the queue. The job is just an id + minimal args; the
    authoritative record lives in Postgres (the scans row)."""
    _r.lpush(QUEUE_KEY, json.dumps(job))


def dequeue(timeout: int = 5) -> Optional[dict[str, Any]]:
    """Block up to `timeout`s for a job, atomically moving it to the processing
    list (reliable-queue pattern) so an in-flight job is recoverable after a crash."""
    raw = _r.brpoplpush(QUEUE_KEY, PROCESSING_KEY, timeout=timeout)
    return json.loads(raw) if raw else None


def ack(job: dict[str, Any]) -> None:
    """Remove the finished job from the processing list."""
    _r.lrem(PROCESSING_KEY, 1, json.dumps(job))

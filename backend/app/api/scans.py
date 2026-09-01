"""The scan API. POST /scans enqueues work and returns immediately — a scan can
take many minutes, so the request MUST NOT block on it."""
from __future__ import annotations

import uuid
from fastapi import APIRouter
from pydantic import BaseModel

from app.db.postgres import cursor
from app.queue import redis_queue

router = APIRouter(prefix="/scans", tags=["scans"])


class ScanRequest(BaseModel):
    repo_id: str
    scanner: str = "semgrep"
    prior_scan_id: str | None = None   # set to diff this run against a prior scan


@router.post("", status_code=202)
def create_scan(body: ScanRequest):
    scan_id = str(uuid.uuid4())
    with cursor() as cur:
        cur.execute(
            """
            INSERT INTO scans (id, repo_id, scanner, status, prior_scan_id)
            VALUES (%s, %s, %s, 'queued', %s)
            """,
            (scan_id, body.repo_id, body.scanner, body.prior_scan_id),
        )
    # Enqueue AFTER the row exists, so the worker always finds an authoritative record.
    redis_queue.enqueue({"scan_id": scan_id})
    # 202 Accepted: the scan exists and is queued, not finished.
    return {"scan_id": scan_id, "status": "queued"}

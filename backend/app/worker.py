"""The scan worker. Separate process from the API. It claims a job, runs the full
ingest->scan->fingerprint->persist pipeline, and advances the scan's status."""
from __future__ import annotations

import tempfile
from datetime import datetime, timezone

from app.db.postgres import cursor
from app.queue import redis_queue
from app.ingest import github_client
from app.repositories.findings import FindingRepo
from app.scanning.adapters.semgrep_adapter import SemgrepAdapter

findings_repo = FindingRepo()
ADAPTERS = {"semgrep": SemgrepAdapter()}


def _load_scan(scan_id: str) -> dict | None:
    with cursor() as cur:
        cur.execute(
            """
            SELECT s.id, s.repo_id, s.scanner, s.status,
                   r.owner, r.name, r.commit_sha
            FROM scans s JOIN repos r ON r.id = s.repo_id
            WHERE s.id = %s
            """,
            (scan_id,),
        )
        return cur.fetchone()


def _set_status(scan_id: str, status: str, error: str | None = None) -> None:
    now = datetime.now(timezone.utc)
    col = "started_at" if status == "running" else "finished_at"
    with cursor() as cur:
        cur.execute(
            f"UPDATE scans SET status=%s, error=%s, {col}=%s WHERE id=%s",
            (status, error, now, scan_id),
        )


def process(job: dict) -> None:
    scan_id = job["scan_id"]
    scan = _load_scan(scan_id)
    if scan is None:
        return  # row gone; nothing to do
    # IDEMPOTENT: if a redelivered job finds the scan already done, skip it. The
    # queue is at-least-once, so a job can legitimately arrive twice.
    if scan["status"] in ("done", "failed"):
        return

    _set_status(scan_id, "running")
    try:
        adapter = ADAPTERS[scan["scanner"]]
        with tempfile.TemporaryDirectory() as tmp:
            root = github_client.download_tree(
                scan["owner"], scan["name"], scan["commit_sha"], tmp
            )
            findings = adapter.scan(root)
        findings_repo.bulk_insert(scan_id, scan["repo_id"], findings)
        _set_status(scan_id, "done")
    except Exception as exc:  # one bad scan must not kill the worker loop
        _set_status(scan_id, "failed", error=str(exc)[:2000])


def run_forever() -> None:
    while True:
        job = redis_queue.dequeue(timeout=5)
        if job is None:
            continue
        try:
            process(job)
        finally:
            redis_queue.ack(job)


if __name__ == "__main__":
    run_forever()

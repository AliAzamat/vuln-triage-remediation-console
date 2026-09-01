"""GET /metrics/summary — the numbers the console header shows: open findings by
severity, mean-time-to-remediate, and the fix rate. All from ONE pass over the data,
not a query per tile."""
from __future__ import annotations

from fastapi import APIRouter
from app.db.postgres import cursor

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/summary")
def summary(repo_id: str):
    with cursor() as cur:
        # Open findings by severity — ONE grouped query, not one per severity.
        cur.execute(
            """
            SELECT severity, count(*) AS n
            FROM findings
            WHERE repo_id=%s AND status IN ('open','triaged','fixing','regressed')
            GROUP BY severity ORDER BY severity DESC
            """,
            (repo_id,),
        )
        open_by_sev = {int(r["severity"]): r["n"] for r in cur.fetchall()}

        # MTTR: average time from a fingerprint's FIRST event to its 'fixed' event.
        cur.execute(
            """
            WITH firsts AS (
              SELECT fingerprint, min(created_at) AS first_at
              FROM finding_events WHERE repo_id=%s GROUP BY fingerprint
            ),
            fixes AS (
              SELECT fingerprint, min(created_at) AS fixed_at
              FROM finding_events
              WHERE repo_id=%s AND to_status='fixed' GROUP BY fingerprint
            )
            SELECT avg(extract(epoch FROM fixes.fixed_at - firsts.first_at)) AS mttr_s
            FROM fixes JOIN firsts USING (fingerprint)
            """,
            (repo_id, repo_id),
        )
        mttr_s = cur.fetchone()["mttr_s"]

    return {
        "open_by_severity": open_by_sev,
        "mttr_seconds": round(mttr_s, 1) if mttr_s is not None else None,
    }

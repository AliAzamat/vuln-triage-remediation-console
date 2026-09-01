"""GET /scans/{id}/diff — run the diff against the scan's prior_scan_id and record
the PROVEN transitions as audit events. This is where 'fixed' finally gets written,
and only ever from evidence: a fingerprint that a fresh scan shows is gone."""
from __future__ import annotations

from fastapi import APIRouter

from app.db.postgres import cursor
from app.rerun.diff import compute_diff
from app.repositories.events import EventRepo
from app.services.errors import error_response

router = APIRouter(prefix="/scans", tags=["rerun"])
events = EventRepo()


@router.get("/{scan_id}/diff")
def scan_diff(scan_id: str):
    with cursor() as cur:
        cur.execute("SELECT repo_id, prior_scan_id FROM scans WHERE id=%s", (scan_id,))
        scan = cur.fetchone()
    if scan is None:
        return error_response(404, "not_found", "scan not found")
    if scan["prior_scan_id"] is None:
        return error_response(400, "no_prior", "scan has no prior scan to diff against")

    diff = compute_diff(scan["repo_id"], scan_id, scan["prior_scan_id"])

    # Record the PROVEN transitions. 'fixed' is written ONLY here, by evidence.
    # The actor is the system: the scan itself is the accountable party for a
    # machine-proven fact, distinct from a human's judgement call.
    for fp in diff.fixed:
        events.append(fingerprint=fp, repo_id=scan["repo_id"], finding_id=None,
                      from_status="fixing", to_status="fixed", actor="scan:" + scan_id,
                      reason="fingerprint absent in re-run")
    for fp in diff.regressed:
        events.append(fingerprint=fp, repo_id=scan["repo_id"], finding_id=None,
                      from_status="fixed", to_status="regressed", actor="scan:" + scan_id,
                      reason="previously-fixed fingerprint reappeared")

    return {
        "scan_id": scan_id,
        "prior_scan_id": scan["prior_scan_id"],
        "fixed": diff.fixed,
        "regressed": diff.regressed,
        "new": diff.new,
        "persistent": diff.persistent,
        "counts": {
            "fixed": len(diff.fixed), "regressed": len(diff.regressed),
            "new": len(diff.new), "persistent": len(diff.persistent),
        },
    }

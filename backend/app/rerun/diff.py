"""The payoff of the whole system: prove which findings a re-run fixed. We compare
the CURRENT scan's fingerprints against the PRIOR scan's, purely as set math. A
fingerprint present-then-absent is a proven fix; absent-then-present is a regression."""
from __future__ import annotations

from dataclasses import dataclass, field

from app.db.postgres import cursor


@dataclass
class ScanDiff:
    fixed: list[str] = field(default_factory=list)       # in prior, gone now  -> PROVEN fixed
    regressed: list[str] = field(default_factory=list)   # was fixed, back now -> regression
    persistent: list[str] = field(default_factory=list)  # in both scans       -> still open
    new: list[str] = field(default_factory=list)         # only in current     -> newly found


def _fingerprints(scan_id: str) -> set[str]:
    with cursor() as cur:
        cur.execute("SELECT fingerprint FROM findings WHERE scan_id=%s", (scan_id,))
        return {r["fingerprint"] for r in cur.fetchall()}


def _prior_fixed(repo_id: str) -> set[str]:
    """Fingerprints whose LATEST event marked them fixed — used to detect regressions
    (a fingerprint we proved fixed before that has reappeared in the current scan)."""
    with cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT ON (fingerprint) fingerprint, to_status
            FROM finding_events WHERE repo_id=%s
            ORDER BY fingerprint, created_at DESC
            """,
            (repo_id,),
        )
        return {r["fingerprint"] for r in cur.fetchall() if r["to_status"] == "fixed"}


def compute_diff(repo_id: str, current_scan: str, prior_scan: str) -> ScanDiff:
    cur_fps = _fingerprints(current_scan)
    prior_fps = _fingerprints(prior_scan)
    previously_fixed = _prior_fixed(repo_id)

    diff = ScanDiff()
    # Present in prior, absent now: the finding is gone -> a PROVEN fix.
    diff.fixed = sorted(prior_fps - cur_fps)
    # Present now, absent in prior: newly discovered this scan...
    fresh = cur_fps - prior_fps
    # ...but if we'd previously proven it fixed and it's back, that's a REGRESSION.
    diff.regressed = sorted(fp for fp in cur_fps if fp in previously_fixed)
    diff.new = sorted(fp for fp in fresh if fp not in previously_fixed)
    # In both scans: still there, still open.
    diff.persistent = sorted(cur_fps & prior_fps)
    return diff

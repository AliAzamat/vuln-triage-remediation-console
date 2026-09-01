"""The triage stage, now instrumented. Each triage is a span; the counter tracks
throughput. This is a NEW/CHANGED file this step — the triage loop is unchanged
except for the span wrapper and the counter increment."""
from __future__ import annotations

from app.db.postgres import cursor
from app.repositories.findings import FindingRepo
from app.triage import prompts
from app.triage.llm import triage_finding, SYSTEM_TRIAGE
from app.obs.tracing import span, findings_triaged

findings_repo = FindingRepo()

_PRIORITY_TO_STATUS = {"p0": "triaged", "p1": "triaged", "p2": "triaged",
                       "p3": "triaged", "needs_human": "open"}


def triage_scan(scan_id: str) -> int:
    with span("triage_scan", scan_id=scan_id):
        with cursor() as cur:
            cur.execute(
                "SELECT * FROM findings WHERE scan_id=%s AND triage IS NULL",
                (scan_id,),
            )
            rows = list(cur.fetchall())

        count = 0
        for f in rows:
            with span("triage_finding", finding_id=str(f["id"]), rule=f["rule_id"]):
                user = prompts.triage_user_prompt(f)
                result = triage_finding(SYSTEM_TRIAGE, user)
                findings_repo.set_triage(f["id"], result)
                findings_repo.set_status(f["id"], _PRIORITY_TO_STATUS[result["priority"]])
                findings_triaged.add(1, {"priority": result["priority"]})
            count += 1
        return count

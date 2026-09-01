from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from app.db.postgres import cursor


@dataclass
class Finding:
    fingerprint: str
    rule_id: str
    severity: int
    file_path: str
    start_line: int
    end_line: int
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)


class FindingRepo:
    def bulk_insert(self, scan_id: str, repo_id: str, findings: list[Finding]) -> list[dict]:
        """Insert a scan's findings. UNIQUE (scan_id, fingerprint) means a scanner
        that emits the same weakness twice collapses to one row per scan."""
        rows: list[dict] = []
        with cursor() as cur:
            for f in findings:
                cur.execute(
                    """
                    INSERT INTO findings
                      (id, scan_id, repo_id, fingerprint, rule_id, severity,
                       file_path, start_line, end_line, message, evidence)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                    ON CONFLICT (scan_id, fingerprint) DO NOTHING
                    RETURNING id, fingerprint
                    """,
                    (str(uuid.uuid4()), scan_id, repo_id, f.fingerprint, f.rule_id,
                     f.severity, f.file_path, f.start_line, f.end_line, f.message,
                     json.dumps(f.evidence)),
                )
                row = cur.fetchone()
                if row:
                    rows.append(row)
        return rows

    def set_triage(self, finding_id: str, triage: dict[str, Any]) -> None:
        with cursor() as cur:
            cur.execute(
                "UPDATE findings SET triage=%s::jsonb WHERE id=%s",
                (json.dumps(triage), finding_id),
            )

    def set_status(self, finding_id: str, status: str) -> None:
        # Cache the derived status on the row for fast list queries. The audit
        # log (finding_events) remains the source of truth.
        with cursor() as cur:
            cur.execute("UPDATE findings SET status=%s WHERE id=%s", (status, finding_id))

    def get(self, finding_id: str) -> Optional[dict]:
        with cursor() as cur:
            cur.execute("SELECT * FROM findings WHERE id=%s", (finding_id,))
            return cur.fetchone()

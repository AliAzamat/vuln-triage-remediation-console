from __future__ import annotations

import uuid
from typing import Optional

from app.db.postgres import cursor


class EventRepo:
    def append(
        self, *, fingerprint: str, repo_id: str, finding_id: Optional[str],
        from_status: Optional[str], to_status: str, actor: str, reason: str = "",
    ) -> None:
        """Append-only. A status change is a NEW immutable row, never an update."""
        with cursor() as cur:
            cur.execute(
                """
                INSERT INTO finding_events
                  (id, fingerprint, repo_id, finding_id, from_status, to_status, actor, reason)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (str(uuid.uuid4()), fingerprint, repo_id, finding_id,
                 from_status, to_status, actor, reason),
            )

    def current_status(self, fingerprint: str) -> Optional[str]:
        """Derive present status = the latest event's to_status for this fingerprint.
        Events are the truth; the cached findings.status is just a projection of this."""
        with cursor() as cur:
            cur.execute(
                """
                SELECT to_status FROM finding_events
                WHERE fingerprint=%s ORDER BY created_at DESC LIMIT 1
                """,
                (fingerprint,),
            )
            row = cur.fetchone()
        return row["to_status"] if row else None

    def history(self, fingerprint: str, limit: int = 100) -> list[dict]:
        with cursor() as cur:
            cur.execute(
                """
                SELECT from_status, to_status, actor, reason, created_at
                FROM finding_events WHERE fingerprint=%s
                ORDER BY created_at DESC LIMIT %s
                """,
                (fingerprint, limit),
            )
            return list(cur.fetchall())

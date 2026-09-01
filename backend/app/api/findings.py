"""The findings API: the triage queue (list), detail, and the status transition.
Status changes go through the state machine and are recorded as audit events."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.repositories.findings import FindingRepo
from app.repositories.events import EventRepo
from app.workflow.transitions import is_legal
from app.services.errors import error_response

router = APIRouter(prefix="/findings", tags=["findings"])
findings = FindingRepo()
events = EventRepo()


class StatusChange(BaseModel):
    to_status: str
    actor: str
    reason: str = ""


@router.post("/{finding_id}/status")
def change_status(finding_id: str, body: StatusChange):
    f = findings.get(finding_id)
    if f is None:
        return error_response(404, "not_found", "finding not found")

    # Derive the TRUE current status from the event log, not the cached column,
    # so two operators racing can't both transition from a stale value.
    current = events.current_status(f["fingerprint"]) or f["status"]
    if not is_legal(current, body.to_status):
        return error_response(
            409, "illegal_transition",
            f"cannot move {current} -> {body.to_status}",
        )

    # Append the immutable event FIRST (the source of truth), then refresh the
    # cached status column that lists read from.
    events.append(
        fingerprint=f["fingerprint"], repo_id=f["repo_id"], finding_id=finding_id,
        from_status=current, to_status=body.to_status, actor=body.actor, reason=body.reason,
    )
    findings.set_status(finding_id, body.to_status)
    return {"finding_id": finding_id, "from": current, "to": body.to_status}


@router.get("/{finding_id}")
def get_finding(finding_id: str):
    f = findings.get(finding_id)
    if f is None:
        return error_response(404, "not_found", "finding not found")
    return {
        "id": f["id"],
        "rule_id": f["rule_id"],
        "severity": f["severity"],
        "location": f"{f['file_path']}:{f['start_line']}-{f['end_line']}",
        "evidence": f["evidence"],
        "triage": f["triage"],
        "status": events.current_status(f["fingerprint"]) or f["status"],
        "history": events.history(f["fingerprint"]),
    }

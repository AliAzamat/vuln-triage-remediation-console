"""The finding status state machine. An operator can only make LEGAL moves — you
can't jump 'open -> fixed' without triaging, and 'fixed' is only claimed via the
re-run diff, never asserted by hand. Encoding this here keeps the API honest."""
from __future__ import annotations

# Human-driven transitions the status endpoint allows. Note what's ABSENT:
# nothing lets a human mark 'fixed' directly — that status is earned by a re-run
# that proves the finding is gone (next step), not asserted in a form.
LEGAL: dict[str, set[str]] = {
    "open":      {"triaged", "fixing", "wontfix"},
    "triaged":   {"fixing", "wontfix", "open"},
    "fixing":    {"wontfix", "open"},        # 'fixed' is NOT here on purpose
    "regressed": {"fixing", "wontfix", "open"},
    "wontfix":   {"open"},                    # reopen is always allowed
    "fixed":     {"open"},                    # a fixed finding can be reopened
}


def is_legal(from_status: str, to_status: str) -> bool:
    return to_status in LEGAL.get(from_status, set())

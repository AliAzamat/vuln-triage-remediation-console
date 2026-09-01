"""The scanner adapter contract. Every scanner (Semgrep, Bandit, a dependency
auditor) implements this, so the rest of the system speaks ONE finding shape and
never knows which tool produced a finding."""
from __future__ import annotations

from typing import Protocol

from app.repositories.findings import Finding


class ScannerAdapter(Protocol):
    name: str

    def scan(self, repo_root: str) -> list[Finding]:
        """Run the tool against repo_root and normalize its output into Findings.
        The adapter owns tool-specific parsing; callers see only Finding objects."""
        ...

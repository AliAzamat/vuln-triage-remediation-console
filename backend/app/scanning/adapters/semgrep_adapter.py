"""A concrete adapter over Semgrep's JSON output. It shells out to the tool, then
maps each raw result into a normalized Finding with a fingerprint."""
from __future__ import annotations

import json
import subprocess
import sys

from app.repositories.findings import Finding
from app.scanning.fingerprint import compute_fingerprint

# Semgrep severities -> our 0..4 integer scale, mapped once at the boundary.
_SEV = {"INFO": 0, "LOW": 1, "WARNING": 2, "ERROR": 3, "CRITICAL": 4}


class SemgrepAdapter:
    name = "semgrep"

    def scan(self, repo_root: str) -> list[Finding]:
        proc = subprocess.run(
            ["semgrep", "--config=auto", "--json", "--quiet", repo_root],
            capture_output=True, text=True, timeout=1800,
        )
        raw = json.loads(proc.stdout or "{}")
        return [self._to_finding(r, repo_root) for r in raw.get("results", [])]

    def _to_finding(self, r: dict, repo_root: str) -> Finding:
        extra = r.get("extra", {})
        # Relative path so the fingerprint doesn't depend on the temp checkout dir.
        rel = r["path"].replace(repo_root, "").lstrip("/")
        snippet = extra.get("lines", "")
        rule_id = r.get("check_id", "unknown")
        return Finding(
            fingerprint=compute_fingerprint(rule_id, rel, snippet),
            rule_id=rule_id,
            severity=_SEV.get(str(extra.get("severity", "WARNING")).upper(), 2),
            file_path=rel,
            start_line=r.get("start", {}).get("line", 0),
            end_line=r.get("end", {}).get("line", 0),
            message=extra.get("message", "")[:2000],
            evidence={
                "snippet": snippet,
                "cwe": extra.get("metadata", {}).get("cwe", []),
                "owasp": extra.get("metadata", {}).get("owasp", []),
                "fix": extra.get("fix"),
            },
        )


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        # Deterministic offline check of the normalizer + fingerprint.
        fp1 = compute_fingerprint("python.sqli", "app/db.py", 'q = "SELECT " + name')
        fp2 = compute_fingerprint("python.sqli", "app/db.py", 'q = "SELECT " + name  ')
        assert fp1 == fp2, "whitespace must not change the fingerprint"
        print("ok", fp1)

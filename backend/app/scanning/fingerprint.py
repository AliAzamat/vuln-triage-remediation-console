"""The dedup fingerprint: a stable identity for 'the same weakness' across scans.
Getting this right is what makes the re-run diff trustworthy."""
from __future__ import annotations

import hashlib
import re


def _normalize_snippet(code: str) -> str:
    """Collapse cosmetic churn so a fingerprint survives reformatting. We keep the
    STRUCTURE of the line (identifiers, calls) and drop whitespace + string/number
    literals, which change constantly without changing the weakness."""
    code = re.sub(r'"[^"]*"|\'[^\']*\'', "STR", code)   # string literals -> STR
    code = re.sub(r"\b\d+\b", "NUM", code)               # number literals -> NUM
    code = re.sub(r"\s+", " ", code).strip()             # whitespace -> single space
    return code


def compute_fingerprint(rule_id: str, file_path: str, code_snippet: str) -> str:
    """Fingerprint = hash(rule, file, normalized code). Deliberately NOT the line
    number: inserting an import above the finding shifts lines but not the weakness.
    A real fix CHANGES the snippet (and thus the fingerprint); reformatting does not."""
    basis = f"{rule_id}\x00{file_path}\x00{_normalize_snippet(code_snippet)}"
    return hashlib.sha256(basis.encode()).hexdigest()[:32]

"""LLM client for triage. Low temperature + strict JSON parse + schema validation.
An unparseable or off-contract response FAILS CLOSED to needs_human — a triage
assistant that can't be trusted defers to a person rather than guessing."""
from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI

_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
TRIAGE_MODEL = "gpt-4o"

_ALLOWED_PRIORITY = {"p0", "p1", "p2", "p3", "needs_human"}
_ALLOWED_EXPLOIT = {"high", "medium", "low", "unknown"}


def _fail_closed(reason: str) -> dict[str, Any]:
    """When we can't trust the model, defer to a human. Never fabricate a verdict."""
    return {
        "explanation": "Automated triage could not produce a reliable result.",
        "priority": "needs_human",
        "exploitability": "unknown",
        "remediation": "",
        "reasoning": reason,
    }


def _validate(obj: Any) -> dict[str, Any]:
    """Enforce the contract. A missing key or an out-of-set value fails closed."""
    if not isinstance(obj, dict):
        return _fail_closed("model output was not an object")
    if obj.get("priority") not in _ALLOWED_PRIORITY:
        return _fail_closed("priority not in the allowed set")
    if obj.get("exploitability") not in _ALLOWED_EXPLOIT:
        return _fail_closed("exploitability not in the allowed set")
    for key in ("explanation", "remediation", "reasoning"):
        if not isinstance(obj.get(key), str):
            return _fail_closed(f"{key} missing or not a string")
    return obj


def triage_finding(system: str, user: str) -> dict[str, Any]:
    resp = _client.chat.completions.create(
        model=TRIAGE_MODEL,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        temperature=0.1,                       # low = stable, auditable triage
        response_format={"type": "json_object"},
    )
    text = resp.choices[0].message.content or ""
    try:
        return _validate(json.loads(text))
    except json.JSONDecodeError:
        return _fail_closed("model returned unparseable JSON")
